import os
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from models import Node, human_size


class ScanMixin:
    def cancel_scan(self):
        self.scan_aborted = True
        self.progress_label.config(text="Cancelling...")

    def start_scan(self, path):
        self.scan_type = "full"  # full or quick
        self.scan_aborted = False
        self.nodes_scanned = 0
        self.access_denied_count = 0
        self.progress_frame.pack(fill="x", before=self.main_notebook)
        self.progress["value"] = 0
        self.progress_label.config(text="Counting items...")
        self.status.config(text=f"Scanning: {self.truncate_text(path)}")
        self.canvas.delete("all")

        def worker():
            self.start_time = time.time()
            total = self.count_items(path)
            self.total_items = total
            show_progress = self.settings.get("show_scan_progress", True)
            if show_progress:
                self.after(0, lambda: self.progress_label.config(text=f"Scanning: 0 / {total} items (0.0s elapsed)..."))
            else:
                self.after(0, lambda: self.progress_label.config(text="Scanning..."))
            node = self.scan_path_with_progress(path)
            self.after(0, lambda: self.finish_scan(node))

        threading.Thread(target=worker, daemon=True).start()

    def start_quick_scan(self, path):
        """Quick scan: only top-level + immediate children, no recursive size calc."""
        self.scan_type = "quick"
        self.scan_aborted = False
        self.nodes_scanned = 0
        self.access_denied_count = 0
        self.progress_frame.pack(fill="x", before=self.main_notebook)
        self.progress["value"] = 0
        self.progress_label.config(text="Quick scanning...")
        self.status.config(text=f"Quick browse: {self.truncate_text(path)}")
        self.canvas.delete("all")

        def worker():
            node = self.quick_scan_path(path)
            self.after(0, lambda: self.finish_scan(node))

        threading.Thread(target=worker, daemon=True).start()

    def count_items(self, path):
        """Quick pre-scan to count total filesystem items."""
        try:
            if not os.path.isdir(path):
                return 1
            total = 1  # count the directory itself
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        total += self.count_items(entry.path)
                    else:
                        total += 1
            return total
        except (PermissionError, OSError):
            return 1

    def quick_scan_path(self, path):
        """Quick scan: only top-level + immediate children.
        Subdirectories get placeholder size (1 byte) for relative comparison.
        Files get actual size.
        """
        node = Node(path, os.path.isdir(path))

        if not node.is_dir:
            try:
                node.size = os.path.getsize(path)
            except OSError:
                node.size = 0
            return node

        # Top-level directory - get actual size only for files directly here
        try:
            entries = list(os.scandir(path))
        except PermissionError:
            return node
        except OSError:
            return node

        for entry in entries:
            if self.scan_aborted:
                return node
            try:
                if entry.is_file(follow_symlinks=False):
                    # Files: get actual size
                    child = Node(entry.path, False)
                    try:
                        child.size = entry.stat().st_size
                    except OSError:
                        child.size = 0
                    node.children.append(child)
                    node.size += child.size
                elif entry.is_dir(follow_symlinks=False):
                    # Directories: placeholder size, will be visually distinguishable
                    child = self.quick_scan_subdir(entry.path)
                    node.children.append(child)
                    node.size += child.size
            except OSError:
                pass

        node.children.sort(key=lambda n: n.size, reverse=True)
        return node

    def quick_scan_subdir(self, path):
        """For quick mode: scan only immediate children of a subdirectory.
        Use small placeholder sizes so folders are visible but comparable.
        """
        node = Node(path, True)
        try:
            entries = list(os.scandir(path))
        except PermissionError:
            self.mark_access_denied(node)
            self.log_from_worker(
                f"Permission denied quick-browsing {path}. Using {human_size(node.size)} placeholder.",
                "WARNING"
            )
            return node
        except OSError:
            node.size = 1
            return node

        for entry in entries:
            try:
                if entry.is_file(follow_symlinks=False):
                    try:
                        node.size += entry.stat().st_size
                    except OSError:
                        pass
                else:
                    # Nested subdirs: minimal placeholder
                    node.size += 1
            except OSError:
                pass

        # Sort children by size if we have them
        node.children.sort(key=lambda n: n.size, reverse=True) if node.children else None
        return node

    def update_scan_progress(self):
        if not self.settings.get("show_scan_progress", True):
            return
        if not hasattr(self, "total_items") or self.total_items <= 0:
            return
        if self.nodes_scanned % 100 != 0 and self.nodes_scanned != self.total_items:
            return

        elapsed = time.time() - self.start_time
        progress = min(1, self.nodes_scanned / self.total_items)
        eta_str = ""
        if progress > 0:
            eta = elapsed / progress * (1 - progress)
            eta_str = f", {eta:.1f}s ETA"

        self.after(0, lambda: (
            self.progress.config(value=progress * 100),
            self.progress_label.config(
                text=(
                    f"Scanning: {self.nodes_scanned} / {self.total_items} "
                    f"items ({elapsed:.1f}s elapsed{eta_str})"
                )
            )
        ))

    def increment_nodes_scanned(self, amount=1):
        with self._nodes_scanned_lock:
            self.nodes_scanned += amount
            self.update_scan_progress()

    def mark_access_denied(self, node):
        node.access_denied = True
        try:
            node.size = os.path.getsize(node.path)
        except OSError:
            node.size = 1
        if node.size <= 0:
            node.size = 1
        with self._nodes_scanned_lock:
            self.access_denied_count = getattr(self, "access_denied_count", 0) + 1
        return node.size

    def scan_file_node(self, path):
        node = Node(path, False)
        try:
            node.size = os.path.getsize(path)
        except OSError:
            node.size = 0
        self.increment_nodes_scanned()
        return node

    def scan_directory_level(self, path):
        node = Node(path, True)
        child_dirs = []
        self.increment_nodes_scanned()

        try:
            entries = list(os.scandir(path))
        except PermissionError:
            fallback_size = self.mark_access_denied(node)
            self.log_from_worker(
                f"Permission denied scanning {path}. Using {human_size(fallback_size)} placeholder.",
                "WARNING"
            )
            return node, child_dirs
        except OSError as e:
            self.log_from_worker(f"Error scanning {path}: {e}", "ERROR")
            return node, child_dirs

        for entry in entries:
            if self.scan_aborted:
                break
            try:
                if entry.is_dir(follow_symlinks=False):
                    child_dirs.append(entry.path)
                else:
                    child = Node(entry.path, False)
                    try:
                        child.size = entry.stat().st_size
                    except OSError:
                        child.size = 0
                    node.children.append(child)
                    node.size += child.size
                    self.increment_nodes_scanned()
            except OSError:
                pass

        return node, child_dirs

    def recompute_directory_sizes(self, node):
        if not node.is_dir:
            return node.size
        if getattr(node, "access_denied", False):
            return node.size

        node.size = sum(self.recompute_directory_sizes(child) for child in node.children)
        node.children.sort(key=lambda n: n.size, reverse=True)
        return node.size

    def scan_path_with_progress(self, path):
        """Scan with node counting and abort capability."""
        try:
            max_threads = int(self.settings.get("max_scan_threads", 6))
        except (TypeError, ValueError):
            max_threads = 6
        max_threads = max(1, min(32, max_threads))

        if not os.path.isdir(path):
            return self.scan_file_node(path)

        root_node = None
        all_dirs = []

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            pending = {
                executor.submit(self.scan_directory_level, path): None
            }

            while pending and not self.scan_aborted:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    parent = pending.pop(future)
                    try:
                        node, child_dirs = future.result()
                    except OSError:
                        continue

                    all_dirs.append(node)
                    if parent is None:
                        root_node = node
                    else:
                        parent.children.append(node)
                        parent.size += node.size

                    for child_path in child_dirs:
                        if self.scan_aborted:
                            break
                        pending[executor.submit(
                            self.scan_directory_level,
                            child_path
                        )] = node

        if self.scan_aborted:
            for future in pending:
                future.cancel()

        if root_node is None:
            root_node = Node(path, True)

        self.recompute_directory_sizes(root_node)

        return root_node

    def finish_scan(self, node):
        self.progress_frame.pack_forget()
        self.progress["value"] = 0
        self.progress_label.config(text="")
        
        if self.scan_aborted:
            self.status.config(text="Scan cancelled")
            self.canvas.delete("all")
            self.root_node = None
            self.current_node = None
            self.selected_node = None
            return

        old_current = self.current_node
        self.root_node = node
        self.selected_node = None

        # Add free space node if toggle is on and it's a drive root
        if self.show_free_space_toggle:
            drive, _ = os.path.splitdrive(self.root_node.path)
            if drive and os.path.basename(self.root_node.path) == "":
                # It's a drive root like "C:\" or "W:\"
                try:
                    if hasattr(os, 'statvfs'):
                        stat = os.statvfs(self.root_node.path)
                        free = stat.f_bavail * stat.f_frsize
                    else:
                        import ctypes
                        free_bytes = ctypes.c_ulonglong(0)
                        total_bytes = ctypes.c_ulonglong(0)
                        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                            self.root_node.path, None, ctypes.byref(total_bytes), ctypes.byref(free_bytes)
                        )
                        free = free_bytes.value
                    if free > 0:
                        free_node = Node("", False)
                        free_node.name = "Free Space"
                        free_node.size = free
                        self.root_node.children.append(free_node)
                        self.root_node.children.sort(key=lambda n: n.size, reverse=True)
                except Exception:
                    pass  # Ignore errors, don't add free space



        self.animate_zoom(old_current, node)
        if getattr(self, "access_denied_count", 0):
            self.log_message(
                f"Scan completed with {self.access_denied_count} inaccessible folder"
                f"{'s' if self.access_denied_count != 1 else ''}. "
                "They are shown as access-denied placeholders.",
                "WARNING",
                show_log=False
            )
        else:
            self.log_message("Scan completed with no inaccessible folders.", "INFO")

    def rescan(self):
        if self.root_node:
            if getattr(self, "scan_type", "full") == "quick":
                self.start_quick_scan(self.root_node.path)
            else:
                self.start_scan(self.root_node.path)
