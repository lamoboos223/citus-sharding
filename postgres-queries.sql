SELECT * FROM users where city_id = 8;


SELECT logicalrelid, partmethod, colocationid 
FROM pg_dist_partition 
WHERE logicalrelid = 'users'::regclass;


SELECT count(*) FROM users;

SELECT undistribute_table('users');

SELECT create_distributed_table('users', 'city_id');

SELECT 
    s.logicalrelid::text as table_name,
    s.shardid,
    p.placementid,
    n.nodename,
    n.nodeport
FROM pg_dist_shard s
JOIN pg_dist_placement p ON s.shardid = p.shardid
JOIN pg_dist_node n ON p.groupid = n.groupid
WHERE s.logicalrelid = 'users'::regclass;


SELECT get_shard_id_for_distribution_column('users', 8);




SELECT 
    s.shardid,
    n.nodename,
    n.nodeport
FROM pg_dist_shard s
JOIN pg_dist_placement p ON s.shardid = p.shardid
JOIN pg_dist_node n ON p.groupid = n.groupid
WHERE s.logicalrelid = 'users'::regclass
AND s.shardid = (SELECT get_shard_id_for_distribution_column('users', 72));



SELECT * FROM pg_dist_shard_placement 
WHERE shardid = 102268;



SELECT 
    s.logicalrelid::text as table_name,
    s.shardid,
    n.nodename,
    n.nodeport
FROM pg_dist_shard s
JOIN pg_dist_placement p ON s.shardid = p.shardid
JOIN pg_dist_node n ON p.groupid = n.groupid
WHERE s.logicalrelid = 'users'::regclass
ORDER BY s.shardid;

