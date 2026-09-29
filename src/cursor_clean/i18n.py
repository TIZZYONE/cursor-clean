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
        "state_backup": "state.vscdb.backup: {size}  (kept, never deleted)",
        "chats_title": "Chats / Composer",
        "keep_days": "  keep-days:     {days}",
        "cutoff": "  cutoff (UTC):  {cutoff}",
        "total": "  total:         {n}",
        "older": "  older:         {n}  (candidates)",
        "est_blobs": "  est. blobs:    {size}",
        "est_blobs_hint": "  est. blobs:    (use --deep for estimate; free space shows after VACUUM)",
        "chats_unavailable": "Chats / Composer: unavailable",
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
        "plan_vacuum": "  - VACUUM state.vscdb (can take several minutes on large DBs)",
        "plan_cache": "  - Clear CachedData/logs ({size})",
        "plan_backup": "  - state.vscdb.backup will NOT be deleted",
        "proceed": "Proceed? [y/N] ",
        "aborted": "Aborted.",
        "done": "Done.",
        "agents_removed": "  agents removed: {n} ({size})",
        "chats_removed": "  chats removed: {n} (kv rows: {kv})",
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
        "progress_del_chats": "Deleting {n} old chat(s) from state.vscdb ...",
        "progress_del_chats_done": "  removed {n} chat(s), {kv} kv row(s) in {sec:.1f}s",
        "progress_vacuum": (
            "VACUUM state.vscdb ({gb:.2f} GB) — may take several minutes; "
            "Cursor must be fully quit ..."
        ),
        "progress_vacuum_done": "  VACUUM done in {sec:.1f}s: {before:.2f} GB -> {after:.2f} GB",
        "progress_del_agents": "Deleting {n} old agent version(s) ...",
        "progress_agents_freed": "  agent versions freed {gb:.2f} GB",
        "progress_cache": "Clearing CachedData / logs ...",
        "progress_cache_done": "  cache/logs freed {mb:.1f} MB",
        "vacuum_locked_hint": (
            " Quit Cursor completely (check Task Manager for Cursor.exe), "
            "then run: cursor-clean vacuum"
        ),
        "chat_failed": "Chat cleanup failed: {err}",
        "agent_failed": "Agent version cleanup failed: {err}",
        "cache_failed": "Cache/logs cleanup failed: {err}",
        "vacuum_failed_err": "VACUUM failed: {err}.{hint}",
        "scan_db_fail": "Failed to read state.vscdb: {err}",
        "scan_db_missing": "state.vscdb not found: {path}",
        "tip_quit_first": "Tip: fully quit Cursor before clean/vacuum, or the tool may hang.",
        "bar_delete_agents": "agents",
        "bar_delete_chats": "chats",
        "bar_vacuum": "VACUUM",
        "progress_size_note": (
            "Note: deleting chats frees logical data immediately; the .vscdb file size "
            "usually drops only after a later VACUUM (Cursor must be quit)."
        ),
        "progress_vacuum_explain": (
            "VACUUM rewrites the whole DB under an exclusive lock. "
            "Live bar shows activity (elapsed + db/wal size)."
        ),
        "progress_wal_warn": (
            "WARNING: state.vscdb-wal is already {gb:.2f} GB. Quit Cursor fully, then continue; "
            "otherwise the folder can grow instead of shrink."
        ),
        "progress_checkpoint": "Running wal_checkpoint(TRUNCATE) first ...",
        "agent_partial_fail": "{n} agent folder(s) could not be deleted (often locked by Cursor).",
        "agent_skipped": "Skipped {n} locked/failed agent folder(s); others were deleted.",
        "cursor_count": "Detected {n} Cursor process(es).",
        "vacuum_auto_skip": (
            "Cursor is running — will delete agents/chats now, but skip VACUUM. "
            "Quit Cursor later and run: cursor-clean vacuum"
        ),
        "plan_vacuum_later": (
            "  - VACUUM skipped for now (Cursor running); run `cursor-clean vacuum` after quit"
        ),
        "hint_run_vacuum": (
            "Tip: quit Cursor completely, then run `cursor-clean vacuum` to shrink state.vscdb on disk."
        ),
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
        "state_backup": "state.vscdb.backup: {size}  （保留，不会删除）",
        "chats_title": "聊天 / Composer",
        "keep_days": "  保留天数:     {days}",
        "cutoff": "  截止日期(UTC): {cutoff}",
        "total": "  会话总数:     {n}",
        "older": "  可清理:       {n}  （超过保留期）",
        "est_blobs": "  估算占用:     {size}",
        "est_blobs_hint": "  估算占用:     （加 --deep 可估算；真正腾出空间需 VACUUM）",
        "chats_unavailable": "聊天 / Composer: 不可用",
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
        "plan_vacuum": "  - VACUUM 压缩 state.vscdb（大库可能需要数分钟）",
        "plan_cache": "  - 清理 CachedData/logs（{size}）",
        "plan_backup": "  - 不会删除 state.vscdb.backup",
        "proceed": "确认执行？[y/N] ",
        "aborted": "已取消。",
        "done": "完成。",
        "agents_removed": "  已删 agent: {n}（{size}）",
        "chats_removed": "  已删聊天: {n}（kv 行: {kv}）",
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
        "progress_del_chats": "正在从 state.vscdb 删除 {n} 个旧聊天 ...",
        "progress_del_chats_done": "  已删除 {n} 个聊天、{kv} 行 kv，用时 {sec:.1f}s",
        "progress_vacuum": (
            "正在 VACUUM state.vscdb（{gb:.2f} GB）— 可能需要几分钟；"
            "请确保已完全退出 Cursor ..."
        ),
        "progress_vacuum_done": "  VACUUM 完成，用时 {sec:.1f}s: {before:.2f} GB -> {after:.2f} GB",
        "progress_del_agents": "正在删除 {n} 个旧 agent 版本 ...",
        "progress_agents_freed": "  agent 版本已释放 {gb:.2f} GB",
        "progress_cache": "正在清理 CachedData / logs ...",
        "progress_cache_done": "  缓存/日志已释放 {mb:.1f} MB",
        "vacuum_locked_hint": (
            " 请完全退出 Cursor（任务管理器确认无 Cursor.exe），然后执行: cursor-clean vacuum"
        ),
        "chat_failed": "聊天清理失败: {err}",
        "agent_failed": "Agent 版本清理失败: {err}",
        "cache_failed": "缓存/日志清理失败: {err}",
        "vacuum_failed_err": "VACUUM 失败: {err}.{hint}",
        "scan_db_fail": "读取 state.vscdb 失败: {err}",
        "scan_db_missing": "未找到 state.vscdb: {path}",
        "tip_quit_first": "提示: 清理/压缩前请先完全退出 Cursor，否则可能卡住。",
        "bar_delete_agents": "删agent",
        "bar_delete_chats": "删聊天",
        "bar_vacuum": "VACUUM",
        "progress_size_note": (
            "说明: 聊天记录会马上从库里删掉；state.vscdb 文件体积通常要等之后 VACUUM "
            "（需退出 Cursor）才会明显变小。"
        ),
        "progress_vacuum_explain": (
            "VACUUM 需要独占锁整库重写。进度条显示活动状态（已用时 + db/wal 大小）。"
        ),
        "progress_wal_warn": (
            "警告: state.vscdb-wal 已有 {gb:.2f} GB。请先彻底退出 Cursor 再继续，"
            "否则目录可能越清越大。"
        ),
        "progress_checkpoint": "先执行 wal_checkpoint(TRUNCATE) ...",
        "agent_partial_fail": "有 {n} 个 agent 目录删不掉（多为被 Cursor 占用）。",
        "agent_skipped": "有 {n} 个 agent 目录被占用/失败已跳过，其余已删除。",
        "cursor_count": "检测到 {n} 个 Cursor 进程。",
        "vacuum_auto_skip": (
            "检测到 Cursor 正在运行 — 现在会删 agent/旧聊天，但跳过 VACUUM。"
            "退出 Cursor 后请执行: cursor-clean vacuum"
        ),
        "plan_vacuum_later": (
            "  - 暂不 VACUUM（Cursor 在运行）；退出后执行 `cursor-clean vacuum`"
        ),
        "hint_run_vacuum": (
            "提示: 完全退出 Cursor 后执行 `cursor-clean vacuum`，才能把 state.vscdb 文件缩小。"
        ),
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
