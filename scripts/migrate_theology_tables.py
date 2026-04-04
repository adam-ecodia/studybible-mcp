#!/usr/bin/env python3
"""Migrate heiser_* tables to unified theology_* tables.

This is a one-time migration that:
1. Renames heiser_content → theology_content (+ adds author index)
2. Renames heiser_verse_index → theology_verse_index
3. Renames heiser_themes → theology_themes (renames heiser_key_works → key_works)
4. Renames heiser_theme_index → theology_theme_index
5. Creates legacy views so heiser_content_id FKs still resolve
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def get_db_path() -> Path:
    return Path(__file__).resolve().parent.parent / "db" / "study_bible.db"


def migrate(db_path: Path):
    conn = sqlite3.connect(str(db_path))

    # Check if migration is needed
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    if "theology_content" in tables:
        print("Migration already done — theology_content table exists.")
        conn.close()
        return

    if "heiser_content" not in tables:
        print("No heiser_content table found — nothing to migrate.")
        print("The new schema will be created on next server start.")
        conn.close()
        return

    print("Migrating heiser_* tables to theology_* tables...")

    # 1. Rename tables
    conn.execute("ALTER TABLE heiser_content RENAME TO theology_content")
    print("  heiser_content → theology_content")

    conn.execute("ALTER TABLE heiser_verse_index RENAME TO theology_verse_index")
    print("  heiser_verse_index → theology_verse_index")

    conn.execute("ALTER TABLE heiser_themes RENAME TO theology_themes")
    print("  heiser_themes → theology_themes")

    conn.execute("ALTER TABLE heiser_theme_index RENAME TO theology_theme_index")
    print("  heiser_theme_index → theology_theme_index")

    # 2. Rename heiser_key_works → key_works in theology_themes
    conn.execute("ALTER TABLE theology_themes RENAME COLUMN heiser_key_works TO key_works")
    print("  heiser_key_works → key_works")

    # 3. Add author index
    conn.execute("CREATE INDEX IF NOT EXISTS idx_theology_author ON theology_content(source_author)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_theology_source ON theology_content(source_work)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_theology_vi_ref ON theology_verse_index(reference)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_theology_vi_book ON theology_verse_index(book)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_theology_ti_theme ON theology_theme_index(theme_key)")
    print("  Created new indexes")

    # 4. Create legacy views for FK compatibility
    conn.execute("CREATE VIEW IF NOT EXISTS heiser_content AS SELECT * FROM theology_content")
    conn.execute("CREATE VIEW IF NOT EXISTS heiser_verse_index AS SELECT * FROM theology_verse_index")
    conn.execute("CREATE VIEW IF NOT EXISTS heiser_themes AS SELECT * FROM theology_themes")
    conn.execute("CREATE VIEW IF NOT EXISTS heiser_theme_index AS SELECT * FROM theology_theme_index")
    print("  Created legacy views")

    conn.commit()

    # Verify
    print("\nVerification:")
    for table in ["theology_content", "theology_verse_index", "theology_themes", "theology_theme_index"]:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        print(f"  {table}: {row[0]} rows")

    conn.close()
    print("\nMigration complete!")


def main():
    db_path = get_db_path()
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        sys.exit(1)
    migrate(db_path)


if __name__ == "__main__":
    main()
