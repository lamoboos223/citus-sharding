import psycopg2
import time
import threading


def check_citus_status():
    """Check Citus cluster configuration and active-active status"""
    
    print("🔍 CHECKING CITUS CLUSTER STATUS")
    print("=" * 60)
    
    # Connect to coordinator
    coord_conn = psycopg2.connect(
        "dbname=postgres user=postgres password=mypass host=localhost port=5432"
    )
    coord_cur = coord_conn.cursor()
    
    # 1. Check worker nodes
    print("\n📡 WORKER NODES:")
    print("-" * 30)
    coord_cur.execute("SELECT * FROM master_get_active_worker_nodes();")
    workers = coord_cur.fetchall()
    for worker in workers:
        print(f"  ✅ {worker[0]}:{worker[1]}")
    
    # 2. Check shard replication
    print(f"\n🔄 SHARD REPLICATION FACTOR:")
    print("-" * 35)
    coord_cur.execute("SHOW citus.shard_replication_factor;")
    replication_factor = coord_cur.fetchone()[0]
    print(f"  Replication Factor: {replication_factor}")
    
    if int(replication_factor) == 1:
        print("  ⚠️  WARNING: Single copy per shard (NOT active-active)")
        print("  📝 Each shard exists on only ONE worker")
    else:
        print(f"  ✅ Multiple copies per shard (replication factor: {replication_factor})")
    
    # 3. Check shard placements
    print(f"\n🗂️  SHARD PLACEMENT DETAILS:")
    print("-" * 35)
    coord_cur.execute("""
        SELECT 
            s.logicalrelid::text as table_name,
            s.shardid,
            COUNT(p.placementid) as replica_count,
            string_agg(n.nodename || ':' || n.nodeport, ', ') as locations
        FROM pg_dist_shard s
        JOIN pg_dist_placement p ON s.shardid = p.shardid
        JOIN pg_dist_node n ON p.groupid = n.groupid
        WHERE s.logicalrelid IN ('rooms'::regclass, 'room_members'::regclass, 'messages'::regclass)
        GROUP BY s.logicalrelid, s.shardid
        ORDER BY s.logicalrelid, s.shardid
        LIMIT 10;
    """)
    
    placements = coord_cur.fetchall()
    for placement in placements:
        table, shard_id, replica_count, locations = placement
        if replica_count > 1:
            print(f"  ✅ {table} Shard {shard_id}: {replica_count} replicas on {locations}")
        else:
            print(f"  ⚠️  {table} Shard {shard_id}: {replica_count} replica on {locations}")
    
    # 4. Test read capabilities from different workers
    print(f"\n📖 TESTING READ CAPABILITIES:")
    print("-" * 35)
    
    worker_ports = [5433, 5434, 5435, 5436]  # Direct worker ports
    read_results = []
    
    for port in worker_ports:
        try:
            worker_conn = psycopg2.connect(
                f"dbname=postgres user=postgres password=mypass host=localhost port={port}"
            )
            worker_cur = worker_conn.cursor()
            
            # Try to read from rooms table
            worker_cur.execute("SELECT COUNT(*) FROM rooms;")
            count = worker_cur.fetchone()[0]
            read_results.append((port, count, "✅"))
            
            worker_cur.close()
            worker_conn.close()
            
        except Exception as e:
            read_results.append((port, 0, f"❌ {str(e)[:50]}..."))
    
    for port, count, status in read_results:
        print(f"  Worker {port}: {status} ({count} rooms)")
    
    # 5. Test write capabilities
    print(f"\n✍️  TESTING WRITE CAPABILITIES:")
    print("-" * 35)
    
    # Test writing through coordinator
    try:
        test_room_id = 999999999  # Large positive ID
        coord_cur.execute("""
            INSERT INTO rooms (id, room_type, created_at, updated_at) 
            VALUES (%s, 1, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING;
        """, (test_room_id,))
        coord_conn.commit()
        
        coord_cur.execute("SELECT COUNT(*) FROM rooms WHERE id = %s;", (test_room_id,))
        if coord_cur.fetchone()[0] > 0:
            print("  ✅ Write through coordinator: SUCCESS")
            
            # Clean up test data
            coord_cur.execute("DELETE FROM rooms WHERE id = %s;", (test_room_id,))
            coord_conn.commit()
        else:
            print("  ❌ Write through coordinator: FAILED")
            
    except Exception as e:
        print(f"  ❌ Write through coordinator: ERROR - {e}")
    
    # 6. Check if it's truly active-active or just distributed
    print(f"\n🎯 ACTIVE-ACTIVE ASSESSMENT:")
    print("-" * 35)
    
    if int(replication_factor) == 1:
        print("  📊 CURRENT SETUP: Distributed (Sharded) Database")
        print("  📝 ARCHITECTURE:")
        print("    - Each shard exists on exactly ONE worker")
        print("    - Data is DISTRIBUTED but NOT REPLICATED")
        print("    - If a worker fails, you lose that shard's data")
        print("    - Reads/writes are load-balanced across workers")
        print("    - This is HORIZONTAL SCALING, not active-active")
        
        print(f"\n  🔧 TO MAKE IT ACTIVE-ACTIVE:")
        print("    1. Increase replication factor: SET citus.shard_replication_factor = 2;")
        print("    2. Recreate distributed tables")
        print("    3. Each shard will exist on 2+ workers")
        print("    4. True fault tolerance and active-active reads")
        
    else:
        print("  ✅ CURRENT SETUP: Active-Active Database")
        print("  📝 ARCHITECTURE:")
        print(f"    - Each shard replicated {replication_factor} times")
        print("    - Multiple workers can serve the same data")
        print("    - Fault tolerant - worker failures don't lose data")
        print("    - True active-active reads from multiple replicas")
    
    coord_cur.close()
    coord_conn.close()


def show_improvement_steps():
    """Show how to convert to true active-active"""
    
    print(f"\n🚀 HOW TO ENABLE TRUE ACTIVE-ACTIVE:")
    print("=" * 50)
    print("1. Set replication factor BEFORE creating distributed tables:")
    print("   SET citus.shard_replication_factor = 2;")
    print("")
    print("2. Recreate your distributed tables:")
    print("   SELECT undistribute_table('rooms');")
    print("   SELECT undistribute_table('room_members');") 
    print("   SELECT undistribute_table('messages');")
    print("   SET citus.shard_count = 4;")
    print("   SET citus.shard_replication_factor = 2;")
    print("   SELECT create_distributed_table('rooms', 'id');")
    print("   SELECT create_distributed_table('room_members', 'room_id');")
    print("   SELECT create_distributed_table('messages', 'room_id');")
    print("")
    print("3. Result: Each shard will exist on 2 workers")
    print("4. Benefits: True fault tolerance + active-active reads")


if __name__ == "__main__":
    try:
        check_citus_status()
        show_improvement_steps()
    except Exception as e:
        print(f"❌ Error checking Citus status: {e}")
        print("Make sure your Citus cluster is running: make prepare-citus") 