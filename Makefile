# Define variables for the PostgreSQL containers
NUM_CONTAINERS := 3
BASE_PORT := 5432
PG_PASSWORD := password
SQL_INIT_SCRIPT := C:\development\sharding-db-demo\init.sql
PREPARE_DB_SCRIPT := ./prepare-db.sh  # Path to the prepare-db.sh script

# Clean up all PostgreSQL containers including Citus
clean:
	@echo "Cleaning up all PostgreSQL and Citus containers..."
	@docker-compose down --volumes --remove-orphans 2>/dev/null || true
	@for i in $(shell seq 1 $(NUM_CONTAINERS)); do \
		CONTAINER_NAME="postgres_$$i"; \
		if docker ps -a -q -f name=$$CONTAINER_NAME; then \
			echo "Removing container: $$CONTAINER_NAME"; \
			docker stop $$CONTAINER_NAME && docker rm $$CONTAINER_NAME || true; \
		else \
			echo "Container $$CONTAINER_NAME does not exist."; \
		fi; \
	done
	@echo "All containers cleaned up."

# Create all PostgreSQL containers by calling prepare-db.sh script
db:
	@echo "Starting PostgreSQL containers using prepare-db.sh script..."
	@bash $(PREPARE_DB_SCRIPT) $(NUM_CONTAINERS) $(BASE_PORT) $(PG_PASSWORD) $(SQL_INIT_SCRIPT)

# Run the application
run:
	@echo "Running the application..."
	@python app.py

# Run the string-based sharding demo
run-matrix:
	@echo "Running the application with Matrix-style IDs..."
	@python app_matrix.py

# Prepare Citus cluster using Docker Compose
prepare-citus:
	@echo "Setting up Citus cluster with Docker Compose..."
	@docker-compose up -d
	@echo "Waiting for cluster setup to complete..."
	@docker-compose logs -f citus_setup

# Stop Citus cluster
stop-citus:
	@echo "Stopping Citus cluster..."
	@docker-compose stop

# View Citus cluster logs
logs-citus:
	@echo "Showing Citus cluster logs..."
	@docker-compose logs -f

# Run Citus sharding example
run-citus:
	@echo "Running Citus sharding example..."
	@python citus-example.py

# Connect to Citus coordinator
connect-citus:
	@echo "Connecting to Citus coordinator..."
	@docker-compose exec citus_coordinator psql -U postgres

# Show cluster status
status-citus:
	@echo "Checking Citus cluster status..."
	@docker-compose ps

# Rebuild and restart Citus cluster
restart-citus: clean prepare-citus

# Restart with active-active configuration (replication factor 2)
restart-active-active: clean prepare-citus
	@echo "✅ Cluster restarted with active-active configuration"
	@echo "📊 Each shard replicated on 2 workers for fault tolerance"

# Show help for all commands
help:
	@echo "Available commands:"
	@echo "  clean              - Clean up and remove all containers"
	@echo "  db                 - Create and start PostgreSQL containers using prepare-db.sh"
	@echo "  run                - Run the Python application with numeric IDs"
	@echo "  run-matrix         - Run the Python application with Matrix-style IDs"
	@echo "  prepare-citus      - Set up Citus cluster with Docker Compose (active-active)"
	@echo "  stop-citus         - Stop Citus cluster"
	@echo "  logs-citus         - Show Citus cluster logs"
	@echo "  run-citus          - Run Citus sharding example"
	@echo "  connect-citus      - Connect to Citus coordinator via psql"
	@echo "  status-citus       - Show cluster status"
	@echo "  restart-citus      - Clean and restart Citus cluster"
	@echo "  restart-active-active - Restart with active-active config (replication=2)"
	@echo "  help               - Show this help message"
	@echo ""
	@echo "🎯 Active-Active Setup:"
	@echo "  The cluster now starts with replication_factor=2 by default"
	@echo "  Each shard is replicated on 2 workers for fault tolerance"
