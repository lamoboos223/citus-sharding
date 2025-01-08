import psycopg2
from psycopg2.extras import execute_values


def setup_citus_cluster():
    conn = psycopg2.connect(
        "dbname=postgres user=postgres password=mypass host=localhost port=5432"
    )
    cur = conn.cursor()

    cur.execute("SELECT * FROM master_get_active_worker_nodes();")
    print("Active workers:", cur.fetchall())

    # Drop tables if they exist
    cur.execute("DROP TABLE IF EXISTS users, cities CASCADE;")

    cur.execute(
        """
        CREATE TABLE users (
            id serial,
            name text,
            email text,
            city_id int,
            PRIMARY KEY (id, city_id)
        );
        
        CREATE TABLE cities (
            id serial PRIMARY KEY,
            name text,
            country text
        );
    """
    )

    cur.execute("SET citus.shard_count = 64;")
    cur.execute("SELECT create_distributed_table('users', 'city_id');")
    cur.execute("SELECT create_reference_table('cities');")

    cities_data = [(i, f"City{i}", "Country1") for i in range(1, 11)]
    execute_values(cur, "INSERT INTO cities (id, name, country) VALUES %s", cities_data)

    users_data = [(f"user{i}", f"user{i}@example.com", i % 10 + 1) for i in range(100)]
    execute_values(
        cur, "INSERT INTO users (name, email, city_id) VALUES %s", users_data
    )

    # Updated query with correct column names
    cur.execute(
        """
        SELECT s.shardid, n.nodename, n.nodeport 
        FROM pg_dist_placement p 
        JOIN pg_dist_shard s ON p.shardid = s.shardid 
        JOIN pg_dist_node n ON p.groupid = n.groupid
        WHERE s.logicalrelid = 'users'::regclass;
        """
    )

    print("\nShard placements:")
    for shard in cur.fetchall():
        print(f"Shard {shard[0]} on {shard[1]}:{shard[2]}")

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    setup_citus_cluster()
