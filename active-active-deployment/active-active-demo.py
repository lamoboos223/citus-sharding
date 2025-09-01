#!/usr/bin/env python3
import os, uuid, random
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values
from collections import defaultdict

TABLES = [("rooms", "id"), ("room_members", "room_id"), ("messages", "room_id")]


# Two coordinators (Cluster A + Cluster B)
DSN_A = os.getenv(
    "CITUS_DSN_A",
    "dbname=postgres user=postgres password=mypass host=localhost port=5432",
)
DSN_B = os.getenv(
    "CITUS_DSN_B",
    "dbname=postgres user=postgres password=mypass host=localhost port=6432",
)

ROOMS_TOTAL = 10_000
MEMBERS_PER_ROOM = 2
MSGS_PER_ROOM = 1
BATCH = 5_000


def chunked(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


def prepare_cluster(cur):
    # Ensure Citus is available on the coordinator session
    cur.execute("CREATE EXTENSION IF NOT EXISTS citus;")

    # Session-level safety (your ALTER SYSTEM in citus-config.sql sets cluster defaults)
    cur.execute("SET citus.shard_count = 3;")
    cur.execute("SET citus.shard_replication_factor = 2;")

    # Distribute & colocate existing tables created by init.sql
    cur.execute(
        """
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_dist_partition
                     WHERE logicalrelid = 'rooms'::regclass) THEN
        PERFORM create_distributed_table('rooms', 'id');
      END IF;

      IF NOT EXISTS (SELECT 1 FROM pg_dist_partition
                     WHERE logicalrelid = 'room_members'::regclass) THEN
        PERFORM create_distributed_table('room_members', 'room_id', colocate_with => 'rooms');
      END IF;

      IF NOT EXISTS (SELECT 1 FROM pg_dist_partition
                     WHERE logicalrelid = 'messages'::regclass) THEN
        PERFORM create_distributed_table('messages', 'room_id', colocate_with => 'rooms');
      END IF;
    END$$;
    """
    )


def truncate_cluster(cur):
    cur.execute("TRUNCATE TABLE messages, room_members, rooms;")


def make_rows(n_rooms, seed):
    random.seed(seed)
    now = datetime.now()

    room_ids = []
    rooms_rows = []
    members_rows = []
    messages_rows = []

    for i in range(n_rooms):
        rid = (uuid.uuid4().int % 1_000_000_000_000) + 1
        room_ids.append(rid)
        rooms_rows.append((rid, random.choice([1, 2, 3]), now, now))

        # two members per room
        for local_member_id in (1, 2):
            members_rows.append(
                (
                    local_member_id,
                    rid,
                    random.randint(1000, 9999),
                    False,
                    False,
                    random.choice([True, False]),
                    False,
                    False,
                    now,
                    now,
                )
            )

        # one message per room
        ts = now - timedelta(minutes=random.randint(0, 60 * 24 * 7))
        messages_rows.append(
            (
                1,
                rid,
                random.choice([1, 2, 3]),
                f"Hello from room {rid}",
                random.choice([True, False]),
                ts,
                ts,
                random.choice([1, 2, 3]),
                False,
                None,
                None,
                ts,
                ts,
            )
        )

    return rooms_rows, members_rows, messages_rows


def bulk_insert(cur, rooms_rows, members_rows, messages_rows):
    for batch in chunked(rooms_rows, BATCH):
        execute_values(
            cur,
            "INSERT INTO rooms (id, room_type, created_at, updated_at) VALUES %s",
            batch,
        )
    for batch in chunked(members_rows, BATCH):
        execute_values(
            cur,
            """
          INSERT INTO room_members
          (id, room_id, member_id, is_pinned, is_deleted, is_muted, is_archived, is_locked,
           created_at, updated_at) VALUES %s
        """,
            batch,
        )
    for batch in chunked(messages_rows, BATCH):
        execute_values(
            cur,
            """
          INSERT INTO messages
          (id, room_id, message_type, text, is_by_partner, local_timestamp,
           server_timestamp, status, is_deleted, action, parent_message_id,
           created_at, updated_at) VALUES %s
        """,
            batch,
        )


def show_cluster(cur, label):
    ascii_shard_tables(cur, label)


def main():
    # Split exactly half of the rooms/messages to each cluster
    rooms_a = ROOMS_TOTAL // 2
    rooms_b = ROOMS_TOTAL - rooms_a

    conn_a = psycopg2.connect(DSN_A)
    cur_a = conn_a.cursor()
    conn_b = psycopg2.connect(DSN_B)
    cur_b = conn_b.cursor()

    # Prepare (tables, distribution) on both clusters
    prepare_cluster(cur_a)
    prepare_cluster(cur_b)
    truncate_cluster(cur_a)
    truncate_cluster(cur_b)
    conn_a.commit()
    conn_b.commit()

    # Generate rows
    rooms_rows_a, members_rows_a, messages_rows_a = make_rows(rooms_a, seed=123)
    rooms_rows_b, members_rows_b, messages_rows_b = make_rows(rooms_b, seed=456)

    # Insert into Cluster A
    bulk_insert(cur_a, rooms_rows_a, members_rows_a, messages_rows_a)
    conn_a.commit()
    print(
        f"Cluster A inserted: rooms={len(rooms_rows_a)}, members={len(members_rows_a)}, messages={len(messages_rows_a)}"
    )

    # Insert into Cluster B
    bulk_insert(cur_b, rooms_rows_b, members_rows_b, messages_rows_b)
    conn_b.commit()
    print(
        f"Cluster B inserted: rooms={len(rooms_rows_b)}, members={len(members_rows_b)}, messages={len(messages_rows_b)}"
    )

    # Show placements
    show_cluster(cur_a, "Cluster A")
    show_cluster(cur_b, "Cluster B")

    cur_a.close()
    conn_a.close()
    cur_b.close()
    conn_b.close()
    print(
        "\n✅ Done. (Total rooms=10k, members=20k, messages=10k across two clusters.)"
    )


def fetch_counts(cur):
    counts = {}
    for table, key in TABLES:
        cur.execute(
            f"""
            SELECT get_shard_id_for_distribution_column('{table}', {key}) AS shardid,
                   COUNT(*) AS rows
            FROM {table}
            GROUP BY 1
            ORDER BY 1;
        """
        )
        for sid, rows in cur.fetchall():
            counts[(table, int(sid))] = int(rows)
    return counts


def fetch_placements(cur):
    placements = defaultdict(list)
    cur.execute(
        """
        SELECT s.logicalrelid::text AS tbl, s.shardid, n.nodename, n.nodeport
        FROM pg_dist_shard s
        JOIN pg_dist_placement p USING (shardid)
        JOIN pg_dist_node n ON p.groupid = n.groupid
        WHERE s.logicalrelid IN ('rooms'::regclass,'room_members'::regclass,'messages'::regclass)
        ORDER BY tbl, shardid, n.nodename, n.nodeport;
    """
    )
    for tbl, sid, node, port in cur.fetchall():
        placements[(tbl, int(sid))].append((node, int(port)))
    return dict(placements)


def fetch_ranges(cur):
    ranges = {}
    cur.execute(
        """
        SELECT s.logicalrelid::text AS tbl, s.shardid, s.shardminvalue::text, s.shardmaxvalue::text
        FROM pg_dist_shard s
        WHERE s.logicalrelid IN ('rooms'::regclass,'room_members'::regclass,'messages'::regclass)
        ORDER BY tbl, shardid;
    """
    )
    for tbl, sid, mn, mx in cur.fetchall():
        ranges[(tbl, int(sid))] = (mn, mx)
    return ranges


def grouped_colocation(ranges):
    by_range = defaultdict(dict)
    for (tbl, sid), rng in ranges.items():
        by_range[rng][tbl] = sid
    ordered = []
    for idx, (rng, mapping) in enumerate(sorted(by_range.items(), key=lambda x: x[0])):
        ordered.append(
            (idx + 1, mapping)
        )  # e.g. (1, {'rooms':102008,'room_members':102012,'messages':102016})
    return ordered


def compute_display_roles(groups, placements):
    """
    Choose a display 'Primary' per co-located group from the group's ROOMS placements (lexicographically).
    Everything else is 'Replica'. Returns:
      - shard_role: { (table, shardid, 'node:port') : 'P'|'R' }
      - group_primary: { group_no : 'node:port' }
    """
    shard_role = {}
    group_primary = {}
    for gno, mapping in groups:
        rsid = mapping.get("rooms")
        if rsid is None:
            continue
        room_places = sorted(placements.get(("rooms", rsid), []))
        if not room_places:
            continue
        primary = f"{room_places[0][0]}:{room_places[0][1]}"
        group_primary[gno] = primary
        for tbl, sid in mapping.items():
            for n, p in placements.get((tbl, sid), []):
                key = (tbl, sid, f"{n}:{p}")
                shard_role[key] = "P" if f"{n}:{p}" == primary else "R"
    return shard_role, group_primary


def ascii_shard_tables(cur, cluster_label):
    counts = fetch_counts(cur)
    placements = fetch_placements(cur)
    ranges = fetch_ranges(cur)
    groups = grouped_colocation(ranges)
    shard_role, _ = compute_display_roles(groups, placements)

    print(
        f"\n===================== {cluster_label}: Shards & Placements ====================="
    )
    for table, _ in TABLES:
        print(f"\n{table.upper()}")
        print(
            "+----------+--------------+----------------------------------------------+"
        )
        print(
            "| Shard ID | Rows         | Placements (Role)                            |"
        )
        print(
            "+----------+--------------+----------------------------------------------+"
        )
        # collect all shard ids seen for this table (even if rowcount is 0)
        shard_ids = sorted([sid for (tbl, sid) in placements.keys() if tbl == table])
        for sid in shard_ids:
            rows = counts.get((table, sid), 0)
            place_list = placements.get((table, sid), [])
            place_str = ", ".join(
                f"{n}:{p} [{shard_role.get((table, sid, f'{n}:{p}'),'?')}]"
                for (n, p) in place_list
            )
            print(f"| {sid:<8} | {rows:>12} | {place_str:<44} |")
        print(
            "+----------+--------------+----------------------------------------------+"
        )


if __name__ == "__main__":
    main()
