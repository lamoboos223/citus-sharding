-- Replicate each shard to 2 workers
ALTER SYSTEM SET citus.shard_replication_factor = 2;

-- Exactly 3 shards
ALTER SYSTEM SET citus.shard_count = 3;

-- Optional read scaling
-- ALTER SYSTEM SET citus.use_secondary_nodes = on;

SELECT pg_reload_conf();
