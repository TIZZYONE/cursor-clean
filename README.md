[![PyPI](https://img.shields.io/pypi/v/cursor-clean.svg)](https://pypi.org/project/cursor-clean/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# cursor-clean

轻量命令行工具：清理 Cursor 在 Windows 上占用的 Roaming 数据。

- 删除超过保留期的 Composer / Agent 聊天（默认 **90** 天，可改）
- 删除旧的 `cursor-agent` 版本（只留最新）
- 可选清理 `CachedData` / `logs`
- **永不删除** `state.vscdb.backup`
- **零第三方依赖**，无本地数据库；内置中/英界面

## Install

```bash
pip install -U cursor-clean
```

Python 3.9+

## Usage

**请先完全退出 Cursor**（任务管理器中确认没有 `Cursor.exe`）。

```bash
# 首次可选择语言；也可用 --lang zh|en 或环境变量 CURSOR_CLEAN_LANG
cursor-clean scan
cursor-clean scan --lang zh
cursor-clean clean --lang zh

# 非交互
cursor-clean clean -y --lang zh --keep-days 90

# 只删旧 agent / 只压缩数据库
cursor-clean clean-agents -y --lang zh
cursor-clean vacuum --lang zh
```

## Safety

1. 先 `scan` 再 `clean`
2. 清理前退出 Cursor，否则 VACUUM 可能卡住
3. 保留 backup
4. 不写删除日志、不建自己的数据库

## Links

- PyPI: https://pypi.org/project/cursor-clean/
- GitHub: https://github.com/TIZZYONE/cursor-clean

## License

MIT
