#!/usr/bin/env python3
"""Import Bradley theological scholarship content into the unified theology tables."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from study_bible_mcp.parsers.heiser import parse_themes_file, parse_heiser_content_file


def get_db_path() -> Path:
    return Path(__file__).resolve().parent.parent / "db" / "study_bible.db"


def main():
    db_path = get_db_path()
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        sys.exit(1)

    data_dir = Path(__file__).resolve().parent.parent / "data" / "bradley"
    conn = sqlite3.connect(str(db_path))

    print("=" * 60)
    print("Importing Bradley Theological Content")
    print("=" * 60)

    # 1. Import themes
    themes_path = data_dir / "themes.json"
    if themes_path.exists():
        themes = parse_themes_file(themes_path)
        count = 0
        for theme in themes:
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO theology_themes
                       (theme_key, theme_label, description, parent_theme, key_works)
                       VALUES (?, ?, ?, ?, ?)""",
                    (theme["theme_key"], theme["theme_label"], theme["description"],
                     theme["parent_theme"], theme["key_works"]),
                )
                count += 1
            except sqlite3.Error as e:
                print(f"  Warning: Failed to insert theme {theme['theme_key']}: {e}")
        conn.commit()
        print(f"\n[Themes] Imported {count} themes")

    # 2. Import content files
    content_dir = data_dir / "content"
    total_entries = 0
    total_refs = 0
    total_themes = 0
    json_files = sorted(content_dir.glob("*.json"))
    print(f"\n[Content] Found {len(json_files)} content files")

    for filepath in json_files:
        entries = 0
        refs = 0
        themes = 0

        for content_entry, verse_refs, theme_keys in parse_heiser_content_file(filepath):
            try:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO theology_content
                       (source_work, source_author, source_type, chapter_or_episode,
                        title, content_summary, content_detail, page_range, url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (content_entry["source_work"], content_entry["source_author"],
                     content_entry["source_type"], content_entry["chapter_or_episode"],
                     content_entry["title"], content_entry["content_summary"],
                     content_entry["content_detail"], content_entry["page_range"],
                     content_entry["url"]),
                )
                if cursor.rowcount == 0:
                    row = conn.execute(
                        """SELECT id FROM theology_content
                           WHERE source_work = ? AND chapter_or_episode IS ? AND title = ?""",
                        (content_entry["source_work"], content_entry["chapter_or_episode"],
                         content_entry["title"]),
                    ).fetchone()
                    content_id = row[0] if row else None
                else:
                    content_id = cursor.lastrowid
                    entries += 1

                if content_id is None:
                    continue

                for vref in verse_refs:
                    try:
                        conn.execute(
                            """INSERT OR IGNORE INTO theology_verse_index
                               (content_id, reference, book, chapter, verse, relevance)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (content_id, vref["reference"], vref["book"],
                             vref["chapter"], vref["verse"], vref["relevance"]),
                        )
                        refs += 1
                    except sqlite3.Error:
                        pass

                for theme_key in theme_keys:
                    try:
                        conn.execute(
                            """INSERT OR IGNORE INTO theology_theme_index
                               (theme_key, content_id, reference)
                               VALUES (?, ?, NULL)""",
                            (theme_key, content_id),
                        )
                        themes += 1
                    except sqlite3.Error:
                        pass

            except sqlite3.Error as e:
                print(f"  Warning: Failed to insert entry '{content_entry.get('title', '?')}': {e}")

        conn.commit()
        total_entries += entries
        total_refs += refs
        total_themes += themes
        print(f"  {filepath.name}: {entries} entries, {refs} verse refs, {themes} theme links")

    print(f"\n[Totals] {total_entries} entries, {total_refs} verse refs, {total_themes} theme links")

    # Summary
    print("\n" + "=" * 60)
    for table in ["theology_themes", "theology_content", "theology_verse_index", "theology_theme_index"]:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        print(f"  {table}: {row[0]} rows")

    # Show per-author breakdown
    print("\nPer-author breakdown:")
    for row in conn.execute("SELECT source_author, COUNT(*) FROM theology_content GROUP BY source_author").fetchall():
        print(f"  {row[0]}: {row[1]} entries")
    print("=" * 60)

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
