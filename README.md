# Database Sharding Demo

This project demonstrates a simple implementation of database sharding using PostgreSQL containers. It shows how to distribute user data across multiple database shards based on both numeric user IDs and string-based IDs (like Matrix-style identifiers).

## Overview

The demo uses Docker containers to create multiple PostgreSQL instances that act as separate database shards. User data is distributed across these shards using:

- Modulo-based sharding strategy for numeric user IDs
- Hash-based sharding strategy for string-based user IDs (e.g., "@user:matrix.org")

## Prerequisites

- Docker
- Python 3.x
- psycopg2 Python package
- Make (for running Makefile commands)

## Project Structure

- `app.py` - Main application that handles numeric ID-based sharding
- `app_matrix.py` - Application that handles string-based ID sharding
- `init.sql` - SQL script to initialize the database schema
- `prepare-db.sh` - Shell script to set up PostgreSQL containers
- `Makefile` - Contains commands to manage the application

## Available Commands

The following commands are available through the Makefile:

- `make clean` - Clean up and remove all PostgreSQL containers
- `make db` - Create and start PostgreSQL containers using prepare-db.sh
- `make run` - Run the Python application with numeric IDs
- `make run-matrix` - Run the Python application with Matrix-style IDs
- `make help` - Show help message with available commands

## How It Works

1. The system creates multiple PostgreSQL containers using Docker
2. Each container runs on a different port (starting from 5433)
3. For numeric IDs:
   - User data is distributed using user_id % number_of_shards
4. For string-based IDs:
   - User data is distributed using hash(user_id) % number_of_shards
5. The Python applications handle the logic for determining which shard to use

## Getting Started

1. Clone the repository
2. Run `make db` to start the PostgreSQL containers
3. Run `make run` to execute the numeric ID demo
4. Run `make run-matrix` to execute the string-based ID demo
5. Use `make clean` when you're done to clean up the containers
