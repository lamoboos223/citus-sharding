# Configuration
NUM_CONTAINERS=4

clean:
	@echo "🧹 Cleaning up Multi-Master Citus cluster..."
	@docker-compose down --volumes --remove-orphans 2>/dev/null || true
	@echo "✅ All containers and volumes cleaned up successfully!"

# Legacy commands for backward compatibility
db:
	@echo "Starting PostgreSQL containers using prepare-db.sh..."
	@bash prepare-db.sh

# Multi-Master Citus commands
prepare-multi-master:
	@echo "🚀 Setting up Multi-Master Citus cluster with Nginx load balancer..."
	@docker-compose up -d
	@echo "⏳ Waiting for multi-master setup to complete..."
	@docker-compose logs -f citus_multi_master_setup

# Stop Multi-Master cluster
stop-multi-master:
	@echo "Stopping Multi-Master Citus cluster..."
	@docker-compose stop

# View Multi-Master cluster logs
logs-multi-master:
	@echo "Showing Multi-Master Citus cluster logs..."
	@docker-compose logs -f

# Run Multi-Master Citus example
run-multi-master:
	@echo "🚀 Running Multi-Master Citus example..."
	@python citus-multi-master-example.py

# Show cluster status
status-multi-master:
	@echo "Checking Multi-Master Citus cluster status..."
	@docker-compose ps
	@echo ""
	@echo "📊 Nginx Status: http://localhost:8081"
	@echo "🏥 Health Check: http://localhost:8080"

# Rebuild and restart Multi-Master cluster
restart-multi-master: clean prepare-multi-master

# Test failover by stopping coordinator 1
test-failover-coord1:
	@echo "🔥 Testing failover - stopping Coordinator 1..."
	@docker-compose stop citus_coordinator1
	@echo "⏳ Testing Nginx load balancer failover in 5 seconds..."
	@sleep 5
	@python -c "import psycopg2; conn=psycopg2.connect('host=localhost port=5438 user=postgres password=mypass dbname=postgres'); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM rooms;'); print(f'✅ Nginx failover successful: {cur.fetchone()[0]} rooms accessible'); conn.close()"
	@echo "🔄 Restarting Coordinator 1..."
	@docker-compose start citus_coordinator1

# Test failover by stopping coordinator 2
test-failover-coord2:
	@echo "🔥 Testing failover - stopping Coordinator 2..."
	@docker-compose stop citus_coordinator2
	@echo "⏳ Testing Nginx load balancer failover in 5 seconds..."
	@sleep 5
	@python -c "import psycopg2; conn=psycopg2.connect('host=localhost port=5438 user=postgres password=mypass dbname=postgres'); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM rooms;'); print(f'✅ Nginx failover successful: {cur.fetchone()[0]} rooms accessible'); conn.close()"
	@echo "🔄 Restarting Coordinator 2..."
	@docker-compose start citus_coordinator2

# Backward compatibility aliases
prepare: prepare-multi-master
stop-citus: stop-multi-master
logs-citus: logs-multi-master
run: run-multi-master
status-citus: status-multi-master
restart-citus: restart-multi-master

# Show help for all commands
help:
	@echo "🚀 MULTI-MASTER CITUS COMMANDS:"
	@echo "  prepare-multi-master   - Set up Multi-Master Citus cluster with Nginx"
	@echo "  stop-multi-master      - Stop Multi-Master cluster"
	@echo "  logs-multi-master      - Show cluster logs"
	@echo "  run-multi-master       - Run Multi-Master application"
	@echo "  status-multi-master    - Show cluster status"
	@echo "  restart-multi-master   - Clean and restart cluster"
	@echo "  test-failover-coord1   - Test failover by stopping Coordinator 1"
	@echo "  test-failover-coord2   - Test failover by stopping Coordinator 2"
	@echo ""
	@echo "📊 MONITORING:"
	@echo "  Nginx Status: http://localhost:8081"
	@echo "  Health Check: http://localhost:8080"
	@echo ""
	@echo "🔌 CONNECTION ENDPOINTS:"
	@echo "  Coordinator 1: localhost:5432"
	@echo "  Coordinator 2: localhost:5437"
	@echo "  Nginx Load Balanced: localhost:5438"
	@echo "  Workers: localhost:5433-5436"
	@echo ""
	@echo "🔄 LEGACY COMMANDS (Backward Compatibility):"
	@echo "  clean                  - Clean up containers"
	@echo "  prepare          - Alias for prepare-multi-master"
	@echo "  run              - Alias for run-multi-master"
	@echo ""
	@echo "🎯 MULTI-MASTER FEATURES:"
	@echo "  ✅ True multi-writer setup (2 coordinators)"
	@echo "  ✅ Nginx load balancing with health checks"
	@echo "  ✅ Automatic failover"
	@echo "  ✅ Concurrent write operations"
	@echo "  ✅ Data consistency verification"
