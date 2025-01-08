# Database Sharding Demo

This project demonstrates different approaches to database sharding using PostgreSQL:

1. Manual sharding with separate PostgreSQL instances
2. String-based sharding for Matrix-style IDs
3. Distributed sharding using Citus

## Overview

The demo includes multiple sharding implementations:

- Basic sharding: Using Docker containers as separate database shards
- Matrix-style: Hash-based sharding for string IDs (e.g., "@user:matrix.org")
- Citus: Enterprise-grade distributed PostgreSQL implementation

## Prerequisites

- Docker
- Python 3.x
- psycopg2 Python package
- Make (for running Makefile commands)
- Citus Docker image (for Citus example)

## Project Structure

- `app.py` - Basic numeric ID-based sharding
- `app_matrix.py` - String-based ID sharding
- `citus-example.py` - Citus distributed database example
- `init.sql` - SQL schema for basic sharding
- `prepare-db.sh` - Setup script for basic sharding
- `prepare-citus-nodes.sh` - Setup script for Citus cluster
- `Makefile` - Commands to manage the application

## Available Commands

The following commands are available through the Makefile:

- `make clean` - Clean up and remove all PostgreSQL containers
- `make db` - Create and start PostgreSQL containers for basic sharding
- `make run` - Run the basic sharding example
- `make run-matrix` - Run the Matrix-style ID sharding example
- `make prepare-citus` - Set up Citus cluster nodes
- `make run-citus` - Run Citus sharding example
- `make help` - Show help message with available commands

## How It Works

### Basic Sharding

1. Creates multiple PostgreSQL containers
2. Distributes data using modulo operation on user IDs

### Matrix-style Sharding

1. Uses hash function for string-based IDs
2. Distributes data across shards using hash value

### Citus Sharding

1. Sets up a coordinator and multiple worker nodes
2. Uses distributed tables with specified shard count
3. Automatically handles data distribution and queries

## Getting Started

1. Clone the repository
2. For basic sharding:

   ```bash
   make db
   make run
   ```

3. For Matrix-style sharding:

   ```bash
   make db
   make run-matrix
   ```

4. For Citus example:

   ```bash
   make prepare-citus
   make run-citus
   ```

5. Use `make clean` when done to clean up containers

## Notes

- Basic sharding demonstrates manual implementation
- Matrix-style shows string-based distribution
- Citus provides enterprise-grade distributed PostgreSQL
