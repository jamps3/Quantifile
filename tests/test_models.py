import os

from models import Node, human_size


def test_node_defaults_for_named_path():
    node = Node(os.path.join("root", "child.txt"), False)

    assert node.path == os.path.join("root", "child.txt")
    assert node.name == "child.txt"
    assert node.is_dir is False
    assert node.size == 0
    assert node.children == []
    assert node.access_denied is False
    assert node.modified_time == 0.0


def test_node_uses_path_as_name_for_root_like_path():
    node = Node(os.path.sep, True)

    assert node.name == os.path.sep


def test_human_size_formats_units():
    assert human_size(0) == "0.0 B"
    assert human_size(1023) == "1023.0 B"
    assert human_size(1024) == "1.0 KB"
    assert human_size(1536) == "1.5 KB"
    assert human_size(1024**2) == "1.0 MB"
    assert human_size(1024**3) == "1.0 GB"
    assert human_size(1024**4) == "1.0 TB"
    assert human_size(1024**5) == "1.0 PB"
