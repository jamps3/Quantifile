import pytest

from build_linux import release_name, use_system_fontconfig


@pytest.mark.parametrize("machine, expected", [("x86_64", "x86_64"), ("AMD64", "x86_64"), ("arm64", "aarch64")])
def test_release_name(machine, expected):
    assert release_name("1.0.5", machine) == f"Quantifile-v1.0.5-linux-{expected}"


@pytest.mark.parametrize("version", ["", "1.2", "../bad", "1.2.3-beta"])
def test_invalid_version(version):
    with pytest.raises(ValueError, match="VERSION"):
        release_name(version, "x86_64")


def test_unsupported_architecture():
    with pytest.raises(ValueError, match="architecture"):
        release_name("1.0.5", "unknown")


def test_system_fontconfig_removes_only_bundled_fontconfig(tmp_path):
    internal = tmp_path / "_internal"
    internal.mkdir()
    (internal / "libfontconfig.so.1.12.0").write_bytes(b"fontconfig")
    (internal / "libfontconfig.so.1").symlink_to("libfontconfig.so.1.12.0")
    (internal / "libtk8.6.so").write_bytes(b"keep")
    use_system_fontconfig(tmp_path)
    assert not list(internal.glob("libfontconfig.so*"))
    assert (internal / "libtk8.6.so").read_bytes() == b"keep"


def test_system_fontconfig_missing_library_is_safe(tmp_path):
    use_system_fontconfig(tmp_path)
