import os


class Node:
    def __init__(self, path, is_dir):
        self.path = path
        self.name = os.path.basename(path) or path
        self.is_dir = is_dir
        self.size = 0
        self.children = []
        self.access_denied = False
        self.modified_time = 0.0


def human_size(size):
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)

    for unit in units:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{value:.1f} PB"
