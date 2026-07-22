from __future__ import annotations

"""Make certifi importable by Flet 0.85.x / serious_python 1.x on Windows.

Flet 0.85.x can package desktop dependencies inside app.zip/__pypackages__.
Some build layouts also expose an unpacked site-packages directory beside the
executable.  This tool installs certifi into both locations and verifies the CA
bundle before the outer release ZIP is created.
"""

import argparse
import hashlib
import importlib.metadata
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile


def _certifi_sources() -> tuple[Path, Path | None]:
    import certifi

    package = Path(certifi.__file__).resolve().parent
    if not (package / "__init__.py").is_file():
        raise RuntimeError(f"certifi package is incomplete: {package}")
    if not (package / "cacert.pem").is_file():
        raise RuntimeError(f"certifi CA bundle is missing: {package / 'cacert.pem'}")

    dist_info: Path | None = None
    distribution = importlib.metadata.distribution("certifi")
    for entry in distribution.files or []:
        parts = PurePosixPath(str(entry).replace("\\", "/")).parts
        if parts and parts[0].lower().startswith("certifi-") and parts[0].lower().endswith(".dist-info"):
            candidate = Path(distribution.locate_file(parts[0])).resolve()
            if candidate.is_dir():
                dist_info = candidate
                break
    return package, dist_info


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
            yield path


def _inject_archive(app_zip: Path, package: Path, dist_info: Path | None) -> None:
    app_zip = app_zip.resolve()
    temp_fd, temp_name = tempfile.mkstemp(prefix=f"{app_zip.stem}.", suffix=".tmp", dir=app_zip.parent)
    os.close(temp_fd)
    temp_zip = Path(temp_name)

    certifi_prefix = "__pypackages__/certifi/"
    dist_prefix = "__pypackages__/certifi-"

    try:
        with zipfile.ZipFile(app_zip, "r") as source, zipfile.ZipFile(
            temp_zip,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as target:
            for info in source.infolist():
                name = info.filename.replace("\\", "/")
                lower = name.lower()
                if lower.startswith(certifi_prefix):
                    continue
                if lower.startswith(dist_prefix) and ".dist-info/" in lower:
                    continue
                target.writestr(info, source.read(info.filename))

            for path in _iter_files(package):
                relative = path.relative_to(package).as_posix()
                target.write(path, f"__pypackages__/certifi/{relative}")

            if dist_info is not None:
                for path in _iter_files(dist_info):
                    relative = path.relative_to(dist_info).as_posix()
                    target.write(path, f"__pypackages__/{dist_info.name}/{relative}")

        os.replace(temp_zip, app_zip)

        # app.zip cambia despu?s de que Serious Python genera app.zip.hash.
        # Recalcular el sidecar obliga al runtime release a invalidar la
        # extracci?n anterior y desempaquetar las dependencias actualizadas.
        archive_hash = hashlib.sha256(app_zip.read_bytes()).hexdigest()
        hash_file = app_zip.with_name(f"{app_zip.name}.hash")
        with hash_file.open("w", encoding="ascii", newline="") as stream:
            stream.write(archive_hash)
    finally:
        try:
            temp_zip.unlink(missing_ok=True)
        except OSError:
            pass

    with zipfile.ZipFile(app_zip, "r") as archive:
        names = {name.replace("\\", "/") for name in archive.namelist()}
    required = {
        "__pypackages__/certifi/__init__.py",
        "__pypackages__/certifi/cacert.pem",
    }
    missing = sorted(required - names)
    if missing:
        raise RuntimeError(f"certifi was not embedded in {app_zip}: {missing}")


def embed_certifi(output: Path) -> dict[str, object]:
    output = output.expanduser().resolve()
    if not output.is_dir():
        raise FileNotFoundError(f"Windows output directory does not exist: {output}")

    package, dist_info = _certifi_sources()

    unpacked_root = output / "site-packages"
    _copy_tree(package, unpacked_root / "certifi")
    if dist_info is not None:
        _copy_tree(dist_info, unpacked_root / dist_info.name)

    app_zips = sorted(path for path in output.rglob("app.zip") if path.is_file())
    for app_zip in app_zips:
        _inject_archive(app_zip, package, dist_info)

    unpacked_required = [
        unpacked_root / "certifi" / "__init__.py",
        unpacked_root / "certifi" / "cacert.pem",
    ]
    if not all(path.is_file() for path in unpacked_required):
        raise RuntimeError("certifi could not be copied to output/site-packages")

    return {
        "output": str(output),
        "source": str(package),
        "unpacked": str(unpacked_root / "certifi"),
        "app_archives": [str(path) for path in app_zips],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result = embed_certifi(args.output)
    print("certifi runtime repaired")
    print(f"  source     : {result['source']}")
    print(f"  site-packages: {result['unpacked']}")
    archives = result["app_archives"]
    if archives:
        for path in archives:
            print(f"  app.zip    : {path}")
    else:
        print("  app.zip    : not present (unpacked layout)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
