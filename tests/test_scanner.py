"""Unit tests that do not touch the real Cursor profile."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from cursor_clean.cleaner import delete_old_chats
from cursor_clean.format_utils import format_bytes
from cursor_clean.scanner import scan_agent_versions, scan_old_composers


def test_format_bytes() -> None:
    assert format_bytes(500) == "500 B"
    assert "KB" in format_bytes(2048)
    assert "MB" in format_bytes(5 * 1024 * 1024)


def test_scan_agent_versions(tmp_path: Path) -> None:
    versions = tmp_path / "versions"
    (versions / "2026.01.01-aaaa").mkdir(parents=True)
    (versions / "2026.09.18-bbbb").mkdir()
    (versions / ".tmp-junk").mkdir()
    (versions / "2026.01.01-aaaa" / "f.bin").write_bytes(b"1234")
    (versions / "2026.09.18-bbbb" / "f.bin").write_bytes(b"12345678")

    items = scan_agent_versions(versions)
    kept = [i for i in items if i.keep]
    assert len(kept) == 1
    assert kept[0].name == "2026.09.18-bbbb"
    deleted = [i for i in items if not i.keep]
    assert {i.name for i in deleted} == {"2026.01.01-aaaa", ".tmp-junk"}


def test_scan_old_composers(tmp_path: Path) -> None:
    db = tmp_path / "state.vscdb"
    con = sqlite3.connect(db)
    con.execute(
        """
        CREATE TABLE composerHeaders (
          composerId TEXT PRIMARY KEY,
          workspaceId TEXT,
          createdAt INTEGER,
          lastUpdatedAt INTEGER,
          isArchived INTEGER,
          isSubagent INTEGER,
          recency INTEGER,
          checkpointAt INTEGER,
          value TEXT,
          subagentTypeName TEXT
        )
        """
    )
    con.execute(
        "CREATE TABLE cursorDiskKV (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)"
    )
    now_ms = int(time.time() * 1000)
    old_ms = now_ms - 120 * 86400 * 1000
    old_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    new_id = "ffffffff-1111-2222-3333-444444444444"
    con.execute(
        "INSERT INTO composerHeaders(composerId, createdAt, lastUpdatedAt) VALUES (?,?,?)",
        (old_id, old_ms, old_ms),
    )
    con.execute(
        "INSERT INTO composerHeaders(composerId, createdAt, lastUpdatedAt) VALUES (?,?,?)",
        (new_id, now_ms, now_ms),
    )
    blob = b"x" * 1000
    con.execute(
        "INSERT INTO cursorDiskKV(key, value) VALUES (?, ?)",
        (f"composerData:{old_id}", blob),
    )
    con.execute(
        "INSERT INTO cursorDiskKV(key, value) VALUES (?, ?)",
        (f"bubbleId:{old_id}:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", blob),
    )
    con.execute(
        "INSERT INTO cursorDiskKV(key, value) VALUES (?, ?)",
        (f"composerData:{new_id}", blob),
    )
    con.commit()
    con.close()

    plan = scan_old_composers(db, keep_days=90, deep=True)
    assert plan.total_composers == 2
    assert plan.old_composers == 1
    assert plan.old_composer_ids == [old_id]
    assert plan.estimated_bytes == 2000

    headers, kv = delete_old_chats(db, plan, progress=lambda _m: None)
    assert headers == 1
    assert kv == 2
    plan2 = scan_old_composers(db, keep_days=90, deep=False)
    assert plan2.total_composers == 1
    assert plan2.old_composers == 0
