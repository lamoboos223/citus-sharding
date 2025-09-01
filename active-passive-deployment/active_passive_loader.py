#!/usr/bin/env python3
import os, uuid, random, time
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

# Connect through HAProxy so you always hit the Patroni leader
DSN = os.getenv(
    "CITUS_DSN",
    "dbname=postgres user=postgres password=mypass host=localhost port=5000",
)

ROOMS = 10_000
BATCH = 5_000

# RF=2 => need at least 2 active workers
REQUIRED_WORKERS = 2
DEFAULT_NODES = (("worker1", 5432), ("worker2", 5432), ("worker3", 5432))


def chunked(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


def ensure_workers(cur, nodes=DEFAULT_NODES, wait_s=20):
    """Make sure Citus is installed, workers are registered, and active."""
    cur.execute("CREATE EXTENSION IF NOT EXISTS citus;")

    # Handle both column name variants across Citus versions
    cur.execute("SELECT * FROM citus_get_active_worker_nodes();")
    cols = [d.name.lower() for d in cur.description]

    def idx(options):
        for name in options:
            if name in cols:
                return cols.index(name)
        raise RuntimeError(f"Expected one of {options} in {cols}")

    i_name = idx(["node_name", "nodename"])
    i_port = idx(["node_port", "nodeport"])

    have = {(row[i_name], int(row[i_port])) for row in cur.fetchall()}

    # Add any missing workers
    for n, p in nodes:
        if (n, p) not in have:
            cur.execute("SELECT citus_add_node(%s,%s);", (n, p))
            print(f"Added worker: {n}:{p}")

    # Wait for enough active workers
    deadline = time.time() + wait_s
    last = -1
    while True:
        cur.execute("SELECT count(*) FROM citus_get_active_worker_nodes();")
        cnt = cur.fetchone()[0]
        if cnt != last:
            print(f"Active workers: {cnt}")
            last = cnt
        if cnt >= REQUIRED_WORKERS:
            break
        if time.time() > deadline:
            raise RuntimeError(
                f"Only {cnt} worker(s) active; need >= {REQUIRED_WORKERS} for RF=2"
            )
        time.sleep(1)


def prepare(cur):
    # Ensure workers first (so RF checks won't fail during distribution)
    ensure_workers(cur)

    # Session GUCs used when creating shards
    cur.execute("SET citus.shard_count = 3;")
    cur.execute("SET citus.shard_replication_factor = 2;")

    # Tables (per your schema; no FKs)
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS rooms (
      id BIGINT PRIMARY KEY,
      room_type SMALLINT NOT NULL,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS room_members (
      id BIGINT,
      room_id BIGINT NOT NULL,
      member_id BIGINT NOT NULL,
      is_pinned BOOLEAN DEFAULT FALSE,
      is_deleted BOOLEAN DEFAULT FALSE,
      is_muted BOOLEAN DEFAULT FALSE,
      is_archived BOOLEAN DEFAULT FALSE,
      is_locked BOOLEAN DEFAULT FALSE,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (id, room_id)
    );
    CREATE TABLE IF NOT EXISTS messages (
      id BIGINT,
      room_id BIGINT NOT NULL,
      message_type SMALLINT NOT NULL,
      text TEXT,
      is_by_partner BOOLEAN DEFAULT FALSE,
      local_timestamp TIMESTAMPTZ,
      server_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
      status SMALLINT,
      is_deleted BOOLEAN DEFAULT FALSE,
      action SMALLINT,
      parent_message_id BIGINT,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (id, room_id)
    );
    """
    )

    # Distribute & colocate by room_id (only if not already distributed)
    cur.execute(
        """
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_dist_partition WHERE logicalrelid='rooms'::regclass) THEN
        PERFORM create_distributed_table('rooms', 'id');
      END IF;
      IF NOT EXISTS (SELECT 1 FROM pg_dist_partition WHERE logicalrelid='room_members'::regclass) THEN
        PERFORM create_distributed_table('room_members', 'room_id', colocate_with => 'rooms');
      END IF;
      IF NOT EXISTS (SELECT 1 FROM pg_dist_partition WHERE logicalrelid='messages'::regclass) THEN
        PERFORM create_distributed_table('messages', 'room_id', colocate_with => 'rooms');
      END IF;
    END$$;
    """
    )


def load(cur):
    random.seed(42)
    now = datetime.now()

    # Rooms
    room_ids, rooms_rows = [], []
    for _ in range(ROOMS):
        rid = (uuid.uuid4().int % 1_000_000_000_000) + 1
        room_ids.append(rid)
        rooms_rows.append((rid, random.choice([1, 2, 3]), now, now))
    for batch in chunked(rooms_rows, BATCH):
        execute_values(
            cur,
            "INSERT INTO rooms (id, room_type, created_at, updated_at) VALUES %s",
            batch,
        )
    print(f"Inserted rooms: {len(rooms_rows):,}")

    # Room members (2 per room)
    members_rows = []
    for rid in room_ids:
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
    print(f"Inserted room_members: {len(members_rows):,}")

    # Messages (1 per room)
    messages_rows = []
    for rid in room_ids:
        ts = now - timedelta(minutes=random.randint(0, 10080))
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
    print(f"Inserted messages: {len(messages_rows):,}")


def main():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()

    prepare(cur)
    conn.commit()

    # Optional: start fresh each run
    cur.execute("TRUNCATE TABLE messages, room_members, rooms;")
    conn.commit()

    load(cur)
    conn.commit()

    cur.close()
    conn.close()
    print("\n✅ Done. Connect DBeaver to localhost:5000 (postgres/mypass).")


if __name__ == "__main__":
    main()
