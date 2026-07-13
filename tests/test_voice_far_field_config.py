from config.voice_config_manager import _clamp_rms_gate, _profile_rms_floor, VoiceConfigManager


def test_far_field_floor_is_more_sensitive_than_adaptive():
    assert _profile_rms_floor("far_field") < _profile_rms_floor("adaptive")
    assert _profile_rms_floor("far_field") <= 0.0035


def test_phase55_six_milli_gate_migrates_lower_for_far_profiles():
    assert _clamp_rms_gate(0.006, "far_field") == 0.006
    # Evitamos inicializar JsonManager para no crear config/json reales en tests.
    manager = VoiceConfigManager.__new__(VoiceConfigManager)
    manager.data = dict(VoiceConfigManager.DEFAULTS)
    manager.data.update({
        "audio_input_profile": "far_field",
        "far_field_assist_enabled": True,
        "wake_probe_min_rms_peak": 0.006,
        "continuous_min_rms_peak": 0.006,
        "wake_short_candidate_min_rms_peak": 0.006,
    })
    manager._ensure_defaults_and_migrate()
    assert manager.data["wake_probe_min_rms_peak"] == _profile_rms_floor("far_field")
    assert manager.data["continuous_min_rms_peak"] == _profile_rms_floor("far_field")


def test_default_far_field_assist_keys_exist():
    defaults = VoiceConfigManager.DEFAULTS
    assert defaults["far_field_assist_enabled"] is True
    assert defaults["speech_start_confirm_blocks"] >= 2
    assert defaults["speech_continue_threshold_ratio"] < 0.8
