-- init.sql

-- Rooms table
CREATE TABLE IF NOT EXISTS rooms (
    id BIGINT PRIMARY KEY,
    room_type SMALLINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Room members table (no foreign keys for active-active compatibility)
CREATE TABLE IF NOT EXISTS room_members (
    id BIGINT,
    room_id BIGINT NOT NULL,
    member_id BIGINT NOT NULL,
    is_pinned BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    is_muted BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    is_locked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, room_id)
    -- Note: Foreign keys removed for active-active replication (factor=2)
);

-- Messages table (no foreign keys for active-active compatibility)
CREATE TABLE IF NOT EXISTS messages (
    id BIGINT,
    room_id BIGINT NOT NULL,
    message_type SMALLINT NOT NULL,
    text TEXT,
    is_by_partner BOOLEAN DEFAULT FALSE,
    local_timestamp TIMESTAMPTZ,
    server_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    status SMALLINT,
    is_deleted BOOLEAN DEFAULT FALSE,
    action SMALLINT,
    parent_message_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, room_id)
    -- Note: Foreign keys removed for active-active replication (factor=2)
);
