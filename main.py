"""Compatibility launcher for the supported Qt desktop application.

Existing source shortcuts that invoke ``python main.py`` continue to work.
The release builders use ``qt_ui.run`` directly.
"""

from qt_ui.run import main


if __name__ == "__main__":
    raise SystemExit(main())
