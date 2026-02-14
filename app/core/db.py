import sqlite3
import os
import json
from typing import List, Dict, Any, Optional

DB_PATH = "data/astromech.db"

class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._ensure_db()
        return cls._instance

    def _ensure_db(self):
        if not os.path.exists(os.path.dirname(DB_PATH)):
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._migrate_from_json()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Tasks Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                priority INTEGER DEFAULT 3,
                created_at TEXT,
                updated_at TEXT,
                result TEXT
            )
        """)

        # Scheduled Jobs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                task_prompt TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1
            )
        """)

        # Protocol Templates Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS protocol_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                default_priority INTEGER DEFAULT 3,
                prompt_template TEXT NOT NULL,
                created_at TEXT
            )
        """)
        
        self.conn.commit()

    def _migrate_from_json(self):
        """Migrate existing JSON data to SQLite if tables are empty."""
        cursor = self.conn.cursor()
        
        # Migrate Tasks
        cursor.execute("SELECT COUNT(*) FROM tasks")
        if cursor.fetchone()[0] == 0 and os.path.exists("data/tasks.json"):
            try:
                with open("data/tasks.json", "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                for t in tasks:
                    try:
                        cursor.execute("""
                            INSERT INTO tasks (id, title, description, status, priority, created_at, updated_at, result)
                            VALUES (:id, :title, :description, :status, :priority, :created_at, :updated_at, :result)
                        """, t)
                    except Exception:
                        pass
                print(f"Migrated {len(tasks)} tasks from JSON to SQLite.")
            except Exception as e:
                print(f"Failed to migrate tasks: {e}")

        # Migrate Cron Jobs
        cursor.execute("SELECT COUNT(*) FROM scheduled_jobs")
        if cursor.fetchone()[0] == 0 and os.path.exists("data/cron_jobs.json"):
            try:
                with open("data/cron_jobs.json", "r", encoding="utf-8") as f:
                    jobs = json.load(f)
                for j in jobs:
                    try:
                        cursor.execute("""
                            INSERT INTO scheduled_jobs (id, name, cron_expression, task_prompt, enabled)
                            VALUES (:id, :name, :cron_expression, :task_prompt, :enabled)
                        """, j)
                    except Exception:
                        pass
                print(f"Migrated {len(jobs)} cron jobs from JSON to SQLite.")
            except Exception as e:
                print(f"Failed to migrate cron jobs: {e}")

        self.conn.commit()

    def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        if status:
            cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC, created_at ASC", (status,))
        else:
            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def add_task(self, task_data: Dict[str, Any]):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (id, title, description, status, priority, created_at, updated_at, result)
            VALUES (:id, :title, :description, :status, :priority, :created_at, :updated_at, :result)
        """, task_data)
        self.conn.commit()

    def update_task_status(self, task_id: str, status: str, result: Optional[str] = None, updated_at: str = ""):
        cursor = self.conn.cursor()
        if result:
            cursor.execute("""
                UPDATE tasks SET status = ?, result = ?, updated_at = ? WHERE id = ?
            """, (status, result, updated_at, task_id))
        else:
            cursor.execute("""
                UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?
            """, (status, updated_at, task_id))
        self.conn.commit()

    def get_jobs(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM scheduled_jobs ORDER BY name ASC, cron_expression ASC, id ASC")
        return [dict(row) for row in cursor.fetchall()]

    def add_job(self, job_data: Dict[str, Any]):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO scheduled_jobs (id, name, cron_expression, task_prompt, enabled)
            VALUES (:id, :name, :cron_expression, :task_prompt, :enabled)
        """, job_data)
        self.conn.commit()

    def remove_job(self, job_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        if not updates:
            return False

        allowed_fields = {"name", "cron_expression", "task_prompt", "enabled"}
        filtered = {k: v for k, v in updates.items() if k in allowed_fields}
        if not filtered:
            return False

        assignments = ", ".join(f"{key} = ?" for key in filtered)
        values = list(filtered.values())
        values.append(job_id)

        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE scheduled_jobs SET {assignments} WHERE id = ?", values)
        self.conn.commit()
        return cursor.rowcount > 0

    # Protocol Templates
    def get_templates(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM protocol_templates ORDER BY name ASC")
        return [dict(row) for row in cursor.fetchall()]

    def add_template(self, template_data: Dict[str, Any]):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO protocol_templates (id, name, description, default_priority, prompt_template, created_at)
            VALUES (:id, :name, :description, :default_priority, :prompt_template, :created_at)
        """, template_data)
        self.conn.commit()

    def delete_template(self, template_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM protocol_templates WHERE id = ?", (template_id,))
        self.conn.commit()
        return cursor.rowcount > 0

db = DatabaseManager()
