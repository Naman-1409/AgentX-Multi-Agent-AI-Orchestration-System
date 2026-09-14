-- Schema DDL for Task Management App with tasks and completion toggle
CREATE TABLE IF NOT EXISTS task_management_app_with_tasks_and_completion_toggle_records (
    id VARCHAR(64) PRIMARY KEY,
    name TEXT NOT NULL,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_task_management_app_with_tasks_and_completion_toggle_created ON task_management_app_with_tasks_and_completion_toggle_records(created_at);