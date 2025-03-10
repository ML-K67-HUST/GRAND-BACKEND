CREATE TABLE users (
    userid SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tasks (
    userid UUID NOT NULL,
    taskid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    taskname TEXT NOT NULL,
    taskdescription TEXT NOT NULL,
    color TEXT DEFAULT 'blue',
    starttime TIMESTAMP NOT NULL,
    endtime TIMESTAMP NOT NULL,
    status TEXT NOT NULL,
    priority INT DEFAULT 3
);

CREATE TABLE password_reset_otp (
    id SERIAL PRIMARY KEY,
    userid INT NOT NULL,
    otp VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userid) REFERENCES users(userid) ON DELETE CASCADE
);
