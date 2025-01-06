import psycopg2
from psycopg2 import sql

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
    # Add more shards as needed
]


# Function to connect to PostgreSQL and execute a query
def connect_to_db(shard):
    conn = psycopg2.connect(
        host=shard["host"],
        port=shard["port"],
        dbname=shard["dbname"],
        user=shard["user"],
        password=shard["password"],
    )
    return conn


# Function to insert data into the appropriate shard
def insert_into_shard(user_id, user_data):
    # Determine the shard number based on user_id using modulo
    shard_index = (user_id - 1) % len(shards)  # Changed // to %

    shard = shards[shard_index]

    # Insert the data into the correct shard
    conn = connect_to_db(shard)
    cursor = conn.cursor()

    # SQL to insert data (for example, a user table)
    insert_query = sql.SQL(
        "INSERT INTO users (user_id, name, email) VALUES (%s, %s, %s)"
    )
    cursor.execute(insert_query, (user_id, user_data["name"], user_data["email"]))

    # Commit the transaction and close the connection
    conn.commit()
    cursor.close()
    conn.close()

    print(f"Inserted user {user_id} into shard {shard['port']}.")


# Example: Insert users into the appropriate shards
users = [
    {"user_id": 1, "name": "Alice", "email": "alice@example.com"},
    {"user_id": 1001, "name": "Bob", "email": "bob@example.com"},
    {"user_id": 2001, "name": "Charlie", "email": "charlie@example.com"},
    {"user_id": 2005, "name": "David", "email": "david@example.com"},
    {"user_id": 3001, "name": "Eve", "email": "eve@example.com"},
    {"user_id": 3002, "name": "Frank", "email": "frank@example.com"},
]

# Insert each user into the corresponding shard
for user in users:
    insert_into_shard(user["user_id"], user)
