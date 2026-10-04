from core.update_checker import is_update_available, parse_release, select_latest_release


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


def test_final_release_replaces_its_release_candidate():
    final = select_latest_release([{"tag_name": "v1.4.2", "prerelease": False}])

    assert final is not None
    assert is_update_available("1.4.2-rc.1", final)
    assert not is_update_available("1.4.2", final)


def test_linux_release_selects_matching_architecture_archive_and_checksum():
    payload = {
        "tag_name": "v1.3.5",
        "assets": [
            {"name": "WizZDesktop-v1.3.5-linux-x64.tar.gz", "browser_download_url": "https://example.test/x64.tar.gz"},
            {"name": "WizZDesktop-v1.3.5-linux-x64.tar.gz.sha256", "browser_download_url": "https://example.test/x64.sha256"},
            {"name": "WizZDesktop-v1.3.5-linux-arm64.tar.gz", "browser_download_url": "https://example.test/arm64.tar.gz"},
            {"name": "WizZDesktop-v1.3.5-linux-arm64.tar.gz.sha256", "browser_download_url": "https://example.test/arm64.sha256"},
        ],
    }

    release = parse_release(payload, platform="linux-arm64")

    assert release is not None
    assert release.download_url == "https://example.test/arm64.tar.gz"
    assert release.checksum_url == "https://example.test/arm64.sha256"
