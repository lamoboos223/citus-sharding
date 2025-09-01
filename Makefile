# Clean up all PostgreSQL containers including Citus
clean-active:
	@echo "🧹 Cleaning up Citus cluster..."
	@docker-compose -f active-active-deployment/docker-compose.yml down --volumes --remove-orphans 2>/dev/null || true
	@echo "✅ All containers and volumes cleaned up successfully!"

# Prepare Citus cluster using Docker Compose
prepare-active:
	@echo "Setting up Citus cluster with Docker Compose..."
	@docker-compose -f active-active-deployment/docker-compose.yml up -d

# Run Citus sharding example
run-active:
	@echo "Running Active-Active example..."
	@python active-active-deployment/active-active-demo.py

# Rebuild and restart Citus cluster
restart-active: clean-active prepare-active
	@echo "✅ Citus cluster is ready to use!"
