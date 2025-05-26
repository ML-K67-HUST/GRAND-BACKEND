-- Database initialization script for TimeNest
-- This creates the basic tables needed for the application

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    userid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    userid UUID NOT NULL REFERENCES users(userid) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    color VARCHAR(7) DEFAULT '#3498DB',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled', 'blocked')),
    priority INTEGER DEFAULT 2 CHECK (priority >= 1 AND priority <= 5),
    category VARCHAR(50) DEFAULT 'other',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_time_range CHECK (end_time > start_time),
    CONSTRAINT valid_color_format CHECK (color ~ '^#[0-9A-Fa-f]{6}$')
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_tasks_userid ON tasks(userid);
CREATE INDEX IF NOT EXISTS idx_tasks_start_time ON tasks(start_time);
CREATE INDEX IF NOT EXISTS idx_tasks_end_time ON tasks(end_time);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert a test user for development
INSERT INTO users (userid, email, username, first_name, last_name, password_hash, is_active)
VALUES (
    '123e4567-e89b-12d3-a456-426614174000',
    'test@timenest.com',
    'testuser',
    'Test',
    'User',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5W', -- password: 'TestPassword123!'
    true
) ON CONFLICT (email) DO NOTHING;

-- Insert some test tasks for the test user
INSERT INTO tasks (userid, name, description, start_time, end_time, status, priority, category, color)
VALUES 
    (
        '123e4567-e89b-12d3-a456-426614174000',
        'Complete backend refactoring',
        'Implement clean architecture and modern patterns',
        '2024-01-15T09:00:00+00:00',
        '2024-01-15T17:00:00+00:00',
        'in_progress',
        4,
        'work',
        '#E74C3C'
    ),
    (
        '123e4567-e89b-12d3-a456-426614174000',
        'Write API documentation',
        'Create comprehensive documentation for all endpoints',
        '2024-01-16T10:00:00+00:00',
        '2024-01-16T15:00:00+00:00',
        'pending',
        3,
        'work',
        '#3498DB'
    ),
    (
        '123e4567-e89b-12d3-a456-426614174000',
        'Team meeting',
        'Weekly sync with development team',
        '2024-01-17T14:00:00+00:00',
        '2024-01-17T15:00:00+00:00',
        'pending',
        2,
        'meeting',
        '#9B59B6'
    )
ON CONFLICT DO NOTHING;

-- Grant permissions (if needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO timenest;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO timenest;

-- Print success message
DO $$
BEGIN
    RAISE NOTICE 'TimeNest database initialized successfully!';
    RAISE NOTICE 'Test user: test@timenest.com (password: TestPassword123!)';
    RAISE NOTICE 'Created % test tasks', (SELECT count(*) FROM tasks);
END $$; 