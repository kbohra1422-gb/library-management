"""
LibManager - Native Desktop Application Launcher
Converts the Flask Web Application into a standalone Native Desktop Application window
using PyWebView (Edge WebView2 Chromium runtime) with automatic standalone app fallback.
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
import socket
import threading
import time
import urllib.request
import subprocess
from app import app, init_db


def find_free_port(preferred_port=5000):
    """Checks if preferred_port is available; if not, finds a dynamic free port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', preferred_port))
            return preferred_port
    except OSError:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]


def run_flask_server(port):
    """Runs the Flask server in a background daemon thread."""
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)


def wait_for_server(port, timeout=8):
    """Polls until the local Flask server responds with 200/302."""
    start_time = time.time()
    url = f"http://127.0.0.1:{port}/"
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LibManagerDesktop/1.0"})
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status in [200, 302]:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def launch_desktop_app():
    """Main desktop launcher function."""
    print("=" * 60)
    print("📚 LibManager Desktop Application Starting...")
    print("=" * 60)

    # 1. Initialize SQLite database and demo accounts
    init_db()

    # 2. Bind to a local port (default 5000)
    port = find_free_port(5000)
    target_url = f"http://127.0.0.1:{port}/"

    # 3. Start Flask web server in a daemon thread
    server_thread = threading.Thread(target=run_flask_server, args=(port,), daemon=True)
    server_thread.start()

    # 4. Wait until Flask is ready
    print(f"Connecting to local engine on http://127.0.0.1:{port}...")
    if not wait_for_server(port):
        print(f"Note: Connecting directly to {target_url}...")

    # 5. Launch native desktop window via PyWebView
    try:
        import webview

        print("Opening native desktop window (Edge WebView2 Engine)...")
        window = webview.create_window(
            title="📚 LibManager - Library Management System (Desktop Edition)",
            url=target_url,
            width=1280,
            height=820,
            min_size=(960, 640),
            confirm_close=True,
            text_select=True,
            zoomable=True
        )

        webview.start(debug=False)
        print("LibManager Desktop Application closed successfully.")
        sys.exit(0)

    except Exception as e:
        print(f"Note: Webview window error ({e}). Using Standalone Application Window mode...")

        # Fallback: Windows Standalone App Window Mode via Microsoft Edge
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
        ]
        edge_bin = next((p for p in edge_paths if os.path.exists(p)), None)

        if edge_bin:
            print("Launching in dedicated Standalone App window...")
            proc = subprocess.Popen([edge_bin, f"--app={target_url}"])
            proc.wait()
            sys.exit(0)
        else:
            import webbrowser
            print(f"Opening browser at {target_url}...")
            webbrowser.open(target_url)
            print("Press CTRL+C in this terminal window to stop the application.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Application stopped.")
                sys.exit(0)


if __name__ == "__main__":
    launch_desktop_app()
