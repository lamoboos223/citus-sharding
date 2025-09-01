# Citus Sharding Deployment Configurations

This repository contains two different **high-availability PostgreSQL database configurations** using Citus for distributed PostgreSQL workloads. Each approach solves different scalability and availability requirements.

## 📁 Project Structure

```
citus-sharding/
├── active-active-deployment/     # Multi-cluster, app-level routing
├── active-passive-deployment/    # Single cluster with coordinator HA
├── Makefile                      # Management commands for both projects
└── venv/                        # Python virtual environment
```

---

## 🔄 Active-Active Deployment

**Path:** `active-active-deployment/`

### What It Is

An **app-level active-active** design using **two independent Citus clusters**, both accepting writes simultaneously. Each cluster is authoritative for different data partitions (e.g., by tenant/room hash), eliminating write conflicts.

### Architecture Diagram

```
                                     Clients
                                         │
                         ┌───────────────┴───────────────┐
                         │        App / Router           │
                         │ (hash/lookup by tenant/room)  │
                         └───────┬───────────────┬───────┘
                                 │               │                
                             to Cluster A     to Cluster B
                                 │               │
                 ┌───────────────▼───────┐ ┌─────▼───────────────┐
                 │   Coordinator  A      │ │   Coordinator  B    │
                 │   (single writer)     │ │   (single writer)   │
                 └───────────┬───────────┘ └───────────┬─────────┘
                             │                         │
        Citus routes by shard key (e.g., room_id)      │
                             │                         │
        ┌─────────┬─────────┬┴────────┐       ┌─────────┬─────────┬┴────────┐
        │Worker A1│Worker A2│Worker A3│       │Worker B1│Worker B2│Worker B3│
        └─────────┴─────────┴─────────┘       └─────────┴─────────┴─────────┘
              ↑         ↑         ↑                 ↑         ↑         ↑
         Shard placements (RF=2)              Shard placements (RF=2)
```

### Key Features

- ✅ **Multiple active writers** (2 coordinators)
- ✅ **No write conflicts** (deterministic data partitioning)
- ✅ **Horizontal write scaling** by adding clusters
- ✅ **Blast-radius isolation** (cluster failures are isolated)
- ✅ **High throughput** for multi-tenant applications

### Use Cases

- Multi-tenant SaaS applications
- Chat applications with room-based partitioning
- E-commerce with customer-based sharding
- Any workload requiring write scale-out

---

## ⚖️ Active-Passive Deployment

**Path:** `active-passive-deployment/`

### What It Is

A **single Citus cluster** with **coordinator high-availability** using Patroni for automatic failover. Provides a unified database endpoint with fault-tolerant coordinator layer.

### Architecture Diagram

```
                                    Clients
                                        │
                            ┌───────────▼───────────┐
                            │      HAProxy          │
                            │   (Load Balancer)     │
                            │    Port: 5000         │
                            └───────────┬───────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
            ┌───────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
            │  Coordinator 1  │ │  Coordinator 2  │ │  Coordinator 3  │
            │   (Patroni)     │ │   (Patroni)     │ │   (Patroni)     │
            │    Primary      │ │   Standby       │ │   Standby       │
            └────────┬────────┘ └─────────────────┘ └─────────────────┘
                     │
                     │ (Citus routes by shard key)
                     │
        ┌────────────┼────────────┬─────────────────┐
        │            │            │                 │
   ┌────▼────┐ ┌─────▼────┐ ┌─────▼────┐      ┌────▼────┐
   │Worker 1 │ │Worker 2  │ │Worker 3  │ ...  │Worker N │
   └─────────┘ └──────────┘ └──────────┘      └─────────┘
        ↑            ↑            ↑                 ↑
   Shard placements distributed across workers (RF≥2)
```

### Key Features

- ✅ **Single database endpoint** (unified view of all data)
- ✅ **Automatic coordinator failover** (Patroni + HAProxy)
- ✅ **Zero-downtime coordinator maintenance**
- ✅ **Simple application integration** (standard PostgreSQL connection)
- ✅ **Cross-tenant analytics** without federation complexity

### Use Cases

- Traditional OLTP applications requiring HA
- Applications needing cross-tenant reporting
- Existing apps migrating to distributed PostgreSQL
- Workloads requiring single-database simplicity

---

## 📊 Comparison Matrix

| Feature | Active-Active | Active-Passive |
|---------|---------------|-----------------|
| **Write Scalability** | ✅ Multiple writers | ⚠️ Single writer |
| **Single Endpoint** | ❌ App-level routing | ✅ HAProxy + Patroni |
| **Cross-Tenant Queries** | ❌ Requires federation | ✅ Native support |
| **Coordinator HA** | ❌ Manual failover | ✅ Automatic failover |
| **Complexity** | 🔶 Medium (app routing) | 🔶 Medium (Patroni setup) |
| **Fault Isolation** | ✅ Per-cluster isolation | ⚠️ Single point of failure |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install psycopg2-binary

# Ensure Docker & Docker Compose are installed
docker --version
docker-compose --version
```

### For Active-Active Setup

```bash
# Clean any existing containers
make clean-active

# Start dual-cluster setup
make prepare-active

# Run the demo application
make run-active

# Restart everything
make restart-active
```

### For Active-Passive Setup

```bash
# Clean any existing containers
make clean-passive

# Start Patroni HA cluster
make prepare-passive

# Run the demo application
make run-passive

# Restart everything
make restart-passive
```

---

## 🛠️ Available Make Commands

### Active-Active Commands

```bash
make clean-active      # Clean up active-active containers and volumes
make prepare-active    # Start dual Citus cluster (Cluster A + B)
make run-active        # Run active-active demo with data partitioning
make restart-active    # Full restart (clean + prepare)
```

### Active-Passive Commands

```bash
make clean-passive     # Clean up active-passive containers and volumes
make prepare-passive   # Start Patroni HA cluster with 3 coordinators
make run-passive       # Run active-passive demo with HA testing
make restart-passive   # Full restart (clean + prepare)
```

---

## 🧪 Testing Scenarios

### Active-Active Fault Tolerance

```bash
# Test cluster isolation
docker stop coord_a worker_a1 worker_a2
# Cluster B continues serving traffic for its tenants

# Test data partitioning
python active-active-deployment/active-active-demo.py
# Observe tenant routing to different clusters
```

### Active-Passive High Availability

```bash
# Test coordinator failover
docker stop active-passive-deployment-coord-1-1
# HAProxy automatically routes to backup coordinator

# Check Patroni status
docker exec -it active-passive-deployment-coord-2-1 patronictl -c /etc/patroni.yml list
```

---

## 📈 When to Choose Which?

### Choose **Active-Active** If

- You need **write scale-out** beyond single coordinator capacity
- Your application can implement **tenant-based routing**
- You want **blast-radius isolation** between customer groups
- **Cross-tenant analytics** can be handled by separate ETL/BI layer

### Choose **Active-Passive** If

- You need a **single database endpoint** for simplicity
- Your application requires **cross-tenant joins/analytics**
- You want **transparent coordinator failover**
- Write load fits within single coordinator capacity

---

## 📝 Configuration Files

| File | Purpose |
|------|---------|
| `active-active-deployment/docker-compose.yml` | Dual cluster setup (6 workers + 2 coordinators) |
| `active-passive-deployment/docker-compose.yml` | Patroni HA setup (3 coordinators + HAProxy) |
| `*/init.sql` | Database schema initialization |
| `*/citus-config.sql` | Citus-specific configuration |
| `*/*demo.py` | Demo applications showing usage patterns |

---

## 🔧 Customization

### Scaling Active-Active

```yaml
# Add more clusters in docker-compose.yml
coord_c:
  image: citusdata/citus:latest
  # ... cluster C configuration
```

### Scaling Active-Passive

```yaml
# Add more workers to existing cluster
worker4:
  image: citusdata/citus:latest
  # ... worker configuration
```

---

**🎯 Both configurations provide production-ready, fault-tolerant PostgreSQL setups for different scaling requirements.**
