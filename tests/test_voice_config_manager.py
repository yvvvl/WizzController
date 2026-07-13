from config.voice_config_manager import _clamp_rms_gate, _profile_rms_cap, _profile_rms_floor


def test_adaptive_rms_gate_migrates_old_high_values():
    assert _clamp_rms_gate(0.075, "adaptive") <= _profile_rms_cap("adaptive")
    assert _clamp_rms_gate(0.075, "adaptive") < 0.03


def test_rms_gate_keeps_sane_floor_for_far_field():
    value = _clamp_rms_gate(0.0, "far_field")
    assert value == _profile_rms_floor("far_field")
    assert value <= 0.01


def test_very_gated_can_stay_stricter_than_adaptive():
    assert _profile_rms_floor("very_gated") > _profile_rms_floor("adaptive")
    assert _profile_rms_cap("very_gated") > _profile_rms_cap("adaptive")
