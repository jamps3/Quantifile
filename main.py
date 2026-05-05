import os
import sys
import math
import json
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


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
        self.geometry("1100x750")

        self.root_node = None
        self.current_node = None
        self.rect_nodes = {}
        self.dark_mode = False

        self.load_settings()
        self.create_ui()
        self.apply_theme()

    def create_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Open Folder", command=self.choose_folder).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Quick Browse", command=self.quick_browse).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Rescan", command=self.rescan).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Zoom Out", command=self.zoom_out).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Open Selected", command=self.open_selected).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=4, pady=4)
        ttk.Button(toolbar, text="Settings", command=self.show_settings).pack(side="right", padx=4, pady=4)

        self.status = ttk.Label(toolbar, text="Choose a folder to scan")
        self.status.pack(side="left", padx=10)

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
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Configure>", self.on_resize)

        self.bind("<BackSpace>", lambda e: self.zoom_out())

        self.selected_node = None
        self.scan_aborted = False
        self.nodes_scanned = 0
        self._resize_job = None

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
        self.status.config(text=f"Scanning: {path}")
        self.canvas.delete("all")

        def worker():
            # Pre-count total items for progress display
            total = self.count_items(path)
            self.after(0, lambda: (
                self.progress_label.config(text=f"Scanning: 0 / {total} items..."),
                setattr(self, "total_items", total)
            ))
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
        self.status.config(text=f"Quick browse: {path}")
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
            total = 1  # count the root folder itself
            with os.scandir(path) as it:
                for entry in it:
                    total += 1
                    if entry.is_dir(follow_symlinks=False):
                        total += self.count_items(entry.path)
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
            self.nodes_scanned += 1
            self.after(0, lambda: self.progress_label.config(
                text=f"Scanning: {self.nodes_scanned} / {getattr(self, 'total_items', '?')} items..."))
            return node

        try:
            entries = list(os.scandir(path))
        except PermissionError:
            return node
        except OSError:
            return node

        total = len(entries)
        for i, entry in enumerate(entries):
            if self.scan_aborted:
                return node

            try:
                child = self.scan_path_with_progress(entry.path)
                node.children.append(child)
                node.size += child.size
            except OSError:
                pass

            # Update progress every 20 items for performance
            if i % 20 == 0:
                self.nodes_scanned += 20
                self.after(0, lambda n=self.nodes_scanned: self.progress_label.config(
                    text=f"Scanning: {max(n, 1)} / {getattr(self, 'total_items', '?')} items..."))

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

        self.root_node = node
        self.current_node = node
        self.selected_node = None
        scan_mode = "Quick browse" if getattr(self, "scan_type", "full") == "quick" else "Full scan"
        self.status.config(text=f"{scan_mode}: {node.path} — {human_size(node.size)}")
        self.draw()

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

    def draw_node(self, node, x, y, w, h, depth):
        if w < 2 or h < 2:
            return

        color = self.color_for_node(node, depth)

        rect = self.canvas.create_rectangle(
            x, y, x + w, y + h,
            fill=color,
            outline="black"
        )

        self.rect_nodes[rect] = node

        if w > 70 and h > 25:
            label = f"{node.name}\n{human_size(node.size)}"
            self.canvas.create_text(
                x + 4,
                y + 4,
                anchor="nw",
                text=label,
                fill="black",
                font=("Segoe UI", 8)
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

    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {"dark_mode": False}
        self.dark_mode = self.settings.get("dark_mode", False)

    def save_settings(self):
        with open("settings.json", "w") as f:
            json.dump(self.settings, f)

    def apply_theme(self):
        if self.dark_mode:
            # Dark theme
            self.configure(bg="#1e1e1e")
            self.canvas.configure(bg="#2d2d30")
            self.style = ttk.Style()
            self.style.configure("TFrame", background="#1e1e1e")
            self.style.configure("TButton", background="#3c3c3c", foreground="#cccccc")
            self.style.map("TButton", background=[("active", "#4a4a4a")])
            self.style.configure("TLabel", background="#1e1e1e", foreground="#cccccc")
        else:
            # Light theme
            self.configure(bg="#f0f0f0")
            self.canvas.configure(bg="white")
            self.style = ttk.Style()
            self.style.configure("TFrame", background="#f0f0f0")
            self.style.configure("TButton", background="#e0e0e0", foreground="black")
            self.style.map("TButton", background=[("active", "#d0d0d0")])
            self.style.configure("TLabel", background="#f0f0f0", foreground="black")

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
        settings_win.geometry("400x300")
        settings_win.transient(self)
        settings_win.grab_set()
        settings_win.resizable(False, False)

        # Center the window
        settings_win.update_idletasks()
        width = settings_win.winfo_width()
        height = settings_win.winfo_height()
        x = (settings_win.winfo_screenwidth() // 2) - (width // 2)
        y = (settings_win.winfo_screenheight() // 2) - (height // 2)
        settings_win.geometry(f"+{x}+{y}")

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

        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=20)

        info_text = (
            "• Click rectangles to select items\n"
            "• Double-click folders to zoom in\n"
            "• Press Backspace or click Zoom Out to go up\n"
            "• Click 'Open Selected' to open with default app\n"
            "• Click 'Delete Selected' to delete (with confirmation)\n"
            "• Hover over rectangles for details\n"
            "• Use 'Quick Browse' for fast directory preview (no recursive size calc)"
        )
        ttk.Label(main_frame, text="Usage Tips:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        tips_label = ttk.Label(main_frame, text=info_text, justify="left")
        tips_label.pack(anchor="w")

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))

        ttk.Button(button_frame, text="Close", command=settings_win.destroy).pack(side="right")

        settings_win.protocol("WM_DELETE_WINDOW", settings_win.destroy)

    def on_theme_change(self, theme):
        self.toggle_dark_mode(theme == "dark")

    def color_for_node(self, node, depth):
        if self.dark_mode:
            if node.is_dir:
                # Dark theme: blue-cyan tones
                base = 60 - min(depth * 6, 40)
                return f"#{base:02x}{120 + min(depth * 15, 80):02x}{200 + min(depth * 10, 55):02x}"
            else:
                # Dark theme: orange-coral tones
                base = 220 + min(depth * 10, 35)
                return f"#{255:02x}{base:02x}{100 + min(depth * 10, 55):02x}"
        else:
            if node.is_dir:
                # Light theme: teal/blue-green tones
                base = 180 - min(depth * 14, 120)
                return f"#{base:02x}{220:02x}{255:02x}"
            else:
                # Light theme: coral/peach tones
                base = 230 - min(depth * 10, 120)
                return f"#{255:02x}{base:02x}{120:02x}"

    def draw_node(self, node, x, y, w, h, depth):
        if w < 2 or h < 2:
            return

        color = self.color_for_node(node, depth)

        # Highlight selected node with a contrasting border
        outline_color = "#ffcc00" if (self.selected_node and node.path == self.selected_node.path) else ("#666666" if self.dark_mode else "black")
        outline_width = 3 if (self.selected_node and node.path == self.selected_node.path) else 1

        rect = self.canvas.create_rectangle(
            x, y, x + w, y + h,
            fill=color,
            outline=outline_color,
            width=outline_width
        )

        self.rect_nodes[rect] = node

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
            self.status.config(text=f"{scan_mode}: {node.path} — {human_size(node.size)}")
            self.draw()

    def on_double_click(self, event):
        node = self.node_at_event(event)

        if node:
            if node.is_dir:
                self.current_node = node
                self.selected_node = node
                self.draw()
                scan_mode = "Quick browse" if getattr(self, "scan_type", "full") == "quick" else "Full scan"
                self.status.config(text=f"{scan_mode}: {node.path} — {human_size(node.size)}")
            else:
                self.selected_node = node
                self.open_selected()

    def on_motion(self, event):
        node = self.node_at_event(event)

        if node:
            self.canvas.config(cursor="hand2")
            self.status.config(text=f"{node.path} — {human_size(node.size)}")
        else:
            self.canvas.config(cursor="")

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
            self.current_node = parent
            self.selected_node = parent
            self.draw()
            scan_mode = "Quick browse" if getattr(self, "scan_type", "full") == "quick" else "Full scan"
            self.status.config(text=f"{scan_mode}: {parent.path} — {human_size(parent.size)}")

    def open_selected(self):
        node = self.selected_node

        if not node:
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

    def delete_selected(self):
        node = self.selected_node

        if not node:
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

            self.rescan()

        except Exception as e:
            messagebox.showerror("Delete failed", str(e))


if __name__ == "__main__":
    app = Quantifile()
    app.mainloop()