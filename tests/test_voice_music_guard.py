from types import SimpleNamespace

from core.voice.voice_service import VoiceService


def _svc():
    svc = VoiceService.__new__(VoiceService)
    svc.config = lambda: {
        "continuous_music_guard_enabled": True,
        "continuous_music_guard_min_words": 8,
        "continuous_max_wake_mentions": 2,
        "continuous_music_guard_max_chars": 140,
        "continuous_min_execute_confidence": 0.84,
        "continuous_color_requires_action_word": True,
    }
    svc._wake_aliases = lambda: ["pese", "pc", "wizz", "wiz"]
    return svc


def test_music_loop_with_repeated_wake_commands_is_rejected():
    text = (
        "pc pese prende la luz al cincuenta, wizz pon rojo al cincuenta, "
        "wizz pon rojo al cincuenta, wizz pon rojo al cincuenta"
    )
    noisy, reason = _svc()._looks_like_repeated_command_noise(text)
    assert noisy
    assert "Ignorado" in reason


def test_normal_single_command_is_not_music_noise():
    noisy, _reason = _svc()._looks_like_repeated_command_noise("pc prende la luz al cincuenta")
    assert noisy is False


def test_continuous_execution_guard_blocks_multi_command_noise():
    svc = _svc()
    intent = SimpleNamespace(ok=True, confidence=0.92, action={"type": "sequence"})
    safety = svc._continuous_execution_guard(
        "prende la luz al cincuenta wizz pon rojo al cincuenta wizz pon rojo al cincuenta",
        intent,
        "continuous_command",
    )
    assert safety is not None
    assert safety["ok"] is False
    assert safety["intent_source"] == "continuous_music_guard"


def test_mixed_wake_aliases_are_rejected_even_when_short():
    noisy, reason = _svc()._looks_like_repeated_command_noise("pc pese apaga")
    assert noisy
    assert "activadores" in reason
