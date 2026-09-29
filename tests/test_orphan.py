"""Orphan session KV cleanup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from cursor_clean.cleaner import count_orphan_composers, delete_orphan_composer_kv
from cursor_clean.i18n import set_lang


def _mk_db(tmp: Path) -> Path:
    db = tmp / "state.vscdb"
    con = sqlite3.connect(str(db))
    con.execute(
        "CREATE TABLE composerHeaders (composerId TEXT PRIMARY KEY, lastUpdatedAt INTEGER)"
    )
    con.execute("CREATE TABLE cursorDiskKV (key TEXT PRIMARY KEY, value BLOB)")
    live = "11111111-1111-1111-1111-111111111111"
    orphan = "22222222-2222-2222-2222-222222222222"
    con.execute("INSERT INTO composerHeaders VALUES (?, ?)", (live, 1))
    con.executemany(
        "INSERT INTO cursorDiskKV(key, value) VALUES (?, ?)",
        [
            (f"bubbleId:{live}:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", b"live"),
            (f"bubbleId:{orphan}:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", b"dead"),
            (f"composerData:{orphan}", b"dead-data"),
            (f"agentKv:blob:{'a'*64}", b"keep-me"),
        ],
    )
    con.commit()
    con.close()
    return db


def test_count_and_delete_orphans(tmp_path: Path) -> None:
    set_lang("en")
    db = _mk_db(tmp_path)
    assert count_orphan_composers(db) == 1
    n_comp, n_kv = delete_orphan_composer_kv(db, progress=lambda _m: None)
    assert n_comp == 1
    assert n_kv == 2
    con = sqlite3.connect(str(db))
    keys = {r[0] for r in con.execute("SELECT key FROM cursorDiskKV")}
    con.close()
    assert any(k.startswith("bubbleId:11111111") for k in keys)
    assert not any("22222222" in k for k in keys)
    assert any(k.startswith("agentKv:") for k in keys)
    assert count_orphan_composers(db) == 0
