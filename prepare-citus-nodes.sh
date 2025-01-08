# Create network
docker network create citus_network

# Launch coordinator
docker run -d --name citus_coordinator --network citus_network \
-p 5432:5432 -e POSTGRES_PASSWORD=mypass citusdata/citus:12.1

# Launch workers
docker run -d --name citus_worker1 --network citus_network \
-p 5433:5432 -e POSTGRES_PASSWORD=mypass citusdata/citus:12.1

docker run -d --name citus_worker2 --network citus_network \
-p 5434:5432 -e POSTGRES_PASSWORD=mypass citusdata/citus:12.1

docker run -d --name citus_worker3 --network citus_network \
-p 5435:5432 -e POSTGRES_PASSWORD=mypass citusdata/citus:12.1

# Add workers using container names
psql -U postgres -h localhost -c "SELECT * FROM master_add_node('citus_worker1', 5432);"
psql -U postgres -h localhost -c "SELECT * FROM master_add_node('citus_worker2', 5432);"
psql -U postgres -h localhost -c "SELECT * FROM master_add_node('citus_worker3', 5432);"
