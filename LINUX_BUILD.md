# Linux Packaging

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
