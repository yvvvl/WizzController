from core.update_checker import is_update_available, select_latest_release


PAYLOADS = [
    {"tag_name": "v1.2.0-beta.1", "prerelease": True},
    {"tag_name": "v1.1.1", "prerelease": False},
    {"tag_name": "v1.1.0", "prerelease": False},
]


def test_stable_channel_ignores_prereleases():
    release = select_latest_release(PAYLOADS, channel="stable")
    assert release is not None
    assert release.version == "1.1.1"


def test_beta_channel_can_select_prerelease():
    release = select_latest_release(PAYLOADS, channel="beta")
    assert release is not None
    assert release.version == "1.2.0-beta.1"


def test_update_comparison_is_deterministic():
    release = select_latest_release(PAYLOADS)
    assert is_update_available("1.1.0", release)
    assert not is_update_available("1.1.1", release)
