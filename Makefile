# Define variables for the PostgreSQL containers
NUM_CONTAINERS := 3
BASE_PORT := 5432
PG_PASSWORD := password
SQL_INIT_SCRIPT := C:\development\sharding-db-demo\init.sql
PREPARE_DB_SCRIPT := ./prepare-db.sh  # Path to the prepare-db.sh script

# Clean up all PostgreSQL containers
clean:
	@echo "Cleaning up all PostgreSQL containers..."
	@for i in $(shell seq 1 $(NUM_CONTAINERS)); do \
		CONTAINER_NAME="postgres_$$i"; \
		if docker ps -a -q -f name=$$CONTAINER_NAME; then \
			echo "Removing container: $$CONTAINER_NAME"; \
			docker stop $$CONTAINER_NAME && docker rm $$CONTAINER_NAME || true; \
		else \
			echo "Container $$CONTAINER_NAME does not exist."; \
		fi; \
	done

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

# Show help for all commands
help:
	@echo "Available commands:"
	@echo "  clean        - Clean up and remove all PostgreSQL containers"
	@echo "  db           - Create and start PostgreSQL containers using prepare-db.sh"
	@echo "  run          - Run the Python application with numeric IDs"
	@echo "  run-matrix   - Run the Python application with Matrix-style IDs"
	@echo "  help         - Show this help message"
