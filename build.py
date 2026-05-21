#!/usr/bin/env python3
"""Build script for Quantifile.

Reads VERSION (MAJOR.MINOR.PATCH), auto-increments patch (or --major/--minor),
runs PyInstaller, stages a complete release/ package, and optionally builds a zip.

Usage:
    python build.py           # patch bump + build
    python build.py --minor   # minor bump
    python build.py --major   # major bump
    python build.py --zip     # also create Quantifile-vX.Y.Z-Windows.zip
    python build.py --no-increment   # build without changing version
"""

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
VERSION_FILE = ROOT / "VERSION"
SPEC_FILE = ROOT / "Quantifile.spec"
DIST_DIR = ROOT / "dist"
RELEASE_DIR = ROOT / "release"
BUILD_DIR = ROOT / "build"


def read_version() -> str:
    if not VERSION_FILE.exists():
        return "1.0.0"
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def write_version(version: str) -> None:
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")


def bump_version(current: str, level: str = "patch") -> str:
    parts = [int(x) for x in current.split(".")]
    while len(parts) < 3:
        parts.append(0)
    if level == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif level == "minor":
        parts[1] += 1
        parts[2] = 0
    else:
        parts[2] += 1
    return ".".join(map(str, parts))


def patch_version_in_text(text: str, new_version: str) -> str:
    # "Quantifile v1.0" or "Quantifile v1.0.0"
    text = re.sub(r"Quantifile v[\d.]+", f"Quantifile v{new_version}", text)
    # Download filename
    text = re.sub(
        r"Quantifile-v[\d.]+-Windows\.zip", f"Quantifile-v{new_version}-Windows.zip", text
    )
    # install.bat style "v1.0"
    text = re.sub(r"\bv[\d.]+\b", f"v{new_version}", text)
    return text


def update_file_version(path: Path, new_version: str) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = patch_version_in_text(text, new_version)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Quantifile release")
    parser.add_argument("--major", action="store_true", help="Bump major version")
    parser.add_argument("--minor", action="store_true", help="Bump minor version")
    parser.add_argument(
        "--no-increment", action="store_true", help="Build without bumping version"
    )
    parser.add_argument("--zip", action="store_true", help="Create versioned release zip")
    args = parser.parse_args()

    current = read_version()
    if args.major:
        new_ver = bump_version(current, "major")
    elif args.minor:
        new_ver = bump_version(current, "minor")
    elif not args.no_increment:
        new_ver = bump_version(current, "patch")
    else:
        new_ver = current

    print(f"Current version: {current}")
    print(f"New version:     {new_ver}")

    # Clean previous PyInstaller output
    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    # Run PyInstaller.
    # We temporarily patch the .spec file to set a versioned name because
    # --name is not allowed when a .spec file is passed on the command line.
    print("Running PyInstaller...")
    versioned_name = f"Quantifile-v{new_ver}"
    versioned_exe = f"{versioned_name}.exe"

    original_spec = SPEC_FILE.read_text(encoding="utf-8")
    patched_spec = re.sub(
        r"name\s*=\s*['\"]Quantifile['\"]",
        f"name='{versioned_name}'",
        original_spec,
    )
    SPEC_FILE.write_text(patched_spec, encoding="utf-8")

    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "-y", str(SPEC_FILE)]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        print("PyInstaller failed. Is it installed? (pip install pyinstaller)")
        sys.exit(1)
    finally:
        # Always restore the original spec so the repo stays clean
        if SPEC_FILE.read_text(encoding="utf-8") != original_spec:
            SPEC_FILE.write_text(original_spec, encoding="utf-8")

    exe_src = DIST_DIR / versioned_exe
    if not exe_src.exists():
        print(f"ERROR: {versioned_exe} was not produced in dist/")
        sys.exit(1)

    # Prepare release/ directory
    RELEASE_DIR.mkdir(exist_ok=True)

    # Remove any previous Quantifile*.exe so only the current versioned one remains
    for old_exe in RELEASE_DIR.glob("Quantifile*.exe"):
        try:
            old_exe.unlink()
        except OSError:
            pass

    # Copy the freshly built versioned executable
    shutil.copy2(exe_src, RELEASE_DIR / versioned_exe)

    # Stage supporting files (version-patched where appropriate)
    shutil.copy2(ROOT / "LICENSE", RELEASE_DIR / "LICENSE")

    # README.md from root, with version strings updated in the release copy
    readme_dest = RELEASE_DIR / "README.md"
    shutil.copy2(ROOT / "README.md", readme_dest)
    update_file_version(readme_dest, new_ver)

    # Copy screenshot.png so the image in the bundled README works when extracted
    screenshot = ROOT / "screenshot.png"
    if screenshot.exists():
        shutil.copy2(screenshot, RELEASE_DIR / "screenshot.png")

    # install.bat lives in release/ (source of truth for the template)
    install_bat = RELEASE_DIR / "install.bat"
    if install_bat.exists():
        update_file_version(install_bat, new_ver)
        # Also replace the bare exe name with the versioned one
        content = install_bat.read_text(encoding="utf-8")
        content = content.replace("Quantifile.exe", versioned_exe)
        install_bat.write_text(content, encoding="utf-8")
    else:
        # Create a minimal one if missing (using the versioned exe name)
        install_bat.write_text(
            f"""@echo off
echo Installing Quantifile v{new_ver}...
echo.

if not exist "%ProgramFiles%\\Quantifile" mkdir "%ProgramFiles%\\Quantifile"

copy "{versioned_exe}" "%ProgramFiles%\\Quantifile\\"
copy "README.md" "%ProgramFiles%\\Quantifile\\"
copy "LICENSE" "%ProgramFiles%\\Quantifile\\"

echo Creating desktop shortcut...
powershell "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%UserProfile%\\Desktop\\Quantifile.lnk'); $sc.TargetPath = '%ProgramFiles%\\Quantifile\\{versioned_exe}'; $sc.WorkingDirectory = '%ProgramFiles%\\Quantifile'; $sc.IconLocation = '%ProgramFiles%\\Quantifile\\{versioned_exe}'; $sc.Save()"

echo.
echo Installation complete!
echo Quantifile has been installed to: %ProgramFiles%\\Quantifile
echo A desktop shortcut has been created.
echo.
pause
""",
            encoding="utf-8",
        )

    print(f"Release package ready in {RELEASE_DIR}")

    if args.zip:
        zip_name = f"Quantifile-v{new_ver}-Windows.zip"
        zip_path = ROOT / zip_name
        print(f"Creating {zip_name}...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in sorted(RELEASE_DIR.iterdir()):
                zf.write(item, arcname=item.name)
        print(f"Created {zip_path}")

    # Only persist the version bump after a fully successful build
    if new_ver != current:
        write_version(new_ver)
        print("VERSION file updated")

    print("Build complete.")


if __name__ == "__main__":
    main()
