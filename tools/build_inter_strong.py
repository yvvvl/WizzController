"""Create the bundled static display face from the OFL-licensed Inter font.

Run with FontTools installed in the development environment. The generated
font ships with assets/fonts/OFL.txt; FontTools is not a runtime dependency.
"""

from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "fonts" / "InterVariable.ttf"
OUTPUT = ROOT / "assets" / "fonts" / "WizZInterStrong.ttf"


def main() -> None:
    font = TTFont(SOURCE)
    instantiateVariableFont(
        font, {"opsz": 18, "wght": 800}, inplace=True, updateFontNames=False
    )

    # Give the modified face its own family so Qt never falls back to the
    # regular variable face when resolving a bold heading on Windows.
    names = {
        1: "WizZ Inter Strong",
        2: "Regular",
        4: "WizZ Inter Strong",
        6: "WizZInterStrong",
        16: "WizZ Inter Strong",
        17: "Regular",
    }
    table = font["name"]
    for record in list(table.names):
        replacement = names.get(record.nameID)
        if replacement is not None:
            table.setName(
                replacement,
                record.nameID,
                record.platformID,
                record.platEncID,
                record.langID,
            )
    font.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
