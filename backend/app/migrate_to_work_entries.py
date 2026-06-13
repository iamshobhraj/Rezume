"""Database migration script: projects → work_entries.

Handles the table rename and column changes for the data model overhaul.
Run this once before starting the updated application.

Usage:
    cd /home/shobh/Projects/airesume/backend
    python -m app.migrate_to_work_entries
"""

import sqlite3
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def migrate(db_path: str = "data/airesume.db"):
    """Migrate the SQLite database from projects schema to work_entries schema."""
    
    if not os.path.exists(db_path):
        logger.info(f"No database found at {db_path}. Fresh start – no migration needed.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if migration is needed
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
    has_projects = cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='work_entries'")
    has_work_entries = cursor.fetchone() is not None
    
    if has_work_entries and not has_projects:
        logger.info("Already migrated. work_entries table exists, projects table does not.")
        conn.close()
        return
    
    if not has_projects and not has_work_entries:
        logger.info("No projects or work_entries table found. Fresh database – no migration needed.")
        conn.close()
        return
    
    logger.info("Starting migration: projects → work_entries")
    
    try:
        # 1. Create work_entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_entries (
                id VARCHAR PRIMARY KEY,
                entry_type VARCHAR(20) NOT NULL DEFAULT 'project',
                title VARCHAR NOT NULL,
                company VARCHAR,
                role VARCHAR,
                start_date VARCHAR,
                end_date VARCHAR,
                raw_text TEXT NOT NULL,
                priority INTEGER DEFAULT 3,
                github_url VARCHAR,
                created_at DATETIME
            )
        """)
        
        # 2. Copy data from projects → work_entries
        cursor.execute("SELECT * FROM projects")
        projects = cursor.fetchall()
        
        # Get column names from projects table
        cursor.execute("PRAGMA table_info(projects)")
        project_cols = [col[1] for col in cursor.fetchall()]
        
        for project in projects:
            row = dict(zip(project_cols, project))
            
            # Map project_type to entry_type
            project_type = row.get("project_type", "personal")
            entry_type_map = {
                "personal": "project",
                "work": "work_experience",
                "oss": "oss",
            }
            entry_type = entry_type_map.get(project_type, "project")
            
            # Parse date_range into start_date/end_date (best effort)
            date_range = row.get("date_range", "") or ""
            start_date = ""
            end_date = ""
            if date_range:
                # Try common formats: "Jan 2024 - Mar 2024", "2024 - Present", etc.
                parts = [p.strip() for p in date_range.replace("–", "-").split("-")]
                if len(parts) >= 2:
                    start_date = parts[0].strip()
                    end_date = parts[1].strip()
                elif len(parts) == 1:
                    start_date = parts[0].strip()
            
            cursor.execute("""
                INSERT OR REPLACE INTO work_entries 
                (id, entry_type, title, company, role, start_date, end_date, raw_text, priority, github_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["id"],
                entry_type,
                row["title"],
                row.get("company", ""),
                row.get("role", ""),
                start_date,
                end_date,
                row["raw_text"],
                row.get("priority", 3),
                row.get("github_url", ""),
                row.get("created_at", ""),
            ))
        
        logger.info(f"Migrated {len(projects)} projects → work_entries")
        
        # 3. Update chunks table: rename project_id → work_entry_id
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chunks'")
        has_chunks = cursor.fetchone() is not None
        
        if has_chunks:
            # Check if chunks already has work_entry_id column
            cursor.execute("PRAGMA table_info(chunks)")
            chunk_cols = [col[1] for col in cursor.fetchall()]
            
            if "project_id" in chunk_cols and "work_entry_id" not in chunk_cols:
                # SQLite doesn't support RENAME COLUMN in all versions, so we recreate
                cursor.execute("""
                    CREATE TABLE chunks_new (
                        id VARCHAR PRIMARY KEY,
                        work_entry_id VARCHAR NOT NULL,
                        chunk_text TEXT NOT NULL,
                        metadata_json TEXT,
                        qdrant_point_id VARCHAR,
                        created_at DATETIME,
                        FOREIGN KEY (work_entry_id) REFERENCES work_entries(id)
                    )
                """)
                
                cursor.execute("""
                    INSERT INTO chunks_new (id, work_entry_id, chunk_text, metadata_json, qdrant_point_id, created_at)
                    SELECT id, project_id, chunk_text, metadata_json, qdrant_point_id, created_at FROM chunks
                """)
                
                cursor.execute("DROP TABLE chunks")
                cursor.execute("ALTER TABLE chunks_new RENAME TO chunks")
                logger.info("Migrated chunks: project_id → work_entry_id")
            elif "work_entry_id" in chunk_cols:
                logger.info("chunks table already has work_entry_id column")
        
        # 4. Create user_skills table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                proficiency VARCHAR DEFAULT 'proficient'
            )
        """)
        logger.info("Created user_skills table")
        
        # 5. Drop old projects table
        cursor.execute("DROP TABLE IF EXISTS projects")
        logger.info("Dropped old projects table")
        
        conn.commit()
        logger.info("Migration complete!")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Try both possible DB paths
    db_path = "data/airesume.db"
    if not os.path.exists(db_path):
        db_path = "airesume.db"
    
    migrate(db_path)
