import scanner
from scanner import scan_path


def test_scan_path_file(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_bytes(b"hello")

    node = scan_path(file_path)

    assert node.path == file_path
    assert node.name == "file.txt"
    assert node.is_dir is False
    assert node.size == 5
    assert node.children == []
    assert node.modified_time > 0


def test_scan_path_directory_recurses_and_sorts(tmp_path):
    (tmp_path / "small.txt").write_bytes(b"a")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "large.txt").write_bytes(b"abcdef")

    node = scan_path(tmp_path)

    assert node.is_dir is True
    assert node.size == 7
    assert [child.name for child in node.children] == ["nested", "small.txt"]
    assert node.children[0].size == 6


def test_scan_path_handles_stat_errors(monkeypatch, tmp_path):
    missing = tmp_path / "missing.txt"

    monkeypatch.setattr(scanner.os.path, "isdir", lambda path: False)
    monkeypatch.setattr(scanner.os.path, "getmtime", lambda path: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(scanner.os.path, "getsize", lambda path: (_ for _ in ()).throw(OSError()))

    node = scan_path(missing)

    assert node.size == 0
    assert node.modified_time == 0


def test_scan_path_handles_permission_error(monkeypatch, tmp_path):
    monkeypatch.setattr(scanner.os, "scandir", lambda path: (_ for _ in ()).throw(PermissionError()))

    node = scan_path(tmp_path)

    assert node.is_dir is True
    assert node.size == 0
    assert node.children == []


def test_scan_path_handles_scandir_os_error(monkeypatch, tmp_path):
    monkeypatch.setattr(scanner.os, "scandir", lambda path: (_ for _ in ()).throw(OSError()))

    node = scan_path(tmp_path)

    assert node.is_dir is True
    assert node.size == 0
    assert node.children == []


def test_scan_path_skips_child_os_error(monkeypatch, tmp_path):
    class BadEntry:
        @property
        def path(self):
            raise OSError()

    def fake_scan(path):
        if path == tmp_path:
            return [BadEntry()]
        raise OSError()

    monkeypatch.setattr(scanner.os, "scandir", fake_scan)
    monkeypatch.setattr(scanner.os.path, "isdir", lambda path: path == tmp_path)

    node = scan_path(tmp_path)

    assert node.children == []
    assert node.size == 0
