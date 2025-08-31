-- Query messages in a specific room
SELECT * FROM messages WHERE room_id = 8;

-- Check distribution configuration for rooms table
SELECT logicalrelid, partmethod, colocationid 
FROM pg_dist_partition 
WHERE logicalrelid = 'rooms'::regclass;

-- Count total rooms
SELECT count(*) FROM rooms;

-- Undistribute rooms table (if needed for reconfiguration)
SELECT undistribute_table('rooms');

-- Create distributed tables with room_id as sharding key
SELECT create_distributed_table('rooms', 'id');
SELECT create_distributed_table('room_members', 'room_id');
SELECT create_distributed_table('messages', 'room_id');

-- Show shard distribution for rooms table
SELECT 
    s.logicalrelid::text as table_name,
    s.shardid,
    p.placementid,
    n.nodename,
    n.nodeport
FROM pg_dist_shard s
JOIN pg_dist_placement p ON s.shardid = p.shardid
JOIN pg_dist_node n ON p.groupid = n.groupid
WHERE s.logicalrelid = 'rooms'::regclass;

-- Get shard ID for a specific room
SELECT get_shard_id_for_distribution_column('rooms', 8);

-- Find which shard and node contains a specific room
SELECT 
    s.shardid,
    n.nodename,
    n.nodeport
FROM pg_dist_shard s
JOIN pg_dist_placement p ON s.shardid = p.shardid
JOIN pg_dist_node n ON p.groupid = n.groupid
WHERE s.logicalrelid = 'rooms'::regclass
AND s.shardid = (SELECT get_shard_id_for_distribution_column('rooms', 72));

-- Check shard placement details for a specific shard
SELECT * FROM pg_dist_shard_placement 
WHERE shardid = 102268;

-- Show all shards and their locations for rooms table
SELECT 
    s.logicalrelid::text as table_name,
    s.shardid,
    n.nodename,
    n.nodeport
FROM pg_dist_shard s
JOIN pg_dist_placement p ON s.shardid = p.shardid
JOIN pg_dist_node n ON p.groupid = n.groupid
WHERE s.logicalrelid = 'rooms'::regclass
ORDER BY s.shardid;

-- Show distribution for all chat tables
SELECT 
    s.logicalrelid::text as table_name,
    s.shardid,
    n.nodename,
    n.nodeport
FROM pg_dist_shard s
JOIN pg_dist_placement p ON s.shardid = p.shardid
JOIN pg_dist_node n ON p.groupid = n.groupid
WHERE s.logicalrelid IN ('rooms'::regclass, 'room_members'::regclass, 'messages'::regclass)
ORDER BY s.logicalrelid, s.shardid;

-- Query to test co-location: get room info with member count and message count
SELECT 
    r.id as room_id,
    r.room_type,
    COUNT(DISTINCT rm.member_id) as member_count,
    COUNT(DISTINCT m.id) as message_count
FROM rooms r
LEFT JOIN room_members rm ON r.id = rm.room_id AND rm.is_deleted = false
LEFT JOIN messages m ON r.id = m.room_id AND m.is_deleted = false
WHERE r.id = 8
GROUP BY r.id, r.room_type;

