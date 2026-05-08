import os

from models import Node


def scan_path(path):
    node = Node(path, os.path.isdir(path))

    if not node.is_dir:
        try:
            node.size = os.path.getsize(path)
        except OSError:
            node.size = 0
        return node

    try:
        entries = list(os.scandir(path))
    except PermissionError:
        return node
    except OSError:
        return node

    for entry in entries:
        try:
            child = scan_path(entry.path)
            node.children.append(child)
            node.size += child.size
        except OSError:
            pass

    node.children.sort(key=lambda n: n.size, reverse=True)
    return node
