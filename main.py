"""
LibManager Desktop Application Entry Point
Usage:
    python main.py              # Launches the full-featured Desktop Application (Web App converted)
    python main.py --tkinter    # Launches the legacy CustomTkinter GUI
"""

import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    if "--tkinter" in sys.argv:
        from desktop_app import LibraryApp
        app = LibraryApp()
        app.mainloop()
    else:
        from desktop_main import launch_desktop_app
        launch_desktop_app()

