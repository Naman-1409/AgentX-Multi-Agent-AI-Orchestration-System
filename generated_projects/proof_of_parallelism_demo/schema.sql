-- SQLite / PostgreSQL Relational Schema for Design Database Schema & Data Models
CREATE TABLE IF NOT EXISTS items (
    id VARCHAR(64) PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    completed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_items_created ON items(created_at);
CREATE INDEX IF NOT EXISTS idx_items_completed ON items(completed);