#!/usr/bin/env python3
import os, uuid, random
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

DSN = os.getenv("CITUS_DSN", "dbname=postgres user=postgres password=mypass host=localhost port=5432")

ROOMS = 10_000
MEMBERS_PER_ROOM = 2
MSGS_PER_ROOM = 1
BATCH = 5_000

TABLES = [("rooms", "id"), ("room_members", "room_id"), ("messages", "room_id")]

def chunked(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i+n]

def ensure_distributed(cur):
    cur.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_dist_partition WHERE logicalrelid = 'rooms'::regclass) THEN
        PERFORM create_distributed_table('rooms', 'id');
      END IF;

      IF NOT EXISTS (SELECT 1 FROM pg_dist_partition WHERE logicalrelid = 'room_members'::regclass) THEN
        PERFORM create_distributed_table('room_members', 'room_id', colocate_with => 'rooms');
      END IF;

      IF NOT EXISTS (SELECT 1 FROM pg_dist_partition WHERE logicalrelid = 'messages'::regclass) THEN
        PERFORM create_distributed_table('messages', 'room_id', colocate_with => 'rooms');
      END IF;
    END$$;
    """)

def truncate_tables(cur):
    cur.execute("TRUNCATE TABLE messages, room_members, rooms;")

def insert_data(cur):
    random.seed(42)
    now = datetime.now()

    # Rooms (10k)
    room_ids, rooms_rows = [], []
    for _ in range(ROOMS):
        rid = (uuid.uuid4().int % 1_000_000_000_000) + 1
        room_ids.append(rid)
        rooms_rows.append((rid, random.choice([1,2,3]), now, now))
    for batch in chunked(rooms_rows, BATCH):
        execute_values(cur, "INSERT INTO rooms (id, room_type, created_at, updated_at) VALUES %s", batch)
    print(f"Inserted rooms: {len(rooms_rows):,}")

    # Members (2 per room)
    members_rows = []
    for rid in room_ids:
        for local_member_id in (1, 2):
            members_rows.append((
                local_member_id, rid,
                random.randint(1000, 9999),
                False, False, random.choice([True, False]),
                False, False, now, now
            ))
    for batch in chunked(members_rows, BATCH):
        execute_values(cur, """
            INSERT INTO room_members
            (id, room_id, member_id, is_pinned, is_deleted, is_muted, is_archived, is_locked,
             created_at, updated_at)
            VALUES %s
        """, batch)
    print(f"Inserted room_members: {len(members_rows):,}")

    # Messages (1 per room)
    messages_rows = []
    for rid in room_ids:
        ts = now - timedelta(minutes=random.randint(0, 60*24*7))
        messages_rows.append((
            1, rid, random.choice([1,2,3]),
            f"Hello from room {rid}",
            random.choice([True, False]),
            ts, ts, random.choice([1,2,3]),
            False, None, None, ts, ts
        ))
    for batch in chunked(messages_rows, BATCH):
        execute_values(cur, """
            INSERT INTO messages
            (id, room_id, message_type, text, is_by_partner, local_timestamp,
             server_timestamp, status, is_deleted, action, parent_message_id,
             created_at, updated_at)
            VALUES %s
        """, batch)
    print(f"Inserted messages: {len(messages_rows):,}")

def rows_per_shard(cur):
    counts = {}
    for table, key in TABLES:
        cur.execute(f"""
            SELECT get_shard_id_for_distribution_column('{table}', {key}) AS shardid,
                   COUNT(*) AS rows
            FROM {table}
            GROUP BY 1
            ORDER BY 1;
        """)
        for shardid, rows in cur.fetchall():
            counts[(table, int(shardid))] = int(rows)
    return counts

def shard_placements(cur):
    placements = {}
    cur.execute("""
        SELECT s.logicalrelid::text AS tbl, s.shardid, n.nodename, n.nodeport
        FROM pg_dist_shard s
        JOIN pg_dist_placement p USING (shardid)
        JOIN pg_dist_node n ON p.groupid = n.groupid
        WHERE s.logicalrelid IN ('rooms'::regclass,'room_members'::regclass,'messages'::regclass)
        ORDER BY tbl, shardid, n.nodename, n.nodeport;
    """)
    for tbl, shardid, node, port in cur.fetchall():
        placements.setdefault((tbl, int(shardid)), []).append((node, int(port)))
    return placements

def shard_ranges(cur):
    ranges = {}
    cur.execute("""
        SELECT s.logicalrelid::text AS tbl, s.shardid, s.shardminvalue::text, s.shardmaxvalue::text
        FROM pg_dist_shard s
        WHERE s.logicalrelid IN ('rooms'::regclass,'room_members'::regclass,'messages'::regclass)
        ORDER BY tbl, shardid;
    """)
    for tbl, shardid, mn, mx in cur.fetchall():
        ranges[(tbl, int(shardid))] = (mn, mx)
    return ranges

def grouped_colocation(ranges):
    groups = {}
    for (tbl, sid), rng in ranges.items():
        groups.setdefault(rng, {}).setdefault(tbl, sid)
    ordered = []
    for idx, (rng, mapping) in enumerate(sorted(groups.items(), key=lambda x: x[0])):
        ordered.append((idx+1, mapping))  # (group_no, {'rooms':sid, 'room_members':sid, 'messages':sid})
    return ordered

def compute_primary_roles(groups, placements):
    """
    Decide a display 'Primary' per co-located group by taking the first placement of the group's
    ROOMS shard (lexicographically). Others are 'Replica'. Returns:
      - shard_role: { (table, shardid, 'node:port') : 'P'|'R' }
      - group_primary: { group_no : 'node:port' }
    """
    shard_role = {}
    group_primary = {}
    for gno, mapping in groups:
        rsid = mapping.get('rooms')
        if rsid is None:
            continue
        room_places = sorted(placements.get(('rooms', rsid), []))  # [(node,port),...]
        if not room_places:
            continue
        primary = f"{room_places[0][0]}:{room_places[0][1]}"
        group_primary[gno] = primary

        # mark roles for all shards in this group based on this primary
        for tbl, sid in mapping.items():
            for (n,p) in placements.get((tbl, sid), []):
                key = (tbl, sid, f"{n}:{p}")
                shard_role[key] = 'P' if f"{n}:{p}" == primary else 'R'
    return shard_role, group_primary

def print_rows_per_shard(counts, placements, shard_role):
    print("\n" + "="*92)
    print("📊 Rows per shard (per table) with roles".center(92))
    print("="*92)
    for table, _ in TABLES:
        print(f"\n{table.upper()}")
        print("-"*92)
        shard_ids = sorted({sid for (tbl, sid) in counts.keys() if tbl == table})
        if not shard_ids:
            print("  (no rows)")
            continue
        print(f"{'Shard ID':<10} {'Rows':>12}    Placements (Role)")
        print("-"*92)
        for sid in shard_ids:
            rows = counts.get((table, sid), 0)
            places = placements.get((table, sid), [])
            place_str = ", ".join(f"{n}:{p} [{shard_role.get((table, sid, f'{n}:{p}'),'?')}]" for (n,p) in places)
            print(f"{sid:<10} {rows:>12}    {place_str}")

def print_workers_ascii(counts, placements, shard_role):
    per_worker = {}
    for (table, sid), nodes in placements.items():
        for (n,p) in nodes:
            key = f"{n}:{p}"
            per_worker.setdefault(key, []).append((table, sid, counts.get((table, sid), 0), shard_role.get((table, sid, key), '?')))

    print("\n\n" + "📦 Shard Placement by Worker (P=Primary, R=Replica)".center(92))
    print("="*92)
    for w in sorted(per_worker.keys()):
        header = f"┌─ {w} " + "─"* (92 - len(w) - 5) + "┐"
        print(f"\n{header}")
        if not per_worker[w]:
            print("│ (no shard placements)".ljust(91) + "│")
        else:
            for table, sid, rows, role in sorted(per_worker[w], key=lambda x: (x[0], x[1])):
                label = f"{table}_{sid}  (rows: {rows})  [{role}]"
                print(("│ " + label).ljust(91) + "│")
        print("└" + "─"*90 + "┘")

def print_groups_ascii(groups, placements, counts, group_primary, shard_role):
    print("\n\n" + "🧩 Co-located Shard Groups (P=Primary, R=Replica)".center(92))
    print("="*92)
    for gno, mapping in groups:
        rooms = mapping.get('rooms'); rm = mapping.get('room_members'); msgs = mapping.get('messages')
        places = placements.get(('rooms', rooms), []) or placements.get(('room_members', rm), []) or placements.get(('messages', msgs), [])
        place_str = ", ".join(f"{n}:{p} [{'P' if f'{n}:{p}'==group_primary.get(gno) else 'R'}]" for (n,p) in places)
        print(f"\nGroup {gno}: placements → {place_str}")
        print(f"  rooms_#{rooms}           rows={counts.get(('rooms', rooms), 0)}")
        print(f"  room_members_#{rm}       rows={counts.get(('room_members', rm), 0)}")
        print(f"  messages_#{msgs}         rows={counts.get(('messages', msgs), 0)}")

def main():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()

    ensure_distributed(cur)
    truncate_tables(cur)
    conn.commit()

    insert_data(cur)
    conn.commit()

    counts      = rows_per_shard(cur)
    placements  = shard_placements(cur)
    ranges      = shard_ranges(cur)
    groups      = grouped_colocation(ranges)
    shard_role, group_primary = compute_primary_roles(groups, placements)

    print_rows_per_shard(counts, placements, shard_role)
    print_workers_ascii(counts, placements, shard_role)
    print_groups_ascii(groups, placements, counts, group_primary, shard_role)

    cur.close(); conn.close()
    print("\n✅ Done.")

if __name__ == "__main__":
    main()
