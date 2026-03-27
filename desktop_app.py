import json
import logging
import socket
import threading
import time
import webbrowser
import ctypes
import sys
from urllib.error import URLError
from urllib.request import urlopen

from app import HOST, PORT, app, start_background_services

try:
    import webview
except ImportError:  # pragma: no cover
    webview = None

APP_URL = f"http://{HOST}:{PORT}/"
LOGIN_URL = f"http://{HOST}:{PORT}/login?desktop=1"
AUTH_STATUS_URL = f"http://{HOST}:{PORT}/auth/status"
DESKTOP_AUTH_URL = f"http://{HOST}:{PORT}/auth/google/start?next=/auth/desktop-complete"


def hide_console_window() -> None:
    try:
        console_window = ctypes.windll.kernel32.GetConsoleWindow()
        if console_window:
            ctypes.windll.user32.ShowWindow(console_window, 0)
    except Exception:
        pass


def start_flask() -> None:
    start_background_services()
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.logger.disabled = True
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


def is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((host, port)) == 0


def wait_for_server(timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def fetch_auth_status() -> dict:
    with urlopen(AUTH_STATUS_URL, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


class DesktopApi:
    def start_google_login(self) -> dict:
        webbrowser.open(DESKTOP_AUTH_URL)
        return {"ok": True}


class DesktopShell:
    def __init__(self) -> None:
        self.window = None
        self.last_logged_in = None
        self.stop_event = threading.Event()

    def create_window(self) -> None:
        if webview is None:
            webbrowser.open(LOGIN_URL)
            raise RuntimeError("pywebview is not installed. Browser fallback opened instead.")
        if hasattr(webview, "settings") and "OPEN_EXTERNAL_LINKS_IN_BROWSER" in webview.settings:
            webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        self.window = webview.create_window(
            "Device Health Monitor PRO",
            LOGIN_URL,
            js_api=DesktopApi(),
            width=1480,
            height=960,
            min_size=(1120, 760),
        )
        self.window.events.closed += self.on_closed
        webview.start(self.start_watchers, self.window, debug=False)

    def on_closed(self) -> None:
        self.stop_event.set()

    def start_watchers(self, window) -> None:
        self.window = window
        threading.Thread(target=self.watch_auth_state, daemon=True).start()

    def watch_auth_state(self) -> None:
        while not self.stop_event.is_set():
            try:
                status = fetch_auth_status()
                logged_in = bool(status.get("logged_in"))
                if self.last_logged_in is None:
                    self.last_logged_in = logged_in
                elif logged_in != self.last_logged_in:
                    self.last_logged_in = logged_in
                    self.window.load_url(APP_URL if logged_in else LOGIN_URL)
                elif logged_in and self.window.get_current_url().rstrip("/") == LOGIN_URL.rstrip("/"):
                    self.window.load_url(APP_URL)
            except (OSError, URLError, ValueError):
                pass
            time.sleep(1.5)


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        hide_console_window()
    if is_port_in_use(HOST, PORT):
        ctypes.windll.user32.MessageBoxW(
            0,
            (
                "Another Device Health Monitor PRO instance is already using port 5000.\n\n"
                "Close the older app window first, then open this build again."
            ),
            "Device Health Monitor PRO",
            0x10,
        )
        raise SystemExit(1)
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    if not wait_for_server():
        raise RuntimeError("Server failed to start in time.")
    DesktopShell().create_window()
