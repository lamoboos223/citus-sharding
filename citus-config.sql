-- Citus configuration for active-active setup
-- This file is loaded after init.sql to configure Citus settings

-- Set replication factor to 2 for active-active (each shard on 2 workers)
ALTER SYSTEM SET citus.shard_replication_factor = 2;

-- Set shard count to 4 (matches our 4 workers)
ALTER SYSTEM SET citus.shard_count = 4;

-- Enable automatic failover
ALTER SYSTEM SET citus.enable_repartition_joins = on;

-- Optimize for active-active reads
ALTER SYSTEM SET citus.task_assignment_policy = 'round-robin';

-- Reload configuration
SELECT pg_reload_conf(); 