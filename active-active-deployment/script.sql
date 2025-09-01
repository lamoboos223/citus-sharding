-- connect to Coordinator A or B


select count(*) from rooms;

select count(*) from room_members;

select count(*) from messages;

-- 1) Mark the dead node inactive so coordinator stops sending work there
SELECT citus_disable_node('worker_a2', 5432, synchronous := true);

-- 2) Verify metadata says it’s inactive
SELECT nodename, nodeport, isactive FROM pg_dist_node ORDER BY 1,2;


-- See which shards still point at the dead node
SELECT s.logicalrelid::regclass AS table, s.shardid, n.nodename, n.nodeport
FROM pg_dist_shard s
JOIN pg_dist_placement p USING (shardid)
JOIN pg_dist_node n ON p.groupid = n.groupid
WHERE n.nodename = 'worker_a2' AND n.nodeport = 5432
ORDER BY 1,2;

-- Confirm every shard has 2 placements (RF=2):
SELECT s.logicalrelid::regclass AS table, s.shardid, COUNT(*) AS placements
FROM pg_dist_shard s
JOIN pg_dist_placement p USING (shardid)
GROUP BY 1,2
HAVING COUNT(*) < 2;  -- should return 0 rows when fully healed





