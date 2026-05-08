import os
import subprocess
import sys
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
        paypal_label = ttk.Label(main_frame, text="Support me on PayPal: paypal.me/jamps3", cursor="hand2", foreground="#0000FF")
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
            return "#888888" if self.dark_mode else "#c0c0c0"  # Distinct gray

        # Directories: check dir_color custom first
        if node.is_dir:
            custom = self.normalize_color(self.settings.get("dir_color", ""))
            if custom:
                return custom
            # Use theme-based directory color
            if self.dark_mode:
                base = 60 - min(depth * 6, 40)
                return f"#{base:02x}{120 + min(depth * 15, 80):02x}{200 + min(depth * 10, 55):02x}"
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
            base = 220 + min(depth * 10, 35)
            return f"#{255:02x}{base:02x}{100 + min(depth * 10, 55):02x}"
        else:
            base = 230 - min(depth * 10, 120)
            return f"#{255:02x}{base:02x}{120:02x}"

    def access_denied_color(self):
        return "#6f4b4b" if self.dark_mode else "#d8b3b3"

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
        category = self.get_file_category(node.name) if not is_dir else None
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

            self.log_message(f"Treemap exported successfully to: {filename}", "INFO", show_log=True)
        except Exception as e:
            self.log_message(f"Export SVG failed: {e}", "ERROR", show_log=True)

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

        ttk.Label(main_frame, text="Directory Color (hex or R,G,B):").pack(anchor="w")
        dir_color_var = tk.StringVar(value=self.settings.get("dir_color", ""))
        ttk.Entry(main_frame, textvariable=dir_color_var).pack(fill="x", pady=(0, 10))

        ttk.Label(main_frame, text="File Color (hex or R,G,B fallback):").pack(anchor="w")
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

        def save_log_colors():
            self.settings["log_bg"] = log_bg_var.get()
            self.settings["log_fg"] = log_fg_var.get()
            self.save_settings()
            self.apply_theme()
            log_win.destroy()

        ttk.Button(button_frame, text="Save", command=save_log_colors).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=log_win.destroy).pack(side="right")
