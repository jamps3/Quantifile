#!/usr/bin/env python3
"""Build a versioned Linux directory bundle and tar.gz without changing VERSION."""

import argparse
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def release_name(version: str, machine: str) -> str:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("VERSION must contain MAJOR.MINOR.PATCH")
    architecture = {"amd64": "x86_64", "arm64": "aarch64"}.get(machine.lower(), machine.lower())
    if architecture not in {"x86_64", "aarch64"}:
        raise ValueError(f"Unsupported architecture: {machine}")
    return f"Quantifile-v{version}-linux-{architecture}"


def use_system_fontconfig(bundle: Path) -> None:
    for library in (bundle / "_internal").glob("libfontconfig.so*"):
        library.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist" / "linux")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Run this script on Linux; PyInstaller cannot cross-compile")
    if importlib.util.find_spec("PyInstaller") is None:
        parser.error("Install PyInstaller in this Python environment first")
    try:
        import tkinter
    except ImportError as error:
        parser.error(f"A working Python Tk/Tcl installation is required: {error}")
    try:
        tkinter.Tcl()
    except tkinter.TclError as error:
        parser.error(f"A working Python Tk/Tcl installation is required: {error}")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    try:
        name = release_name(version, platform.machine())
    except ValueError as error:
        parser.error(str(error))
    output = args.output_dir.resolve()
    archive = output / f"{name}.tar.gz"
    checksum = output / f"{name}.tar.gz.sha256"
    if archive.exists() or checksum.exists():
        parser.error(f"Release already exists in {output}; choose a new --output-dir")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="quantifile-linux-") as temporary:
        work = Path(temporary)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--onedir",
                "--name",
                "Quantifile",
                "--distpath",
                str(work / "dist"),
                "--workpath",
                str(work / "build"),
                "--specpath",
                str(work),
                "--add-data",
                f"{ROOT / 'VERSION'}:.",
                "--add-data",
                f"{ROOT / 'icon-1024.png'}:.",
                str(ROOT / "main.py"),
            ],
            cwd=ROOT,
            check=True,
        )
        bundle = work / "dist" / "Quantifile"
        use_system_fontconfig(bundle)
        for filename in ("LICENSE", "README.md", "screenshot.png"):
            shutil.copy2(ROOT / filename, bundle / filename)
        metadata = {
            "version": version,
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "libc": platform.libc_ver(),
            "distribution": platform.platform(),
            "system_libraries": ["libfontconfig.so.1"],
            "pyinstaller": subprocess.check_output(
                [sys.executable, "-m", "PyInstaller", "--version"], text=True
            ).strip(),
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "source_dirty": bool(
                subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
            ),
        }
        (bundle / "BUILD-INFO.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        (bundle / "RUNNING.txt").write_text(
            "Extract the entire archive, then run ./Quantifile from its extracted directory.\n"
            "Keep the _internal directory beside the executable. No Python installation is required.\n"
            "A graphical Linux desktop and compatible system libraries are required.\n"
            "System Fontconfig (libfontconfig.so.1) is required so font rules match the host.\n"
            "See BUILD-INFO.json for the build distribution and glibc version.\n"
            "Build on the oldest supported distribution for wider glibc compatibility.\n",
            encoding="utf-8",
        )
        staged_archive = work / archive.name
        with tarfile.open(staged_archive, "w:gz") as tar:
            tar.add(bundle, arcname=name)
        hasher = hashlib.sha256()
        with staged_archive.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(block)
        digest = hasher.hexdigest()
        shutil.copy2(staged_archive, archive)
        checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(f"Created {archive}")
    print(f"SHA256  {digest}")
    print("VERSION and Windows build files were not modified.")


if __name__ == "__main__":
    main()
