-- connect to haproxy
-- psql -h localhost -p 5000 -U postgres -d postgres
-- password: mypass

SELECT * FROM citus_get_active_worker_nodes();

select count(*) from rooms

-- Peek placements for one table
SELECT shardid, shardstate, nodename, nodeport
FROM pg_dist_shard s
JOIN pg_dist_placement p USING(shardid)
JOIN pg_dist_node n ON n.groupid=p.groupid
WHERE s.logicalrelid='rooms'::regclass
ORDER BY shardid, nodename, nodeport;



