from __future__ import annotations

import ctypes
import glob
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from app import DATA_ROOT, HOST, PORT, app, get_configured_public_base_url, start_background_services

LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
LOG_DIR = DATA_ROOT
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        RotatingFileHandler(LOG_DIR / "desktop_app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"),
    ],
)
log = logging.getLogger("desktop_app")

try:
    import webview
except ImportError:  # pragma: no cover
    webview = None
    log.warning("pywebview is not installed, browser fallback will be used.")

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    pystray = None
    Image = None
    ImageDraw = None
    log.warning("pystray or Pillow is not installed, tray support will be unavailable.")

LOCAL_APP_BASE = f"http://{HOST}:{PORT}"
AUTH_STATUS_URL = f"{LOCAL_APP_BASE}/auth/status"
APP_TITLE = "Device Health Monitor"
APP_URL = f"{LOCAL_APP_BASE}/"
LOGIN_URL = f"{LOCAL_APP_BASE}/login?desktop=1"
DESKTOP_AUTH_URL = f"{LOCAL_APP_BASE}/auth/google/start?next=/auth/desktop-complete"
NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"
PUBLIC_APP_BASE = ""
NGROK_PROCESS: subprocess.Popen[str] | None = None
MINIMIZE_TO_TRAY_ON_CLOSE = False


def hide_console_window() -> None:
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        log.debug("Could not hide console window.", exc_info=True)


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


def configure_visible_base(base_url: str) -> None:
    normalized = (base_url or "").strip().rstrip("/") or LOCAL_APP_BASE
    global APP_URL, LOGIN_URL, DESKTOP_AUTH_URL, PUBLIC_APP_BASE
    APP_URL = f"{normalized}/"
    LOGIN_URL = f"{normalized}/login?desktop=1"
    DESKTOP_AUTH_URL = f"{normalized}/auth/google/start?next=/auth/desktop-complete"
    PUBLIC_APP_BASE = "" if normalized == LOCAL_APP_BASE else normalized


def _hidden_subprocess_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {}
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return kwargs


def find_ngrok_executable() -> str | None:
    direct = shutil.which("ngrok")
    if direct:
        return direct

    candidates = [
        LOCAL_APPDATA / "Microsoft" / "WindowsApps" / "ngrok.exe",
        LOCAL_APPDATA / "ngrok" / "ngrok.exe",
        Path.home() / "AppData" / "Local" / "ngrok" / "ngrok.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    package_pattern = str(LOCAL_APPDATA / "Packages" / "*" / "LocalCache" / "Local" / "ngrok" / "ngrok.exe")
    for match in glob.iglob(package_pattern):
        if Path(match).exists():
            return match
    return None


def get_ngrok_tunnels() -> list[dict]:
    try:
        with urlopen(NGROK_API_URL, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return list(payload.get("tunnels", []))
    except Exception:
        return []


def get_public_tunnel(expected_public_url: str) -> dict | None:
    expected = expected_public_url.rstrip("/")
    for tunnel in get_ngrok_tunnels():
        if str(tunnel.get("public_url", "")).rstrip("/") == expected:
            return tunnel
    return None


def tunnel_targets_local_flask(tunnel: dict | None) -> bool:
    if not tunnel:
        return False
    config = tunnel.get("config") or {}
    addr = str(config.get("addr", "")).strip().lower()
    expected_addrs = {
        f"http://localhost:{PORT}",
        f"http://127.0.0.1:{PORT}",
        f"localhost:{PORT}",
        f"127.0.0.1:{PORT}",
    }
    return addr in expected_addrs


def has_public_tunnel(expected_public_url: str) -> bool:
    return tunnel_targets_local_flask(get_public_tunnel(expected_public_url))


def stop_conflicting_ngrok_processes(expected_public_url: str) -> None:
    tunnel = get_public_tunnel(expected_public_url)
    if not tunnel or tunnel_targets_local_flask(tunnel):
        return

    conflicting_addr = str((tunnel.get("config") or {}).get("addr", "")).strip() or "unknown target"
    log.warning(
        "Configured ngrok URL %s is currently routed to %s. Restarting ngrok so the desktop app can use port %s.",
        expected_public_url,
        conflicting_addr,
        PORT,
    )

    stop_ngrok_tunnel()
    try:
        subprocess.run(
            ["taskkill", "/IM", "ngrok.exe", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
            **_hidden_subprocess_kwargs(),
        )
    except Exception:
        log.debug("Could not stop conflicting ngrok process cleanly.", exc_info=True)

    deadline = time.time() + 8
    while time.time() < deadline:
        if get_public_tunnel(expected_public_url) is None:
            return
        time.sleep(0.5)


def wait_for_public_url(url: str, timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(f"{url.rstrip('/')}/auth/status", timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if response.status == 200 and payload.get("ok") is True and "logged_in" in payload:
                    return True
        except Exception:
            time.sleep(1)
    return False


def stop_ngrok_tunnel() -> None:
    global NGROK_PROCESS
    if NGROK_PROCESS is None:
        return
    try:
        if NGROK_PROCESS.poll() is None:
            NGROK_PROCESS.terminate()
            NGROK_PROCESS.wait(timeout=5)
    except Exception:
        try:
            NGROK_PROCESS.kill()
        except Exception:
            log.debug("Could not stop ngrok cleanly.", exc_info=True)
    NGROK_PROCESS = None


def start_ngrok_tunnel(expected_public_url: str) -> bool:
    global NGROK_PROCESS
    if not expected_public_url:
        return False

    stop_conflicting_ngrok_processes(expected_public_url)
    if has_public_tunnel(expected_public_url):
        log.info("Using existing ngrok tunnel: %s", expected_public_url)
        return True

    ngrok_path = find_ngrok_executable()
    if not ngrok_path:
        log.warning("ngrok executable not found. Falling back to local app URL.")
        return False

    try:
        NGROK_PROCESS = subprocess.Popen(
            [ngrok_path, "http", str(PORT), "--url", expected_public_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(Path(__file__).resolve().parent),
            text=True,
            **_hidden_subprocess_kwargs(),
        )
    except Exception:
        log.warning("Could not start ngrok. Falling back to local app URL.", exc_info=True)
        NGROK_PROCESS = None
        return False

    deadline = time.time() + 20
    while time.time() < deadline:
        if NGROK_PROCESS.poll() is not None:
            log.warning("ngrok exited early. Falling back to local app URL.")
            NGROK_PROCESS = None
            return False
        if has_public_tunnel(expected_public_url):
            log.info("ngrok tunnel started: %s", expected_public_url)
            return True
        time.sleep(1)

    log.warning("ngrok did not expose the configured domain in time. Falling back to local app URL.")
    stop_ngrok_tunnel()
    return False


def start_flask() -> None:
    start_background_services()
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.logger.disabled = True
    try:
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
    except Exception:
        log.exception("Flask crashed and cannot recover.")
        raise SystemExit(1)


def _make_tray_icon(size: int = 64) -> "Image.Image":
    if Image is None or ImageDraw is None:  # pragma: no cover
        raise RuntimeError("Tray icon support is unavailable.")
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([4, 4, size - 4, size - 4], fill=(29, 158, 117, 255))
    center_x = size // 2
    center_y = size // 2
    thickness = max(2, size // 10)
    draw.rectangle([center_x - thickness, center_y - size // 3, center_x + thickness, center_y + size // 3], fill="white")
    draw.rectangle([center_x - size // 3, center_y - thickness, center_x + size // 3, center_y + thickness], fill="white")
    return image


class TrayManager:
    def __init__(self, shell: "DesktopShell") -> None:
        self._shell = shell
        self._icon = None
        self.enabled = pystray is not None and Image is not None and ImageDraw is not None

    def start(self) -> None:
        if not self.enabled:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Open", self._on_open, default=True),
            pystray.MenuItem("Hide", self._on_hide),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit),
        )
        self._icon = pystray.Icon(APP_TITLE, _make_tray_icon(), APP_TITLE, menu)
        threading.Thread(target=self._icon.run, name="tray", daemon=True).start()
        log.info("System tray icon started.")

    def stop(self) -> None:
        if self._icon is None:
            return
        try:
            self._icon.stop()
        except Exception:
            log.debug("Tray stop failed.", exc_info=True)

    def notify(self, title: str, message: str) -> None:
        if self._icon is None:
            return
        try:
            self._icon.notify(message, title)
        except Exception:
            log.debug("Tray notification failed.", exc_info=True)

    def _on_open(self, icon, item) -> None:  # noqa: ANN001
        self._shell.show_window()

    def _on_hide(self, icon, item) -> None:  # noqa: ANN001
        self._shell.hide_window()

    def _on_quit(self, icon, item) -> None:  # noqa: ANN001
        log.info("Quit requested from system tray.")
        self._shell.quit()


class DesktopApi:
    def start_google_login(self) -> dict:
        webbrowser.open(DESKTOP_AUTH_URL)
        return {"ok": True}


class DesktopShell:
    def __init__(self) -> None:
        self.window = None
        self._last_logged_in: bool | None = None
        self._stop_event = threading.Event()
        self._hidden = False
        self._quit_requested = False
        self.tray = TrayManager(self)

    def show_window(self) -> None:
        if self.window is None:
            return
        try:
            self.window.show()
            self._hidden = False
            log.info("Window restored from tray.")
        except Exception:
            log.debug("show_window failed.", exc_info=True)

    def hide_window(self) -> None:
        if self.window is None or not self.tray.enabled:
            return
        try:
            self.window.hide()
            self._hidden = True
            log.info("Window minimized to tray.")
            self.tray.notify(APP_TITLE, "Running in the background. Use the tray icon to restore the app.")
        except Exception:
            log.debug("hide_window failed.", exc_info=True)

    def quit(self) -> None:
        self._quit_requested = True
        self._stop_event.set()
        self.tray.stop()
        stop_ngrok_tunnel()
        if self.window is not None:
            try:
                self.window.destroy()
                return
            except Exception:
                log.debug("Window destroy failed during quit.", exc_info=True)
        raise SystemExit(0)

    def create_window(self) -> None:
        if webview is None:
            log.warning("pywebview missing, opening browser fallback.")
            webbrowser.open(LOGIN_URL)
            raise RuntimeError("pywebview is not installed. Browser fallback opened instead.")

        if hasattr(webview, "settings") and "OPEN_EXTERNAL_LINKS_IN_BROWSER" in webview.settings:
            webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True

        self.window = webview.create_window(
            APP_TITLE,
            LOGIN_URL,
            js_api=DesktopApi(),
            width=1480,
            height=960,
            min_size=(1120, 760),
        )
        self.window.events.closing += self._on_closing
        self.window.events.closed += self._on_closed

        self.tray.start()
        webview.start(self._on_webview_started, self.window, debug=False)

    def _on_closing(self) -> bool:
        if self._quit_requested or not self.tray.enabled or not MINIMIZE_TO_TRAY_ON_CLOSE:
            self._quit_requested = True
            self._stop_event.set()
            log.info("Close button pressed, exiting app.")
            return True
        log.info("Close button pressed, minimizing to tray.")
        threading.Thread(target=self.hide_window, daemon=True).start()
        return False

    def _on_closed(self) -> None:
        self._stop_event.set()
        self.tray.stop()
        stop_ngrok_tunnel()

    def _on_webview_started(self, window) -> None:
        self.window = window
        threading.Thread(target=self._watch_auth_state, name="auth-watcher", daemon=True).start()

    def _watch_auth_state(self) -> None:
        consecutive_errors = 0
        while not self._stop_event.is_set():
            try:
                status = fetch_auth_status()
                consecutive_errors = 0
                logged_in = bool(status.get("logged_in"))

                if self._last_logged_in is None:
                    self._last_logged_in = logged_in
                elif logged_in != self._last_logged_in:
                    self._last_logged_in = logged_in
                    target = APP_URL if logged_in else LOGIN_URL
                    self.window.load_url(target)
                    log.info("Auth state changed, navigating to %s", target)
                elif logged_in and self.window.get_current_url().rstrip("/") == LOGIN_URL.rstrip("/"):
                    self.window.load_url(APP_URL)
            except (OSError, URLError, ValueError) as exc:
                consecutive_errors += 1
                if consecutive_errors == 5:
                    log.warning("Auth watcher hit 5 consecutive errors: %s", exc)
            except Exception:
                log.debug("Unexpected auth watcher failure.", exc_info=True)

            time.sleep(1.5)


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        hide_console_window()

    if is_port_in_use(HOST, PORT):
        ctypes.windll.user32.MessageBoxW(
            0,
            (
                "Another Device Health Monitor instance is already using port 5000.\n\n"
                "Close the older app window first, then open this build again."
            ),
            APP_TITLE,
            0x10,
        )
        raise SystemExit(1)

    flask_thread = threading.Thread(target=start_flask, name="flask", daemon=True)
    flask_thread.start()
    log.info("Flask thread started, waiting for server.")

    if not wait_for_server():
        log.error("Server failed to start within 20 seconds.")
        raise RuntimeError("Server failed to start in time.")

    configured_public_base = get_configured_public_base_url()
    if configured_public_base and start_ngrok_tunnel(configured_public_base) and wait_for_public_url(configured_public_base):
        configure_visible_base(configured_public_base)
        log.info("Server ready, launching desktop shell via public URL: %s", configured_public_base)
    else:
        if configured_public_base:
            ctypes.windll.user32.MessageBoxW(
                0,
                (
                    "The configured ngrok URL could not be started or verified.\n\n"
                    "Open ngrok for this reserved domain first, then start the app again.\n\n"
                    f"Configured URL:\n{configured_public_base}"
                ),
                APP_TITLE,
                0x10,
            )
            log.error("Configured ngrok URL failed to start or verify: %s", configured_public_base)
            raise SystemExit(1)
        configure_visible_base(LOCAL_APP_BASE)
        log.info("Server ready, launching desktop shell via local URL.")
    DesktopShell().create_window()
