import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from models import Node, human_size


class ActionsMixin:
    def choose_folder(self):
        path = filedialog.askdirectory(title="Select folder or drive")
        if path:
            self.start_scan(path)

    def quick_browse(self):
        """Quick browse mode: shallow scan, no size calculation for subdirs."""
        path = filedialog.askdirectory(title="Select folder to quick browse")
        if path:
            self.start_quick_scan(path)

    def show_about(self):
        about_win = tk.Toplevel(self)
        about_win.title("About Quantifile")
        about_win.geometry("400x300")
        about_win.resizable(False, False)
        about_win.transient(self)
        about_win.grab_set()

        # Apply dark theme to dialog if in dark mode
        if self.dark_mode:
            about_win.configure(bg=self.setting_color("dark_window_bg", "#0f0f0f"))
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

        title_font = (
            self.settings.get("ui_font_family", "Segoe UI"),
            self.get_setting_int("heading_font_size", 10, 6, 28) + 4,
            "bold"
        )
        ttk.Label(main_frame, text="Quantifile", font=title_font).pack()
        ttk.Label(main_frame, text="Disk space visualization tool inspired by SpaceMonger 1.4.0").pack(pady=(0, 5))
        ttk.Label(main_frame, text="Explore and analyze directory structures with interactive treemaps.").pack(pady=(0, 10))
        ttk.Label(main_frame, text="© 2026 Jan-Erik Labbas. All rights reserved.").pack(pady=(0, 5))
        ttk.Label(main_frame, text="Licensed under MIT License.").pack(pady=(0, 5))
        paypal_label = ttk.Label(
            main_frame,
            text="Support me on PayPal: paypal.me/jamps3",
            cursor="hand2",
            foreground=self.setting_color("link_color", "#0000ff")
        )
        paypal_label.pack(pady=(0, 10))
        paypal_label.bind("<Button-1>", lambda e: self.open_paypal())
        ttk.Label(main_frame, text="Version 1.0").pack(pady=(0, 10))

        ttk.Button(main_frame, text="Close", command=about_win.destroy).pack(pady=(10, 0))

        about_win.protocol("WM_DELETE_WINDOW", about_win.destroy)

    def open_paypal(self):
        import webbrowser
        webbrowser.open("https://paypal.me/jamps3")

    def show_properties(self):
        self.log_message("Properties dialog is not supported in this version.", "INFO", show_log=True)

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

    def normalize_color(self, color_value):
        color_value = color_value.strip()
        if not color_value:
            return ""

        if color_value.startswith("#") and len(color_value) == 7:
            try:
                int(color_value[1:], 16)
                return color_value
            except ValueError:
                return ""

        if "," in color_value:
            try:
                r, g, b = [int(x.strip()) for x in color_value.split(",")]
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                return f"#{r:02x}{g:02x}{b:02x}"
            except (ValueError, TypeError):
                return ""

        return ""

    def color_for_node(self, node, depth):
        # Special case for free space
        if node.name == "Free Space":
            return self.setting_color(
                "free_space_color",
                "#888888" if self.dark_mode else "#c0c0c0"
            )

        # Directories: check dir_color custom first
        if node.is_dir:
            custom = self.normalize_color(self.settings.get("dir_color", ""))
            if custom:
                return custom
            # Use theme-based directory color
            if self.dark_mode:
                base = 30 - min(depth * 4, 20)
                return f"#{base:02x}{70 + min(depth * 8, 35):02x}{110 + min(depth * 6, 25):02x}"
            else:
                base = 180 - min(depth * 14, 120)
                return f"#{base:02x}{220:02x}{255:02x}"

        # Check file type category colors
        file_type_colors = self.settings.get("file_type_colors", {})
        if file_type_colors:
            category = self.get_file_category(node.name)
            cat_color = self.normalize_color(file_type_colors.get(category, ""))
            if cat_color:
                return cat_color

        # Files: check custom file_color fallback
        custom = self.normalize_color(self.settings.get("file_color", ""))
        if custom:
            return custom

        # Use theme-based file color
        if self.dark_mode:
            base = 140 + min(depth * 6, 30)
            return f"#{200:02x}{base:02x}{60 + min(depth * 6, 25):02x}"
        else:
            base = 230 - min(depth * 10, 120)
            return f"#{255:02x}{base:02x}{120:02x}"

    def access_denied_color(self):
        return self.setting_color(
            "access_denied_color",
            "#6f4b4b" if self.dark_mode else "#d8b3b3"
        )

    def dim_color(self, hex_color):
        """Darken a hex color by 50% for search dimming effect."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return self.setting_color("invalid_color", "#888888")
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            r = int(r * 0.5)
            g = int(g * 0.5)
            b = int(b * 0.5)
            return f"#{r:02x}{g:02x}{b:02x}"
        except ValueError:
            return self.setting_color("invalid_color", "#888888")

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
                self.log_message(
                    "Free space visualization is only available at the drive root level.",
                    "INFO",
                    show_log=True
                )
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
        node = self.node_at_event(event)
        if node:
            self.selected_node = node
            self.draw()

        if self.quick_zoom_mode:
            self.zoom_out()
        else:
            self.show_context_menu(event)
        return "break"

    def show_context_menu(self, event):
        if not self.context_menu:
            self.context_menu = tk.Menu(self, tearoff=0)
            self.context_menu.add_command(label="Open", command=self.open_selected)
            self.context_menu.add_command(label="Color", command=self.show_selected_color_dialog)
            self.context_menu.add_command(label="Properties", command=self.show_properties)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Show in Explorer", command=self.open_in_manager)
            self.context_menu.add_command(label="Go Up", command=self.zoom_out)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Add to Bookmarks", command=self.add_current_to_bookmarks)
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

    def show_selected_color_dialog(self):
        node = self.selected_node
        if not node:
            return

        if node.name == "Free Space":
            self.log_message("Free space uses a fixed color.", "INFO", show_log=True)
            return

        is_dir = node.is_dir
        category = self.get_file_category(node.name) if not is_dir else "other"
        title = "Folder Color" if is_dir else f"{category.capitalize()} File Color"
        setting_key = "dir_color" if is_dir else category
        current_color = (
            self.settings.get("dir_color", "")
            if is_dir
            else self.settings.get("file_type_colors", {}).get(category, "")
        )
        current_hex = self.normalize_color(current_color)

        color_win = tk.Toplevel(self)
        color_win.title(title)
        width, height = 360, 220
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        color_win.geometry(f"{width}x{height}+{x}+{y}")
        color_win.transient(self)
        color_win.grab_set()

        # Apply dark theme to dialog if in dark mode
        if self.dark_mode:
            color_win.configure(bg=self.setting_color("dark_window_bg", "#0f0f0f"))
        color_win.resizable(False, False)

        main_frame = ttk.Frame(color_win, padding=20)
        main_frame.pack(fill="both", expand=True)

        label_text = "Set color for all folders." if is_dir else f"Set color for {category} files."
        ttk.Label(main_frame, text=label_text).pack(anchor="w", pady=(0, 10))

        color_var = tk.StringVar(value=current_hex)
        entry = ttk.Entry(main_frame, textvariable=color_var)
        entry.pack(fill="x", pady=(0, 10))

        preview = tk.Canvas(main_frame, width=70, height=32, bg=current_hex or "#ffffff", relief="sunken", bd=1)
        preview.pack(anchor="w", pady=(0, 10))

        def update_preview(*args):
            color = self.normalize_color(color_var.get())
            try:
                preview.configure(bg=color or "#ffffff")
            except tk.TclError:
                preview.configure(bg="#ffffff")

        def pick_color():
            initial_color = self.normalize_color(color_var.get()) or "#ffffff"
            chosen = colorchooser.askcolor(color=initial_color, parent=color_win, title=title)[1]
            if chosen:
                color_var.set(chosen)

        def save_color():
            color = color_var.get().strip()
            if color and not self.normalize_color(color):
                self.log_message(
                    "Invalid color. Use a hex color like #ff0000 or R,G,B values.",
                    "ERROR",
                    show_log=True
                )
                return
            if is_dir:
                self.settings["dir_color"] = color
            else:
                self.settings.setdefault("file_type_colors", {})[setting_key] = color
            self.save_settings()
            if self.current_node:
                self.draw()
            color_win.destroy()

        def reset_color():
            color_var.set("")
            save_color()

        color_var.trace_add("write", update_preview)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(5, 0))
        ttk.Button(button_frame, text="Choose...", command=pick_color).pack(side="left")
        ttk.Button(button_frame, text="Reset", command=reset_color).pack(side="left", padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=save_color).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=color_win.destroy).pack(side="right")

        color_win.protocol("WM_DELETE_WINDOW", color_win.destroy)

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
            self.log_message(f"Open failed: {e}", "ERROR", show_log=True)

    def open_in_manager(self):
        node = self.selected_node

        if not node or not node.path:
            return

        try:
            if sys.platform.startswith("win"):
                # Open the containing folder
                folder = node.path if os.path.isdir(node.path) else os.path.dirname(node.path)
                os.startfile(folder, 'explore')
            elif sys.platform == "darwin":
                subprocess.run(["open", node.path], check=False)
            else:
                subprocess.run(["xdg-open", node.path], check=False)
        except Exception as e:
            self.log_message(f"Open in file manager failed: {e}", "ERROR", show_log=True)

    def delete_selected(self):
        node = self.selected_node

        if not node or not node.path:
            return

        if self.settings.get("disable_delete", False):
            self.log_message("Delete command is disabled in settings.", "INFO", show_log=True)
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
            self.log_message(f"Delete failed: {e}", "ERROR", show_log=True)

    def show_free_space(self):
        """Show free space on the current drive."""
        if not self.root_node:
            self.log_message("No folder scanned yet.", "INFO", show_log=True)
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
            self.log_message(
                f"Drive: {os.path.splitdrive(self.root_node.path)[0]}\n\n"
                f"Free: {human_size(free)}\n"
                f"Total: {human_size(total)}\n"
                f"Used: {human_size(total - free)}",
                "INFO",
                show_log=True
            )
        except Exception as e:
            self.log_message(f"Could not get free space: {e}", "ERROR", show_log=True)

    def export_svg(self):
        """Export current treemap as an SVG file."""
        if not self.current_node:
            self.log_message("No data to export.", "INFO", show_log=True)
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
            svg_lines.append('<svg xmlns="http://www.w3.org/2000/svg" version="1.1"')
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

            self.log_message(f"Treemap exported successfully to: {filename}", "INFO", show_log=True)
        except Exception as e:
            self.log_message(f"Export SVG failed: {e}", "ERROR", show_log=True)

    def show_color_settings(self):
        """Dialog for customizing colors."""
        colors_win = tk.Toplevel(self)
        colors_win.title("Color Settings")
        width, height = 300, 640
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        colors_win.geometry(f"{width}x{height}+{x}+{y}")
        colors_win.minsize(300, 420)
        colors_win.transient(self)
        colors_win.grab_set()

        # Apply dark theme to dialog if in dark mode
        if self.dark_mode:
            colors_win.configure(bg=self.setting_color("dark_window_bg", "#0f0f0f"))

        main_frame = ttk.Frame(colors_win, padding=20)
        main_frame.pack(fill="both", expand=True)

        body_frame = ttk.Frame(main_frame)
        body_frame.pack(fill="both", expand=True)
        canvas_bg = self.setting_color("dark_window_bg", "#0f0f0f") if self.dark_mode else self.setting_color("light_window_bg", "#f0f0f0")
        canvas = tk.Canvas(body_frame, bg=canvas_bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body_frame, orient="vertical", command=canvas.yview)
        body_frame.columnconfigure(0, weight=1)
        body_frame.columnconfigure(1, weight=0)
        body_frame.rowconfigure(0, weight=1)
        content = ttk.Frame(canvas)
        content.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(content_window, width=event.width)
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        color_vars = {}

        def add_color(parent, key, label):
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=3)
            row.columnconfigure(0, weight=1)
            row.columnconfigure(1, weight=0)
            ttk.Label(row, text=label).grid(row=0, column=0, sticky="w", padx=(0, 8))
            var = tk.StringVar(value=self.settings.get(key, ""))
            ttk.Entry(row, textvariable=var, width=12).grid(row=0, column=1, sticky="e")
            color_vars[key] = var

        sections = [
            (
                "Treemap",
                [
                    ("dir_color", "Directory color"),
                    ("file_color", "File fallback color"),
                    ("selection_color", "Selection outline color"),
                    ("outline_color", "Normal outline color"),
                    ("label_color", "Label text color"),
                    ("canvas_bg", "Canvas background color"),
                    ("free_space_color", "Free space color"),
                    ("access_denied_color", "Access denied color"),
                    ("invalid_color", "Invalid/dim fallback color"),
                    ("recent_hour_outline_color", "Last-hour outline color"),
                    ("recent_outline_color", "Recent outline color"),
                    ("recent_hour_indicator_color", "Last-hour indicator color"),
                    ("recent_hour_indicator_text_color", "Last-hour indicator text"),
                    ("recent_indicator_color", "Recent indicator color"),
                ],
            ),
            (
                "Application",
                [
                    ("link_color", "Link color"),
                    ("log_bg", "Log background"),
                    ("log_fg", "Log text"),
                    ("light_window_bg", "Light window background"),
                    ("light_surface_bg", "Light surface background"),
                    ("light_surface_alt_bg", "Light alternate surface"),
                    ("light_border_color", "Light border color"),
                    ("light_text_color", "Light text color"),
                    ("light_muted_text_color", "Light muted text color"),
                    ("light_accent_color", "Light accent color"),
                    ("light_button_bg", "Light button background"),
                    ("light_button_active_bg", "Light active button"),
                    ("light_input_bg", "Light input background"),
                    ("light_input_text_color", "Light input text"),
                    ("light_select_bg", "Light selection background"),
                    ("light_select_text_color", "Light selection text"),
                    ("dark_window_bg", "Dark window background"),
                    ("dark_surface_bg", "Dark surface background"),
                    ("dark_surface_alt_bg", "Dark alternate surface"),
                    ("dark_border_color", "Dark border color"),
                    ("dark_text_color", "Dark text color"),
                    ("dark_muted_text_color", "Dark muted text color"),
                    ("dark_accent_color", "Dark accent color"),
                    ("dark_button_bg", "Dark button background"),
                    ("dark_button_active_bg", "Dark active button"),
                    ("dark_input_bg", "Dark input background"),
                    ("dark_input_text_color", "Dark input text"),
                    ("dark_select_bg", "Dark selection background"),
                    ("dark_select_text_color", "Dark selection text"),
                ],
            ),
        ]

        for title, items in sections:
            ttk.Label(content, text=title, style="Heading.TLabel").pack(anchor="w", pady=(0, 8))
            for key, label in items:
                add_color(content, key, label)
            ttk.Separator(content, orient="horizontal").pack(fill="x", pady=(12, 14))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        def apply_colors(close=False):
            for key, var in color_vars.items():
                self.settings[key] = var.get().strip()
            self.save_settings()
            self.apply_theme()
            updated_canvas_bg = self.setting_color("dark_window_bg", "#0f0f0f") if self.dark_mode else self.setting_color("light_window_bg", "#f0f0f0")
            colors_win.configure(bg=updated_canvas_bg)
            canvas.configure(bg=updated_canvas_bg)
            self._style_widget_tree(colors_win)
            if self.current_node:
                self.draw()
            if close:
                colors_win.destroy()

        ttk.Button(button_frame, text="Apply", command=lambda: apply_colors(False)).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=lambda: apply_colors(True)).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=colors_win.destroy).pack(side="right")
        self._style_widget_tree(colors_win)

    def show_file_type_colors(self):
        """Dialog for configuring file type category colors."""
        ft_win = tk.Toplevel(self)
        ft_win.title("File Type Colors")
        width, height = 450, 600
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        ft_win.geometry(f"{width}x{height}+{x}+{y}")
        ft_win.transient(self)
        ft_win.grab_set()

        # Apply dark theme to dialog if in dark mode
        if self.dark_mode:
            ft_win.configure(bg=self.setting_color("dark_window_bg", "#0f0f0f"))
        ft_win.resizable(False, False)

        main_frame = ttk.Frame(ft_win, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="File Type Categories", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(main_frame, text="Select a category to edit its color.").pack(anchor="w", pady=(0, 15))

        # Left: category list
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(side="left", fill="both", expand=False, padx=(0, 10))

        categories = ["image", "video", "audio", "document", "archive", "executable", "code", "text", "other"]
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
                self.log_message("Please select a file type category.", "INFO", show_log=True)
                return
            cat = categories[selection[0]]
            color_val = color_var.get().strip()
            if color_val and not (color_val.startswith('#') and len(color_val) == 7):
                self.log_message("Invalid color. Color must be a hex color like #ff0000.", "ERROR", show_log=True)
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

    def show_log_color_settings(self):
        """Dialog for customizing log colors."""
        log_win = tk.Toplevel(self)
        log_win.title("Log Color Settings")
        width, height = 400, 300
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        log_win.geometry(f"{width}x{height}+{x}+{y}")
        log_win.transient(self)
        log_win.grab_set()

        # Apply dark theme to dialog if in dark mode
        if self.dark_mode:
            log_win.configure(bg=self.setting_color("dark_window_bg", "#0f0f0f"))

        main_frame = ttk.Frame(log_win, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Log Background Color (hex or empty for theme default):").pack(anchor="w")
        log_bg_var = tk.StringVar(value=self.settings.get("log_bg", ""))
        ttk.Entry(main_frame, textvariable=log_bg_var).pack(fill="x", pady=(0, 10))

        ttk.Label(main_frame, text="Log Text Color (hex or empty for theme default):").pack(anchor="w")
        log_fg_var = tk.StringVar(value=self.settings.get("log_fg", ""))
        ttk.Entry(main_frame, textvariable=log_fg_var).pack(fill="x", pady=(0, 20))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        def apply_log_colors(close=False):
            self.settings["log_bg"] = log_bg_var.get()
            self.settings["log_fg"] = log_fg_var.get()
            self.save_settings()
            self.apply_theme()
            if close:
                log_win.destroy()

        ttk.Button(button_frame, text="Apply", command=lambda: apply_log_colors(False)).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=lambda: apply_log_colors(True)).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=log_win.destroy).pack(side="right")

    def show_advanced_search(self):
        """Show the advanced search dialog."""
        search_win = tk.Toplevel(self)
        search_win.title("Advanced Search")
        search_win.geometry("500x600")
        search_win.resizable(True, True)
        search_win.transient(self)
        search_win.grab_set()

        # Apply dark theme to dialog if in dark mode
        if self.dark_mode:
            search_win.configure(bg=self.setting_color("dark_window_bg", "#0f0f0f"))

        # Create main frame
        main_frame = ttk.Frame(search_win, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Title
        ttk.Label(main_frame, text="Advanced Search & Filtering", font=("", 12, "bold")).pack(pady=(0, 10))

        # Create notebook for different filter categories
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=(0, 10))

        # Basic Filters Tab
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="Basic")

        # Name/Regex search
        name_frame = ttk.LabelFrame(basic_frame, text="Name Search", padding="5")
        name_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(name_frame, text="Search text:").grid(row=0, column=0, sticky="w", pady=2)
        name_entry = ttk.Entry(name_frame, width=30)
        name_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=(5, 0))

        name_case_var = tk.BooleanVar()
        ttk.Checkbutton(name_frame, text="Case sensitive", variable=name_case_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=2)

        regex_var = tk.BooleanVar()
        ttk.Checkbutton(name_frame, text="Regular expression", variable=regex_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=2)

        # File type filter
        type_frame = ttk.LabelFrame(basic_frame, text="File Type", padding="5")
        type_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(type_frame, text="Extensions (comma-separated):").grid(row=0, column=0, sticky="w", pady=2)
        type_entry = ttk.Entry(type_frame, width=30)
        type_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=(5, 0))
        ttk.Label(type_frame, text="e.g., .txt,.pdf,.docx").grid(row=1, column=0, columnspan=2, sticky="w", pady=2, padx=(15, 0))

        type_exclude_var = tk.BooleanVar()
        ttk.Checkbutton(type_frame, text="Exclude these types", variable=type_exclude_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=2)

        # Size Filters Tab
        size_frame = ttk.Frame(notebook)
        notebook.add(size_frame, text="Size")

        size_filter_frame = ttk.LabelFrame(size_frame, text="Size Range", padding="5")
        size_filter_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(size_filter_frame, text="Minimum size:").grid(row=0, column=0, sticky="w", pady=2)
        min_size_entry = ttk.Entry(size_filter_frame, width=15)
        min_size_entry.grid(row=0, column=1, sticky="w", pady=2, padx=(5, 0))
        ttk.Label(size_filter_frame, text="(e.g., 1MB, 500KB, 100)").grid(row=0, column=2, sticky="w", pady=2, padx=(5, 0))

        ttk.Label(size_filter_frame, text="Maximum size:").grid(row=1, column=0, sticky="w", pady=2)
        max_size_entry = ttk.Entry(size_filter_frame, width=15)
        max_size_entry.grid(row=1, column=1, sticky="w", pady=2, padx=(5, 0))

        # Date Filters Tab
        date_frame = ttk.Frame(notebook)
        notebook.add(date_frame, text="Date")

        date_filter_frame = ttk.LabelFrame(date_frame, text="Modified Date", padding="5")
        date_filter_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(date_filter_frame, text="Modified within last:").grid(row=0, column=0, sticky="w", pady=2)
        date_days_entry = ttk.Entry(date_filter_frame, width=10)
        date_days_entry.grid(row=0, column=1, sticky="w", pady=2, padx=(5, 0))
        ttk.Label(date_filter_frame, text="days").grid(row=0, column=2, sticky="w", pady=2, padx=(5, 0))

        # Type Filters Tab
        type_filter_frame = ttk.Frame(notebook)
        notebook.add(type_filter_frame, text="Type")

        category_frame = ttk.LabelFrame(type_filter_frame, text="Item Type", padding="5")
        category_frame.pack(fill="x", pady=(0, 5))

        file_only_var = tk.BooleanVar()
        dir_only_var = tk.BooleanVar()

        ttk.Checkbutton(category_frame, text="Files only", variable=file_only_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(category_frame, text="Directories only", variable=dir_only_var).pack(anchor="w", pady=2)

        # Logic Tab
        logic_frame = ttk.Frame(notebook)
        notebook.add(logic_frame, text="Logic")

        logic_filter_frame = ttk.LabelFrame(logic_frame, text="Combination Logic", padding="5")
        logic_filter_frame.pack(fill="x", pady=(0, 5))

        logic_var = tk.StringVar(value="AND")
        ttk.Radiobutton(logic_filter_frame, text="AND (all conditions must match)", variable=logic_var, value="AND").pack(anchor="w", pady=2)
        ttk.Radiobutton(logic_filter_frame, text="OR (any condition can match)", variable=logic_var, value="OR").pack(anchor="w", pady=2)

        # Results preview
        results_frame = ttk.LabelFrame(main_frame, text="Search Results", padding="5")
        results_frame.pack(fill="both", expand=True, pady=(0, 10))

        results_text = tk.Text(results_frame, height=6, wrap="word", state="disabled")
        results_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=results_text.yview)
        results_text.configure(yscrollcommand=results_scrollbar.set)

        results_text.pack(side="left", fill="both", expand=True)
        results_scrollbar.pack(side="right", fill="y")

        def update_preview():
            """Update the search results preview."""
            if not self.current_node:
                results_text.configure(state="normal")
                results_text.delete("1.0", tk.END)
                results_text.insert("1.0", "No directory scanned yet.")
                results_text.configure(state="disabled")
                return

            # Collect filter criteria
            filters = {
                'name': name_entry.get().strip(),
                'case_sensitive': name_case_var.get(),
                'regex': regex_var.get(),
                'extensions': [ext.strip().lstrip('.') for ext in type_entry.get().split(',') if ext.strip()],
                'exclude_types': type_exclude_var.get(),
                'min_size': min_size_entry.get().strip(),
                'max_size': max_size_entry.get().strip(),
                'days': date_days_entry.get().strip(),
                'files_only': file_only_var.get(),
                'dirs_only': dir_only_var.get(),
                'logic': logic_var.get()
            }

            # Apply filters and count matches
            matches = self._apply_advanced_filters(self.current_node, filters)

            results_text.configure(state="normal")
            results_text.delete("1.0", tk.END)
            results_text.insert("1.0", f"Found {len(matches)} matching items\n\n")
            if matches:
                for i, path in enumerate(list(matches)[:10]):  # Show first 10
                    name = os.path.basename(path) or path
                    results_text.insert(tk.END, f"• {name}\n")
                if len(matches) > 10:
                    results_text.insert(tk.END, f"... and {len(matches) - 10} more")
            results_text.configure(state="disabled")

        # Bind updates to entry changes
        for entry in [name_entry, type_entry, min_size_entry, max_size_entry, date_days_entry]:
            entry.bind("<KeyRelease>", lambda e: search_win.after(300, update_preview))

        for var in [name_case_var, regex_var, type_exclude_var, file_only_var, dir_only_var, logic_var]:
            var.trace_add("write", lambda *args: search_win.after(300, update_preview))

        # Initial preview
        update_preview()

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        def apply_search():
            """Apply the advanced search filters."""
            if not self.current_node:
                messagebox.showerror("No Data", "Please scan a directory first.")
                return

            filters = {
                'name': name_entry.get().strip(),
                'case_sensitive': name_case_var.get(),
                'regex': regex_var.get(),
                'extensions': [ext.strip().lstrip('.') for ext in type_entry.get().split(',') if ext.strip()],
                'exclude_types': type_exclude_var.get(),
                'min_size': min_size_entry.get().strip(),
                'max_size': max_size_entry.get().strip(),
                'days': date_days_entry.get().strip(),
                'files_only': file_only_var.get(),
                'dirs_only': dir_only_var.get(),
                'logic': logic_var.get()
            }

            matches = self._apply_advanced_filters(self.current_node, filters)
            self.search_matches.clear()
            self.search_matches.update(matches)
            self.search_active = bool(matches)

            if matches:
                self.status.config(text=f"Advanced search: {len(matches)} matches")
            else:
                self.status.config(text="Advanced search: No matches found")

            self.draw()
            search_win.destroy()

        def clear_filters():
            """Clear all filter fields."""
            name_entry.delete(0, tk.END)
            type_entry.delete(0, tk.END)
            min_size_entry.delete(0, tk.END)
            max_size_entry.delete(0, tk.END)
            date_days_entry.delete(0, tk.END)
            name_case_var.set(False)
            regex_var.set(False)
            type_exclude_var.set(False)
            file_only_var.set(False)
            dir_only_var.set(False)
            logic_var.set("AND")
            update_preview()

        ttk.Button(button_frame, text="Apply Search", command=apply_search).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Clear All", command=clear_filters).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=search_win.destroy).pack(side="right")

    def _apply_advanced_filters(self, node, filters):
        """Apply advanced filters to the tree and return matching paths."""
        matches = set()

        def check_node(node):
            """Check if a node matches all the filters."""
            if not node:
                return False

            # Name/regex filter
            name_match = True
            if filters['name']:
                if filters['regex']:
                    try:
                        import re
                        pattern = filters['name']
                        if not filters['case_sensitive']:
                            pattern = "(?i)" + pattern
                        name_match = bool(re.search(pattern, node.name))
                    except re.error:
                        name_match = False  # Invalid regex
                else:
                    haystack = node.name if filters['case_sensitive'] else node.name.lower()
                    needle = filters['name'] if filters['case_sensitive'] else filters['name'].lower()
                    name_match = needle in haystack

            # Extension filter
            ext_match = True
            if filters['extensions']:
                if node.is_dir:
                    ext_match = not filters['exclude_types']  # Directories match if not excluding
                else:
                    node_ext = os.path.splitext(node.name)[1].lstrip('.').lower()
                    has_ext = node_ext in [ext.lower() for ext in filters['extensions']]
                    ext_match = has_ext if not filters['exclude_types'] else not has_ext

            # Size filters
            size_match = True
            if filters['min_size'] or filters['max_size']:
                try:
                    min_bytes = self.parse_size(filters['min_size']) if filters['min_size'] else 0
                    max_bytes = self.parse_size(filters['max_size']) if filters['max_size'] else float('inf')
                    size_match = min_bytes <= node.size <= max_bytes
                except (TypeError, ValueError):
                    size_match = True  # Invalid size specification

            # Date filter
            date_match = True
            if filters['days']:
                try:
                    days = int(filters['days'])
                    if hasattr(node, 'modified_time') and node.modified_time:
                        age_days = (time.time() - node.modified_time) / 86400
                        date_match = age_days <= days
                    else:
                        date_match = False
                except (TypeError, ValueError):
                    date_match = True

            # Type filter
            type_match = True
            if filters['files_only'] and filters['dirs_only']:
                type_match = False  # Can't be both
            elif filters['files_only']:
                type_match = not node.is_dir
            elif filters['dirs_only']:
                type_match = node.is_dir

            # Combine with logic
            if filters['logic'] == 'AND':
                return name_match and ext_match and size_match and date_match and type_match
            else:  # OR
                return name_match or ext_match or size_match or date_match or type_match

        def collect_matches(node):
            """Recursively collect matching nodes."""
            if check_node(node):
                matches.add(node.path)

            if node.children:
                for child in node.children:
                    collect_matches(child)

        collect_matches(node)
        return matches

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

    def add_current_to_bookmarks(self):
        """Add the current directory to bookmarks."""
        if not self.current_node:
            messagebox.showinfo("No Directory", "No directory is currently selected.")
            return

        path = self.current_node.path
        if path in self.bookmarks:
            messagebox.showinfo("Already Bookmarked", f"'{path}' is already bookmarked.")
            return

        # Store the current root node for this bookmark
        self.bookmarks[path] = self.root_node
        self.bookmarked_paths.append(path)
        self.update_bookmarks_list()
        if self.bookmarks_visible:
            self.update_bookmarks_panel_list()
        self.save_bookmarks()

    def remove_selected_bookmark(self):
        """Remove the most recent bookmark (cards have individual × buttons)."""
        if not self.bookmarked_paths:
            return
        path = self.bookmarked_paths[-1]
        if messagebox.askyesno("Remove Bookmark", f"Remove bookmark for '{path}'?"):
            del self.bookmarks[path]
            self.bookmarked_paths.pop()
            self.update_bookmarks_list()
            if self.bookmarks_visible:
                self.update_bookmarks_panel_list()
            self.save_bookmarks()

    def browse_selected_bookmark(self, event=None):
        """Browse the most recent bookmark (or use card click)."""
        if not self.bookmarked_paths:
            return
        path = self.bookmarked_paths[-1]
        self.switch_to_bookmark(path)

    def on_bookmark_double_click(self, event):
        """Handle double-click on bookmark."""
        self.browse_selected_bookmark(event)

    def switch_to_bookmark(self, path):
        """Switch the treemap to show a bookmarked directory."""
        # Check if the directory still exists
        if not os.path.exists(path):
            messagebox.showerror("Directory Not Found", f"The directory '{path}' no longer exists.")
            # Remove the invalid bookmark
            if path in self.bookmarks:
                del self.bookmarks[path]
                if path in self.bookmarked_paths:
                    self.bookmarked_paths.remove(path)
                self.update_bookmarks_list()
                if self.bookmarks_visible:
                    self.update_bookmarks_panel_list()
                self.save_bookmarks()
            return

        # Check if we have a cached scan for this bookmark
        if path in self.bookmarks and self.bookmarks[path]:
            # Use cached scan data
            self.root_node = self.bookmarks[path]
            # Find the target node in the cached tree
            target_node = self.find_node_by_path(self.root_node, path)
            if target_node:
                self.animate_zoom(None, target_node)
                self.main_notebook.select(self.treemap_tab)
                self.log_message(f"Loaded bookmark '{path}' from cache", "INFO")
                return

        # No valid cache or path not found, scan the directory
        self.log_message(f"Scanning bookmarked directory '{path}'...", "INFO")
        self.start_scan(path)

    def find_node_by_path(self, root_node, target_path):
        """Find a node by its path in the tree."""
        if root_node.path == target_path:
            return root_node

        for child in root_node.children:
            result = self.find_node_by_path(child, target_path)
            if result:
                return result
        return None

    def update_bookmarks_list(self):
        """Update the bookmark cards in the tab."""
        for widget in self.bookmarks_tab_cards.winfo_children():
            widget.destroy()
        for path in self.bookmarked_paths:
            self.create_bookmark_card(self.bookmarks_tab_cards, path, is_tab=True)

    def update_bookmarks_panel_list(self):
        """Update the bookmark cards in the side panel."""
        for widget in self.bookmarks_panel_cards.winfo_children():
            widget.destroy()
        for path in self.bookmarked_paths:
            self.create_bookmark_card(self.bookmarks_panel_cards, path, is_tab=False)

    def create_bookmark_card(self, parent, path, is_tab):
        card = ttk.Frame(parent, relief="ridge", borderwidth=1)
        card.pack(fill="x", padx=4, pady=3)

        # Full path label
        label = ttk.Label(card, text=path, anchor="w", wraplength=280)
        label.pack(side="left", fill="x", expand=True, padx=8, pady=6)

        # Remove button
        remove_btn = ttk.Button(card, text="×", width=3, command=lambda p=path: self.remove_bookmark_by_path(p))
        remove_btn.pack(side="right", padx=4)

        # Click to browse
        def browse(event, p=path):
            self.switch_to_bookmark(p)
        card.bind("<Button-1>", browse)
        label.bind("<Button-1>", browse)

    def save_bookmarks(self):
        """Save bookmarks to settings."""
        self.settings["bookmarks"] = self.bookmarked_paths.copy()
        self.save_settings()

    def load_bookmarks(self):
        """Load bookmarks from settings."""
        saved_bookmarks = self.settings.get("bookmarks", [])
        self.bookmarked_paths = saved_bookmarks.copy()
        # Note: We don't load the actual scan data, bookmarks will rescan when accessed
        self.update_bookmarks_list()
        if self.bookmarks_visible:
            self.update_bookmarks_panel_list()

    def remove_bookmark_by_path(self, path):
        if path in self.bookmarks:
            del self.bookmarks[path]
        if path in self.bookmarked_paths:
            self.bookmarked_paths.remove(path)
        self.update_bookmarks_list()
        if self.bookmarks_visible:
            self.update_bookmarks_panel_list()
        self.save_bookmarks()

    def toggle_bookmarks_panel(self):
        """Toggle the bookmarks side panel visibility."""
        if self.bookmarks_visible:
            # Hide the panel
            self.main_paned.remove(self.bookmarks_panel)
            self.bookmarks_visible = False
            self.bookmarks_toggle_button.config(text="Bookmarks (HIDDEN)")
        else:
            # Show the panel
            self.main_paned.insert(0, self.bookmarks_panel)
            self.main_paned.sashpos(0, 200)  # Set initial width
            self.bookmarks_visible = True
            self.bookmarks_toggle_button.config(text="Bookmarks (SHOWN)")
            # Refresh the panel listbox
            self.update_bookmarks_panel_list()

    def show_bookmarks_tab(self):
        """Switch to the bookmarks tab."""
        self.main_notebook.select(self.bookmarks_tab)
