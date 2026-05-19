import os
import tkinter as tk
import tkinter.font as tkfont
import time

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
        self.node_rects.clear()

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

        recency = self.modified_recency(node)

        # Determine outline color and width based on selection and settings
        if self.selected_node and node.path == self.selected_node.path:
            outline_color = self.settings.get("selection_color", "#ffcc00")
            outline_width = 3
        elif recency and self.settings.get("recent_modified_outline_style", "indicator_only") == "subtle_outline":
            if recency == "hour":
                outline_color = self.setting_color(
                    "recent_hour_outline_color",
                    "#2f8f6a" if self.dark_mode else "#5b8f76"
                )
            else:
                outline_color = self.setting_color(
                    "recent_outline_color",
                    "#4f7f8f" if self.dark_mode else "#6f8fa8"
                )
            outline_width = 1
        else:
            outline_color = self.settings.get("outline_color", "")
            if not outline_color:
                outline_color = "#222222" if self.dark_mode else "black"
            outline_width = 1

        rect = self.canvas.create_rectangle(
            x, y, x + w, y + h,
            fill=color,
            outline=outline_color,
            width=outline_width
        )

        self.rect_nodes[rect] = node
        self.node_rects[rect] = node

        if recency:
            self.draw_modified_indicator(node, x, y, w, h, recency)

        label_color = self.settings.get("label_color", "")
        if not label_color:
            label_color = "#ffffff" if self.dark_mode else "#000000"

        if w > 70 and h > 25:
            # Adjust font size based on rectangle dimensions
            min_size = self.get_setting_int("canvas_label_min_size", 5, 4, 18)
            max_size = self.get_setting_int("canvas_label_max_size", 8, min_size, 32)
            font_family = self.settings.get("canvas_font_family", "Segoe UI") or "Segoe UI"
            if node.is_dir and node.children:
                # Multi-line label needs more space
                font_size = max(min_size, min(max_size, int(h / 10), int(w / 15)))
            else:
                font_size = max(min_size, min(max_size, int(h / 8), int(w / 10)))

            label_font = (font_family, font_size)
            measured_font = tkfont.Font(family=font_family, size=font_size)
            available_text_width = max(1, int(w - 8))

            if getattr(node, "access_denied", False):
                name_part = self.truncate_canvas_label(node.name, measured_font, available_text_width)
                label = f"{name_part}\nAccess denied\n{human_size(node.size)}"
            elif node.is_dir and node.children:
                item_count = len(node.children)
                name_part = self.truncate_canvas_label(node.name, measured_font, available_text_width)
                label = f"{name_part}\n{human_size(node.size)}\n{item_count} item{'s' if item_count != 1 else ''}"
            else:
                name_part = self.truncate_canvas_label(node.name, measured_font, available_text_width)
                label = f"{name_part}\n{human_size(node.size)}"

            if font_size >= min_size:
                self.canvas.create_text(
                    x + 4,
                    y + 4,
                    anchor="nw",
                    text=label,
                    fill=label_color,
                    font=label_font
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

    def truncate_canvas_label(self, text, font, max_width):
        if font.measure(text) <= max_width:
            return text

        ellipsis = "..."
        if font.measure(ellipsis) > max_width:
            return ""

        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            candidate = text[:mid] + ellipsis
            if font.measure(candidate) <= max_width:
                low = mid
            else:
                high = mid - 1

        return text[:low] + ellipsis

    def modified_recency(self, node):
        if not self.settings.get("show_recent_modified", True):
            return None
        if not getattr(node, "modified_time", 0):
            return None

        age_seconds = time.time() - node.modified_time
        if age_seconds < 0:
            age_seconds = 0
        if age_seconds <= 3600:
            return "hour"

        recent_days = self.get_setting_int("recent_modified_days", 7, 1, 365)
        if age_seconds <= recent_days * 86400:
            return "recent"

        return None

    def draw_modified_indicator(self, node, x, y, w, h, recency):
        if w < 12 or h < 12:
            return

        if recency == "hour":
            fill = self.setting_color(
                "recent_hour_indicator_color",
                "#00ff99" if self.dark_mode else "#00b36b"
            )
            text_fill = self.setting_color(
                "recent_hour_indicator_text_color",
                "#002b1a" if self.dark_mode else "#ffffff"
            )
            size = min(18, max(10, int(min(w, h) * 0.18)))
            x1 = x + w - size - 3
            y1 = y + 3
            marker = self.canvas.create_rectangle(
                x1, y1, x1 + size, y1 + size,
                fill=fill,
                outline=""
            )
            self.rect_nodes[marker] = node
            if size >= 12:
                label = self.canvas.create_text(
                    x1 + size / 2,
                    y1 + size / 2,
                    text="1h",
                    fill=text_fill,
                    font=(self.settings.get("canvas_font_family", "Segoe UI"), max(6, int(size * 0.42))),
                    anchor="center"
                )
                self.rect_nodes[label] = node
            return

        marker_size = min(10, max(5, int(min(w, h) * 0.12)))
        fill = self.setting_color(
            "recent_indicator_color",
            "#66d9ff" if self.dark_mode else "#0078d7"
        )
        marker = self.canvas.create_oval(
            x + w - marker_size - 4,
            y + 4,
            x + w - 4,
            y + marker_size + 4,
            fill=fill,
            outline=""
        )
        self.rect_nodes[marker] = node

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
        return "break"

    def animate_zoom(self, old_node, new_node, steps=None, duration=None):
        """Animate transition between nodes."""
        mode = self.settings.get("animation_mode", "none")
        if self.settings.get("animated_zoom", False) and mode == "none":
            mode = "zoom"
        if mode == "none":
            self._finish_animation(new_node)
            return
        if steps is None:
            steps = self.get_setting_int("animation_steps", 10, 3, 40)
        if duration is None:
            duration = self.get_setting_int("animation_duration", 160, 50, 1000)

        # If no old_node (first load), do a simple fade-in zoom from center
        if not old_node:
            if new_node:
                self.animate_rect_zoom(new_node, None, steps, duration)
            return

        if mode == "zoom":
            self.animate_rect_zoom(new_node, self.node_bbox(new_node), steps, duration)
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
            self.node_rects.clear()
            
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

    def node_bbox(self, node):
        for rect, rect_node in self.rect_nodes.items():
            if rect_node == node:
                try:
                    return self.canvas.bbox(rect)
                except tk.TclError:
                    return None
        return None

    def animate_rect_zoom(self, node, start_bbox, steps, duration):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        end_bbox = (5, 5, max(6, width - 5), max(6, height - 5))

        if not start_bbox:
            cx = width / 2
            cy = height / 2
            start_bbox = (cx - 2, cy - 2, cx + 2, cy + 2)

        color = self.access_denied_color() if getattr(node, "access_denied", False) else self.color_for_node(node, 0)
        outline = self.settings.get("selection_color", "#ffcc00")

        def lerp(a, b, t):
            return a + (b - a) * t

        def draw_step(step=0):
            if step >= steps:
                self._finish_animation(node)
                return

            t = (step + 1) / steps
            eased = 1 - (1 - t) * (1 - t)
            x1 = lerp(start_bbox[0], end_bbox[0], eased)
            y1 = lerp(start_bbox[1], end_bbox[1], eased)
            x2 = lerp(start_bbox[2], end_bbox[2], eased)
            y2 = lerp(start_bbox[3], end_bbox[3], eased)

            self.canvas.delete("all")
            self.rect_nodes.clear()
            self.node_rects.clear()
            rect = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=color,
                outline=outline,
                width=3
            )
            self.rect_nodes[rect] = node
            self.node_rects[rect] = node
            self.after(max(1, int(duration / steps)), lambda: draw_step(step + 1))

        draw_step()

    def _finish_animation(self, node):
        """Complete animation by setting node and drawing final state."""
        self.current_node = node
        self.selected_node = node
        if hasattr(self, "path_var"):
            self.path_var.set(node.path.replace("\\", "/"))
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

        direction = event.keysym
        if direction not in ("Left", "Right", "Up", "Down"):
            return

        current_rect = self._main_rect_for_node(self.selected_node)
        if not current_rect:
            return

        current_bbox = self.canvas.bbox(current_rect)
        if not current_bbox:
            return

        candidates = []
        selected_path = getattr(self.selected_node, "path", None)
        for r, n in self.node_rects.items():
            if r == current_rect:
                continue
            if n == self.selected_node or getattr(n, "path", None) == selected_path:
                continue
            bbox = self.canvas.bbox(r)
            if not bbox:
                continue
            if self._bbox_contains(bbox, current_bbox):
                continue
            score = self._arrow_candidate_score(direction, current_bbox, bbox)
            if score is not None:
                inside_current = self._bbox_contains(current_bbox, bbox)
                candidates.append(((inside_current,) + score, n))

        if not candidates:
            return

        self.selected_node = min(candidates, key=lambda c: c[0])[1]
        self._update_status(self.selected_node)
        self.draw()

    def _main_rect_for_node(self, node):
        node_path = getattr(node, "path", None)
        for rect, rect_node in self.node_rects.items():
            rect_path = getattr(rect_node, "path", None)
            if rect_node == node or rect_path == node_path:
                return rect
        return None

    def _arrow_candidate_score(self, direction, current_bbox, bbox):
        x1, y1, x2, y2 = current_bbox
        bx1, by1, bx2, by2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        bx = (bx1 + bx2) / 2
        by = (by1 + by2) / 2

        if direction == "Right":
            if bx <= cx:
                return None
            primary = bx1 - x2 if bx1 >= x2 else bx - cx
            gap = self._interval_gap(y1, y2, by1, by2)
            cross = abs(by - cy)
        elif direction == "Left":
            if bx >= cx:
                return None
            primary = x1 - bx2 if bx2 <= x1 else cx - bx
            gap = self._interval_gap(y1, y2, by1, by2)
            cross = abs(by - cy)
        elif direction == "Down":
            if by <= cy:
                return None
            primary = by1 - y2 if by1 >= y2 else by - cy
            gap = self._interval_gap(x1, x2, bx1, bx2)
            cross = abs(bx - cx)
        elif direction == "Up":
            if by >= cy:
                return None
            primary = y1 - by2 if by2 <= y1 else cy - by
            gap = self._interval_gap(x1, x2, bx1, bx2)
            cross = abs(bx - cx)
        else:
            return None

        if primary <= 0:
            return None

        return (gap > 0, gap, primary, cross)

    def _interval_gap(self, start, end, other_start, other_end):
        if end < other_start:
            return other_start - end
        if other_end < start:
            return start - other_end
        return 0

    def _bbox_contains(self, outer, inner):
        return (
            outer[0] <= inner[0]
            and outer[1] <= inner[1]
            and outer[2] >= inner[2]
            and outer[3] >= inner[3]
            and (
                outer[2] - outer[0] > inner[2] - inner[0]
                or outer[3] - outer[1] > inner[3] - inner[1]
            )
        )

    def on_double_click(self, event):
        node = self.node_at_event(event) or self.selected_node

        if node:
            self.selected_node = node
            if node.is_dir and not getattr(node, "access_denied", False):
                self.animate_zoom(self.current_node, node)
            else:
                self.open_selected()
            return "break"

        return None

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
        return "break"

    def _find_node_by_path(self, node, target_path):
        if not node:
            return None
        if os.path.normcase(os.path.normpath(node.path)) == os.path.normcase(target_path):
            return node
        for child in node.children:
            found = self._find_node_by_path(child, target_path)
            if found:
                return found
        return None

    def on_path_enter(self, event):
        if not hasattr(self, "path_var") or not self.root_node:
            return
        target = os.path.normcase(os.path.normpath(self.path_var.get().strip()))
        if not target:
            return
        node = self._find_node_by_path(self.root_node, target)
        if node:
            if node.is_dir and not getattr(node, "access_denied", False):
                self.animate_zoom(self.current_node, node)
            else:
                self.selected_node = node
                self.open_selected()
        else:
            self.log_message(f"Path not found in tree: {target}", "WARNING")
        return "break"
