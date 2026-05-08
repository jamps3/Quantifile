import tkinter as tk

from layout import treemap
from models import human_size


class RenderMixin:
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

        color = self.access_denied_color() if getattr(node, "access_denied", False) else self.color_for_node(node, depth)

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
            if getattr(node, "access_denied", False):
                name_part = node.name
                if len(name_part) > 16:
                    name_part = name_part[:14] + ".."
                label = f"{name_part}\nAccess denied\n{human_size(node.size)}"
            elif node.is_dir and node.children:
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
            min_size = self.get_setting_int("canvas_label_min_size", 5, 4, 18)
            max_size = self.get_setting_int("canvas_label_max_size", 8, min_size, 32)
            font_family = self.settings.get("canvas_font_family", "Segoe UI") or "Segoe UI"
            if node.is_dir and node.children:
                # Multi-line label needs more space
                font_size = max(min_size, min(max_size, int(h / 10), int(w / 15)))
            else:
                font_size = max(min_size, min(max_size, int(h / 8), int(w / (len(name_part) + 3))))

            if font_size >= min_size:
                self.canvas.create_text(
                    x + 4,
                    y + 4,
                    anchor="nw",
                    text=label,
                    fill=label_color,
                    font=(font_family, font_size)
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
