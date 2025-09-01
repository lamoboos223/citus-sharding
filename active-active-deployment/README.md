# Active-Active (Segmented / Partitioned) with Citus

## What this is

An **app-level active-active** design using **two independent Citus clusters**, both live.
Each cluster is **authoritative for a different slice** of data (e.g., by `tenant_id` / `partner_id` / `room_id` hash).
Both coordinators accept writes, **but never to the same rows**. No conflict resolution is needed.

```
Clients → App Router (hash/lookup by tenant)
             ├──────────────► Cluster A (Coord A + Workers A1..A3)
             └──────────────► Cluster B (Coord B + Workers B1..B3)
     (each cluster: sharded tables, RF=2, 3 shards, colocated by room_id)
```

## How routing works

* The **App Router** chooses the cluster via a **deterministic rule** (e.g., consistent hash of `tenant_id`), or a **tenant→cluster** mapping table.
* **Stickiness is mandatory**: the same tenant must always go to the same cluster.
* Within a cluster, Citus routes by the shard key; each shard has **replicated placements (RF≥2)** across workers.

## What you get

* **Multiple writers** (the two coordinators), with **no cross-cluster write conflicts**.
* **Horizontal write capacity** by adding clusters and partitioning tenants.
* **Blast-radius isolation**: a failure in one cluster only impacts its tenants.

## What you don’t get

* A **single database endpoint** with all data (DBeaver will see one cluster at a time).
  To view/join everything, add a **read federation layer** (e.g., `postgres_fdw`) or stream to a **BI/lake** (ETL).
* **True multi-master (same rows writable from both sites)** — that’s a different tech (e.g., PGD/BDR), not Citus.

## Failure behavior (per cluster)

* **Worker down**: surviving shard placement serves traffic; later **repair/rebalance** to restore RF.
* **Coordinator down**: that cluster is unavailable unless you add **coordinator HA** (e.g., Patroni + LB).
  The other cluster remains fully functional.

## When to use this

* You need **higher write throughput** and **fault isolation** across tenant groups.
* You can tolerate **cross-tenant analytics** being served via a separate **read layer** (FDW/ETL) instead of the OLTP path.

---

*If later you need a **single endpoint** with the whole dataset and HA, switch to **one Citus cluster + Patroni** for coordinator failover (active-passive writer)*

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
        Citus routes by shard key (e.g., room_id)      │________________________
                             │                                                  |
        ┌───────────────┬────┴─────┬───────────────┐       ┌───────────────┬────┴─────┬───────────────┐
        │   Worker A1   │ Worker A2│   Worker A3   │       │   Worker B1   │ Worker B2│   Worker B3   │
        └───────────────┴──────────┴───────────────┘       └───────────────┴──────────┴───────────────┘
                  ↑            ↑            ↑                        ↑            ↑            ↑
                  │            │            │                        │            │            │
          Shard placements (RF=2) per cluster                Shard placements (RF=2) per cluster
          e.g., in A:                                        e.g., in B:
            S#102008 → A1, A2                                  S#102008 → B1, B2
            S#102009 → A2, A3                                  S#102009 → B2, B3
            S#102010 → A1, A3                                  S#102010 → B1, B3
```
