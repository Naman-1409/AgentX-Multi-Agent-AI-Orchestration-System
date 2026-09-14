-- Schema DDL for Task To-Do App with item list and completion checkboxes
CREATE TABLE IF NOT EXISTS task_to_do_app_with_item_list_and_completion_checkboxes_records (
    id VARCHAR(64) PRIMARY KEY,
    name TEXT NOT NULL,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_task_to_do_app_with_item_list_and_completion_checkboxes_created ON task_to_do_app_with_item_list_and_completion_checkboxes_records(created_at);