"""i18n helpers."""

from cursor_clean.i18n import normalize_lang, set_lang, t


def test_normalize_lang() -> None:
    assert normalize_lang("zh") == "zh"
    assert normalize_lang("zh-CN") == "zh"
    assert normalize_lang("en") == "en"
    assert normalize_lang("2") == "en"
    assert normalize_lang("nope") is None


def test_messages_switch() -> None:
    set_lang("zh")
    assert "确认" in t("proceed") or "y/N" in t("proceed")
    set_lang("en")
    assert "Proceed" in t("proceed")
