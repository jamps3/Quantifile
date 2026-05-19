import json
import sys
import tkinter as tk
from tkinter import ttk


LIGHT_THEME = {
    "window": "#f0f0f0",
    "surface": "#ffffff",
    "surface_alt": "#eef2f7",
    "border": "#cfd7e3",
    "text": "#1f2933",
    "muted": "#52616f",
    "accent": "#2563eb",
    "button": "#e6edf7",
    "button_active": "#d6e2f2",
    "entry": "#ffffff",
    "entry_text": "#111827",
    "select": "#cfe0ff",
    "select_text": "#0f172a",
}

DARK_THEME = {
    "window": "#0f0f0f",
    "surface": "#1f2937",
    "surface_alt": "#273445",
    "border": "#4b5563",
    "text": "#f3f4f6",
    "muted": "#cbd5e1",
    "accent": "#60a5fa",
    "button": "#374151",
    "button_active": "#4b5563",
    "entry": "#111827",
    "entry_text": "#f9fafb",
    "select": "#1d4ed8",
    "select_text": "#ffffff",
}


def system_prefers_dark_theme():
    if sys.platform != "win32":
        return None  # not available
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return value == 0
    except Exception:
        return None  # detection failed → fallback to dark


def set_windows_dark_title_bar(window, enabled: bool) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1 if enabled else 0)
        for attribute in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


class SettingsMixin:
    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {}
        defaults = {
            "theme_mode": "system",
            "dark_mode": False,
            "min_density": 1,
            "disable_delete": False,
            "remember_window_pos": True,
            "fullscreen": False,
            "show_scan_progress": True,
            "max_scan_threads": 6,
            "show_recent_modified": True,
            "recent_modified_days": 7,
            "recent_modified_outline_style": "indicator_only",
            "animated_zoom": False,
            "animation_mode": "none",
            "animation_duration": 160,
            "animation_steps": 10,
            "auto_rescan_on_delete": True,
            "dir_color": "",
            "file_color": "",
            "selection_color": "#ffcc00",
            "outline_color": "",
            "label_color": "",
            "canvas_bg": "",
            "recent_hour_outline_color": "",
            "recent_outline_color": "",
            "recent_hour_indicator_color": "",
            "recent_hour_indicator_text_color": "",
            "recent_indicator_color": "",
            "free_space_color": "",
            "access_denied_color": "",
            "invalid_color": "",
            "link_color": "",
            "light_window_bg": LIGHT_THEME["window"],
            "light_surface_bg": LIGHT_THEME["surface"],
            "light_surface_alt_bg": LIGHT_THEME["surface_alt"],
            "light_border_color": LIGHT_THEME["border"],
            "light_text_color": LIGHT_THEME["text"],
            "light_muted_text_color": LIGHT_THEME["muted"],
            "light_accent_color": LIGHT_THEME["accent"],
            "light_button_bg": LIGHT_THEME["button"],
            "light_button_active_bg": LIGHT_THEME["button_active"],
            "light_input_bg": LIGHT_THEME["entry"],
            "light_input_text_color": LIGHT_THEME["entry_text"],
            "light_select_bg": LIGHT_THEME["select"],
            "light_select_text_color": LIGHT_THEME["select_text"],
            "dark_window_bg": DARK_THEME["window"],
            "dark_surface_bg": DARK_THEME["surface"],
            "dark_surface_alt_bg": DARK_THEME["surface_alt"],
            "dark_border_color": DARK_THEME["border"],
            "dark_text_color": DARK_THEME["text"],
            "dark_muted_text_color": DARK_THEME["muted"],
            "dark_accent_color": DARK_THEME["accent"],
            "dark_button_bg": DARK_THEME["button"],
            "dark_button_active_bg": DARK_THEME["button_active"],
            "dark_input_bg": DARK_THEME["entry"],
            "dark_input_text_color": DARK_THEME["entry_text"],
            "dark_select_bg": DARK_THEME["select"],
            "dark_select_text_color": DARK_THEME["select_text"],
            "ui_font_family": "Segoe UI",
            "ui_font_size": 9,
            "heading_font_size": 10,
            "canvas_font_family": "Segoe UI",
            "canvas_label_min_size": 5,
            "canvas_label_max_size": 8,
             "file_type_colors": {
                 "image": "#ff6600",
                 "video": "#cc0000",
                 "audio": "#00cc00",
                 "document": "#0066ff",
                 "archive": "#cccc00",
                 "executable": "#cc00cc",
                 "code": "#00cccc",
                 "text": "#aaaaaa",
                 "other": ""
             },
             "log_bg": "",
             "log_fg": ""
        }
        for key, value in defaults.items():
            if key not in self.settings:
                self.settings[key] = value
        if self.settings.get("animated_zoom", False) and self.settings.get("animation_mode", "none") == "none":
            self.settings["animation_mode"] = "zoom"
        theme_mode = self.settings.get("theme_mode", "system")
        if theme_mode == "dark":
            self.dark_mode = True
        elif theme_mode == "light":
            self.dark_mode = False
        else:  # system
            pref = system_prefers_dark_theme()
            self.dark_mode = pref if pref is not None else True

    def setting_color(self, key, default):
        value = self.settings.get(key, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default

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
        ui_font = (self.settings.get("ui_font_family", "Segoe UI"), self.get_setting_int("ui_font_size", 9, 6, 24))

        base_colors = DARK_THEME if self.dark_mode else LIGHT_THEME
        prefix = "dark" if self.dark_mode else "light"
        colors = {
            "window": self.setting_color(f"{prefix}_window_bg", base_colors["window"]),
            "surface": self.setting_color(f"{prefix}_surface_bg", base_colors["surface"]),
            "surface_alt": self.setting_color(f"{prefix}_surface_alt_bg", base_colors["surface_alt"]),
            "border": self.setting_color(f"{prefix}_border_color", base_colors["border"]),
            "text": self.setting_color(f"{prefix}_text_color", base_colors["text"]),
            "muted": self.setting_color(f"{prefix}_muted_text_color", base_colors["muted"]),
            "accent": self.setting_color(f"{prefix}_accent_color", base_colors["accent"]),
            "button": self.setting_color(f"{prefix}_button_bg", base_colors["button"]),
            "button_active": self.setting_color(f"{prefix}_button_active_bg", base_colors["button_active"]),
            "entry": self.setting_color(f"{prefix}_input_bg", base_colors["entry"]),
            "entry_text": self.setting_color(f"{prefix}_input_text_color", base_colors["entry_text"]),
            "select": self.setting_color(f"{prefix}_select_bg", base_colors["select"]),
            "select_text": self.setting_color(f"{prefix}_select_text_color", base_colors["select_text"]),
        }

        self.configure(bg=colors["window"])
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Base ttk styles
        self.style.configure(".", font=ui_font, background=colors["window"], foreground=colors["text"])
        self.style.configure("TFrame", background=colors["window"])
        self.style.configure("TNotebook", background=colors["window"], borderwidth=1, bordercolor=colors["border"])
        self.style.configure("TNotebook.Tab", background=colors["surface"], foreground=colors["text"], font=ui_font)
        self.style.map("TNotebook.Tab", background=[("selected", colors["surface_alt"])])
        self.style.configure("TButton", background=colors["button"], foreground=colors["text"])
        self.style.map("TButton", background=[("active", colors["button_active"])])
        self.style.configure("TLabel", background=colors["window"], foreground=colors["text"])
        self.style.configure(
            "TEntry",
            fieldbackground=colors["entry"],
            foreground=colors["entry_text"],
            insertcolor=colors["entry_text"]
        )
        self.style.configure("TCombobox", fieldbackground=colors["entry"], foreground=colors["entry_text"])
        self.style.configure("TRadiobutton", background=colors["window"], foreground=colors["text"])
        self.style.map("TRadiobutton",
                       background=[("active", colors["surface_alt"])],
                       foreground=[("active", colors["text"])])
        self.style.configure("TCheckbutton", background=colors["window"], foreground=colors["text"])

        # Canvas
        canvas_bg = self.settings.get("canvas_bg", "") or colors["surface"]
        if hasattr(self, "canvas"):
            self.canvas.configure(bg=canvas_bg)

        # Log
        if hasattr(self, "log_text"):
            log_bg = self.settings.get("log_bg", "") or colors["surface"]
            log_fg = self.settings.get("log_fg", "") or colors["text"]
            self.log_text.configure(bg=log_bg, fg=log_fg, insertbackground=log_fg)

        # Style all widgets recursively
        self._style_widget_tree(self)

        # Windows dark title bar
        self.update_idletasks()
        set_windows_dark_title_bar(self, self.dark_mode)

        # Redraw treemap if needed
        if hasattr(self, "current_node") and self.current_node:
            self.draw()

    def _style_widget_tree(self, widget):
        base_colors = DARK_THEME if self.dark_mode else LIGHT_THEME
        prefix = "dark" if self.dark_mode else "light"
        colors = {
            "window": self.setting_color(f"{prefix}_window_bg", base_colors["window"]),
            "surface": self.setting_color(f"{prefix}_surface_bg", base_colors["surface"]),
            "entry": self.setting_color(f"{prefix}_input_bg", base_colors["entry"]),
            "entry_text": self.setting_color(f"{prefix}_input_text_color", base_colors["entry_text"]),
            "select": self.setting_color(f"{prefix}_select_bg", base_colors["select"]),
            "select_text": self.setting_color(f"{prefix}_select_text_color", base_colors["select_text"]),
            "text": self.setting_color(f"{prefix}_text_color", base_colors["text"]),
        }
        try:
            wclass = widget.winfo_class()
            if wclass in ("Tk", "Toplevel", "Frame"):
                widget.configure(background=colors["window"])
            elif isinstance(widget, tk.Canvas):
                widget.configure(background=colors["surface"])
            elif isinstance(widget, tk.Entry):
                widget.configure(background=colors["entry"], foreground=colors["entry_text"], insertbackground=colors["entry_text"])
            elif isinstance(widget, tk.Listbox):
                widget.configure(background=colors["entry"], foreground=colors["entry_text"],
                                 selectbackground=colors["select"], selectforeground=colors["select_text"])
            elif isinstance(widget, tk.Text):
                if widget is not getattr(self, "log_text", None):
                    widget.configure(background=colors["surface"], foreground=colors["text"], insertbackground=colors["text"])
        except Exception:
            pass

        for child in widget.winfo_children():
            self._style_widget_tree(child)

    def get_setting_int(self, key, default, minimum, maximum):
        try:
            value = int(self.settings.get(key, default))
        except (TypeError, ValueError):
            value = default
        return max(minimum, min(maximum, value))

    def get_int_var(self, variable, default, minimum, maximum):
        try:
            value = int(variable.get())
        except (tk.TclError, TypeError, ValueError):
            value = default
        return max(minimum, min(maximum, value))

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
        width, height = 480, 520
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        settings_win.geometry(f"{width}x{height}+{x}+{y}")
        settings_win.transient(self)
        settings_win.grab_set()
        settings_win.resizable(False, False)

        # Apply title bar and correct theme colors to settings dialog
        set_windows_dark_title_bar(settings_win, self.dark_mode)
        colors = DARK_THEME if self.dark_mode else LIGHT_THEME
        settings_win.configure(bg=colors["window"])

        main_frame = ttk.Frame(settings_win, padding=12)
        main_frame.pack(fill="both", expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)

        appearance_tab = ttk.Frame(notebook, padding=12)
        fonts_tab = ttk.Frame(notebook, padding=12)
        behavior_tab = ttk.Frame(notebook, padding=12)
        scan_tab = ttk.Frame(notebook, padding=12)

        notebook.add(appearance_tab, text="Appearance")
        notebook.add(fonts_tab, text="Fonts")
        notebook.add(behavior_tab, text="Behavior")
        notebook.add(scan_tab, text="Scan")

        ttk.Label(appearance_tab, text="Theme", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        theme_frame = ttk.Frame(appearance_tab)
        theme_frame.pack(fill="x", pady=(0, 16))

        ttk.Label(theme_frame, text="Mode:").pack(side="left")

        current_mode = self.settings.get("theme_mode", "system")
        self.theme_var = tk.StringVar(value=current_mode)

        ttk.Radiobutton(theme_frame, text="System default", variable=self.theme_var, value="system",
                        command=lambda: self.on_theme_change("system")).pack(side="left", padx=(10, 15))
        ttk.Radiobutton(theme_frame, text="Light", variable=self.theme_var, value="light",
                        command=lambda: self.on_theme_change("light")).pack(side="left", padx=(0, 15))
        ttk.Radiobutton(theme_frame, text="Dark", variable=self.theme_var, value="dark",
                        command=lambda: self.on_theme_change("dark")).pack(side="left", padx=(0, 15))

        ttk.Label(appearance_tab, text="Colors", style="Heading.TLabel").pack(anchor="w", pady=(8, 10))
        ttk.Button(appearance_tab, text="General Colors...", command=self.show_color_settings).pack(anchor="w", pady=(0, 8))
        ttk.Button(appearance_tab, text="File Type Colors...", command=self.show_file_type_colors).pack(anchor="w", pady=(0, 8))
        ttk.Button(appearance_tab, text="Log Colors...", command=self.show_log_color_settings).pack(anchor="w", pady=(0, 16))

        ttk.Label(fonts_tab, text="Interface Font", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        font_family_values = sorted({
            "Segoe UI",
            "Arial",
            "Calibri",
            "Consolas",
            "Tahoma",
            "Verdana",
            self.settings.get("ui_font_family", "Segoe UI"),
            self.settings.get("canvas_font_family", "Segoe UI")
        })

        def add_labeled_spinbox(parent, label, variable, from_, to_, width=6):
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=24).pack(side="left")
            ttk.Spinbox(row, from_=from_, to=to_, textvariable=variable, width=width).pack(side="left")

        ui_family_frame = ttk.Frame(fonts_tab)
        ui_family_frame.pack(fill="x", pady=3)
        ttk.Label(ui_family_frame, text="UI font family", width=24).pack(side="left")
        self.ui_font_family_var = tk.StringVar(value=self.settings.get("ui_font_family", "Segoe UI"))
        ttk.Combobox(
            ui_family_frame,
            textvariable=self.ui_font_family_var,
            values=font_family_values,
            width=20
        ).pack(side="left")

        self.ui_font_size_var = tk.IntVar(value=self.get_setting_int("ui_font_size", 9, 6, 24))
        add_labeled_spinbox(fonts_tab, "UI font size", self.ui_font_size_var, 6, 24)

        self.heading_font_size_var = tk.IntVar(value=self.get_setting_int("heading_font_size", 10, 6, 28))
        add_labeled_spinbox(fonts_tab, "Heading font size", self.heading_font_size_var, 6, 28)

        ttk.Separator(fonts_tab, orient="horizontal").pack(fill="x", pady=14)
        ttk.Label(fonts_tab, text="Treemap Labels", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        canvas_family_frame = ttk.Frame(fonts_tab)
        canvas_family_frame.pack(fill="x", pady=3)
        ttk.Label(canvas_family_frame, text="Label font family", width=24).pack(side="left")
        self.canvas_font_family_var = tk.StringVar(value=self.settings.get("canvas_font_family", "Segoe UI"))
        ttk.Combobox(
            canvas_family_frame,
            textvariable=self.canvas_font_family_var,
            values=font_family_values,
            width=20
        ).pack(side="left")

        self.canvas_label_min_size_var = tk.IntVar(value=self.get_setting_int("canvas_label_min_size", 5, 4, 18))
        add_labeled_spinbox(fonts_tab, "Minimum label size", self.canvas_label_min_size_var, 4, 18)

        self.canvas_label_max_size_var = tk.IntVar(value=self.get_setting_int("canvas_label_max_size", 8, 5, 32))
        add_labeled_spinbox(fonts_tab, "Maximum label size", self.canvas_label_max_size_var, 5, 32)

        ttk.Label(behavior_tab, text="Actions", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        self.density_var = tk.IntVar(value=self.settings.get("min_density", 1))
        ttk.Checkbutton(behavior_tab, text="Hide small files (density filter)", variable=self.density_var).pack(anchor="w", pady=2)

        self.disable_delete_var = tk.BooleanVar(value=self.settings.get("disable_delete", False))
        ttk.Checkbutton(behavior_tab, text="Disable delete command", variable=self.disable_delete_var).pack(anchor="w", pady=2)

        self.remember_pos_var = tk.BooleanVar(value=self.settings.get("remember_window_pos", True))
        ttk.Checkbutton(behavior_tab, text="Remember window position", variable=self.remember_pos_var).pack(anchor="w", pady=2)

        ttk.Separator(behavior_tab, orient="horizontal").pack(fill="x", pady=12)
        ttk.Label(behavior_tab, text="Animation", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        animation_mode = self.settings.get("animation_mode", "none")
        if self.settings.get("animated_zoom", False) and animation_mode == "none":
            animation_mode = "zoom"
        self.animation_mode_var = tk.StringVar(value=animation_mode)
        animation_frame = ttk.Frame(behavior_tab)
        animation_frame.pack(fill="x", pady=3)
        ttk.Label(animation_frame, text="Mode", width=24).pack(side="left")
        ttk.Combobox(
            animation_frame,
            textvariable=self.animation_mode_var,
            values=["none", "zoom", "collapse"],
            width=14,
            state="readonly"
        ).pack(side="left")

        self.animation_duration_var = tk.IntVar(value=self.get_setting_int("animation_duration", 160, 50, 1000))
        add_labeled_spinbox(behavior_tab, "Duration (ms)", self.animation_duration_var, 50, 1000)

        self.animation_steps_var = tk.IntVar(value=self.get_setting_int("animation_steps", 10, 3, 40))
        add_labeled_spinbox(behavior_tab, "Steps", self.animation_steps_var, 3, 40)

        self.auto_rescan_var = tk.BooleanVar(value=self.settings.get("auto_rescan_on_delete", True))
        ttk.Checkbutton(behavior_tab, text="Auto rescan after delete", variable=self.auto_rescan_var).pack(anchor="w", pady=2)

        ttk.Label(scan_tab, text="Scan Progress", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        self.show_scan_progress_var = tk.BooleanVar(value=self.settings.get("show_scan_progress", True))
        ttk.Checkbutton(scan_tab, text="Show scan progress details", variable=self.show_scan_progress_var).pack(anchor="w", pady=2)

        ttk.Label(scan_tab, text="Maximum scan threads:").pack(anchor="w", pady=(12, 2))
        self.max_threads_var = tk.IntVar(value=self.get_setting_int("max_scan_threads", 6, 1, 32))
        ttk.Spinbox(scan_tab, from_=1, to=32, textvariable=self.max_threads_var, width=5).pack(anchor="w", pady=(0, 10))

        ttk.Separator(scan_tab, orient="horizontal").pack(fill="x", pady=12)
        ttk.Label(scan_tab, text="Modified Files", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))

        self.show_recent_modified_var = tk.BooleanVar(value=self.settings.get("show_recent_modified", True))
        ttk.Checkbutton(
            scan_tab,
            text="Show recently modified indicators",
            variable=self.show_recent_modified_var
        ).pack(anchor="w", pady=2)

        self.recent_modified_outline_style_var = tk.StringVar(
            value=self.settings.get("recent_modified_outline_style", "indicator_only")
        )
        outline_style_frame = ttk.Frame(scan_tab)
        outline_style_frame.pack(fill="x", pady=(12, 2))
        ttk.Label(outline_style_frame, text="Indicator style:", width=24).pack(side="left")
        ttk.Combobox(
            outline_style_frame,
            textvariable=self.recent_modified_outline_style_var,
            values=["indicator_only", "subtle_outline"],
            width=16,
            state="readonly"
        ).pack(side="left")

        ttk.Label(scan_tab, text="Recent window (days):").pack(anchor="w", pady=(12, 2))
        self.recent_modified_days_var = tk.IntVar(value=self.get_setting_int("recent_modified_days", 7, 1, 365))
        ttk.Spinbox(scan_tab, from_=1, to=365, textvariable=self.recent_modified_days_var, width=5).pack(anchor="w", pady=(0, 10))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(12, 0))

        def save_and_close():
            self.settings["min_density"] = self.density_var.get()
            self.settings["disable_delete"] = self.disable_delete_var.get()
            self.settings["remember_window_pos"] = self.remember_pos_var.get()
            self.settings["show_scan_progress"] = self.show_scan_progress_var.get()
            self.settings["max_scan_threads"] = self.get_int_var(self.max_threads_var, 6, 1, 32)
            self.settings["show_recent_modified"] = self.show_recent_modified_var.get()
            self.settings["recent_modified_outline_style"] = self.recent_modified_outline_style_var.get()
            self.settings["recent_modified_days"] = self.get_int_var(self.recent_modified_days_var, 7, 1, 365)
            animation_mode = self.animation_mode_var.get()
            self.settings["animation_mode"] = animation_mode
            self.settings["animated_zoom"] = animation_mode != "none"
            self.settings["animation_duration"] = self.get_int_var(self.animation_duration_var, 160, 50, 1000)
            self.settings["animation_steps"] = self.get_int_var(self.animation_steps_var, 10, 3, 40)
            self.settings["auto_rescan_on_delete"] = self.auto_rescan_var.get()
            self.settings["theme_mode"] = self.theme_var.get()
            mode = self.theme_var.get()
            if mode == "dark":
                self.settings["dark_mode"] = True
            elif mode == "light":
                self.settings["dark_mode"] = False
            else:
                pref = system_prefers_dark_theme()
                self.settings["dark_mode"] = pref if pref is not None else True
            self.settings["ui_font_family"] = self.ui_font_family_var.get().strip() or "Segoe UI"
            self.settings["ui_font_size"] = self.get_int_var(self.ui_font_size_var, 9, 6, 24)
            self.settings["heading_font_size"] = self.get_int_var(self.heading_font_size_var, 10, 6, 28)
            self.settings["canvas_font_family"] = self.canvas_font_family_var.get().strip() or "Segoe UI"
            min_label_size = self.get_int_var(self.canvas_label_min_size_var, 5, 4, 18)
            max_label_size = self.get_int_var(self.canvas_label_max_size_var, 8, 5, 32)
            self.settings["canvas_label_min_size"] = min_label_size
            self.settings["canvas_label_max_size"] = max(min_label_size, max_label_size)
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

        # Style the entire settings dialog
        self._style_widget_tree(settings_win)

        # Ensure dark title bar is applied to the settings window
        settings_win.update_idletasks()
        set_windows_dark_title_bar(settings_win, self.dark_mode)

    def on_theme_change(self, theme):
        self.settings["theme_mode"] = theme
        if theme == "dark":
            self.dark_mode = True
        elif theme == "light":
            self.dark_mode = False
        else:  # system
            pref = system_prefers_dark_theme()
            self.dark_mode = pref if pref is not None else True
        self.apply_theme()
        if self.current_node:
            self.draw()
