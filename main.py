import os
import sys
import math
import json
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor


class Node:
    def __init__(self, path, is_dir):
        self.path = path
        self.name = os.path.basename(path) or path
        self.is_dir = is_dir
        self.size = 0
        self.children = []


def human_size(size):
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)

    for unit in units:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{value:.1f} PB"


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
            messagebox.showerror("Scan Failed", f"Permission denied scanning {path}. Try running as administrator or scan a subdirectory.")
            return node
        except OSError as e:
            messagebox.showerror("Scan Failed", f"Error scanning {path}: {e}")
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


def treemap(nodes, x, y, w, h):
    total = sum(n.size for n in nodes)

    if total <= 0 or not nodes:
        return []

    result = []
    _squarify(nodes, x, y, w, h, total, result)
    return result


def _squarify(nodes, x, y, w, h, total, result):
    """Squarified treemap layout algorithm.
    Recursively places nodes to minimize worst-case aspect ratio.
    """
    if not nodes:
        return

    if w <= 0 or h <= 0:
        return

    # For very small areas or single node, just fill
    if len(nodes) == 1:
        result.append((nodes[0], x, y, w, h))
        return

    # Decide primary axis: use the longer side for rows/columns
    vertical = h > w  # If height > width, lay out in columns (vertical)

    # Find the row of nodes that best fits the available space
    row, rest = _pick_row(nodes, total, w if not vertical else h)

    if not row:
        # Fallback: treat first node as row
        row = [nodes[0]]
        rest = nodes[1:]

    row_total = sum(n.size for n in row)

    if vertical:
        # Lay out row as a column (fixed width, split height)
        row_height = max(1, h * row_total / total)
        row_height = min(row_height, h)

        current_y = y
        for node in row:
            node_h = max(1, row_height * node.size / row_total) if row_total > 0 else 1
            if node_h < 1:
                node_h = 1
            # Ensure we don't exceed remaining height
            if current_y + node_h > y + h:
                node_h = max(1, y + h - current_y)
            result.append((node, x, current_y, w, node_h))
            current_y += node_h

        # Remaining space for rest
        remaining_h = max(0, h - (current_y - y))
        if rest and remaining_h > 1:
            _squarify(rest, x, current_y, w, remaining_h,
                     total - row_total, result)
    else:
        # Lay out row as a row (fixed height, split width)
        row_width = max(1, w * row_total / total)
        row_width = min(row_width, w)

        current_x = x
        for node in row:
            node_w = max(1, row_width * node.size / row_total) if row_total > 0 else 1
            if node_w < 1:
                node_w = 1
            # Ensure we don't exceed remaining width
            if current_x + node_w > x + w:
                node_w = max(1, x + w - current_x)
            result.append((node, current_x, y, node_w, h))
            current_x += node_w

        # Remaining space for rest
        remaining_w = max(0, w - (current_x - x))
        if rest and remaining_w > 1:
            _squarify(rest, current_x, y, remaining_w, h,
                     total - row_total, result)


def _pick_row(nodes, total, space_len):
    """Select a row of nodes that minimizes the worst-case aspect ratio.
    Returns (row_nodes, remaining_nodes).
    """
    if not nodes:
        return [], []

    # For very small sets, take first few
    if len(nodes) <= 3:
        return nodes[:1], nodes[1:]

    best_row = []
    best_worst_ratio = float('inf')
    best_remainder = []

    # Try different row sizes, find best worst-case aspect ratio
    for i in range(1, min(len(nodes) + 1, 20)):  # Cap at 20 for performance
        row = nodes[:i]
        remain = nodes[i:]
        row_sum = sum(n.size for n in row)
        rest_sum = total - row_sum

        if row_sum <= 0:
            break

        # Calculate aspect ratios for this row
        # Space fraction for this row: row_sum / total
        row_space = space_len * row_sum / total

        # Worst aspect ratio in the row
        worst_ratio = 0
        for node in row:
            if node.size <= 0:
                continue
            node_space = row_space * node.size / row_sum
            if row_space > 0 and node_space > 0:
                # Aspect ratio: max(w,h) / min(w,h)
                ratio = max(row_space, node_space) / min(row_space, node_space)
                worst_ratio = max(worst_ratio, ratio)

        # Also consider the remainder would get squished too small
        if remain and rest_sum > 0:
            remain_space = space_len * rest_sum / total
            if remain_space < space_len * 0.01:  # Less than 1% of space
                # Penalize tiny remainders
                worst_ratio *= 3

        # Better if worst ratio is smaller
        if worst_ratio < best_worst_ratio:
            best_worst_ratio = worst_ratio
            best_row = row
            best_remainder = remain

    return best_row, best_remainder


class Quantifile(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Quantifile")

        self.load_settings()
        self.apply_geometry()

        self.root_node = None
        self.current_node = None
        self.rect_nodes = {}
        self.dark_mode = False

        self.create_ui()
        self.apply_theme()

        # Save window position on close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_search_ui(self):
        # Search row
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=4, pady=(0, 4))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.apply_search())

        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 4))
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack(side="left", padx=(0, 4))

        self.search_type_var = tk.StringVar(value="name")
        ttk.Radiobutton(search_frame, text="Name", variable=self.search_type_var, value="name",
                        command=self.apply_search).pack(side="left", padx=2)
        ttk.Radiobutton(search_frame, text="Size ≥ ", variable=self.search_type_var, value="size",
                        command=self.apply_search).pack(side="left", padx=2)

        self.min_size_var = tk.StringVar(value="1MB")
        self.size_entry = ttk.Entry(search_frame, textvariable=self.min_size_var, width=8)
        self.size_entry.pack(side="left", padx=(0, 4))
        self.size_entry.bind("<Return>", lambda e: self.apply_search())
        self.size_entry.bind("<KeyRelease>", lambda e: self.apply_search() if e.keysym in ("Return", "KP_Enter") else None)

        ttk.Button(search_frame, text="×", width=2, command=self.clear_search).pack(side="left", padx=2)

    def create_status_ui(self):
        # Status row
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=4, pady=(0, 4))

        self.status = ttk.Label(status_frame, text="Choose a folder to scan", anchor="w")
        self.status.pack(fill="x")

    def truncate_text(self, text):
        import tkinter.font as tkfont
        # Get available width for text (window width minus padding)
        available_width = max(100, self.winfo_width() - 20)  # Minimum 100
        font_str = self.status.cget("font")
        font = tkfont.Font(font=font_str)
        full_width = font.measure(text)
        if full_width <= available_width:
            return text
        # Binary search for max length
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            truncated = text[:mid] + "..."
            width = font.measure(truncated)
            if width <= available_width:
                low = mid
            else:
                high = mid - 1
        return text[:low] + "..."

    def create_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Open Folder", command=self.choose_folder).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Quick Browse", command=self.quick_browse).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Rescan", command=self.rescan).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Zoom Out", command=self.zoom_out).pack(side="left", padx=4, pady=4)
        self.quick_zoom_button = ttk.Button(toolbar, text="Quick Zoom (OFF)", command=self.toggle_quick_zoom)
        self.quick_zoom_button.pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Open Selected", command=self.open_selected).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=4, pady=4)
        self.free_space_button = ttk.Button(toolbar, text="Free Space (OFF)", command=self.toggle_free_space)
        self.free_space_button.pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Export SVG", command=self.export_svg).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Settings", command=self.show_settings).pack(side="right", padx=4, pady=4)
        ttk.Button(toolbar, text="About", command=self.show_about).pack(side="right", padx=4, pady=4)

        self.create_search_ui()
        self.create_status_ui()

        # Progress bar (initially hidden)
        self.progress_frame = ttk.Frame(self)
        self.progress = ttk.Progressbar(self.progress_frame, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=5, pady=2)
        self.progress_label = ttk.Label(self.progress_frame, text="", anchor="center")
        self.progress_label.pack(fill="x", padx=5)
        self.cancel_button = ttk.Button(self.progress_frame, text="Cancel Scan", command=self.cancel_scan)
        self.cancel_button.pack(pady=2)
        self.progress_frame.pack_forget()

        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Configure>", self.on_resize)

        self.bind("<BackSpace>", lambda e: self.zoom_out())
        self.bind("<Return>", self.on_enter)
        self.bind("<KP_Enter>", self.on_enter)
        self.bind("<Left>", self.on_arrow)
        self.bind("<Right>", self.on_arrow)
        self.bind("<Up>", self.on_arrow)
        self.bind("<Down>", self.on_arrow)

        self.selected_node = None
        self.scan_aborted = False
        self.nodes_scanned = 0
        self._nodes_scanned_lock = threading.Lock()
        self._resize_job = None

        # Search state
        self.search_matches = set()  # Set of node paths that match the current search
        self.current_search = ""
        self.search_active = False

        # Right-click menu and toggle
        self.quick_zoom_mode = False  # False = show menu, True = instant zoom out
        self.context_menu = None

        # Free space toggle
        self.show_free_space_toggle = False

    def on_resize(self, event):
        """Redraw treemap when window is resized (e.g., fullscreen toggle)."""
        # Ignore resize events from the progress frame
        if not hasattr(self, "canvas") or not hasattr(self, "current_node"):
            return
        if hasattr(self, "progress_frame") and self.progress_frame.winfo_ismapped():
            return
        if not self.current_node or self.scan_aborted:
            return

        # Debounce rapid resize events (e.g., during window drag)
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, self._do_resize_draw)

    def _do_resize_draw(self):
        """Perform the actual redraw after resize debounce."""
        self._resize_job = None
        if self.current_node and not self.scan_aborted:
            self.draw()

    def parse_size(self, size_str):
        """Convert a size string like '1MB', '500KB', '2GB' to bytes."""
        if not size_str:
            return 0
        size_str = size_str.strip().upper()
        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
        
        # Try format: number + unit (e.g., "5MB", "1GB")
        for unit, multiplier in units.items():
            if size_str.endswith(unit.upper()):
                try:
                    num = float(size_str[:-len(unit)])
                    return int(num * multiplier)
                except ValueError:
                    continue
        
        # Try plain number (assume bytes)
        try:
            return int(float(size_str))
        except ValueError:
            return 0

    def apply_search(self):
        """Filter nodes based on search criteria."""
        search_text = self.search_var.get().strip()
        self.current_search = search_text
        
        if not search_text:
            self.clear_search()
            return

        self.search_active = True
        search_type = self.search_type_var.get()
        
        # Build matches set
        self.search_matches.clear()
        
        if self.current_node:
            if search_type == "name":
                self._collect_name_matches(self.current_node, search_text.lower())
            elif search_type == "size":
                min_bytes = self.parse_size(self.min_size_var.get())
                self._collect_size_matches(self.current_node, min_bytes)
        
        # Redraw to highlight matches
        self.draw()
        
        # Update status
        match_count = len(self.search_matches)
        if match_count > 0:
            scan_mode = "Quick browse" if getattr(self, "scan_type", "full") == "quick" else "Full scan"
            self.status.config(text=f"{scan_mode}: {self.truncate_text(self.current_node.path)} — {human_size(self.current_node.size)} | {match_count} matches")
        else:
            scan_mode = "Quick browse" if getattr(self, "scan_type", "full") == "quick" else "Full scan"
            self.status.config(text=f"{scan_mode}: {self.truncate_text(self.current_node.path)} — {human_size(self.current_node.size)} | No matches")

    def _collect_name_matches(self, node, search_lower):
        """Recursively collect nodes whose name contains the search text."""
        if search_lower in node.name.lower():
            self.search_matches.add(node.path)
        for child in node.children:
            self._collect_name_matches(child, search_lower)

    def _collect_size_matches(self, node, min_bytes):
        """Recursively collect nodes whose size >= min_bytes."""
        if node.size >= min_bytes:
            self.search_matches.add(node.path)
        for child in node.children:
            self._collect_size_matches(child, min_bytes)

    def clear_search(self):
        """Clear current search and reset highlighting."""
        self.search_var.set("")
        self.min_size_var.set("1MB")
        self.search_active = False
        self.search_matches.clear()
        self.draw()
        if self.current_node:
            scan_mode = "Quick browse" if getattr(self, "scan_type", "full") == "quick" else "Full scan"
            self.status.config(text=f"{scan_mode}: {self.truncate_text(self.current_node.path)} — {human_size(self.current_node.size)}")

    def choose_folder(self):
        path = filedialog.askdirectory(title="Select folder or drive")
        if path:
            self.start_scan(path)

    def quick_browse(self):
        """Quick browse mode: shallow scan, no size calculation for subdirs."""
        path = filedialog.askdirectory(title="Select folder to quick browse")
        if path:
            self.start_quick_scan(path)

    def cancel_scan(self):
        self.scan_aborted = True
        self.progress_label.config(text="Cancelling...")

    def start_scan(self, path):
        self.scan_type = "full"  # full or quick
        self.scan_aborted = False
        self.nodes_scanned = 0
        self.progress_frame.pack(fill="x", before=self.canvas)
        self.progress["value"] = 0
        self.progress_label.config(text="Counting items...")
        self.status.config(text=f"Scanning: {self.truncate_text(path)}")
        self.canvas.delete("all")

        def worker():
            total = self.count_items(path)
            self.total_items = total
            show_progress = self.settings.get("show_scan_progress", True)
            if show_progress:
                self.after(0, lambda: self.progress_label.config(text=f"Scanning: 0 / {total} items..."))
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
        self.progress_frame.pack(fill="x", before=self.canvas)
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
            # Give directories a minimal placeholder so they appear
            node.size = 1
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

    def scan_path_with_progress(self, path):
        """Scan with node counting and abort capability."""
        node = Node(path, os.path.isdir(path))

        if not node.is_dir:
            try:
                node.size = os.path.getsize(path)
            except OSError:
                node.size = 0
            with self._nodes_scanned_lock:
                self.nodes_scanned += 1
                if self.settings.get("show_scan_progress", True) and hasattr(self, 'total_items') and (self.nodes_scanned % 100 == 0 or self.nodes_scanned == self.total_items):
                    self.after(0, lambda: (
                        self.progress.config(value=self.nodes_scanned / self.total_items * 100),
                        self.progress_label.config(text=f"Scanning: {self.nodes_scanned} / {self.total_items} items...")
                    ))
            return node

        with self._nodes_scanned_lock:
            self.nodes_scanned += 1
            if self.settings.get("show_scan_progress", True) and hasattr(self, 'total_items') and (self.nodes_scanned % 100 == 0 or self.nodes_scanned == self.total_items):
                self.after(0, lambda: (
                    self.progress.config(value=self.nodes_scanned / self.total_items * 100),
                    self.progress_label.config(text=f"Scanning: {self.nodes_scanned} / {self.total_items} items...")
                ))

        try:
            entries = list(os.scandir(path))
        except PermissionError:
            messagebox.showerror("Scan Failed", f"Permission denied scanning {path}. Try running as administrator or scan a subdirectory.")
            return node
        except OSError as e:
            messagebox.showerror("Scan Failed", f"Error scanning {path}: {e}")
            return node

        with self._nodes_scanned_lock:
            self.nodes_scanned += 1
            if self.settings.get("show_scan_progress", True) and hasattr(self, 'total_items') and (self.nodes_scanned % 100 == 0 or self.nodes_scanned == self.total_items):
                self.after(0, lambda: (
                    self.progress.config(value=self.nodes_scanned / self.total_items * 100),
                    self.progress_label.config(text=f"Scanning: {self.nodes_scanned} / {self.total_items} items...")
                ))

        try:
            entries = list(os.scandir(path))
        except PermissionError:
            return node
        except OSError:
            return node

        dirs = []
        files = []
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    dirs.append(entry)
                else:
                    files.append(entry)
            except OSError:
                pass  # Skip entries that can't be accessed

        for entry in files:
            if self.scan_aborted:
                return node
            try:
                child = Node(entry.path, False)
                child.size = entry.stat().st_size
                node.children.append(child)
                node.size += child.size
            except OSError:
                pass
            else:
                with self._nodes_scanned_lock:
                    self.nodes_scanned += 1
                    if self.settings.get("show_scan_progress", True) and hasattr(self, 'total_items') and (self.nodes_scanned % 100 == 0 or self.nodes_scanned == self.total_items):
                        self.after(0, lambda: (
                            self.progress.config(value=self.nodes_scanned / self.total_items * 100),
                            self.progress_label.config(text=f"Scanning: {self.nodes_scanned} / {self.total_items} items...")
                        ))

        if dirs and not self.scan_aborted:
            def scan_dir(entry):
                try:
                    return self.scan_path_with_progress(entry.path)
                except OSError:
                    return None

            with ThreadPoolExecutor(max_workers=min(len(dirs), 8)) as executor:
                results = list(executor.map(scan_dir, dirs))
                for child in results:
                    if child:
                        node.children.append(child)
                        node.size += child.size

        node.children.sort(key=lambda n: n.size, reverse=True)
        return node



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

    def rescan(self):
        if self.root_node:
            if getattr(self, "scan_type", "full") == "quick":
                self.start_quick_scan(self.root_node.path)
            else:
                self.start_scan(self.root_node.path)

    def draw(self):
        self.canvas.delete("all")
        self.rect_nodes.clear()

        if not self.current_node:
            return

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        self.draw_node(self.current_node, 5, 5, width - 10, height - 10, depth=0)

    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {}
        defaults = {
            "dark_mode": False,
            "min_density": 1,
            "disable_delete": False,
            "remember_window_pos": True,
            "fullscreen": False,
            "show_scan_progress": True,
            "animated_zoom": False,
            "auto_rescan_on_delete": True,
            "dir_color": "",
            "file_color": "",
            "selection_color": "#ffcc00",
            "outline_color": "",
            "label_color": "",
            "canvas_bg": "",
            "file_type_colors": {
                "image": "#ff6600",
                "video": "#cc0000",
                "audio": "#00cc00",
                "document": "#0066ff",
                "archive": "#cccc00",
                "executable": "#cc00cc",
                "code": "#00cccc",
                "text": "#aaaaaa"
            }
        }
        for key, value in defaults.items():
            if key not in self.settings:
                self.settings[key] = value
        self.dark_mode = self.settings.get("dark_mode", False)

    def apply_geometry(self):
        """Restore window position and size if remembered."""
        if self.settings.get("remember_window_pos", True):
            fullscreen = self.settings.get("fullscreen", False)
            if fullscreen:
                self.state("zoomed")
                return
            # Try saved geometry
            geom = self.settings.get("window_geometry")
            if geom:
                try:
                    self.geometry(geom)
                    return
                except tk.TclError:
                    pass  # Invalid geometry, use default
        
        # Fallback to default centered geometry
        self.geometry("1100x750")
        self.center_window()

    def center_window(self):
        """Center the window on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def on_close(self):
        """Save window position before exiting."""
        if self.settings.get("remember_window_pos", True):
            fullscreen = self.state() == "zoomed"
            self.settings["fullscreen"] = fullscreen
            if not fullscreen:
                self.settings["window_geometry"] = self.geometry()
            else:
                # Clear geometry if maximized
                self.settings.pop("window_geometry", None)
            self.save_settings()
        self.destroy()

    def save_settings(self):
        with open("settings.json", "w") as f:
            json.dump(self.settings, f)

    def apply_theme(self):
        if self.dark_mode:
            # Dark theme
            self.configure(bg="#1e1e1e")
            default_canvas_bg = "#2d2d30"
            self.style = ttk.Style()
            self.style.configure("TFrame", background="#1e1e1e")
            self.style.configure("TButton", background="#3c3c3c", foreground="#cccccc")
            self.style.map("TButton", background=[("active", "#4a4a4a")])
            self.style.configure("TLabel", background="#1e1e1e", foreground="#cccccc")
        else:
            # Light theme
            self.configure(bg="#f0f0f0")
            default_canvas_bg = "white"
            self.style = ttk.Style()
            self.style.configure("TFrame", background="#f0f0f0")
            self.style.configure("TButton", background="#e0e0e0", foreground="black")
            self.style.map("TButton", background=[("active", "#d0d0d0")])
            self.style.configure("TLabel", background="#f0f0f0", foreground="black")

        # Apply canvas background (custom or default)
        canvas_bg = self.settings.get("canvas_bg", default_canvas_bg)
        if not canvas_bg:
            canvas_bg = default_canvas_bg
        self.canvas.configure(bg=canvas_bg)

    def toggle_dark_mode(self, enabled):
        self.dark_mode = enabled
        self.settings["dark_mode"] = enabled
        self.save_settings()
        self.apply_theme()
        if self.current_node:
            self.draw()

    def show_settings(self):
        settings_win = tk.Toplevel(self)
        settings_win.title("Settings")
        width, height = 440, 440
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        settings_win.geometry(f"{width}x{height}+{x}+{y}")
        settings_win.transient(self)
        settings_win.grab_set()
        settings_win.resizable(False, False)

        main_frame = ttk.Frame(settings_win, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Appearance", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 10))

        theme_frame = ttk.Frame(main_frame)
        theme_frame.pack(fill="x", pady=(0, 20))

        ttk.Label(theme_frame, text="Theme:").pack(side="left")

        self.theme_var = tk.StringVar(value="light" if not self.dark_mode else "dark")

        ttk.Radiobutton(theme_frame, text="Light", variable=self.theme_var, value="light",
                        command=lambda: self.on_theme_change("light")).pack(side="left", padx=(10, 20))
        ttk.Radiobutton(theme_frame, text="Dark", variable=self.theme_var, value="dark",
                        command=lambda: self.on_theme_change("dark")).pack(side="left", padx=(0, 20))

        ttk.Button(main_frame, text="Color Settings...", command=self.show_color_settings).pack(anchor="w", pady=(0, 10))
        ttk.Button(main_frame, text="File Type Colors...", command=self.show_file_type_colors).pack(anchor="w", pady=(0, 20))

        ttk.Label(main_frame, text="Behavior", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 5))

        self.density_var = tk.IntVar(value=self.settings.get("min_density", 1))
        ttk.Checkbutton(main_frame, text="Hide small files (density filter)", variable=self.density_var).pack(anchor="w", pady=2)

        self.disable_delete_var = tk.BooleanVar(value=self.settings.get("disable_delete", False))
        ttk.Checkbutton(main_frame, text="Disable delete command", variable=self.disable_delete_var).pack(anchor="w", pady=2)

        self.remember_pos_var = tk.BooleanVar(value=self.settings.get("remember_window_pos", True))
        ttk.Checkbutton(main_frame, text="Remember window position", variable=self.remember_pos_var).pack(anchor="w", pady=2)

        self.show_scan_progress_var = tk.BooleanVar(value=self.settings.get("show_scan_progress", True))
        ttk.Checkbutton(main_frame, text="Show scan progress details", variable=self.show_scan_progress_var).pack(anchor="w", pady=2)

        self.animated_zoom_var = tk.BooleanVar(value=self.settings.get("animated_zoom", False))
        ttk.Checkbutton(main_frame, text="Animated zoom in/out", variable=self.animated_zoom_var).pack(anchor="w", pady=2)

        self.auto_rescan_var = tk.BooleanVar(value=self.settings.get("auto_rescan_on_delete", True))
        ttk.Checkbutton(main_frame, text="Auto rescan after delete", variable=self.auto_rescan_var).pack(anchor="w", pady=2)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))

        def save_and_close():
            self.settings["min_density"] = self.density_var.get()
            self.settings["disable_delete"] = self.disable_delete_var.get()
            self.settings["remember_window_pos"] = self.remember_pos_var.get()
            self.settings["show_scan_progress"] = self.show_scan_progress_var.get()
            self.settings["animated_zoom"] = self.animated_zoom_var.get()
            self.settings["auto_rescan_on_delete"] = self.auto_rescan_var.get()
            self.settings["dark_mode"] = (self.theme_var.get() == "dark")
            self.dark_mode = self.settings["dark_mode"]
            self.save_settings()
            self.apply_theme()
            if self.current_node:
                self.draw()
            settings_win.destroy()

        def cancel_and_close():
            self.load_settings()
            settings_win.destroy()

        ttk.Button(button_frame, text="Save", command=save_and_close).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=cancel_and_close).pack(side="right")

        settings_win.protocol("WM_DELETE_WINDOW", cancel_and_close)

    def show_about(self):
        about_win = tk.Toplevel(self)
        about_win.title("About Quantifile")
        width = 500
        height = 550  # Increased height for more text
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        about_win.geometry(f"{width}x{height}+{x}+{y}")
        about_win.transient(self)
        about_win.grab_set()
        about_win.resizable(False, False)

        main_frame = ttk.Frame(about_win, padding=20)
        main_frame.pack(fill="both", expand=True)

        try:
            logo = tk.PhotoImage(file="icon-1024.png")
            logo = logo.subsample(4, 4)
            logo_label = ttk.Label(main_frame, image=logo)
            logo_label.image = logo
            logo_label.pack(pady=(0, 10))
        except tk.TclError:
            pass

        ttk.Label(main_frame, text="Quantifile", font=("", 14, "bold")).pack()
        ttk.Label(main_frame, text="Disk space visualization tool inspired by SpaceMonger 1.4.0").pack(pady=(0, 5))
        ttk.Label(main_frame, text="Explore and analyze directory structures with interactive treemaps.").pack(pady=(0, 10))
        ttk.Label(main_frame, text="© 2026 Jan-Erik Labbas. All rights reserved.").pack(pady=(0, 5))
        ttk.Label(main_frame, text="Licensed under MIT License.").pack(pady=(0, 5))
        paypal_label = ttk.Label(main_frame, text="Support me on PayPal: paypal.me/jamps3", cursor="hand2", foreground="#0000FF")
        paypal_label.pack(pady=(0, 10))
        paypal_label.bind("<Button-1>", lambda e: self.open_paypal())
        ttk.Label(main_frame, text="Version 1.0").pack(pady=(0, 10))

        ttk.Button(main_frame, text="Close", command=about_win.destroy).pack(pady=(10, 0))

        about_win.protocol("WM_DELETE_WINDOW", about_win.destroy)

    def on_theme_change(self, theme):
        self.toggle_dark_mode(theme == "dark")

    def open_paypal(self):
        import webbrowser
        webbrowser.open("https://paypal.me/jamps3")

    def show_properties(self):
        node = self.selected_node
        if not node or not node.path:
            return
        try:
            if sys.platform.startswith("win"):
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(None, "properties", node.path, None, None, 1)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", node.path], check=False)
            else:
                # Linux, try common file managers
                success = False
                for cmd in [["nautilus", "--properties", node.path], ["dolphin", "--properties", node.path], ["thunar", "--properties", node.path]]:
                    try:
                        subprocess.run(cmd, check=False)
                        success = True
                        break
                    except FileNotFoundError:
                        continue
                if not success:
                    messagebox.showinfo("Properties", "Properties dialog not supported on this system.")
        except Exception as e:
            messagebox.showerror("Properties", f"Could not open properties: {e}")

    def get_file_category(self, filename):
        """Return file type category based on extension."""
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        
        categories = {
            'image': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'svg', 'ico', 'heic', 'heif'},
            'video': {'mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', 'mpg', 'mpeg'},
            'audio': {'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma', 'opus', 'aiff'},
            'document': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf', 'csv', 'odt', 'ods', 'odp'},
            'archive': {'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'iso', 'dmg', 'vmdk'},
            'executable': {'exe', 'msi', 'bat', 'sh', 'app', 'dmg', 'pkg', 'deb', 'rpm', 'apk'},
            'code': {'py', 'js', 'ts', 'html', 'css', 'c', 'cpp', 'h', 'hpp', 'java', 'go', 'rs', 'rb', 'php', 'sql', 'json', 'xml', 'yaml', 'yml', 'md', 'sh', 'bash', 'zsh', 'ps1', 'lua', 'perl'}
        }
        
        for category, extensions in categories.items():
            if ext in extensions:
                return category
        return "other"

    def color_for_node(self, node, depth):
        # Special case for free space
        if node.name == "Free Space":
            return "#888888" if self.dark_mode else "#c0c0c0"  # Distinct gray

        # Directories: check dir_color custom first
        if node.is_dir:
            custom = self.settings.get("dir_color", "")
            if custom and "," in custom:
                try:
                    r, g, b = [int(x.strip()) for x in custom.split(",")]
                    r = max(0, min(255, r))
                    g = max(0, min(255, g))
                    b = max(0, min(255, b))
                    return f"#{r:02x}{g:02x}{b:02x}"
                except (ValueError, TypeError):
                    pass
            # Use theme-based directory color
            if self.dark_mode:
                base = 60 - min(depth * 6, 40)
                return f"#{base:02x}{120 + min(depth * 15, 80):02x}{200 + min(depth * 10, 55):02x}"
            else:
                base = 180 - min(depth * 14, 120)
                return f"#{base:02x}{220:02x}{255:02x}"

        # Files: check custom file_color first
        custom = self.settings.get("file_color", "")
        if custom and "," in custom:
            try:
                r, g, b = [int(x.strip()) for x in custom.split(",")]
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                return f"#{r:02x}{g:02x}{b:02x}"
            except (ValueError, TypeError):
                pass

        # Check file type category colors
        file_type_colors = self.settings.get("file_type_colors", {})
        if file_type_colors:
            category = self.get_file_category(node.name)
            cat_color = file_type_colors.get(category)
            if cat_color:
                return cat_color

        # Use theme-based file color
        if self.dark_mode:
            base = 220 + min(depth * 10, 35)
            return f"#{255:02x}{base:02x}{100 + min(depth * 10, 55):02x}"
        else:
            base = 230 - min(depth * 10, 120)
            return f"#{255:02x}{base:02x}{120:02x}"

    def dim_color(self, hex_color):
        """Darken a hex color by 50% for search dimming effect."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return "#888888"
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            r = int(r * 0.5)
            g = int(g * 0.5)
            b = int(b * 0.5)
            return f"#{r:02x}{g:02x}{b:02x}"
        except ValueError:
            return "#888888"

    def draw_node(self, node, x, y, w, h, depth):
        if w < 2 or h < 2:
            return

        color = self.color_for_node(node, depth)

        # Apply search dimming if active and node is not a match
        if self.search_active and node.path not in self.search_matches:
            color = self.dim_color(color)

        # Determine outline color and width based on selection and settings
        if self.selected_node and node.path == self.selected_node.path:
            outline_color = self.settings.get("selection_color", "#ffcc00")
            outline_width = 3
        else:
            outline_color = self.settings.get("outline_color", "")
            if not outline_color:
                outline_color = "#666666" if self.dark_mode else "black"
            outline_width = 1

        rect = self.canvas.create_rectangle(
            x, y, x + w, y + h,
            fill=color,
            outline=outline_color,
            width=outline_width
        )

        self.rect_nodes[rect] = node

        label_color = self.settings.get("label_color", "")
        if not label_color:
            label_color = "white" if self.dark_mode else "black"

        if w > 70 and h > 25:
            # Build label with item count for directories
            if node.is_dir and node.children:
                item_count = len(node.children)
                name_part = node.name
                # Truncate long names
                if len(name_part) > 16:
                    name_part = name_part[:14] + ".."
                label = f"{name_part}\n{human_size(node.size)}\n{item_count} item{'s' if item_count != 1 else ''}"
            else:
                name_part = node.name
                if len(name_part) > 20:
                    name_part = name_part[:18] + ".."
                label = f"{name_part}\n{human_size(node.size)}"

            # Adjust font size based on rectangle dimensions
            # Base size 8, shrink if rectangle is small or label is long
            base_size = 8
            if node.is_dir and node.children:
                # Multi-line label needs more space
                font_size = max(5, min(base_size, int(h / 10), int(w / 15)))
            else:
                font_size = max(5, min(base_size, int(h / 8), int(w / (len(name_part) + 3))))

            if font_size >= 5:
                self.canvas.create_text(
                    x + 4,
                    y + 4,
                    anchor="nw",
                    text=label,
                    fill=label_color,
                    font=("Segoe UI", font_size)
                )

        if node.is_dir and node.children:
            padding = 18 if w > 80 and h > 50 else 2
            inner_x = x + 2
            inner_y = y + padding
            inner_w = max(1, w - 4)
            inner_h = max(1, h - padding - 2)

            visible_children = [c for c in node.children if c.size > 0]

            for child, cx, cy, cw, ch in treemap(visible_children, inner_x, inner_y, inner_w, inner_h):
                if cw >= 3 and ch >= 3:
                    self.draw_node(child, cx, cy, cw, ch, depth + 1)

    def node_at_event(self, event):
        items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)

        for item in reversed(items):
            if item in self.rect_nodes:
                return self.rect_nodes[item]

        return None

    def on_click(self, event):
        node = self.node_at_event(event)

        if node:
            self.selected_node = node
            scan_mode = "Quick browse" if getattr(self, "scan_type", "full") == "quick" else "Full scan"
            self.status.config(text=f"{scan_mode}: {self.truncate_text(node.path)} — {human_size(node.size)}")
            self.draw()

    def animate_zoom(self, old_node, new_node, steps=10, duration=150):
        """Animate transition between nodes."""
        if not self.settings.get("animated_zoom", False):
            self._finish_animation(new_node)
            return

        # If no old_node (first load), do a simple fade-in zoom from center
        if not old_node:
            if new_node:
                self.current_node = new_node
                self.selected_node = new_node
                self.canvas.delete("all")
                self.rect_nodes.clear()
                width = self.canvas.winfo_width()
                height = self.canvas.winfo_height()
                cx, cy = width // 2, height // 2
                
                def progressive_draw(step=0):
                    if step >= steps:
                        self.draw()
                        self._update_status(new_node)
                        return
                    
                    scale = (step + 1) / steps
                    self.canvas.delete("all")
                    self.rect_nodes.clear()
                    
                    base_w = width - 10
                    base_h = height - 10
                    draw_w = base_w * scale
                    draw_h = base_h * scale
                    draw_x = cx - draw_w // 2
                    draw_y = cy - draw_h // 2
                    
                    color = self.color_for_node(new_node, 0)
                    temp_rect_id = self.canvas.create_rectangle(
                        draw_x, draw_y, draw_x + draw_w, draw_y + draw_h,
                        fill=color, outline="black", width=1
                    )
                    self.rect_nodes[temp_rect_id] = new_node
                    
                    self.after(int(duration / steps), lambda: progressive_draw(step + 1))
                
                progressive_draw()
            return

        # Normal zoom between two existing nodes - capture old canvas state before deletion
        old_items = []
        if old_node and self.canvas.find_all():
            for rect in self.canvas.find_all():
                if rect in self.rect_nodes:
                    try:
                        x1, y1, x2, y2 = self.canvas.bbox(rect)
                        fill = self.canvas.itemcget(rect, "fill")
                        outline = self.canvas.itemcget(rect, "outline")
                        width_val = self.canvas.itemcget(rect, "width")
                        old_items.append((x1, y1, x2, y2, fill, outline, width_val))
                    except tk.TclError:
                        pass

        def do_animation(i=steps):
            if i <= 0:
                self._finish_animation(new_node)
                return
            
            scale = i / steps
            self.canvas.delete("all")
            self.rect_nodes.clear()
            
            # Draw shrinking old rectangles
            for (x1, y1, x2, y2, fill, outline, width_val) in old_items:
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                w = (x2 - x1) * scale
                h = (y2 - y1) * scale
                if w > 1 and h > 1:
                    self.canvas.create_rectangle(cx - w/2, cy - h/2, cx + w/2, cy + h/2,
                                                fill=fill, outline=outline, width=width_val)
            
            self.after(int(duration / steps), lambda: do_animation(i - 1))

        do_animation()

    def _finish_animation(self, node):
        """Complete animation by setting node and drawing final state."""
        self.current_node = node
        self.selected_node = node
        self.draw()
        # Re-apply search if active to refresh matches on new tree
        if self.search_active:
            self.apply_search()
        else:
            self._update_status(node)

    def _update_status(self, node):
        scan_mode = "Quick browse" if getattr(self, "scan_type", "full") == "quick" else "Full scan"
        if node.is_dir:
            self.status.config(text=f"{scan_mode}: {self.truncate_text(node.path)} — {human_size(node.size)} ({len(node.children)} items)")
        else:
            self.status.config(text=f"{scan_mode}: {self.truncate_text(node.path)} — {human_size(node.size)}")

    def on_enter(self, event):
        if self.selected_node:
            if self.selected_node.is_dir:
                self.animate_zoom(self.current_node, self.selected_node)
            else:
                self.open_selected()
        else:
            self.choose_folder()

    def on_arrow(self, event):
        if not self.selected_node:
            return

        # Find current rect
        current_rect = None
        for r, n in self.rect_nodes.items():
            if n == self.selected_node:
                current_rect = r
                break
        if not current_rect:
            return

        current_bbox = self.canvas.bbox(current_rect)
        if not current_bbox:
            return

        cx = (current_bbox[0] + current_bbox[2]) / 2
        cy = (current_bbox[1] + current_bbox[3]) / 2
        current_width = current_bbox[2] - current_bbox[0]
        current_height = current_bbox[3] - current_bbox[1]

        candidates = []
        for r, n in self.rect_nodes.items():
            if r == current_rect:
                continue
            bbox = self.canvas.bbox(r)
            if not bbox:
                continue
            rx = (bbox[0] + bbox[2]) / 2
            ry = (bbox[1] + bbox[3]) / 2
            if event.keysym == "Right" and rx > cx and abs(ry - cy) < current_height / 2:
                candidates.append((r, rx, ry))
            elif event.keysym == "Left" and rx < cx and abs(ry - cy) < current_height / 2:
                candidates.append((r, rx, ry))
            elif event.keysym == "Down" and ry > cy and abs(rx - cx) < current_width / 2:
                candidates.append((r, ry, rx))
            elif event.keysym == "Up" and ry < cy and abs(rx - cx) < current_width / 2:
                candidates.append((r, ry, rx))

        if not candidates:
            return

        # Find closest in the band
        if event.keysym in ("Left", "Right"):
            closest = min(candidates, key=lambda c: abs(c[1] - cx))  # Closest in x
        else:
            closest = min(candidates, key=lambda c: abs(c[1] - cy))  # Closest in y

        self.selected_node = self.rect_nodes[closest[0]]
        self.draw()

    def on_double_click(self, event):
        node = self.node_at_event(event)

        if node:
            if node.is_dir:
                self.animate_zoom(self.current_node, node)
            else:
                self.selected_node = node
                self.open_selected()

    def on_motion(self, event):
        node = self.node_at_event(event)

        if node:
            self.canvas.config(cursor="hand2")
            self.status.config(text=f"{self.truncate_text(node.path)} — {human_size(node.size)}")
        else:
            self.canvas.config(cursor="")
            if self.current_node:
                scan_mode = "Quick browse" if getattr(self, "scan_type", "full") == "quick" else "Full scan"
                self.status.config(text=f"{scan_mode}: {self.truncate_text(self.current_node.path)} — {human_size(self.current_node.size)}")

    def toggle_quick_zoom(self):
        self.quick_zoom_mode = not self.quick_zoom_mode
        # Update button appearance to show state
        if self.quick_zoom_mode:
            self.quick_zoom_button.config(text="Quick Zoom (ON)")
        else:
            self.quick_zoom_button.config(text="Quick Zoom (OFF)")

    def toggle_free_space(self):
        self.show_free_space_toggle = not self.show_free_space_toggle
        if self.show_free_space_toggle:
            self.free_space_button.config(text="Free Space (ON)")
            if self.current_node == self.root_node:
                self.add_free_space_node()
            else:
                messagebox.showinfo("Free Space", "Free space visualization is only available at the drive root level.")
        else:
            self.free_space_button.config(text="Free Space (OFF)")
            if self.current_node == self.root_node:
                self.remove_free_space_node()
        # Redraw
        if self.current_node:
            self.draw()

    def add_free_space_node(self):
        if not self.root_node or self.current_node != self.root_node:
            return  # Only add at root level
        drive, _ = os.path.splitdrive(self.root_node.path)
        if not (drive and os.path.basename(self.root_node.path) == ""):
            return  # Not a drive root
        # Check if free space node already exists
        for child in self.root_node.children:
            if child.name == "Free Space":
                return  # Already added
        # Add free space node
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
            pass  # Don't add if calculation fails

    def remove_free_space_node(self):
        if not self.root_node:
            return
        self.root_node.children = [child for child in self.root_node.children if child.name != "Free Space"]

    def on_right_click(self, event):
        if self.quick_zoom_mode:
            self.zoom_out()
        else:
            self.show_context_menu(event)

    def show_context_menu(self, event):
        if not self.context_menu:
            self.context_menu = tk.Menu(self, tearoff=0)
            self.context_menu.add_command(label="Open", command=self.open_selected)
            self.context_menu.add_command(label="Show in Explorer", command=self.open_in_manager)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Go Up", command=self.zoom_out)
            # Could add more items here in the future

        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def zoom_out(self):
        if not self.current_node or self.current_node == self.root_node:
            return

        parent_path = os.path.dirname(self.current_node.path)

        def find_parent(node, target_parent):
            if node.path == target_parent:
                return node

            for child in node.children:
                found = find_parent(child, target_parent)
                if found:
                    return found

            return None

        parent = find_parent(self.root_node, parent_path)

        if parent:
            self.animate_zoom(self.current_node, parent)

    def open_selected(self):
        node = self.selected_node

        if not node or not node.path:
            # Free space node or no selection
            if node and node.name == "Free Space":
                # Show free space info
                self.show_free_space()
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(node.path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", node.path])
            else:
                subprocess.Popen(["xdg-open", node.path])
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def open_in_manager(self):
        node = self.selected_node

        if not node or not node.path:
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(node.path, 'explore')
            elif sys.platform == "darwin":
                subprocess.run(["open", node.path], check=False)
            else:
                subprocess.run(["xdg-open", node.path], check=False)
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def delete_selected(self):
        node = self.selected_node

        if not node or not node.path:
            return

        if self.settings.get("disable_delete", False):
            messagebox.showinfo("Delete", "Delete command is disabled in settings")
            return

        confirm = messagebox.askyesno(
            "Delete",
            f"Delete this item?\n\n{node.path}"
        )

        if not confirm:
            return

        try:
            if node.is_dir:
                import shutil
                shutil.rmtree(node.path)
            else:
                os.remove(node.path)

            if self.settings.get("auto_rescan_on_delete", True):
                self.rescan()

        except Exception as e:
            messagebox.showerror("Delete failed", str(e))

    def show_free_space(self):
        """Show free space on the current drive."""
        if not self.root_node:
            messagebox.showinfo("Free Space", "No folder scanned yet")
            return
        try:
            stat = os.statvfs(self.root_node.path) if hasattr(os, 'statvfs') else None
            if stat:
                free = stat.f_bavail * stat.f_frsize
                total = stat.f_blocks * stat.f_frsize
            else:
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    self.root_node.path, None, ctypes.byref(total_bytes), ctypes.byref(free_bytes)
                )
                free = free_bytes.value
                total = total_bytes.value
            messagebox.showinfo("Free Space",
                f"Drive: {os.path.splitdrive(self.root_node.path)[0]}\n\n"
                f"Free: {human_size(free)}\n"
                f"Total: {human_size(total)}\n"
                f"Used: {human_size(total - free)}")
        except Exception as e:
            messagebox.showerror("Free Space", f"Could not get free space: {e}")

    def export_svg(self):
        """Export current treemap as an SVG file."""
        if not self.current_node:
            messagebox.showinfo("Export SVG", "No data to export.")
            return

        filename = filedialog.asksaveasfilename(
            title="Save treemap as SVG",
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")]
        )
        if not filename:
            return

        try:
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()

            # Collect all canvas items (rectangles and text)
            items = []
            for item in self.canvas.find_all():
                try:
                    item_type = self.canvas.type(item)
                    if item_type in ("rectangle", "text"):
                        items.append(item)
                except tk.TclError:
                    continue

            svg_lines = []
            svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1"')
            svg_lines.append(f'      width="{width}" height="{height}"')
            svg_lines.append(f'      viewBox="0 0 {width} {height}">')
            svg_lines.append('')

            # Draw rectangles first
            for item in items:
                try:
                    if self.canvas.type(item) == "rectangle":
                        x1, y1, x2, y2 = self.canvas.bbox(item)
                        fill = self.canvas.itemcget(item, "fill")
                        outline = self.canvas.itemcget(item, "outline")
                        width_val = self.canvas.itemcget(item, "width")
                        try:
                            stroke_w = int(float(width_val)) if width_val else 1
                        except ValueError:
                            stroke_w = 1
                        svg_lines.append(f'  <rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}"')
                        svg_lines.append(f'        fill="{fill}" stroke="{outline}" stroke-width="{stroke_w}"/>')
                except tk.TclError:
                    pass

            # Draw text on top
            for item in items:
                try:
                    if self.canvas.type(item) == "text":
                        x, y = self.canvas.coords(item)
                        text = self.canvas.itemcget(item, "text")
                        # Escape special XML characters
                        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                        fill = self.canvas.itemcget(item, "fill")
                        font_str = self.canvas.itemcget(item, "font")
                        font_parts = font_str.split()
                        if len(font_parts) >= 2:
                            size_str = font_parts[-1]
                            family = " ".join(font_parts[:-1]).strip("{}")
                        else:
                            size_str = "8"
                            family = font_str.strip("{}")
                        try:
                            size = int(size_str)
                        except ValueError:
                            size = 8
                        # Use dominant-baseline="hanging" to match Tkinter's anchor="nw" (top-left alignment)
                        svg_lines.append(f'  <text x="{x}" y="{y}" dominant-baseline="hanging"')
                        if family:
                            svg_lines.append(f'        font-family="{family}"')
                        svg_lines.append(f'        font-size="{size}" fill="{fill}">{text}</text>')
                except (tk.TclError, ValueError):
                    pass

            svg_lines.append('</svg>')

            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(svg_lines))

            messagebox.showinfo("Export SVG", f"Treemap exported successfully to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export SVG", f"Export failed: {e}")

    def show_color_settings(self):
        """Dialog for customizing colors."""
        colors_win = tk.Toplevel(self)
        colors_win.title("Color Settings")
        width, height = 420, 500
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        colors_win.geometry(f"{width}x{height}+{x}+{y}")
        colors_win.transient(self)
        colors_win.grab_set()

        main_frame = ttk.Frame(colors_win, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Directory Color (R,G,B):").pack(anchor="w")
        dir_color_var = tk.StringVar(value=self.settings.get("dir_color", ""))
        ttk.Entry(main_frame, textvariable=dir_color_var).pack(fill="x", pady=(0, 10))

        ttk.Label(main_frame, text="File Color (R,G,B):").pack(anchor="w")
        file_color_var = tk.StringVar(value=self.settings.get("file_color", ""))
        ttk.Entry(main_frame, textvariable=file_color_var).pack(fill="x", pady=(0, 10))

        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=(10, 15))

        ttk.Label(main_frame, text="Selection Outline Color (hex, e.g., #ffcc00):").pack(anchor="w")
        selection_color_var = tk.StringVar(value=self.settings.get("selection_color", "#ffcc00"))
        ttk.Entry(main_frame, textvariable=selection_color_var).pack(fill="x", pady=(0, 10))

        ttk.Label(main_frame, text="Normal Outline Color (hex or empty for theme default):").pack(anchor="w")
        outline_color_var = tk.StringVar(value=self.settings.get("outline_color", ""))
        ttk.Entry(main_frame, textvariable=outline_color_var).pack(fill="x", pady=(0, 10))

        ttk.Label(main_frame, text="Label Text Color (hex or empty for theme default):").pack(anchor="w")
        label_color_var = tk.StringVar(value=self.settings.get("label_color", ""))
        ttk.Entry(main_frame, textvariable=label_color_var).pack(fill="x", pady=(0, 10))

        ttk.Label(main_frame, text="Canvas Background Color (hex or empty for theme default):").pack(anchor="w")
        canvas_bg_var = tk.StringVar(value=self.settings.get("canvas_bg", ""))
        ttk.Entry(main_frame, textvariable=canvas_bg_var).pack(fill="x", pady=(0, 20))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        def save_colors():
            self.settings["dir_color"] = dir_color_var.get()
            self.settings["file_color"] = file_color_var.get()
            self.settings["selection_color"] = selection_color_var.get()
            self.settings["outline_color"] = outline_color_var.get()
            self.settings["label_color"] = label_color_var.get()
            self.settings["canvas_bg"] = canvas_bg_var.get()
            self.save_settings()
            self.apply_theme()
            if self.current_node:
                self.draw()
            colors_win.destroy()

        ttk.Button(button_frame, text="Save", command=save_colors).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=colors_win.destroy).pack(side="right")

    def show_file_type_colors(self):
        """Dialog for configuring file type category colors."""
        ft_win = tk.Toplevel(self)
        ft_win.title("File Type Colors")
        width, height = 450, 400
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        ft_win.geometry(f"{width}x{height}+{x}+{y}")
        ft_win.transient(self)
        ft_win.grab_set()
        ft_win.resizable(False, False)

        main_frame = ttk.Frame(ft_win, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="File Type Categories", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(main_frame, text="Select a category to edit its color.").pack(anchor="w", pady=(0, 15))

        # Left: category list
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(side="left", fill="both", expand=False, padx=(0, 10))

        categories = ["image", "video", "audio", "document", "archive", "executable", "code", "text"]
        listbox = tk.Listbox(list_frame, height=8, exportselection=False)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.config(yscrollcommand=scrollbar.set)

        for cat in categories:
            listbox.insert(tk.END, cat.capitalize())

        # Right: color editor
        editor_frame = ttk.Frame(main_frame)
        editor_frame.pack(side="right", fill="both", expand=True)

        ttk.Label(editor_frame, text="Color (hex, e.g., #ff0000):").pack(anchor="w", pady=(0, 5))
        color_var = tk.StringVar()
        color_entry = ttk.Entry(editor_frame, textvariable=color_var, width=12)
        color_entry.pack(anchor="w", pady=(0, 10))

        # Preview canvas
        ttk.Label(editor_frame, text="Preview:").pack(anchor="w", pady=(5, 5))
        preview_canvas = tk.Canvas(editor_frame, width=50, height=30, bg="#ffffff", relief="sunken", bd=1)
        preview_canvas.pack(anchor="w")

        def update_preview(hex_color):
            try:
                preview_canvas.configure(bg=hex_color)
            except tk.TclError:
                pass

        def on_category_select(event):
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                cat = categories[idx]
                current_color = self.settings.get("file_type_colors", {}).get(cat, "")
                color_var.set(current_color)
                update_preview(current_color if current_color else "#ffffff")

        listbox.bind("<<ListboxSelect>>", on_category_select)
        
        # Live preview while typing
        color_var.trace_add("write", lambda *args: update_preview(color_var.get()))

        def apply_color():
            selection = listbox.curselection()
            if not selection:
                messagebox.showinfo("No Selection", "Please select a file type category.")
                return
            cat = categories[selection[0]]
            color_val = color_var.get().strip()
            if color_val and not (color_val.startswith('#') and len(color_val) == 7):
                messagebox.showerror("Invalid Color", "Color must be a hex color like #ff0000")
                return
            if "file_type_colors" not in self.settings:
                self.settings["file_type_colors"] = {}
            self.settings["file_type_colors"][cat] = color_val
            self.save_settings()
            self.draw()

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side="bottom", fill="x", pady=(20, 0))

        ttk.Button(button_frame, text="Apply", command=apply_color).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Close", command=ft_win.destroy).pack(side="right")

        ft_win.protocol("WM_DELETE_WINDOW", ft_win.destroy)


if __name__ == "__main__":
    app = Quantifile()
    app.mainloop()