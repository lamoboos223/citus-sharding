#!/bin/bash

# Get the arguments passed from Makefile
NUM_CONTAINERS=$1
BASE_PORT=$2
PG_PASSWORD=$3
SQL_INIT_SCRIPT=$4

# Stop and remove existing containers if they exist
echo "Cleaning up existing PostgreSQL containers..."
for i in $(seq 1 $NUM_CONTAINERS); do
    CONTAINER_NAME="postgres_$i"
    if docker ps -a -q -f name=$CONTAINER_NAME; then
        echo "Removing container: $CONTAINER_NAME"
        docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME || true
    else
        echo "Container $CONTAINER_NAME does not exist."
    fi
done

# Start the new PostgreSQL containers
echo "Starting PostgreSQL containers..."
for i in $(seq 1 $NUM_CONTAINERS); do
    CONTAINER_NAME="postgres_$i"
    PORT=$((BASE_PORT + i))
    echo "Starting container $CONTAINER_NAME on port $PORT..."
    docker run -d \
    --name $CONTAINER_NAME \
    -e POSTGRES_PASSWORD=$PG_PASSWORD \
    -p $PORT:5432 \
    -v $SQL_INIT_SCRIPT:/docker-entrypoint-initdb.d/init.sql \
    postgres:latest
done
