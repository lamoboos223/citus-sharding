# Database Sharding Demo

This project demonstrates a simple implementation of database sharding using PostgreSQL containers. It shows how to distribute user data across multiple database shards based on user IDs.

## Overview

The demo uses Docker containers to create multiple PostgreSQL instances that act as separate database shards. User data is distributed across these shards using a modulo-based sharding strategy, where the user ID determines which shard will store the data.

## Prerequisites

- Docker
- Python 3.x
- psycopg2 Python package
- Make (for running Makefile commands)

## Project Structure

- `app.py` - Main application that handles data insertion across shards
- `init.sql` - SQL script to initialize the database schema
- `prepare-db.sh` - Shell script to set up PostgreSQL containers
- `Makefile` - Contains commands to manage the application

## Available Commands

The following commands are available through the Makefile:

- `make clean` - Clean up and remove all PostgreSQL containers
- `make db` - Create and start PostgreSQL containers using prepare-db.sh
- `make run` - Run the Python application
- `make help` - Show help message with available commands

## How It Works

1. The system creates multiple PostgreSQL containers using Docker
2. Each container runs on a different port (starting from 5433)
3. User data is distributed across shards based on user_id % number_of_shards
4. The Python application handles the logic for determining which shard to use for each user

## Getting Started

1. Clone the repository
2. Run `make db` to start the PostgreSQL containers
3. Run `make run` to execute the demo application
4. Use `make clean` when you're done to clean up the containers
