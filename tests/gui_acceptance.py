"""Run scripted GUI acceptance with synthetic files on a dedicated X display."""

import json
import importlib
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
Quantifile = importlib.import_module("app").Quantifile
ImageGrab = importlib.import_module("PIL.ImageGrab")

OUTPUT = Path(os.environ.get("QUANTIFILE_QA_OUTPUT", "/work/qa"))
OUTPUT.mkdir(parents=True, exist_ok=True)


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def button(window, label):
    return next(w for w in descendants(window) if w.winfo_class() == "TButton" and w.cget("text") == label)


with tempfile.TemporaryDirectory(prefix="quantifile-acceptance-") as temporary:
    os.chdir(temporary)
    data = Path(temporary) / "Demo files"
    data.mkdir()
    (data / "Documents").mkdir()
    (data / "Documents" / "report.txt").write_bytes(b"x" * 32768)
    (data / "photo.png").write_bytes(b"x" * 65536)
    (data / "archive.zip").write_bytes(b"x" * 16384)
    app = Quantifile()
    app.geometry("1600x1000+0+0")
    errors = []
    app.report_callback_exception = lambda *args: errors.append(str(args))

    def accept():
        if app.root_node is None:
            app.after(50, accept)
            return
        try:
            assert app.root_node.size == 114688
            assert app.canvas.find_all()
            app.search_var.set("report")
            assert app.search_matches == {str(data / "Documents" / "report.txt")}
            app.clear_search()
            folder = next(n for n in app.root_node.children if n.name == "Documents")
            app.animate_zoom(app.current_node, folder)
            assert app.current_node == folder
            app.zoom_out()
            assert app.current_node == app.root_node
            app.add_current_to_bookmarks()
            assert str(data) in json.loads(Path("settings.json").read_text())["bookmarks"]
            button(app, "Bookmarks (HIDDEN)").invoke()
            assert app.bookmarks_visible
            button(app, "Bookmarks (SHOWN)").invoke()
            assert not app.bookmarks_visible
            exported = Path(temporary) / "treemap.svg"
            with patch("actions_controller.filedialog.asksaveasfilename", return_value=str(exported)):
                app.export_svg()
            assert ET.parse(exported).getroot().tag.endswith("svg")
            for theme in ("light", "dark"):
                app.main_notebook.select(app.treemap_tab)
                app.on_theme_change(theme)
                app.update()
                ImageGrab.grab(bbox=(0, 0, 1600, 1000)).save(OUTPUT / f"quantifile-{theme}.png")
            app.show_settings()
            app.update()
            dialog = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
            app.theme_var.set("light")
            button(dialog, "Save").invoke()
            assert json.loads(Path("settings.json").read_text())["theme_mode"] == "light"
            app.show_about()
            app.update()
            dialog = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
            assert dialog.title() == "About Quantifile"
            dialog.destroy()
            app.main_notebook.select(app.log_tab)
            app.update()
            assert "Ready" in app.log_text.get("1.0", "end")
            app.main_notebook.select(app.treemap_tab)
            app.geometry("1100x750+0+0")
            app.update()
            for label in (
                "Open Folder",
                "Quick Browse",
                "Rescan",
                "Zoom Out",
                "Settings",
                "About",
                "Export",
                "Bookmarks (HIDDEN)",
            ):
                control = button(app, label)
                assert control.winfo_ismapped(), label
                assert control.winfo_rootx() + control.winfo_width() <= 1100, label
            ImageGrab.grab(bbox=(0, 0, 1100, 750)).save(OUTPUT / "quantifile-default-size.png")
            print(
                "GUI PASS: scan, search, zoom in/out, bookmarks, SVG export, settings save, themes, About, Log",
                flush=True,
            )
        except Exception as error:
            errors.append(repr(error))
        finally:
            app.destroy()

    app.after(50, lambda: app.start_scan(str(data)))
    app.after(100, accept)
    app.after(30000, lambda: (errors.append("GUI timeout"), app.destroy()))
    app.mainloop()
    assert not errors, errors
