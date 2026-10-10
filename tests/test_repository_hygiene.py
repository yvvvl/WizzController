from tools.repository_hygiene import problem_for_path


def test_rejects_private_and_generated_files():
    for name in (
        "config/json/bulbs.json",
        "config/json/hotkeys.json",
        ".env.production",
        "build/pyinstaller/WizZDesktop.exe",
        "logs/app.log",
        "ui/__pycache__/app.pyc",
    ):
        assert problem_for_path(name) is not None


def test_keeps_public_examples_and_source():
    for name in (
        "config/json/bulbs.example.json",
        ".env.example",
        "core/light_controller.py",
        "assets/fonts/InterVariable.ttf",
        "uv.lock",
    ):
        assert problem_for_path(name) is None
