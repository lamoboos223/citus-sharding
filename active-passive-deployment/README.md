# Active-Passive Citus Deployment with Patroni HA

This deployment provides a **production-ready, highly-available Citus cluster** with **automatic coordinator failover** using Patroni, etcd, and HAProxy. Unlike traditional active-active setups, this configuration offers a **single database endpoint** with transparent failover capabilities.

## 🏗️ Architecture Overview

### What This Is

A **single Citus cluster** with **coordinator high-availability**:

- **Patroni** manages PostgreSQL coordinator failover
- **HAProxy** provides load balancing and health checking
- **etcd** stores cluster state and configuration
- **3 Citus workers** handle distributed data shards
- **Single endpoint** for all database operations

### Architecture Diagram

```
                                    Clients
                                        │
                            ┌───────────▼───────────┐
                            │      HAProxy          │
                            │   (Load Balancer)     │
                            │    Port: 5000         │
                            │    Stats: 7000        │
                            └───────────┬───────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
            ┌───────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
            │  Coordinator 1  │ │  Coordinator 2  │ │      etcd       │
            │   (Patroni)     │ │   (Patroni)     │ │  (Consensus)    │
            │    Primary      │ │   Standby       │ │   Port: 2379    │
            └────────┬────────┘ └─────────────────┘ └─────────────────┘
                     │                   ▲
                     │ Citus distributes │ Replication
                     │ queries by shard  │
                     │                   │
        ┌────────────┼───────────────────┼─────────────────┐
        │            │                   │                 │
   ┌────▼────┐ ┌─────▼────┐ ┌─────────▼──┐      ┌─────▼────┐
   │Worker 1 │ │Worker 2  │ │Worker 3    │      │Worker N  │
   │Port:5432│ │Port:5432 │ │Port:5432   │ ...  │Port:5432 │
   └─────────┘ └──────────┘ └────────────┘      └──────────┘
        ↑            ↑            ↑                 ↑
   Shard placements distributed across workers (RF=2)
```

### Service Breakdown

| Component | Purpose | Port | Health Check |
|-----------|---------|------|--------------|
| **HAProxy** | Load balancer for coordinators | 5000 (SQL)<br/>7000 (Stats) | Patroni REST API |
| **Coordinator 1** | Primary Patroni + Citus coordinator | 5432 (PG)<br/>8008 (API) | Patroni health endpoint |
| **Coordinator 2** | Standby Patroni + Citus coordinator | 5432 (PG)<br/>8008 (API) | Patroni health endpoint |
| **etcd** | Consensus store for Patroni | 2379 (Client)<br/>2380 (Peer) | etcd health endpoint |
| **Worker 1-3** | Citus worker nodes | 5432 (PG) | `pg_isready` |
| **Setup** | One-time cluster initialization | - | - |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Ensure Docker & Docker Compose are installed
docker --version
docker-compose --version

# Install Python dependencies (for demo script)
pip install psycopg2-binary
```

### 1. Start the Cluster

```bash
# Clean any existing setup
make clean-passive

# Build and start HA cluster
make prepare-passive
```

This will:

- Build custom Patroni+Citus Docker images
- Start etcd consensus store
- Launch 2 Patroni coordinators with automatic leader election
- Start HAProxy load balancer
- Initialize 3 Citus worker nodes
- Configure Citus cluster (replication factor = 2)

### 2. Verify Setup

```bash
# Check Patroni cluster status
docker exec active-passive-deployment-coord-1-1 \
  sh -lc 'curl -s http://localhost:8008/cluster | jq -r ".members[] | [.name,.role,.state] | @tsv"'

coord-1 leader  running
coord-2 quorum_standby  streaming
```

```bash
# Check HAProxy stats
curl http://localhost:7000
# Or visit http://localhost:7000 in browser
```

### 3. Connect to Database

```bash
# Connect through HAProxy (always hits the leader)
psql -h localhost -p 5000 -U postgres -d postgres
# Password: mypass

# Check Citus workers
postgres=# SELECT * FROM citus_get_active_worker_nodes();
```

### 4. Run Demo Application

```bash
# Load sample data and test HA
make run-passive
```

---

## 🧪 High Availability Testing

### Test 1: Coordinator Failover

```bash
# Stop the current leader
docker stop active-passive-deployment-coord-2-1

# HAProxy automatically detects failure and routes to backup
# Check new leader
docker exec -it active-passive-deployment-coord-1-1 patronictl -c /etc/patroni.yml list

# Database operations continue without interruption
psql -h localhost -p 5000 -U postgres -d postgres -c "SELECT count(*) FROM rooms;"
```

### Test 2: Worker Failure Resilience

```bash
# Stop one worker (RF=2 allows for 1 worker failure)
docker stop active-passive-deployment-worker1-1

# Cluster remains operational
psql -h localhost -p 5000 -U postgres -d postgres -c "SELECT * FROM citus_get_active_worker_nodes();"
```

### Test 3: Complete Recovery

```bash
# Restart failed services
docker start active-passive-deployment-coord-2-1
docker start active-passive-deployment-worker1-1

# Verify automatic recovery
docker exec -it active-passive-deployment-coord-1-1 patronictl -c /etc/patroni.yml list
```

---

## 📊 Configuration Details

### Patroni Configuration

**File:** `patroni-citus/patroni.yml`

Key settings:

```yaml
# Consensus and leader election
scope: citusap
etcd:
  hosts: etcd:2379

# PostgreSQL + Citus configuration
postgresql:
  parameters:
    shared_preload_libraries: "citus,pg_stat_statements"
    max_connections: 300
    wal_level: replica

# Citus coordinator setup
citus:
  group: 0          # Group 0 = coordinator
  database: postgres
```

### HAProxy Configuration

**File:** `haproxy/haproxy.cfg`

```bash
# Write traffic (port 5000)
listen postgres_write
  bind *:5000
  option httpchk OPTIONS /master    # Check Patroni leader status
  server coord1 coord-1:5432 check port 8008
  server coord2 coord-2:5432 check port 8008

# Monitoring (port 7000)
listen stats
  bind *:7000
  stats enable
```

### Citus Cluster Settings

Applied during setup:

```sql
-- Distributed across 3 workers with 2x replication
ALTER SYSTEM SET citus.shard_count = 3;
ALTER SYSTEM SET citus.shard_replication_factor = 2;

-- Workers automatically registered
SELECT citus_add_node('worker1', 5432);
SELECT citus_add_node('worker2', 5432);
SELECT citus_add_node('worker3', 5432);
```

---

## 🔧 Management Commands

### Patroni Operations

```bash
# View cluster status
docker exec -it active-passive-deployment-coord-1-1 patronictl -c /etc/patroni.yml list

# Manual failover
docker exec -it active-passive-deployment-coord-1-1 patronictl -c /etc/patroni.yml switchover

# Reinitialize a node
docker exec -it active-passive-deployment-coord-1-1 patronictl -c /etc/patroni.yml reinit citusap coord-1
```

### Database Operations

```bash
# Connect to current leader
psql -h localhost -p 5000 -U postgres -d postgres

# Check worker status
SELECT * FROM citus_get_active_worker_nodes();

# View shard placements
SELECT shardid, shardstate, nodename, nodeport
FROM pg_dist_shard s
JOIN pg_dist_placement p USING(shardid)
JOIN pg_dist_node n ON n.groupid=p.groupid
WHERE s.logicalrelid='rooms'::regclass
ORDER BY shardid, nodename, nodeport;
```

### Container Management

```bash
# View all services
docker-compose -f active-passive-deployment/docker-compose.yml ps

# View logs
docker-compose -f active-passive-deployment/docker-compose.yml logs -f coord-1
docker-compose -f active-passive-deployment/docker-compose.yml logs -f haproxy

# Scale workers (requires manual Citus registration)
docker-compose -f active-passive-deployment/docker-compose.yml up -d --scale worker1=2
```

---

## 🛠️ Troubleshooting

### Common Issues

**1. Patroni Leader Election Fails**

```bash
# Check etcd connectivity
docker exec -it active-passive-deployment-coord-1-1 curl -s http://etcd:2379/health

# Restart etcd if needed
docker-compose -f active-passive-deployment/docker-compose.yml restart etcd
```

**2. HAProxy Can't Connect to Coordinators**

```bash
# Check Patroni API status
docker exec -it active-passive-deployment-coord-1-1 curl -s http://localhost:8008/health

# Check HAProxy configuration
docker exec -it active-passive-deployment-haproxy-1 cat /usr/local/etc/haproxy/haproxy.cfg
```

**3. Citus Workers Not Registered**

```bash
# Re-run setup manually
docker-compose -f active-passive-deployment/docker-compose.yml up setup
```

### Logs to Check

```bash
# Patroni coordinator logs
docker logs active-passive-deployment-coord-1-1
docker logs active-passive-deployment-coord-2-1

# HAProxy logs
docker logs active-passive-deployment-haproxy-1

# etcd logs
docker logs active-passive-deployment-etcd-1
```

---

## 📈 Performance Characteristics

### Coordinator HA Benefits

- ✅ **Zero-downtime failover** (< 5 seconds)
- ✅ **Automatic leader election**
- ✅ **Application transparency** (same connection string)
- ✅ **Read/write splitting** potential (add read replicas)

### Citus Distribution

- **3 shards** distributed across 3 workers
- **Replication factor 2** (each shard on 2 workers)
- **Fault tolerance**: Survives 1 worker failure
- **Load balancing**: Queries distributed across healthy workers

### Scaling Options

**Horizontal Scaling:**

```yaml
# Add more workers
worker4:
  image: citusdata/citus:latest
  # ... configuration
```

**Coordinator HA:**

```yaml
# Add third coordinator for higher availability
coord-3:
  build: ./patroni-citus
  # ... configuration
```

---

## 🎯 Production Considerations

### Monitoring

- **HAProxy stats**: <http://localhost:7000>
- **Patroni API**: <http://coord-1:8008/health>, <http://coord-2:8008/health>
- **PostgreSQL metrics**: Standard pg_stat_* views
- **etcd health**: <http://etcd:2379/health>

### Backup Strategy

```bash
# Patroni handles base backups automatically
# For additional backups, use pg_dump through HAProxy
pg_dump -h localhost -p 5000 -U postgres postgres > backup.sql
```

### Security Hardening

- Change default passwords in production
- Configure TLS for all connections
- Restrict network access to Docker bridge
- Use secrets management for credentials

---

**🎯 This active-passive configuration provides enterprise-grade high availability with automatic failover, making it ideal for production workloads requiring single-endpoint simplicity with fault tolerance.**
