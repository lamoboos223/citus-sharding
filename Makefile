# Clean up all PostgreSQL containers including Citus
clean:
	@echo "🧹 Cleaning up Citus cluster..."
	@docker-compose down --volumes --remove-orphans 2>/dev/null || true
	@echo "✅ All containers and volumes cleaned up successfully!"

# Prepare Citus cluster using Docker Compose
prepare:
	@echo "Setting up Citus cluster with Docker Compose..."
	@docker-compose up -d
	@echo "Waiting for cluster setup to complete..."
	@docker-compose logs -f citus_setup

# Run Citus sharding example
run-citus:
	@echo "Running Citus sharding example..."
	@python citus-example.py

setup-metadata:
	@echo "Setting up Citus distributed table metadata..."
	@python setup-citus-metadata.py

insert-data:
	@echo "Inserting data through PgPool..."
	@python insert-data-pgpool.py

run:
	@echo "Running Citus + PgPool high availability example..."
	@python citus-example-pgpool.py

# Rebuild and restart Citus cluster
restart-citus: clean prepare


# Show help for all commands
help:
	@echo "Available commands:"
	@echo "  clean              - Clean up and remove all containers"
	@echo "  prepare            - Set up Citus cluster with Docker Compose (active-active)"
	@echo "  setup-metadata     - Create distributed tables (requires all workers)"
	@echo "  insert-data        - Insert sample data through PgPool (HA capable)"
	@echo "  run-citus          - Run Citus sharding example"
	@echo "  run                - Run Citus + PgPool HA example"
	@echo "  restart-citus      - Clean and restart Citus cluster"
	@echo "  help               - Show this help message"
