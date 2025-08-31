import psycopg2
from psycopg2.extras import execute_values
import random
from datetime import datetime, timedelta
import hashlib


def setup_citus_cluster():
    conn = psycopg2.connect(
        "dbname=postgres user=postgres password=mypass host=localhost port=5432"
    )
    cur = conn.cursor()

    cur.execute("SELECT * FROM master_get_active_worker_nodes();")
    print("Active workers:", cur.fetchall())

    # Drop tables if they exist
    cur.execute("DROP TABLE IF EXISTS messages, room_members, rooms CASCADE;")

    # Execute init.sql to create tables
    with open('init.sql', 'r') as f:
        init_sql = f.read()
        cur.execute(init_sql)

    # Create distributed tables with room_id as sharding key for co-location
    # Configuration (shard_count=4, shard_replication_factor=2) is set in docker-compose
    cur.execute("SELECT create_distributed_table('rooms', 'id');")
    cur.execute("SELECT create_distributed_table('room_members', 'room_id');")
    cur.execute("SELECT create_distributed_table('messages', 'room_id');")

    print("✅ Tables created with active-active replication")

    # Insert sample rooms data (100 rooms with better distribution)
    # Use specific ranges to ensure distribution across all 4 shards
    
    rooms_data = []
    room_ids = []
    
    # Define shard ranges based on Citus hash distribution
    shard_ranges = [
        (-2147483648, -1073741825),  # Shard 1 range
        (-1073741824, -1),           # Shard 2 range  
        (0, 1073741823),             # Shard 3 range
        (1073741824, 2147483647)     # Shard 4 range
    ]
    
    # Generate 25 rooms per shard to ensure even distribution
    for shard_idx, (min_val, max_val) in enumerate(shard_ranges):
        for i in range(25):  # 25 rooms per shard = 100 total
            # Generate room ID within this shard's range
            range_size = max_val - min_val
            room_id = min_val + (i * (range_size // 25)) + random.randint(0, range_size // 100)
            room_ids.append(room_id)
            rooms_data.append((
                room_id, 
                random.choice([1, 2, 3]), 
                datetime.now(), 
                datetime.now()
            ))
    
    execute_values(
        cur, 
        "INSERT INTO rooms (id, room_type, created_at, updated_at) VALUES %s", 
        rooms_data
    )

    # Insert sample room members data - exactly 2 members per room (chat parties)
    room_members_data = []
    member_id_counter = 1
    for room_id in room_ids:
        # Each room has exactly 2 members (the two parties having the chat)
        for party in range(2):
            room_members_data.append((
                member_id_counter,
                room_id,
                random.randint(1000, 9999),  # member_id (unique user ID)
                random.choice([True, False]),  # is_pinned
                False,  # is_deleted
                random.choice([True, False]),  # is_muted
                False,  # is_archived
                False,  # is_locked
                datetime.now(),
                datetime.now()
            ))
            member_id_counter += 1

    execute_values(
        cur,
        """INSERT INTO room_members 
           (id, room_id, member_id, is_pinned, is_deleted, is_muted, is_archived, is_locked, created_at, updated_at) 
           VALUES %s""",
        room_members_data
    )

    # Insert sample messages data - exactly 5 messages per room
    messages_data = []
    message_id_counter = 1
    for room_id in room_ids:
        # Each room has exactly 5 messages (total = 100 rooms * 5 messages = 500 messages)
        for msg_num in range(5):
            timestamp = datetime.now() - timedelta(hours=random.randint(1, 168))  # Last week
            messages_data.append((
                message_id_counter,
                room_id,
                random.choice([1, 2, 3]),  # message_type
                f"Chat message {msg_num + 1} in room {room_id}",
                random.choice([True, False]),  # is_by_partner (alternating between the two parties)
                timestamp,
                timestamp,
                random.choice([1, 2, 3]),  # status
                False,  # is_deleted
                None,  # action
                None,  # parent_message_id
                timestamp,
                timestamp
            ))
            message_id_counter += 1

    execute_values(
        cur,
        """INSERT INTO messages 
           (id, room_id, message_type, text, is_by_partner, local_timestamp, 
            server_timestamp, status, is_deleted, action, parent_message_id, created_at, updated_at) 
           VALUES %s""",
        messages_data
    )

    # Show shard distribution across all chat tables
    cur.execute(
        """
        SELECT 
            s.logicalrelid::text as table_name,
            s.shardid, 
            n.nodename, 
            n.nodeport,
            COUNT(*) as placement_count
        FROM pg_dist_placement p 
        JOIN pg_dist_shard s ON p.shardid = s.shardid 
        JOIN pg_dist_node n ON p.groupid = n.groupid
        WHERE s.logicalrelid IN ('rooms'::regclass, 'room_members'::regclass, 'messages'::regclass)
        GROUP BY s.logicalrelid, s.shardid, n.nodename, n.nodeport
        ORDER BY s.logicalrelid, s.shardid;
        """
    )

    print("\nShard placements for chat tables:")
    for shard in cur.fetchall():
        print(f"Table: {shard[0]}, Shard {shard[1]} on {shard[2]}:{shard[3]} (placements: {shard[4]})")

    # Show record counts per shard for each table
    print("\n" + "="*80)
    print("DETAILED SHARD RECORD COUNTS")
    print("="*80)
    
    # Get shard record counts for each table
    tables = ['rooms', 'room_members', 'messages']
    for table in tables:
        print(f"\n📊 {table.upper()} TABLE:")
        print("-" * 50)
        
        if table == 'rooms':
            shard_key = 'id'
        else:
            shard_key = 'room_id'
        
        cur.execute(f"""
            SELECT 
                s.shardid,
                s.shardminvalue::bigint as min_val,
                s.shardmaxvalue::bigint as max_val,
                n.nodename,
                n.nodeport
            FROM pg_dist_shard s
            JOIN pg_dist_placement p ON s.shardid = p.shardid
            JOIN pg_dist_node n ON p.groupid = n.groupid
            WHERE s.logicalrelid = '{table}'::regclass
            ORDER BY s.shardid;
        """)
        
        shard_info = cur.fetchall()
        total_records = 0
        
        for shard_id, min_val, max_val, node_name, node_port in shard_info:
            # Count records in this shard range
            cur.execute(f"""
                SELECT count(*) 
                FROM {table} 
                WHERE {shard_key} >= {min_val} AND {shard_key} <= {max_val};
            """)
            record_count = cur.fetchone()[0]
            total_records += record_count
            
            print(f"  Shard {shard_id} ({node_name}:{node_port}): {record_count:,} records [range: {min_val}-{max_val}]")
        
        print(f"  TOTAL: {total_records:,} records")

    # Show co-location verification with sample data
    cur.execute(
        """
        SELECT 
            r.id as room_id,
            COUNT(DISTINCT rm.id) as member_count,
            COUNT(DISTINCT m.id) as message_count
        FROM rooms r
        LEFT JOIN room_members rm ON r.id = rm.room_id AND rm.is_deleted = false
        LEFT JOIN messages m ON r.id = m.room_id AND m.is_deleted = false
        GROUP BY r.id
        ORDER BY r.id
        LIMIT 10;
        """
    )

    print(f"\n📈 SAMPLE ROOM STATISTICS (first 10 rooms):")
    print("-" * 50)
    for row in cur.fetchall():
        print(f"Room {row[0]}: {row[1]} members, {row[2]} messages")

    # Show overall statistics
    cur.execute("SELECT COUNT(*) FROM rooms;")
    total_rooms = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM room_members;")
    total_members = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM messages;")
    total_messages = cur.fetchone()[0]

    print(f"\n🎯 OVERALL STATISTICS:")
    print("-" * 50)
    print(f"Total Rooms: {total_rooms:,}")
    print(f"Total Room Members: {total_members:,}")
    print(f"Total Messages: {total_messages:,}")
    print(f"Average Members per Room: {total_members/total_rooms:.1f}")
    print(f"Average Messages per Room: {total_messages/total_rooms:.1f}")

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    setup_citus_cluster()
