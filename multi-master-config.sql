-- Multi-Master Citus configuration
-- This file configures additional settings for multi-coordinator setup

-- Enable cross-coordinator queries
ALTER SYSTEM SET citus.enable_repartition_joins = on;

-- Set coordinator assignment policy for better load distribution
ALTER SYSTEM SET citus.task_assignment_policy = 'round-robin';

-- Enable coordinator participation in query execution
ALTER SYSTEM SET citus.coordinator_aggregation_strategy = 'row-gather';

-- Configure timeout for cross-coordinator operations
ALTER SYSTEM SET citus.remote_task_check_interval = 1000;

-- Enable distributed deadlock detection
ALTER SYSTEM SET citus.distributed_deadlock_detection_factor = 2;

-- Configure connection pooling for coordinators
ALTER SYSTEM SET citus.max_intermediate_result_size = '1GB';

-- Use transactional metadata sync (valid option)
ALTER SYSTEM SET citus.metadata_sync_mode = 'transactional';

-- Optimize for multi-coordinator writes
ALTER SYSTEM SET citus.multi_task_query_log_level = 'debug1';

-- Allow reads from secondary nodes, but don't force it for writes
ALTER SYSTEM SET citus.use_secondary_nodes = 'never';

-- Configure replication for coordinator metadata
ALTER SYSTEM SET citus.replicate_reference_tables_on_activate = on;

-- Reload configuration
SELECT pg_reload_conf(); 