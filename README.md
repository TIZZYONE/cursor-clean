# cursor-clean

[![PyPI](https://img.shields.io/pypi/v/cursor-clean.svg)](https://pypi.org/project/cursor-clean/)

Clean Cursor Roaming data on Windows: old chats, orphan session KV, `state.vscdb.backup`, unused agent versions.

```bash
pip install -U cursor-clean

cursor-clean scan --lang zh
cursor-clean clean --lang zh -y
# keep backup:  cursor-clean clean --keep-backup -y
```

**Defaults:** delete `state.vscdb.backup`, delete orphan session KV (`bubbleId` / `composerData` / … whose `composerId` is not in `composerHeaders`), age-based chats (`--keep-days`, default 45), then VACUUM if Cursor is quit and free disk ≥ ~1× DB size.

**agentKv:** do not wipe blindly. In Cursor run `Developer: GC Agent KV Blobs` (Ctrl+Shift+P). Compaction needs about **1× `state.vscdb` free disk** ([forum](https://forum.cursor.com/t/state-vscdb-grows-to-30gb-due-to-bubbleid-agentkv-entries/167641), [temp space](https://forum.cursor.com/t/gc-agent-kv-blobs-temporarily-consumed-62-gb-of-free-space-while-compacting-a-29-gb-state-vscdb/172165)). `scan` / `clean` print free vs need.

**Quit Cursor before VACUUM.** Safe to re-run. MIT License.
