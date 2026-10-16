# Linux Packaging

## Version 1.0.6

The current builder intentionally omits bundled libfontconfig.so files and uses
the host's Fontconfig library so its parser matches the host's font rules.
Install libfontconfig1 on Ubuntu/Debian (fontconfig on Arch/CachyOS).
Python/Tcl/Tk remain bundled. Baseline: Ubuntu22.04/glibc2.35, x86_64.
The earlier Fontconfig limitation documented below was resolved for this build.

Version1.0.6 also splits the application toolbar into two rows so all commands
are visible at the default1100x750 window size. VERSION, pyproject and lockfile
project metadata agree; Windows1.0.5 download remains unchanged.

31 unit tests pass with100% models/layout/scanner coverage. Ruff check/format
and Pyright pass. The corrected package has clean no-stderr startup on Ubuntu
and CachyOS. Scripted GUI acceptance covers synthetic scanning, name search,
zoom in/out, bookmark persistence/sidebar, SVG export, theme changes, settings
save, About and Log dialogs.1100px toolbar visibility is asserted; actual
light/dark screenshots were visually reviewed. This is automated GUI coverage
plus visual review, not a claim of a human-operated physical-desktop session.
External open/delete integration and other distributions remain untested.

Optional GUI acceptance (test dependency only, not bundled into the app):

```sh
uv pip install --python .venv/bin/python pillow
xvfb-run -a -s '-screen 0 1920x1080x24' .venv/bin/python tests/gui_acceptance.py
```

Use QUANTIFILE_QA_OUTPUT to set the screenshot output directory. The test only
creates/scans temporary synthetic files and saves settings in a temp folder.

Run on Linux with Python 3.9+ and working Tk/Tcl libraries. PyInstaller is a
build-only dependency; this script does not change the application version or
the Windows build.py / Quantifile.spec files.

```sh
uv sync --dev --locked
uv pip install --python .venv/bin/python 'pyinstaller==6.22.3'
.venv/bin/python -m pytest
.venv/bin/python build_linux.py
```

Outputs go to dist/linux/ (already ignored by Git):

- Quantifile-vVERSION-linux-ARCH.tar.gz
- Quantifile-vVERSION-linux-ARCH.tar.gz.sha256

An existing release is never overwritten. Use --output-dir for another build.
The archive contains the executable, its _internal libraries, license,
README, screenshot, run instructions and build provenance. Extract everything
and run ./Quantifile from the extracted directory. Verify the download with
sha256sum -c FILE.tar.gz.sha256.

The Linux directory bundle is intentional: it avoids one-file temporary
extraction and makes bundled Tcl/Tk libraries easy to inspect. Python and Tk
are bundled, but a graphical Linux session and compatible system libraries
are still required. Build on the oldest supported distribution: a build on a
rolling distribution does not establish compatibility with older Ubuntu or
Debian releases. Review BUILD-INFO.json before publishing.

## Validation

Run the unit tests, Ruff and Pyright, then validate source GUI startup and a
small synthetic directory scan on a dedicated Xvfb display. Extract the
archive into a fresh directory and smoke-test its executable without the
build environment's LD_LIBRARY_PATH / TCL_LIBRARY / TK_LIBRARY. A successful
startup smoke test is not a full interactive desktop acceptance test.

No Linux artifact is automatically uploaded or published by this script.

### Kuu Validation, 2026-10-16

- CachyOS x86_64, Python 3.14.8, glibc 2.44, PyInstaller 6.22.3.
- 29 tests passed; 100% coverage of models/layout/scanner (not GUI/build code).
- Ruff check/format and Pyright passed.
- Source GUI: startup, synthetic 1088-byte scan, nonempty treemap and theme
  changes passed on a dedicated Xvfb display.
- Extracted executable stayed running without stderr for five seconds with
  build-only library environment overrides removed. This is a startup smoke
  test, not full interactive acceptance or older-distribution compatibility.
- Tk 8.6.16 and Xvfb were extracted into /home/jamps/o/.build-tools/sysroot;
  no sudo or system package installation was used. For this host, prefix build
  and source GUI commands with:

```sh
env LD_LIBRARY_PATH=/home/jamps/o/.build-tools/sysroot/usr/lib \
    TK_LIBRARY=/home/jamps/o/.build-tools/sysroot/usr/lib/tk8.6 \
    .venv/bin/python build_linux.py
```

### Ubuntu 22.04 Compatibility, 2026-10-16

The original CachyOS artifact failed on Ubuntu 22.04/glibc 2.35: its bundled
libz.so.1 requires GLIBC_ABI_DT_RELR. Do not publish that artifact as a general
Linux download.

Rebuilt unmodified source commit b9c4628 inside a rootless Ubuntu Base 22.04.5
environment (Python 3.10.12, glibc 2.35, PyInstaller 6.22.3). All 29 tests
passed with 100% core coverage. The source GUI scanned the synthetic 1088-byte
fixture, rendered a treemap and switched themes. The extracted Ubuntu binary
created a visible X window and stayed running without stderr for five seconds.
This is an older-userspace test sharing Kuu's kernel, not a separate VM or a
full manual desktop acceptance test.

Ubuntu artifact SHA256:
0594f5eb412c9b1f7d8a39b3fbcba2addc6467e89574168efdece0fb07a1aed3

On Kuu, the Ubuntu build is retained under
/home/jamps/o/.build-tools/ubuntu2204/rootfs/work/Quantifile/dist/ubuntu2204/.
No public release or upload was performed.

The same Ubuntu artifact also remains running on CachyOS, but its older bundled
Fontconfig reports parsing warnings against CachyOS's newer system font rules.
Treat this as an unresolved cross-distribution packaging issue, not a clean
CachyOS pass. Resolve font configuration/library compatibility before promoting
the Ubuntu archive as the general Linux download.
