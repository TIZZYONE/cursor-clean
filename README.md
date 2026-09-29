# cursor-clean

[![PyPI](https://img.shields.io/pypi/v/cursor-clean.svg)](https://pypi.org/project/cursor-clean/)

Clean Cursor Roaming data on Windows (old chats + unused agent versions).

```bash
pip install -U cursor-clean

# language flag works before or after the subcommand
cursor-clean clean --lang zh
cursor-clean --lang zh clean -y

# default keep-days = 45
cursor-clean scan --lang zh
cursor-clean clean --lang zh --keep-days 45
```

**Quit Cursor before VACUUM** (shrinking `state.vscdb`). If Cursor is running, `clean` still removes agents/chats and skips VACUUM — re-run `cursor-clean vacuum` after quit.

Safe to re-run: already-deleted agents/chats are skipped.

Never deletes `state.vscdb.backup`. MIT License.
