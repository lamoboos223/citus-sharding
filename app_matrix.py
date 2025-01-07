import psycopg2
from psycopg2 import sql
import hashlib

# Define PostgreSQL connections for each shard (using different ports)
shards = [
    {
        "host": "localhost",
        "port": 5435,
        "dbname": "postgres",
        "user": "postgres",
        "password": "password",
    },
    {
        "host": "localhost",
        "port": 5433,
        "dbname": "postgres",
        "user": "postgres",
        "password": "password",
    },
    {
        "host": "localhost",
        "port": 5434,
        "dbname": "postgres",
        "user": "postgres",
        "password": "password",
    },
]


def connect_to_db(shard):
    conn = psycopg2.connect(
        host=shard["host"],
        port=shard["port"],
        dbname=shard["dbname"],
        user=shard["user"],
        password=shard["password"],
    )
    return conn


def insert_into_shard_string(user_id, user_data):
    # Convert string user_id to numeric value using hash
    hash_value = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
    shard_index = hash_value % len(shards)

    shard = shards[shard_index]

    conn = connect_to_db(shard)
    cursor = conn.cursor()

    insert_query = sql.SQL(
        "INSERT INTO users2 (user_id, name, email) VALUES (%s, %s, %s)"
    )
    cursor.execute(insert_query, (user_id, user_data["name"], user_data["email"]))

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Inserted user {user_id} into shard {shard['port']}.")


# Example Matrix-style users
matrix_users = [
    {
        "user_id": "@alice:matrix.org",
        "name": "Alice M",
        "email": "alice.matrix@example.com",
    },
    {"user_id": "@bob:matrix.org", "name": "Bob M", "email": "bob.matrix@example.com"},
    {
        "user_id": "@charlie:matrix.org",
        "name": "Charlie M",
        "email": "charlie.matrix@example.com",
    },
    {
        "user_id": "@david:matrix.org",
        "name": "David M",
        "email": "david.matrix@example.com",
    },
    {"user_id": "@eve:matrix.org", "name": "Eve M", "email": "eve.matrix@example.com"},
]

if __name__ == "__main__":
    print("Inserting Matrix-style users...")
    for user in matrix_users:
        insert_into_shard_string(user["user_id"], user)
