import pytest

from build_linux import release_name


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
