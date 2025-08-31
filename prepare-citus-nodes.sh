# Create network
docker network create citus_network

# Launch coordinator
docker run -d --name citus_coordinator --network citus_network \
-p 5432:5432 -e POSTGRES_PASSWORD=mypass citusdata/citus:12.1

# Launch workers (4 workers for optimal 4-shard distribution)
docker run -d --name citus_worker1 --network citus_network \
-p 5433:5432 -e POSTGRES_PASSWORD=mypass citusdata/citus:12.1

docker run -d --name citus_worker2 --network citus_network \
-p 5434:5432 -e POSTGRES_PASSWORD=mypass citusdata/citus:12.1

docker run -d --name citus_worker3 --network citus_network \
-p 5435:5432 -e POSTGRES_PASSWORD=mypass citusdata/citus:12.1

docker run -d --name citus_worker4 --network citus_network \
-p 5436:5432 -e POSTGRES_PASSWORD=mypass citusdata/citus:12.1

# Wait for containers to be ready
echo "Waiting for containers to start..."
sleep 15

# Add workers using container names (internal port 5432)
echo "Adding worker nodes to cluster..."
psql -U postgres -h localhost -p 5432 -c "SELECT * FROM master_add_node('citus_worker1', 5432);"
psql -U postgres -h localhost -p 5432 -c "SELECT * FROM master_add_node('citus_worker2', 5432);"
psql -U postgres -h localhost -p 5432 -c "SELECT * FROM master_add_node('citus_worker3', 5432);"
psql -U postgres -h localhost -p 5432 -c "SELECT * FROM master_add_node('citus_worker4', 5432);"

# Verify cluster setup
echo "Verifying cluster setup..."
psql -U postgres -h localhost -p 5432 -c "SELECT * FROM master_get_active_worker_nodes();"

echo "Citus cluster is ready!"
echo "Coordinator: localhost:5432"
echo "Worker 1: localhost:5433"
echo "Worker 2: localhost:5434" 
echo "Worker 3: localhost:5435"
echo "Worker 4: localhost:5436"
