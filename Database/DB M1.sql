--Database Creation--
CREATE DATABASE behavior_guard_ai;

--Creating schemas--
CREATE SCHEMA core;
CREATE SCHEMA events;
CREATE SCHEMA features;
CREATE SCHEMA ml;
CREATE SCHEMA security;
CREATE SCHEMA audit;

--Tables in core schema--
CREATE TABLE core.departments (
    department_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE core.roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE core.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    department_id UUID REFERENCES core.departments(department_id),
    role_id UUID REFERENCES core.roles(role_id),
    hire_date DATE,
    status VARCHAR(20) CHECK (status IN ('active', 'terminated')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE core.devices (
    device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name VARCHAR(100) NOT NULL,
    device_type VARCHAR(50),
    assigned_user_id UUID REFERENCES core.users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

--Tables in events schema--
CREATE TABLE events.login_events (
    event_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES core.users(user_id),
    event_timestamp TIMESTAMP NOT NULL,
    login_status VARCHAR(20),
    ip_address INET,
    device_id UUID REFERENCES core.devices(device_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_login_user_time
ON events.login_events(user_id, event_timestamp);

CREATE TABLE events.file_events (
    event_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES core.users(user_id),
    event_timestamp TIMESTAMP NOT NULL,
    file_name TEXT,
    file_path TEXT,
    action VARCHAR(20),
    device_id UUID REFERENCES core.devices(device_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_file_user_time
ON events.file_events(user_id, event_timestamp);

CREATE TABLE events.email_events (
    event_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES core.users(user_id),
    event_timestamp TIMESTAMP NOT NULL,
    recipient_count INTEGER,
    external_recipient BOOLEAN,
    attachment_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_email_user_time
ON events.email_events(user_id, event_timestamp);

CREATE TABLE events.http_events (
    event_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES core.users(user_id),
    event_timestamp TIMESTAMP NOT NULL,
    url TEXT,
    domain VARCHAR(150),
    bytes_sent BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_http_user_time
ON events.http_events(user_id, event_timestamp);

--Tables in features schema--
CREATE TABLE features.user_daily_features (
    user_id UUID REFERENCES core.users(user_id),
    feature_date DATE NOT NULL,
    login_count INTEGER DEFAULT 0,
    failed_login_count INTEGER DEFAULT 0,
    file_access_count INTEGER DEFAULT 0,
    email_sent_count INTEGER DEFAULT 0,
    external_email_count INTEGER DEFAULT 0,
    http_request_count INTEGER DEFAULT 0,
    after_hours_activity INTEGER DEFAULT 0,
    feature_version INTEGER NOT NULL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, feature_date, feature_version)
);
CREATE INDEX idx_features_user_date
ON features.user_daily_features(user_id, feature_date);

--Tables in ml schema--
CREATE TABLE ml.models (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    algorithm VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ml.model_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID REFERENCES ml.models(model_id),
    feature_version INTEGER NOT NULL,
    training_start DATE,
    training_end DATE,
    hyperparameters JSONB,
    dataset_hash TEXT,
    model_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ml.training_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID REFERENCES ml.model_versions(version_id),
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--Tables in security schema--
CREATE TABLE security.risk_scores (
    score_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES core.users(user_id),
    model_version_id UUID REFERENCES ml.model_versions(version_id),
    score_timestamp TIMESTAMP NOT NULL,
    risk_score FLOAT,
    anomaly_flag BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_risk_user_time
ON security.risk_scores(user_id, score_timestamp);

CREATE TABLE security.alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES core.users(user_id),
    risk_score_id BIGINT REFERENCES security.risk_scores(score_id),
    severity VARCHAR(20),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--Tables in audit schema--
CREATE TABLE audit.experiment_tracking (
    experiment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_hash TEXT,
    feature_version INTEGER,
    model_version_id UUID REFERENCES ml.model_versions(version_id),
    git_commit_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--Roles in PostgreSQL--
DROP ROLE IF EXISTS db_admin;
CREATE ROLE db_admin WITH LOGIN PASSWORD 'admin_password';
CREATE ROLE backend_service WITH LOGIN PASSWORD 'backend_password';
CREATE ROLE ml_service WITH LOGIN PASSWORD 'ml_password';
CREATE ROLE read_only_analyst WITH LOGIN PASSWORD 'readonly_password';
GRANT ALL PRIVILEGES ON DATABASE behavior_guard_ai TO db_admin;
GRANT CONNECT ON DATABASE behavior_guard_ai TO backend_service;
GRANT CONNECT ON DATABASE behavior_guard_ai TO ml_service;
GRANT CONNECT ON DATABASE behavior_guard_ai TO read_only_analyst;
GRANT USAGE ON SCHEMA core, events, features, ml, security, audit TO backend_service, ml_service, read_only_analyst;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core, events, features, security TO backend_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA features, ml TO ml_service;
GRANT SELECT ON ALL TABLES IN SCHEMA core, events, features, security TO read_only_analyst;
ALTER DEFAULT PRIVILEGES IN SCHEMA core
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO backend_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA features
GRANT SELECT, INSERT, UPDATE ON TABLES TO ml_service;
