"""Lightweight i18n: in-memory message tables only (no database, no files)."""

from __future__ import annotations

import locale
import os
from typing import Any

Lang = str  # "zh" | "en"

_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "choose_lang": "Select language / 选择语言:\n  1) 中文\n  2) English\nEnter 1 or 2 [1]: ",
        "invalid_lang": "Invalid choice, using Chinese.",
        "cursor_running": (
            "Cursor is still running (check Task Manager for Cursor.exe).\n"
            "Fully quit Cursor, then retry. Or pass --force (VACUUM may hang)."
        ),
        "cursor_running_warn": (
            "WARNING: Cursor still appears to be running; VACUUM may hang on database lock."
        ),
        "data_root": "Cursor data: {path}",
        "state_db": "state.vscdb:        {size}",
        "state_backup": "state.vscdb.backup: {size}  (deleted by default)",
        "disk_free": "Free disk:          {free}  (VACUUM/GC need ~{need})",
        "disk_free_ok": "  headroom: OK for VACUUM / official GC compact",
        "disk_free_low": "  headroom: LOW — free ~{need} before VACUUM or Developer: GC Agent KV Blobs",
        "chats_title": "Chats / Composer",
        "keep_days": "  keep-days:     {days}",
        "cutoff": "  cutoff (UTC):  {cutoff}",
        "total": "  total:         {n}",
        "older": "  older:         {n}  (candidates)",
        "est_blobs": "  est. blobs:    {size}",
        "est_blobs_hint": "  est. blobs:    (use --deep for estimate; free space shows after VACUUM)",
        "chats_unavailable": "Chats / Composer: unavailable",
        "orphan_title": "Orphan session KV (composerId not in headers)",
        "orphan_count": "  orphan composers: {n}",
        "agents_title": "cursor-agent versions",
        "agents_none": "  (none found)",
        "keep": "KEEP ",
        "delete": "DELETE",
        "reclaimable": "  reclaimable: {size}",
        "cache_title": "Optional cache/logs",
        "warning": "WARNING: {msg}",
        "nothing": "Nothing to clean.",
        "planned": "Planned actions:",
        "plan_agents": "  - Delete {n} old agent version(s) ({size})",
        "plan_chats": "  - Delete {n} old chat(s)",
        "plan_orphans": "  - Delete orphan session KV ({n} composer(s))",
        "plan_backup": "  - Delete state.vscdb.backup ({size})",
        "plan_vacuum": "  - VACUUM state.vscdb (needs ~1× DB size free disk)",
        "plan_cache": "  - Clear CachedData/logs ({size})",
        "plan_keep_backup": "  - Keep state.vscdb.backup",
        "proceed": "Proceed? [y/N] ",
        "aborted": "Aborted.",
        "done": "Done.",
        "agents_removed": "  agents removed: {n} ({size})",
        "chats_removed": "  chats removed: {n} (kv rows: {kv})",
        "orphans_removed": "  orphan KV removed: {composers} composer(s), {kv} rows",
        "backup_removed": "  backup removed: {size}",
        "state_result": "  state.vscdb:   {before} -> {after} (freed {freed}){vacuum}",
        "vacuum_ok": "  [VACUUM ok]",
        "cache_freed": "  cache/logs:    {size}",
        "error": "ERROR: {msg}",
        "db_missing": "state.vscdb not found: {path}",
        "vacuum_failed": "VACUUM failed: {err}",
        "vacuum_retry": "Fully quit Cursor and retry.",
        "no_agents": "No old agent versions to delete.",
        "will_agents": "Will delete {n} version(s) ({size}), keep newest.",
        "agents_done": "Done. Removed {n} ({size}).",
        "progress_del_chats": "Deleting {n} old chat(s) ...",
        "progress_del_chats_done": "  chats done: {n}, kv rows: {kv}, {sec:.1f}s",
        "progress_vacuum": "VACUUM state.vscdb ({gb:.2f} GB) ...",
        "progress_vacuum_done": "  VACUUM done in {sec:.1f}s: {before:.2f} GB -> {after:.2f} GB",
        "progress_del_agents": "Deleting {n} old agent version(s) ...",
        "progress_agents_freed": "  agents freed {gb:.2f} GB",
        "progress_cache": "Clearing CachedData / logs ...",
        "progress_cache_done": "  cache/logs freed {mb:.1f} MB",
        "phase_agents": "=== [agents] remove {n} old version(s) ===",
        "phase_chats": "=== [chats] delete {n} old session(s) ===",
        "phase_orphans": "=== [orphans] delete session KV not in composerHeaders ===",
        "phase_backup": "=== [backup] delete state.vscdb.backup ({size}) ===",
        "phase_vacuum": "=== [vacuum] compact state.vscdb ({gb:.2f} GB) ===",
        "orphan_none": "  orphans: none",
        "orphan_done": "  orphans done: {composers} composer(s), {kv} rows, {sec:.1f}s",
        "backup_done": "  backup deleted ({size})",
        "agent_kv_title": "agentKv (use Cursor official GC — do not wipe blindly)",
        "agent_kv_count": "  rows:          {n}",
        "hint_gc": (
            "agentKv: in Cursor run  Developer: GC Agent KV Blobs  "
            "(Ctrl+Shift+P). Needs ~{need} free (now {free}). {status}"
        ),
        "hint_gc_ok": "Disk OK.",
        "hint_gc_low": "Free more disk first, or GC compact may fail.",
        "resume_safe": "Safe to re-run: already-removed items are skipped automatically.",
        "progress_size_note": (
            "Chat rows are removed now; file size drops after VACUUM (quit Cursor first)."
        ),
        "progress_vacuum_explain": (
            "Bar shows estimated % from elapsed time (VACUUM has no native progress). "
            "Ends at 100% when finished. Needs ~1× DB size free disk."
        ),
        "progress_wal_warn": "WARNING: wal is {gb:.2f} GB — quit Cursor fully before VACUUM.",
        "progress_checkpoint": "wal_checkpoint(TRUNCATE) ...",
        "agent_skipped": "Skipped {n} locked folder(s); deleted ones are gone (re-run skips them).",
        "cursor_count": "Detected {n} Cursor process(es).",
        "vacuum_auto_skip": (
            "Cursor running — will clean, skip VACUUM. Later: cursor-clean vacuum"
        ),
        "plan_vacuum_later": "  - VACUUM later (Cursor running): cursor-clean vacuum",
        "hint_run_vacuum": "Next: quit Cursor, then run  cursor-clean vacuum",
        "bar_delete_agents": "agents",
        "bar_delete_chats": "chats",
        "bar_orphans": "orphans",
        "bar_vacuum": "VACUUM",
        "vacuum_locked_hint": " Quit Cursor, then: cursor-clean vacuum",
        "vacuum_space_skip": "VACUUM skipped: free {free} < need ~{need}. Free disk or use --force.",
        "vacuum_space_force": "WARNING: free {free} < need ~{need}; forcing VACUUM anyway.",
        "chat_failed": "Chat cleanup failed: {err}",
        "agent_failed": "Agent cleanup failed: {err}",
        "orphan_failed": "Orphan KV cleanup failed: {err}",
        "backup_failed": "Backup delete failed: {err}",
        "cache_failed": "Cache cleanup failed: {err}",
        "vacuum_failed_err": "VACUUM failed: {err}.{hint}",
        "tip_quit_first": "Quit Cursor completely, then retry.",
    },
    "zh": {
        "choose_lang": "选择语言 / Select language:\n  1) 中文\n  2) English\n请输入 1 或 2 [默认 1]: ",
        "invalid_lang": "输入无效，使用中文。",
        "cursor_running": (
            "检测到 Cursor 仍在运行（请在任务管理器中确认 Cursor.exe）。\n"
            "请完全退出 Cursor 后再试。若确认无占用可加 --force（VACUUM 可能卡住）。"
        ),
        "cursor_running_warn": (
            "警告：仍检测到 Cursor 进程；VACUUM 可能因数据库锁而卡住。"
        ),
        "data_root": "Cursor 数据目录: {path}",
        "state_db": "state.vscdb:        {size}",
        "state_backup": "state.vscdb.backup: {size}  （默认删除）",
        "disk_free": "磁盘剩余:          {free}  （VACUUM/官方 GC 约需 {need}）",
        "disk_free_ok": "  空间: 够 VACUUM / 官方 GC 压缩",
        "disk_free_low": "  空间: 不足 — 请先腾出约 {need}，再 VACUUM 或 Developer: GC Agent KV Blobs",
        "chats_title": "聊天 / Composer",
        "keep_days": "  保留天数:     {days}",
        "cutoff": "  截止日期(UTC): {cutoff}",
        "total": "  会话总数:     {n}",
        "older": "  可清理:       {n}  （超过保留期）",
        "est_blobs": "  估算占用:     {size}",
        "est_blobs_hint": "  估算占用:     （加 --deep 可估算；真正腾出空间需 VACUUM）",
        "chats_unavailable": "聊天 / Composer: 不可用",
        "orphan_title": "无主会话级 KV（composerId 不在 headers）",
        "orphan_count": "  无主会话数:   {n}",
        "agents_title": "cursor-agent 版本",
        "agents_none": "  （未找到）",
        "keep": "保留",
        "delete": "删除",
        "reclaimable": "  可回收: {size}",
        "cache_title": "可选缓存/日志",
        "warning": "警告: {msg}",
        "nothing": "没有可清理的内容。",
        "planned": "计划执行:",
        "plan_agents": "  - 删除 {n} 个旧 agent 版本（{size}）",
        "plan_chats": "  - 删除 {n} 个旧聊天",
        "plan_orphans": "  - 删除无主会话级 KV（{n} 个会话）",
        "plan_backup": "  - 删除 state.vscdb.backup（{size}）",
        "plan_vacuum": "  - VACUUM 压缩 state.vscdb（约需 1× 库体积的空闲磁盘）",
        "plan_cache": "  - 清理 CachedData/logs（{size}）",
        "plan_keep_backup": "  - 保留 state.vscdb.backup",
        "proceed": "确认执行？[y/N] ",
        "aborted": "已取消。",
        "done": "完成。",
        "agents_removed": "  已删 agent: {n}（{size}）",
        "chats_removed": "  已删聊天: {n}（kv 行: {kv}）",
        "orphans_removed": "  已删无主 KV: {composers} 个会话，{kv} 行",
        "backup_removed": "  已删 backup: {size}",
        "state_result": "  state.vscdb:   {before} -> {after}（释放 {freed}）{vacuum}",
        "vacuum_ok": "  [VACUUM 成功]",
        "cache_freed": "  缓存/日志:    {size}",
        "error": "错误: {msg}",
        "db_missing": "未找到 state.vscdb: {path}",
        "vacuum_failed": "VACUUM 失败: {err}",
        "vacuum_retry": "请完全退出 Cursor 后重试。",
        "no_agents": "没有可删除的旧 agent 版本。",
        "will_agents": "将删除 {n} 个版本（{size}），仅保留最新。",
        "agents_done": "完成。已删除 {n}（{size}）。",
        "progress_del_chats": "正在删除 {n} 个旧聊天 ...",
        "progress_del_chats_done": "  聊天完成: {n} 个，kv {kv} 行，{sec:.1f}s",
        "progress_vacuum": "正在 VACUUM state.vscdb（{gb:.2f} GB）...",
        "progress_vacuum_done": "  VACUUM 完成，用时 {sec:.1f}s: {before:.2f} GB -> {after:.2f} GB",
        "progress_del_agents": "正在删除 {n} 个旧 agent 版本 ...",
        "progress_agents_freed": "  agent 已释放 {gb:.2f} GB",
        "progress_cache": "正在清理 CachedData / logs ...",
        "progress_cache_done": "  缓存/日志已释放 {mb:.1f} MB",
        "phase_agents": "=== [agent] 删除 {n} 个旧版本 ===",
        "phase_chats": "=== [聊天] 删除 {n} 个旧会话 ===",
        "phase_orphans": "=== [无主] 删除不在 composerHeaders 的会话级 KV ===",
        "phase_backup": "=== [backup] 删除 state.vscdb.backup（{size}）===",
        "phase_vacuum": "=== [vacuum] 压缩 state.vscdb（{gb:.2f} GB）===",
        "orphan_none": "  无主: 无",
        "orphan_done": "  无主完成: {composers} 个会话，{kv} 行，{sec:.1f}s",
        "backup_done": "  已删 backup（{size}）",
        "agent_kv_title": "agentKv（请用 Cursor 官方 GC，勿盲目全删）",
        "agent_kv_count": "  行数:         {n}",
        "hint_gc": (
            "agentKv: 在 Cursor 中执行  Developer: GC Agent KV Blobs  "
            "（Ctrl+Shift+P）。压缩约需空闲 {need}（当前 {free}）。{status}"
        ),
        "hint_gc_ok": "磁盘空间充足。",
        "hint_gc_low": "请先腾出磁盘，否则 GC 压缩可能失败。",
        "resume_safe": "可重复执行：已删除的内容会自动跳过。",
        "progress_size_note": "聊天会立刻从库中删除；文件体积需退出 Cursor 后 VACUUM 才会明显下降。",
        "progress_vacuum_explain": "进度条按耗时估算百分比（VACUUM 无原生进度）。约需 1× 库体积的空闲磁盘。",
        "progress_wal_warn": "警告: wal 已有 {gb:.2f} GB，请先彻底退出 Cursor 再 VACUUM。",
        "progress_checkpoint": "wal_checkpoint(TRUNCATE) ...",
        "agent_skipped": "跳过 {n} 个被占用目录；已删的下次会自动跳过。",
        "cursor_count": "检测到 {n} 个 Cursor 进程。",
        "vacuum_auto_skip": "Cursor 运行中 — 先清理，跳过 VACUUM。稍后: cursor-clean vacuum",
        "plan_vacuum_later": "  - 稍后 VACUUM（Cursor 在运行）: cursor-clean vacuum",
        "hint_run_vacuum": "下一步: 退出 Cursor，再执行  cursor-clean vacuum",
        "bar_delete_agents": "agent",
        "bar_delete_chats": "聊天",
        "bar_orphans": "无主",
        "bar_vacuum": "VACUUM",
        "vacuum_locked_hint": " 请退出 Cursor 后执行: cursor-clean vacuum",
        "vacuum_space_skip": "已跳过 VACUUM：空闲 {free} < 约需 {need}。请腾出空间或加 --force。",
        "vacuum_space_force": "警告：空闲 {free} < 约需 {need}，仍强制 VACUUM。",
        "chat_failed": "聊天清理失败: {err}",
        "agent_failed": "Agent 清理失败: {err}",
        "orphan_failed": "无主 KV 清理失败: {err}",
        "backup_failed": "backup 删除失败: {err}",
        "cache_failed": "缓存清理失败: {err}",
        "vacuum_failed_err": "VACUUM 失败: {err}.{hint}",
        "tip_quit_first": "请先完全退出 Cursor 再重试。",
    },
}

_current: Lang = "zh"


def normalize_lang(value: str | None) -> Lang | None:
    if not value:
        return None
    v = value.strip().lower().replace("_", "-")
    if v in {"zh", "zh-cn", "zh-hans", "cn", "chinese", "1"}:
        return "zh"
    if v in {"en", "en-us", "en-gb", "english", "2"}:
        return "en"
    return None


def detect_lang_from_locale() -> Lang:
    try:
        loc = locale.getdefaultlocale()[0] or ""
    except Exception:
        loc = ""
    if loc.lower().startswith("zh"):
        return "zh"
    return "en"


def set_lang(lang: Lang) -> None:
    global _current
    _current = "zh" if lang == "zh" else "en"


def get_lang() -> Lang:
    return _current


def t(key: str, **kwargs: Any) -> str:
    table = _MESSAGES.get(_current) or _MESSAGES["en"]
    text = table.get(key) or _MESSAGES["en"].get(key) or key
    if kwargs:
        return text.format(**kwargs)
    return text


def resolve_lang(
    *,
    cli_lang: str | None,
    interactive: bool,
) -> Lang:
    """Resolve language: --lang > CURSOR_CLEAN_LANG > prompt > locale."""
    for candidate in (cli_lang, os.environ.get("CURSOR_CLEAN_LANG")):
        normalized = normalize_lang(candidate)
        if normalized:
            return normalized

    if interactive and sys_stdin_isatty():
        try:
            raw = input(_MESSAGES["zh"]["choose_lang"]).strip()
        except EOFError:
            raw = ""
        if not raw:
            return "zh"
        normalized = normalize_lang(raw)
        if normalized:
            return normalized
        print(_MESSAGES["zh"]["invalid_lang"])
        return "zh"

    return detect_lang_from_locale()


def sys_stdin_isatty() -> bool:
    try:
        return bool(getattr(__import__("sys").stdin, "isatty", lambda: False)())
    except Exception:
        return False
