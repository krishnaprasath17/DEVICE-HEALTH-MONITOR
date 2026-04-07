from __future__ import annotations

import base64
import csv
import getpass
import html as html_lib
import json
import logging
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import warnings
from collections import deque
from copy import deepcopy
from datetime import datetime
from email.mime.text import MIMEText
from io import BytesIO
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# This desktop app uses a localhost HTTP callback for Google OAuth.
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

warnings.filterwarnings(
    "ignore",
    message="You are using a Python version",
    category=FutureWarning,
    module=r"google\.api_core\._python_version_support",
)

import psutil
from flask import Flask, jsonify, has_request_context, redirect, render_template, request, send_file, session, url_for
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    import qrcode
except ImportError:  # pragma: no cover
    qrcode = None

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None

HOST = "127.0.0.1"
PORT = 5000
APP_DISPLAY_NAME = "Device Health Monitor"
APP_STORAGE_DIRNAME = "DeviceHealthMonitor"
LEGACY_APP_STORAGE_DIRNAME = "DeviceHealthMonitorPRO"
LOCAL_REDIRECT_URI = f"http://{HOST}:{PORT}/auth/google/callback"
PUBLIC_BASE_URL = (os.environ.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")

SOURCE_ROOT = Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", SOURCE_ROOT))
EXE_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else SOURCE_ROOT
LOCAL_APPDATA_ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
LEGACY_LOCAL_APPDATA_DATA_ROOT = LOCAL_APPDATA_ROOT / LEGACY_APP_STORAGE_DIRNAME
PORTABLE_MARKER = "portable_mode.flag"
LEGACY_DIST_ROOT = SOURCE_ROOT / "dist"
RUNTIME_DIR_NAME = "runtime"
SOURCE_RUNTIME_ROOT = SOURCE_ROOT / RUNTIME_DIR_NAME


def is_portable_mode() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    if os.environ.get("DEVICE_HEALTH_MONITOR_PORTABLE", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return (EXE_ROOT / PORTABLE_MARKER).exists()


DATA_ROOT = EXE_ROOT if is_portable_mode() else ((LOCAL_APPDATA_ROOT / APP_STORAGE_DIRNAME) if getattr(sys, "frozen", False) else SOURCE_RUNTIME_ROOT)

CLIENT_CONFIG_FILE = RESOURCE_ROOT / "google_oauth_client.json"
TEMPLATE_ROOT = RESOURCE_ROOT / "templates"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.send",
]
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.send"

DEFAULT_NOTIFICATION_SETTINGS: dict[str, Any] = {
    "email_alerts_enabled": True,
    "email_subject_prefix": "Device Health Alert",
    "cpu_alerts_enabled": True,
    "ram_alerts_enabled": True,
    "cpu_high": 90,
    "ram_high": 90,
    "battery_low": 20,
    "cooldown_minutes": 60,
    "alert_check_seconds": 60,
}

app = Flask(__name__, template_folder=str(TEMPLATE_ROOT))
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

notification_settings_lock = threading.Lock()
notification_settings: dict[str, Any] = {}

background_services_started = False
background_lock = threading.Lock()
monitor_thread: threading.Thread | None = None
monitor_supervisor_thread: threading.Thread | None = None
cpu_sampler_thread: threading.Thread | None = None
system_snapshot_thread: threading.Thread | None = None
monitor_stop_event = threading.Event()
alert_cooldown = {"cpu": 0.0, "ram": 0.0}

BATTERY_REPORT_CACHE_SECONDS = 180
BATTERY_REPORT_LOADING_MESSAGE = "Battery report is loading in the background."
SYSTEM_SNAPSHOT_INTERVAL_SECONDS = 1.5
SYSTEM_SNAPSHOT_STALE_SECONDS = 4.0
battery_report_lock = threading.Lock()
battery_report_cache: dict[str, Any] = {"timestamp": 0.0, "data": None}
BATTERY_LIVE_DETAILS_CACHE_SECONDS = 10
battery_live_details_lock = threading.Lock()
battery_live_details_cache: dict[str, Any] = {"timestamp": 0.0, "data": {}}
_battery_refresh_lock = threading.Lock()
_battery_refresh_in_progress = False
_system_identity_cache: dict[str, str | None] | None = None
_system_identity_lock = threading.Lock()


class _NetworkState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.totals: tuple[int, int] | None = None
        self.timestamp = 0.0
        self.upload_history: deque[float] = deque(maxlen=4)
        self.download_history: deque[float] = deque(maxlen=4)


_network_state = _NetworkState()


class _CpuState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.history: deque[float] = deque(maxlen=6)
        self.latest = 0.0
        self.has_sample = False


_cpu_state = _CpuState()


class _SystemSnapshotState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.timestamp = 0.0
        self.data: dict[str, Any] = {}


_system_snapshot_state = _SystemSnapshotState()
_system_snapshot_refresh_lock = threading.Lock()
GPU_CACHE_SECONDS = 2
gpu_snapshot_lock = threading.Lock()
gpu_snapshot_cache: dict[str, Any] = {"timestamp": 0.0, "data": {}}

SOURCE_RUNTIME_FILENAMES = {
    "app.log",
    "auth_debug.log",
    "battery_report.html",
    "desktop_app.log",
    "google_auth_state.bin",
    "google_auth_state.json",
    "notification_settings.json",
    "secret.key",
}


def get_read_data_file_path(filename: str) -> Path:
    primary = DATA_ROOT / filename
    candidates = [primary]
    if getattr(sys, "frozen", False):
        candidates.append(EXE_ROOT / filename)
        candidates.append(LEGACY_LOCAL_APPDATA_DATA_ROOT / filename)
    else:
        candidates.append(SOURCE_ROOT / filename)
        candidates.append(LEGACY_DIST_ROOT / filename)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return primary


def get_write_data_file_path(filename: str) -> Path:
    return DATA_ROOT / filename


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def migrate_source_runtime_files() -> None:
    if getattr(sys, "frozen", False):
        return
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for filename in sorted(SOURCE_RUNTIME_FILENAMES):
        legacy_path = SOURCE_ROOT / filename
        target_path = DATA_ROOT / filename
        if not legacy_path.exists() or target_path.exists():
            continue
        ensure_parent_dir(target_path)
        try:
            shutil.move(str(legacy_path), str(target_path))
        except Exception:
            # Keep startup resilient if a legacy file is locked.
            continue


def configure_logging() -> None:
    log_path = get_write_data_file_path("app.log")
    ensure_parent_dir(log_path)
    app_logger = logging.getLogger("device_health_monitor")
    if app_logger.handlers:
        return
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(stream_handler)
    app_logger.propagate = False


def _get_or_create_secret_key() -> str:
    key_path = get_write_data_file_path("secret.key")
    ensure_parent_dir(key_path)
    if key_path.exists():
        key = key_path.read_text(encoding="utf-8").strip()
        if len(key) >= 32:
            return key
    key = secrets.token_hex(32)
    key_path.write_text(key, encoding="utf-8")
    return key


migrate_source_runtime_files()
configure_logging()
log = logging.getLogger("device_health_monitor")
app.secret_key = os.environ.get("DEVICE_HEALTH_MONITOR_SECRET") or _get_or_create_secret_key()


def run_hidden_subprocess(
    args: list[str],
    *,
    timeout: int | float,
    text: bool = True,
) -> subprocess.CompletedProcess[str]:
    options: dict[str, Any] = {
        "capture_output": True,
        "text": text,
        "timeout": timeout,
        "check": False,
    }
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        options["startupinfo"] = startupinfo
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(args, **options)


def get_battery_report_file_path() -> Path:
    return get_write_data_file_path("battery_report.html")


def append_auth_debug_log(message: str) -> None:
    log.info(message)


def coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def coerce_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def get_safe_next_path(raw: str | None) -> str:
    path = (raw or "").strip()
    if not path:
        return "/"
    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc:
        return "/"
    if not path.startswith("/") or path.startswith("//"):
        return "/"
    return path


def google_login_enabled() -> bool:
    return CLIENT_CONFIG_FILE.exists()


def get_public_base_url() -> str:
    if has_request_context():
        return request.url_root.rstrip("/")
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    return f"http://{HOST}:{PORT}"


def get_google_redirect_uri() -> str:
    return f"{get_public_base_url()}/auth/google/callback"


def normalize_base_url(value: str | None) -> str:
    candidate = (value or "").strip().rstrip("/")
    if not candidate:
        return ""
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def is_local_host(hostname: str | None) -> bool:
    value = (hostname or "").strip().lower()
    if not value:
        return True
    return value in {"localhost", "127.0.0.1", "::1"}


def get_configured_public_base_url() -> str:
    configured = normalize_base_url(PUBLIC_BASE_URL)
    if configured:
        return configured

    candidates = [
        get_write_data_file_path("public_base_url.txt"),
        EXE_ROOT / "public_base_url.txt",
        RESOURCE_ROOT / "public_base_url.txt",
        SOURCE_ROOT / "public_base_url.txt",
    ]
    for candidate in candidates:
        try:
            if candidate.exists():
                value = normalize_base_url(candidate.read_text(encoding="utf-8").strip())
                if value:
                    return value
        except OSError:
            continue
    return ""


def resolve_phone_access_base_url() -> tuple[str, str]:
    if has_request_context():
        request_root = normalize_base_url(request.url_root)
        request_host = urlparse(request_root).hostname if request_root else ""
        if request_root and not is_local_host(request_host):
            return request_root, "Live public link"

    configured = get_configured_public_base_url()
    if configured:
        return configured, "ngrok phone link"

    return "", "Phone link unavailable"


def build_qr_data_uri(text: str) -> str:
    if not text or qrcode is None:
        return ""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(text)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def get_phone_access_context() -> dict[str, Any]:
    base_url, mode_label = resolve_phone_access_base_url()
    share_url = f"{base_url}/login?next=/" if base_url else ""
    enabled = bool(share_url)
    if share_url:
        setup_hint = "Scan the code from your phone to open the login page, then sign in and monitor the same device remotely."
        if "ngrok" in mode_label.lower():
            setup_hint = "Scan the code from your phone while ngrok is running. If your ngrok domain changes, update public_base_url.txt and Google OAuth redirect URIs."
    else:
        setup_hint = "Add your ngrok HTTPS URL to public_base_url.txt, then restart the app so the phone QR can point to your live tunnel."
    return {
        "enabled": enabled,
        "mode_label": mode_label,
        "share_url": share_url,
        "qr_data_uri": build_qr_data_uri(share_url) if enabled else "",
        "setup_hint": setup_hint,
        "config_path": str(get_write_data_file_path("public_base_url.txt")),
    }


def load_client_config(required_redirect_uri: str | None = None) -> dict[str, Any]:
    if not google_login_enabled():
        raise FileNotFoundError("Google OAuth client configuration is missing.")
    with CLIENT_CONFIG_FILE.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if "web" not in config:
        if "installed" in config:
            raise ValueError(
                "Use the Google OAuth web client JSON file for this app, not the installed client JSON."
            )
        raise ValueError("Google OAuth client configuration is invalid.")
    web_config = config.setdefault("web", {})
    redirect_uris = web_config.setdefault("redirect_uris", [])
    redirect_uri = (required_redirect_uri or "").strip()
    if redirect_uri and redirect_uri not in redirect_uris:
        redirect_uris.append(redirect_uri)
        origin = normalize_base_url(redirect_uri.rsplit("/auth/google/callback", 1)[0])
        if origin:
            javascript_origins = web_config.setdefault("javascript_origins", [])
            if origin not in javascript_origins:
                javascript_origins.append(origin)
        log.info("Added runtime OAuth redirect URI for current request host: %s", redirect_uri)
    return config


def normalize_auth_state(raw_state: dict[str, Any] | None) -> dict[str, Any]:
    state = dict(raw_state or {})
    if not state:
        return {}

    if google_login_enabled():
        client = load_client_config().get("web", {})
        state.setdefault("client_id", client.get("client_id", ""))
        state.setdefault("client_secret", client.get("client_secret", ""))
        state.setdefault("token_uri", client.get("token_uri", "https://oauth2.googleapis.com/token"))

    scopes = state.get("scopes")
    if not scopes:
        scope_value = state.get("scope", "")
        if isinstance(scope_value, str):
            scopes = [item for item in scope_value.split() if item]
        else:
            scopes = []
    elif isinstance(scopes, str):
        scopes = [item for item in scopes.split() if item]

    state["scopes"] = scopes or []
    if not state.get("scope") and state["scopes"]:
        state["scope"] = " ".join(state["scopes"])
    return state


def _dpapi_encrypt(plaintext: str) -> bytes:
    try:
        import win32crypt  # type: ignore

        return win32crypt.CryptProtectData(
            plaintext.encode("utf-8"),
            APP_DISPLAY_NAME,
            None,
            None,
            None,
            0,
        )
    except Exception:
        return plaintext.encode("utf-8")


def _dpapi_decrypt(ciphertext: bytes) -> str:
    try:
        import win32crypt  # type: ignore

        return win32crypt.CryptUnprotectData(ciphertext, None, None, None, 0)[1].decode("utf-8")
    except Exception:
        return ciphertext.decode("utf-8")


def _clear_saved_google_auth_state_files() -> None:
    seen: set[Path] = set()
    for candidate in [
        get_write_data_file_path("google_auth_state.bin"),
        get_read_data_file_path("google_auth_state.bin"),
        get_write_data_file_path("google_auth_state.json"),
        get_read_data_file_path("google_auth_state.json"),
    ]:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            try:
                candidate.unlink()
            except OSError:
                continue


def load_saved_google_auth_state() -> dict[str, Any]:
    try:
        encrypted_path = get_read_data_file_path("google_auth_state.bin")
        if encrypted_path.exists():
            return normalize_auth_state(json.loads(_dpapi_decrypt(encrypted_path.read_bytes())))
        legacy_path = get_read_data_file_path("google_auth_state.json")
        if legacy_path.exists():
            with legacy_path.open("r", encoding="utf-8") as handle:
                return normalize_auth_state(json.load(handle))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        log.warning("Could not read saved Google auth state.", exc_info=True)
        _clear_saved_google_auth_state_files()
    return {}


def save_google_auth_state(state: dict[str, Any]) -> None:
    normalized = normalize_auth_state(state)
    binary_path = get_write_data_file_path("google_auth_state.bin")
    ensure_parent_dir(binary_path)
    binary_path.write_bytes(_dpapi_encrypt(json.dumps(normalized, indent=2)))

    legacy_json_paths = {
        get_write_data_file_path("google_auth_state.json"),
        get_read_data_file_path("google_auth_state.json"),
    }
    for legacy_path in legacy_json_paths:
        if legacy_path.exists():
            legacy_path.unlink()


def clear_google_auth_state() -> None:
    _clear_saved_google_auth_state_files()


def get_delivery_email(auth_state: dict[str, Any] | None = None) -> str:
    state = auth_state or load_saved_google_auth_state()
    return str(state.get("email", "")).strip()


def get_current_user() -> dict[str, Any]:
    state = load_saved_google_auth_state()
    if not state:
        return {}
    return {
        "email": str(state.get("email", "")).strip(),
        "name": str(state.get("name", "")).strip(),
        "picture": str(state.get("picture", "")).strip(),
        "verified_email": bool(state.get("verified_email")),
    }


def build_credentials(refresh: bool = False) -> Credentials | None:
    state = load_saved_google_auth_state()
    if not state:
        log.debug("No saved Google auth state was found.")
        return None
    try:
        credentials = Credentials.from_authorized_user_info(state, SCOPES)
    except Exception:
        log.warning("Could not build Google credentials from saved state.", exc_info=True)
        clear_google_auth_state()
        return None

    if refresh and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(GoogleRequest())
        except Exception:
            log.warning("Google token refresh failed.", exc_info=True)
            clear_google_auth_state()
            return None
        updated = json.loads(credentials.to_json())
        updated.update(
            {
                "email": state.get("email", ""),
                "name": state.get("name", ""),
                "picture": state.get("picture", ""),
                "verified_email": state.get("verified_email", False),
            }
        )
        save_google_auth_state(updated)
        try:
            credentials = Credentials.from_authorized_user_info(normalize_auth_state(updated), SCOPES)
        except Exception:
            log.warning("Could not rebuild Google credentials after refresh.", exc_info=True)
            clear_google_auth_state()
            return None
    elif refresh and credentials.expired and not credentials.refresh_token:
        log.warning("Google credentials are expired and no refresh token is available.")
        clear_google_auth_state()
        return None
    return credentials


def gmail_auth_ready(auth_state: dict[str, Any] | None = None) -> bool:
    state = normalize_auth_state(auth_state or load_saved_google_auth_state())
    if not state or not get_delivery_email(state):
        return False
    scopes = state.get("scopes", [])
    if GMAIL_SCOPE not in scopes:
        return False
    try:
        credentials = Credentials.from_authorized_user_info(state, SCOPES)
    except Exception:
        return False
    if credentials.expired and not credentials.refresh_token:
        return False
    return True


def get_public_notification_error_message(message: str = "") -> str:
    text = str(message or "").strip().lower()
    if "sign in with google" in text or "google sign-in required" in text:
        return "Please sign in with Google to continue."
    if "permission" in text or "logout and sign in again" in text or "refresh email access" in text:
        return "Please sign in again to refresh email access."
    if "setup" in text or "getting ready" in text:
        return "Email delivery is getting ready. Try again in a moment."
    if "expired" in text or "revoked" in text:
        return "Your Google session needs to be refreshed. Please sign in again."
    return "We could not complete that action right now. Please try again."


def get_public_login_error_message(message: str = "") -> str:
    raw = str(message or "").strip()
    text = raw.lower()
    if not text:
        return ""
    if "access_denied" in text or "cancel" in text:
        return "Google sign-in was cancelled. Please try again."
    if "redirect_uri_mismatch" in text:
        return "Google OAuth redirect URI mismatch. Use the latest rebuilt app."
    if "use the google oauth web client json file" in text:
        return "Use the Google OAuth web client JSON file that contains 127.0.0.1:5000."
    if "missing redirect uri" in text:
        return raw
    if "state missing" in text or "state mismatch" in text or "csrf" in text:
        return "Google sign-in session expired. Close old app windows and try again."
    if "another device health monitor instance is already using port 5000" in text or "another device health monitor pro instance is already using port 5000" in text:
        return "Close the older Device Health Monitor app window first, then try again."
    if "insecure_transport" in text:
        return "Local OAuth transport was blocked. Use the latest rebuilt app."
    if "connectionerror" in text or "httpsconnectionpool" in text:
        return "Google sign-in could not reach Google servers. Check your internet connection and try again."
    if "expired" in text or "authorization code" in text:
        return "Google sign-in expired. Please try again."
    if len(raw) <= 180:
        return raw
    return "We could not finish Google sign-in. Please try again."


def load_notification_settings() -> dict[str, Any]:
    path = get_read_data_file_path("notification_settings.json")
    settings = deepcopy(DEFAULT_NOTIFICATION_SETTINGS)
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                settings.update(json.load(handle))
        except (OSError, json.JSONDecodeError):
            pass
    validate_notification_settings(settings)
    return settings


def save_notification_settings_file(settings: dict[str, Any]) -> None:
    path = get_write_data_file_path("notification_settings.json")
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)


def validate_notification_settings(settings: dict[str, Any]) -> None:
    settings["email_alerts_enabled"] = coerce_bool(settings.get("email_alerts_enabled"), True)
    settings["cpu_alerts_enabled"] = coerce_bool(settings.get("cpu_alerts_enabled"), True)
    settings["ram_alerts_enabled"] = coerce_bool(settings.get("ram_alerts_enabled"), True)
    settings["cpu_high"] = coerce_int(settings.get("cpu_high"), 90, 1, 100)
    settings["ram_high"] = coerce_int(settings.get("ram_high"), 90, 1, 100)
    settings["battery_low"] = coerce_int(settings.get("battery_low"), 20, 1, 100)
    settings["cooldown_minutes"] = coerce_int(settings.get("cooldown_minutes"), 60, 0, 1440)
    settings["alert_check_seconds"] = coerce_int(settings.get("alert_check_seconds"), 60, 5, 3600)
    prefix = str(settings.get("email_subject_prefix", "Device Health Alert")).strip()
    settings["email_subject_prefix"] = prefix or "Device Health Alert"


def get_notification_settings_snapshot() -> dict[str, Any]:
    with notification_settings_lock:
        return dict(notification_settings)


def update_notification_settings(payload: dict[str, Any]) -> dict[str, Any]:
    with notification_settings_lock:
        updated = dict(notification_settings)
        updated["email_alerts_enabled"] = coerce_bool(
            payload.get("email_alerts_enabled"), updated["email_alerts_enabled"]
        )
        updated["cpu_alerts_enabled"] = coerce_bool(
            payload.get("cpu_alerts_enabled"), updated["cpu_alerts_enabled"]
        )
        updated["ram_alerts_enabled"] = coerce_bool(
            payload.get("ram_alerts_enabled"), updated["ram_alerts_enabled"]
        )
        updated["cpu_high"] = coerce_int(payload.get("cpu_high"), updated["cpu_high"], 1, 100)
        updated["ram_high"] = coerce_int(payload.get("ram_high"), updated["ram_high"], 1, 100)
        updated["cooldown_minutes"] = coerce_int(
            payload.get("cooldown_minutes"), updated["cooldown_minutes"], 0, 1440
        )
        updated["alert_check_seconds"] = coerce_int(
            payload.get("alert_check_seconds"), updated["alert_check_seconds"], 5, 3600
        )
        validate_notification_settings(updated)
        notification_settings.clear()
        notification_settings.update(updated)
        save_notification_settings_file(notification_settings)

    for key in alert_cooldown:
        alert_cooldown[key] = 0.0
    return updated


def email_alerts_ready(settings: dict[str, Any] | None = None) -> bool:
    current = settings or get_notification_settings_snapshot()
    return bool(current.get("email_alerts_enabled")) and gmail_auth_ready()


def notification_channels(settings: dict[str, Any] | None = None) -> list[str]:
    current = settings or get_notification_settings_snapshot()
    return ["email"] if email_alerts_ready(current) else []


def build_public_notification_settings() -> dict[str, Any]:
    settings = get_notification_settings_snapshot()
    auth_state = load_saved_google_auth_state()
    delivery_email = get_delivery_email(auth_state)
    return {
        "email_alerts_enabled": settings["email_alerts_enabled"],
        "delivery_email": delivery_email,
        "signed_in_name": auth_state.get("name", ""),
        "signed_in_email": delivery_email,
        "google_logged_in": bool(auth_state),
        "gmail_ready": gmail_auth_ready(auth_state),
        "cpu_alerts_enabled": settings["cpu_alerts_enabled"],
        "ram_alerts_enabled": settings["ram_alerts_enabled"],
        "cpu_high": settings["cpu_high"],
        "ram_high": settings["ram_high"],
        "cooldown_minutes": settings["cooldown_minutes"],
        "alert_check_seconds": settings["alert_check_seconds"],
        "email_ready": email_alerts_ready(settings),
        "channels": notification_channels(settings),
        "monitor_running": bool(monitor_thread and monitor_thread.is_alive()),
    }


def make_login_required_response() -> tuple[Any, int]:
    return (
        jsonify(
            {
                "ok": False,
                "error": "Please sign in with Google to continue.",
                "login_url": url_for("login", desktop=1),
            }
        ),
        401,
    )


def format_gb(value: float) -> str:
    return f"{value / (1024 ** 3):.1f}"


def format_bytes_compact(value: int | float | None) -> str | None:
    try:
        size = float(value)
    except (TypeError, ValueError):
        return None
    if size < 0:
        return None
    if size >= 1024 ** 3:
        return f"{size / (1024 ** 3):.1f} GB"
    if size >= 1024 ** 2:
        return f"{size / (1024 ** 2):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{int(size)} B"


def format_seconds(value: int | None) -> str | None:
    try:
        seconds = int(float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None
    if seconds is None or seconds < 0 or seconds > 7 * 24 * 3600:
        return None
    if seconds < 60:
        return "Under 1 min"
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = max(0, round(remainder / 60))
    if minutes == 60:
        hours += 1
        minutes = 0
    if days:
        return f"{days} day {hours} hr" if hours else f"{days} day"
    if hours:
        return f"{hours} hr {minutes} min" if minutes else f"{hours} hr"
    return f"{max(1, minutes)} min"


def describe_battery_state(percent: float | None, plugged: bool | None) -> tuple[str | None, str | None]:
    if plugged is None:
        return None, None
    if plugged:
        if percent is not None and percent >= 99.5:
            return "Connected", "Fully charged"
        return "Connected", "Charging"
    return "Disconnected", "On battery"


def clean_html_text(value: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_capacity_mwh(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value)
    if not digits:
        return None
    return int(digits)


def format_capacity_mwh(value: int | None) -> str | None:
    if value is None:
        return None
    return f"{value:,} mWh"


def clean_system_identity_value(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    invalid_values = {
        "default string",
        "none",
        "not applicable",
        "system product name",
        "system manufacturer",
        "to be filled by o.e.m.",
        "to be filled by o.e.m",
    }
    if text.lower() in invalid_values:
        return None
    return text


def read_registry_text(key_path: str, value_name: str) -> str | None:
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            value, _value_type = winreg.QueryValueEx(key, value_name)
    except OSError:
        return None
    return clean_system_identity_value(str(value))


def read_powershell_system_identity() -> dict[str, str | None]:
    command = (
        "$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop; "
        "$prod = Get-CimInstance Win32_ComputerSystemProduct -ErrorAction Stop; "
        "[pscustomobject]@{ "
        "manufacturer = $cs.Manufacturer; "
        "model = $cs.Model; "
        "product = $prod.Name "
        "} | ConvertTo-Json -Compress"
    )
    try:
        result = run_hidden_subprocess(
            ["powershell", "-NoProfile", "-Command", command],
            timeout=8,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            return {}
        return {
            "manufacturer": clean_system_identity_value(payload.get("manufacturer")),
            "model": clean_system_identity_value(payload.get("model")),
            "product": clean_system_identity_value(payload.get("product")),
        }
    except Exception:
        return {}


def map_battery_chemistry(value: Any) -> str | None:
    mapping = {
        1: "Other",
        2: "Unknown",
        3: "Lead acid",
        4: "Nickel cadmium",
        5: "Nickel metal hydride",
        6: "Lithium-ion",
        7: "Zinc air",
        8: "Lithium polymer",
    }
    try:
        return mapping.get(int(value))
    except (TypeError, ValueError):
        return None


def describe_wmi_battery_status(value: Any) -> tuple[bool | None, str | None, str | None]:
    try:
        code = int(value)
    except (TypeError, ValueError):
        return None, None, None

    if code == 3:
        return True, "Connected", "Fully charged"
    if code in {6, 7, 8, 9, 11}:
        return True, "Connected", "Charging"
    if code in {4, 5}:
        return False, "Disconnected", "On battery"
    return None, None, None


def read_powershell_battery_details() -> dict[str, Any]:
    command = (
        "$bat = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select-Object -First 1; "
        "$static = Get-CimInstance -Namespace root\\wmi BatteryStaticData -ErrorAction SilentlyContinue | Select-Object -First 1; "
        "$full = Get-CimInstance -Namespace root\\wmi BatteryFullChargedCapacity -ErrorAction SilentlyContinue | Select-Object -First 1; "
        "$cycle = Get-CimInstance -Namespace root\\wmi BatteryCycleCount -ErrorAction SilentlyContinue | Select-Object -First 1; "
        "if ($null -eq $bat -and $null -eq $static -and $null -eq $full -and $null -eq $cycle) { '{}' } else { "
        "[pscustomobject]@{ "
        "name = if ($bat) { $bat.Name } elseif ($static) { $static.DeviceName } else { $null }; "
        "estimated_charge_remaining = if ($bat) { $bat.EstimatedChargeRemaining } else { $null }; "
        "estimated_runtime_minutes = if ($bat) { $bat.EstimatedRunTime } else { $null }; "
        "battery_status = if ($bat) { $bat.BatteryStatus } else { $null }; "
        "chemistry = if ($bat) { $bat.Chemistry } else { $null }; "
        "device_name = if ($static) { $static.DeviceName } else { $null }; "
        "manufacturer = if ($static) { $static.ManufactureName } else { $null }; "
        "serial_number = if ($static) { $static.SerialNumber } else { $null }; "
        "designed_capacity = if ($static) { $static.DesignedCapacity } else { $null }; "
        "design_voltage = if ($static) { $static.DesignedVoltage } else { $null }; "
        "full_charged_capacity = if ($full) { $full.FullChargedCapacity } else { $null }; "
        "cycle_count = if ($cycle) { $cycle.CycleCount } else { $null } "
        "} | ConvertTo-Json -Compress }"
    )
    try:
        result = run_hidden_subprocess(
            ["powershell", "-NoProfile", "-Command", command],
            timeout=8,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            return {}

        runtime_minutes = payload.get("estimated_runtime_minutes")
        try:
            runtime_seconds = int(float(runtime_minutes)) * 60 if runtime_minutes not in (None, "", 71582788) else None
        except (TypeError, ValueError):
            runtime_seconds = None

        estimated_charge_remaining = payload.get("estimated_charge_remaining")
        try:
            estimated_charge_remaining = round(float(estimated_charge_remaining), 1)
        except (TypeError, ValueError):
            estimated_charge_remaining = None

        designed_capacity = payload.get("designed_capacity")
        try:
            designed_capacity = int(float(designed_capacity))
        except (TypeError, ValueError):
            designed_capacity = None

        full_charged_capacity = payload.get("full_charged_capacity")
        try:
            full_charged_capacity = int(float(full_charged_capacity))
        except (TypeError, ValueError):
            full_charged_capacity = None

        design_voltage = payload.get("design_voltage")
        try:
            design_voltage = int(float(design_voltage))
        except (TypeError, ValueError):
            design_voltage = None

        cycle_count = payload.get("cycle_count")
        try:
            cycle_count = int(float(cycle_count))
        except (TypeError, ValueError):
            cycle_count = None

        health_percent = None
        wear_percent = None
        if designed_capacity and full_charged_capacity:
            health_percent = round((full_charged_capacity / designed_capacity) * 100, 1)
            wear_percent = round(max(0.0, 100.0 - health_percent), 1)

        plugged_hint, connection_status, state_label = describe_wmi_battery_status(payload.get("battery_status"))
        return {
            "name": clean_system_identity_value(payload.get("name")),
            "device_name": clean_system_identity_value(payload.get("device_name")),
            "manufacturer": clean_system_identity_value(payload.get("manufacturer")),
            "serial_number": clean_system_identity_value(payload.get("serial_number")),
            "estimated_charge_remaining": estimated_charge_remaining,
            "estimated_runtime_seconds": runtime_seconds,
            "plugged_hint": plugged_hint,
            "connection_status": connection_status,
            "state_label": state_label,
            "chemistry": map_battery_chemistry(payload.get("chemistry")),
            "designed_capacity_mwh": designed_capacity,
            "designed_capacity": format_capacity_mwh(designed_capacity),
            "full_charged_capacity_mwh": full_charged_capacity,
            "full_charged_capacity": format_capacity_mwh(full_charged_capacity),
            "design_voltage_mv": design_voltage,
            "cycle_count": cycle_count,
            "health_percent": health_percent,
            "wear_percent": wear_percent,
        }
    except Exception:
        return {}


def get_battery_live_details(force_refresh: bool = False) -> dict[str, Any]:
    with battery_live_details_lock:
        cached = dict(battery_live_details_cache.get("data") or {})
        timestamp = float(battery_live_details_cache.get("timestamp") or 0.0)
        if cached and not force_refresh and time.time() - timestamp < BATTERY_LIVE_DETAILS_CACHE_SECONDS:
            return cached

    details = read_powershell_battery_details()
    with battery_live_details_lock:
        battery_live_details_cache["timestamp"] = time.time()
        battery_live_details_cache["data"] = dict(details)
    return dict(details)


def get_windows_system_identity() -> dict[str, str | None]:
    global _system_identity_cache
    with _system_identity_lock:
        if _system_identity_cache is not None:
            return dict(_system_identity_cache)

        registry_sources = (
            r"HARDWARE\DESCRIPTION\System\BIOS",
            r"SYSTEM\CurrentControlSet\Control\SystemInformation",
        )
        manufacturer = None
        product = None
        model = None

        for key_path in registry_sources:
            manufacturer = manufacturer or read_registry_text(key_path, "SystemManufacturer")
            product = product or read_registry_text(key_path, "SystemProductName")
            model = model or read_registry_text(key_path, "BaseBoardProduct")

        if not product or not manufacturer:
            powershell_identity = read_powershell_system_identity()
            manufacturer = manufacturer or powershell_identity.get("manufacturer")
            model = model or powershell_identity.get("model")
            product = product or powershell_identity.get("product")

        display_parts: list[str] = []
        if manufacturer:
            display_parts.append(manufacturer)
        if product and product.lower() not in " ".join(display_parts).lower():
            display_parts.append(product)
        elif not display_parts and product:
            display_parts.append(product)
        elif model and model.lower() not in " ".join(display_parts).lower():
            display_parts.append(model)

        result = {
            "manufacturer": manufacturer,
            "product": product or model,
            "model": model,
            "display_name": " · ".join(display_parts) if display_parts else None,
        }
        if any(result.values()):
            _system_identity_cache = result
        return dict(result)


def extract_table_after_heading(report_html: str, heading: str) -> str:
    match = re.search(
        rf"<h2>\s*{re.escape(heading)}\s*</h2>.*?<table[^>]*>(.*?)</table>",
        report_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(1) if match else ""


def parse_html_table_rows(table_html: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.IGNORECASE | re.DOTALL):
        cells = [
            clean_html_text(cell_html)
            for cell_html in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.IGNORECASE | re.DOTALL)
        ]
        if cells:
            rows.append(cells)
    return rows


def extract_labeled_report_value(section_html: str, label: str) -> str | None:
    match = re.search(
        rf'<span class="label">\s*{re.escape(label)}\s*</span>\s*</td>\s*<td>(.*?)</td>',
        section_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    value = clean_html_text(match.group(1))
    return value or None


def build_empty_battery_report(error: str = "") -> dict[str, Any]:
    return {
        "available": False,
        "generated_at": None,
        "summary": {
            "name": None,
            "manufacturer": None,
            "serial_number": None,
            "chemistry": None,
            "design_capacity": None,
            "design_capacity_mwh": None,
            "full_charge_capacity": None,
            "full_charge_capacity_mwh": None,
            "cycle_count": None,
            "health_percent": None,
            "wear_percent": None,
        },
        "recent_usage": [],
        "capacity_history": [],
        "life_estimates": None,
        "error": error or "",
    }


def parse_battery_summary(report_html: str) -> dict[str, Any]:
    section_html = extract_table_after_heading(report_html, "Installed batteries")
    if not section_html:
        return build_empty_battery_report("Windows did not return installed battery details.")["summary"]

    design_capacity_mwh = parse_capacity_mwh(extract_labeled_report_value(section_html, "DESIGN CAPACITY"))
    full_charge_capacity_mwh = parse_capacity_mwh(
        extract_labeled_report_value(section_html, "FULL CHARGE CAPACITY")
    )
    cycle_raw = extract_labeled_report_value(section_html, "CYCLE COUNT")
    cycle_digits = re.sub(r"[^\d]", "", cycle_raw or "")
    health_percent = None
    wear_percent = None
    if design_capacity_mwh and full_charge_capacity_mwh:
        health_percent = round((full_charge_capacity_mwh / design_capacity_mwh) * 100, 1)
        wear_percent = round(max(0.0, 100.0 - health_percent), 1)

    return {
        "name": extract_labeled_report_value(section_html, "NAME"),
        "manufacturer": extract_labeled_report_value(section_html, "MANUFACTURER"),
        "serial_number": extract_labeled_report_value(section_html, "SERIAL NUMBER"),
        "chemistry": extract_labeled_report_value(section_html, "CHEMISTRY"),
        "design_capacity": format_capacity_mwh(design_capacity_mwh),
        "design_capacity_mwh": design_capacity_mwh,
        "full_charge_capacity": format_capacity_mwh(full_charge_capacity_mwh),
        "full_charge_capacity_mwh": full_charge_capacity_mwh,
        "cycle_count": int(cycle_digits) if cycle_digits else None,
        "health_percent": health_percent,
        "wear_percent": wear_percent,
    }


def parse_recent_battery_usage(report_html: str, limit: int = 10) -> list[dict[str, Any]]:
    table_html = extract_table_after_heading(report_html, "Recent usage")
    rows = parse_html_table_rows(table_html)
    entries: list[dict[str, Any]] = []
    for cells in rows[1:]:
        if len(cells) < 5:
            continue
        entries.append(
            {
                "start_time": cells[0],
                "state": cells[1],
                "source": cells[2],
                "charge_percent": cells[3],
                "remaining_capacity": cells[4],
            }
        )
    return entries[:limit]


def parse_capacity_history(report_html: str, limit: int = 10) -> list[dict[str, Any]]:
    table_html = extract_table_after_heading(report_html, "Battery capacity history")
    rows = parse_html_table_rows(table_html)
    history: list[dict[str, Any]] = []
    for cells in rows[1:]:
        if len(cells) < 3:
            continue
        full_charge_capacity_mwh = parse_capacity_mwh(cells[1])
        design_capacity_mwh = parse_capacity_mwh(cells[2])
        health_percent = None
        if full_charge_capacity_mwh and design_capacity_mwh:
            health_percent = round((full_charge_capacity_mwh / design_capacity_mwh) * 100, 1)
        history.append(
            {
                "period": cells[0],
                "full_charge_capacity": cells[1],
                "design_capacity": cells[2],
                "full_charge_capacity_mwh": full_charge_capacity_mwh,
                "design_capacity_mwh": design_capacity_mwh,
                "health_percent": health_percent,
            }
        )
    return history[-limit:]


def parse_battery_life_estimates(report_html: str) -> dict[str, Any] | None:
    table_html = extract_table_after_heading(report_html, "Battery life estimates")
    rows = parse_html_table_rows(table_html)
    candidates: list[list[str]] = []
    for cells in rows[2:]:
        if len(cells) < 6:
            continue
        metrics = [cells[1], cells[2], cells[4], cells[5]]
        if any(value and value != "-" for value in metrics):
            candidates.append(cells)
    if not candidates:
        return None

    latest = candidates[-1]
    return {
        "period": latest[0],
        "active_full_charge": latest[1],
        "connected_standby_full_charge": latest[2],
        "active_design_capacity": latest[4],
        "connected_standby_design_capacity": latest[5],
    }


def _run_battery_report_subprocess() -> dict[str, Any]:
    report_path = get_battery_report_file_path()
    ensure_parent_dir(report_path)
    try:
        result = run_hidden_subprocess(
            ["powercfg", "/batteryreport", "/output", str(report_path)],
            timeout=25,
        )
        if result.returncode != 0 or not report_path.exists():
            message = (result.stderr or result.stdout or "Battery report generation failed.").strip()
            data = build_empty_battery_report(message)
        else:
            report_html = report_path.read_text(encoding="utf-8", errors="ignore")
            summary = parse_battery_summary(report_html)
            data = {
                "available": any(
                    [
                        summary.get("name"),
                        summary.get("design_capacity_mwh"),
                        summary.get("full_charge_capacity_mwh"),
                    ]
                ),
                "generated_at": datetime.fromtimestamp(report_path.stat().st_mtime).isoformat(),
                "summary": summary,
                "recent_usage": parse_recent_battery_usage(report_html),
                "capacity_history": parse_capacity_history(report_html),
                "life_estimates": parse_battery_life_estimates(report_html),
                "error": "",
            }
    except Exception as exc:
        data = build_empty_battery_report(str(exc))

    with battery_report_lock:
        battery_report_cache["timestamp"] = time.time()
        battery_report_cache["data"] = deepcopy(data)
    return deepcopy(data)


def _refresh_battery_report_in_background() -> None:
    global _battery_refresh_in_progress
    try:
        _run_battery_report_subprocess()
    finally:
        with _battery_refresh_lock:
            _battery_refresh_in_progress = False


def get_battery_report_snapshot(force_refresh: bool = False) -> dict[str, Any]:
    global _battery_refresh_in_progress
    battery = psutil.sensors_battery()
    with battery_report_lock:
        cached = battery_report_cache.get("data")
        cached_at = float(battery_report_cache.get("timestamp") or 0.0)
        cache_fresh = bool(cached) and time.time() - cached_at < BATTERY_REPORT_CACHE_SECONDS
        if cache_fresh and not force_refresh:
            return deepcopy(cached)

    if not battery:
        empty = build_empty_battery_report("No battery detected on this device.")
        with battery_report_lock:
            battery_report_cache["timestamp"] = time.time()
            battery_report_cache["data"] = deepcopy(empty)
        return empty

    placeholder = build_empty_battery_report(BATTERY_REPORT_LOADING_MESSAGE)

    with _battery_refresh_lock:
        already_running = _battery_refresh_in_progress
        should_start_refresh = not already_running
        if should_start_refresh:
            _battery_refresh_in_progress = True

    if force_refresh and not already_running:
        try:
            return _run_battery_report_subprocess()
        finally:
            with _battery_refresh_lock:
                _battery_refresh_in_progress = False

    if should_start_refresh:
        threading.Thread(target=_refresh_battery_report_in_background, name="battery-report-refresh", daemon=True).start()

    if cached:
        with battery_report_lock:
            return deepcopy(battery_report_cache["data"])
    with battery_report_lock:
        pending = deepcopy(battery_report_cache["data"])
    return pending if pending else placeholder


def build_battery_report_placeholder_html(message: str) -> str:
    safe_message = html_lib.escape(message or "Battery report is not available on this device.")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Battery Report</title>
    <style>
        body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 24px;
            font-family: "Segoe UI", system-ui, sans-serif;
            background: linear-gradient(160deg, #08111f 0%, #102036 44%, #111827 100%);
            color: #f8fafc;
        }}
        .card {{
            width: min(720px, 100%);
            padding: 28px;
            border-radius: 24px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            background: rgba(15, 23, 42, 0.9);
            box-shadow: 0 24px 60px rgba(2, 6, 23, 0.42);
        }}
        h1 {{ margin: 0 0 12px; font-size: 2rem; }}
        p {{ margin: 0; color: #cbd5e1; line-height: 1.7; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Battery Report Unavailable</h1>
        <p>{safe_message}</p>
    </div>
</body>
</html>"""


def get_battery_snapshot(
    report: dict[str, Any] | None = None,
    live_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_summary = (report or {}).get("summary", {})
    live_details = dict(live_details or get_battery_live_details())
    summary_health = report_summary.get("health_percent", live_details.get("health_percent"))
    summary_design_capacity = report_summary.get("design_capacity") or live_details.get("designed_capacity")
    summary_full_capacity = report_summary.get("full_charge_capacity") or live_details.get("full_charged_capacity")
    summary_cycle_count = report_summary.get("cycle_count")
    if summary_cycle_count is None:
        summary_cycle_count = live_details.get("cycle_count")
    summary_wear = report_summary.get("wear_percent", live_details.get("wear_percent"))
    summary_chemistry = report_summary.get("chemistry") or live_details.get("chemistry")
    summary_manufacturer = report_summary.get("manufacturer") or live_details.get("manufacturer")
    summary_serial_number = report_summary.get("serial_number") or live_details.get("serial_number")
    battery = psutil.sensors_battery()
    if not battery:
        percent = live_details.get("estimated_charge_remaining")
        plugged = live_details.get("plugged_hint")
        connection_status = live_details.get("connection_status")
        state_label = live_details.get("state_label")
        secsleft = live_details.get("estimated_runtime_seconds")
        time_remaining = format_seconds(secsleft) if plugged is False else None
        time_to_full = None
        time_status = f"Estimated {time_remaining} left" if time_remaining else None
        status_parts = [part for part in [connection_status, state_label] if part]
        if time_status:
            status_parts.append(time_status)
        return {
            "percent": percent,
            "plugged": plugged,
            "secsleft": secsleft,
            "time_remaining": time_remaining,
            "time_to_full": time_to_full,
            "health": summary_health,
            "design_capacity": summary_design_capacity,
            "full_capacity": summary_full_capacity,
            "cycle_count": summary_cycle_count,
            "wear": summary_wear,
            "chemistry": summary_chemistry,
            "manufacturer": summary_manufacturer,
            "serial_number": summary_serial_number,
            "connection_status": connection_status,
            "state_label": state_label,
            "time_status": time_status,
            "status_text": " · ".join(status_parts) if status_parts else "Battery not detected",
        }

    secsleft = battery.secsleft
    if secsleft in {psutil.POWER_TIME_UNKNOWN, psutil.POWER_TIME_UNLIMITED}:
        secsleft = live_details.get("estimated_runtime_seconds")

    percent = round(float(battery.percent), 1)
    if percent < 0 or percent > 100:
        fallback_percent = live_details.get("estimated_charge_remaining")
        percent = round(float(fallback_percent), 1) if fallback_percent is not None else 0.0
    plugged = bool(battery.power_plugged)
    connection_status, state_label = describe_battery_state(percent, plugged)
    time_remaining = None if plugged else format_seconds(secsleft)
    time_to_full = format_seconds(secsleft) if plugged else None
    time_status = None

    status_parts = [part for part in [connection_status, state_label] if part]
    if plugged and time_to_full and state_label != "Fully charged":
        time_status = f"Estimated {time_to_full} to full"
        status_parts.append(time_status)
    elif not plugged and time_remaining:
        time_status = f"Estimated {time_remaining} left"
        status_parts.append(time_status)
    elif plugged and state_label != "Fully charged":
        time_status = "Windows did not provide a reliable charge estimate"
    elif not plugged:
        time_status = "Windows did not provide a reliable battery estimate"

    return {
        "percent": percent,
        "plugged": plugged,
        "secsleft": secsleft,
        "time_remaining": time_remaining,
        "time_to_full": time_to_full,
        "health": summary_health,
        "design_capacity": summary_design_capacity,
        "full_capacity": summary_full_capacity,
        "cycle_count": summary_cycle_count,
        "wear": summary_wear,
        "chemistry": summary_chemistry,
        "manufacturer": summary_manufacturer,
        "serial_number": summary_serial_number,
        "connection_status": connection_status,
        "state_label": state_label,
        "time_status": time_status,
        "status_text": " · ".join(status_parts) if status_parts else "Battery status unavailable",
    }


def get_temperature_snapshot() -> list[dict[str, Any]]:
    temperatures: list[dict[str, Any]] = []
    try:
        groups = psutil.sensors_temperatures()
    except (AttributeError, NotImplementedError):
        return temperatures
    for group_name, items in groups.items():
        for item in items:
            label = item.label or group_name or "Sensor"
            if item.current is None:
                continue
            temperatures.append({"label": label, "current": round(float(item.current), 1)})
    return temperatures


def get_fan_snapshot() -> list[dict[str, Any]]:
    fans: list[dict[str, Any]] = []
    try:
        groups = psutil.sensors_fans()
    except (AttributeError, NotImplementedError):
        return fans
    for group_name, items in groups.items():
        for item in items:
            label = item.label or group_name or "Fan"
            if item.current is None:
                continue
            fans.append({"label": label, "speed": int(item.current)})
    return fans


def get_network_speed_snapshot() -> dict[str, float]:
    counters = psutil.net_io_counters()
    now = time.time()
    with _network_state.lock:
        if _network_state.totals is not None and _network_state.timestamp:
            elapsed = max(now - _network_state.timestamp, 0.001)
            previous_sent, previous_recv = _network_state.totals
            upload_speed = max(0.0, (counters.bytes_sent - previous_sent) / 1024 / elapsed)
            download_speed = max(0.0, (counters.bytes_recv - previous_recv) / 1024 / elapsed)
        else:
            upload_speed = 0.0
            download_speed = 0.0

        _network_state.upload_history.append(upload_speed)
        _network_state.download_history.append(download_speed)
        _network_state.totals = (counters.bytes_sent, counters.bytes_recv)
        _network_state.timestamp = now

        smoothed_upload = sum(_network_state.upload_history) / len(_network_state.upload_history)
        smoothed_download = sum(_network_state.download_history) / len(_network_state.download_history)

    return {
        "upload_speed": round(smoothed_upload, 1),
        "download_speed": round(smoothed_download, 1),
    }


def _coerce_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not number == number:
        return None
    return number


def _coerce_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _gpu_stable_order_key(item: dict[str, Any]) -> tuple[int, int, str]:
    index = _coerce_int(item.get("index"))
    if index is None:
        index = _coerce_int(item.get("gpu_index"))
    if index is None:
        index = 10_000
    name = str(item.get("name") or "")
    return (index, 0 if "intel" in name.lower() else 1, name.lower())


def read_nvidia_smi_snapshot() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return {}

    gpu_query = (
        "index,name,utilization.gpu,utilization.memory,memory.used,memory.total,"
        "temperature.gpu,power.draw,clocks.current.graphics"
    )
    try:
        gpu_result = run_hidden_subprocess(
            [
                executable,
                f"--query-gpu={gpu_query}",
                "--format=csv,noheader,nounits",
            ],
            timeout=8,
        )
        if gpu_result.returncode != 0 or not gpu_result.stdout.strip():
            return {}
    except Exception:
        return {}

    adapters: list[dict[str, Any]] = []
    try:
        reader = csv.reader(gpu_result.stdout.splitlines())
        for row in reader:
            if not row:
                continue
            values = [item.strip() for item in row]
            if len(values) < 9:
                continue
            memory_used_mb = _coerce_float(values[4])
            memory_total_mb = _coerce_float(values[5])
            memory_percent = None
            if memory_used_mb is not None and memory_total_mb and memory_total_mb > 0:
                memory_percent = round(min(100.0, max(0.0, (memory_used_mb / memory_total_mb) * 100.0)), 1)

            adapters.append(
                {
                    "gpu_index": _coerce_int(values[0]),
                    "name": clean_system_identity_value(values[1]) or "NVIDIA GPU",
                    "utilization_percent": round(min(100.0, max(0.0, _coerce_float(values[2]) or 0.0)), 1),
                    "memory_utilization_percent": _coerce_float(values[3]),
                    "memory_used_mb": memory_used_mb,
                    "memory_total_mb": memory_total_mb,
                    "dedicated_usage_bytes": int(memory_used_mb * 1024 * 1024) if memory_used_mb is not None else None,
                    "adapter_ram_bytes": int(memory_total_mb * 1024 * 1024) if memory_total_mb is not None else None,
                    "memory_percent": memory_percent,
                    "temperature_c": _coerce_float(values[6]),
                    "power_draw_w": _coerce_float(values[7]),
                    "graphics_clock_mhz": _coerce_float(values[8]),
                    "source": "nvidia-smi",
                }
            )
    except Exception:
        return {}

    if not adapters:
        return {}

    adapters.sort(key=_gpu_stable_order_key)
    primary = max(adapters, key=lambda item: item.get("utilization_percent") or 0.0)
    return {
        "available": True,
        "source": "nvidia-smi",
        "percent": primary.get("utilization_percent"),
        "primary_index": primary.get("gpu_index"),
        "primary_name": primary.get("name"),
        "adapters": adapters,
        "top_processes": [],
    }


def read_powershell_gpu_snapshot() -> dict[str, Any]:
    command = r"""
$controllers = @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Where-Object { $_.Name });
$engines = @(Get-CimInstance -Namespace root\CIMV2 -ClassName Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction SilentlyContinue);
$memories = @(Get-CimInstance -Namespace root\CIMV2 -ClassName Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction SilentlyContinue);

$adapterUtil = @{}
$adapterMemory = @{}

foreach ($engine in $engines) {
    $name = [string]$engine.Name
    if ([string]::IsNullOrWhiteSpace($name)) { continue }

    try { $util = [double]$engine.UtilizationPercentage } catch { continue }
    if ($util -lt 0) { continue }

    $physMatch = [regex]::Match($name, 'phys_(\d+)')
    $adapterIndex = if ($physMatch.Success) { [int]$physMatch.Groups[1].Value } else { 0 }
    if (-not $adapterUtil.ContainsKey($adapterIndex) -or $util -gt [double]$adapterUtil[$adapterIndex]) {
        $adapterUtil[$adapterIndex] = $util
    }
}

foreach ($memory in $memories) {
    $name = [string]$memory.Name
    if ([string]::IsNullOrWhiteSpace($name)) { continue }

    $physMatch = [regex]::Match($name, 'phys_(\d+)')
    $adapterIndex = if ($physMatch.Success) { [int]$physMatch.Groups[1].Value } else { 0 }
    try { $dedicated = [int64]$memory.DedicatedUsage } catch { $dedicated = 0 }
    try { $shared = [int64]$memory.SharedUsage } catch { $shared = 0 }

    if (-not $adapterMemory.ContainsKey($adapterIndex)) {
        $adapterMemory[$adapterIndex] = [ordered]@{
            dedicated_usage_bytes = 0
            shared_usage_bytes = 0
        }
    }

    if ($dedicated -gt [int64]$adapterMemory[$adapterIndex].dedicated_usage_bytes) {
        $adapterMemory[$adapterIndex].dedicated_usage_bytes = $dedicated
    }
    if ($shared -gt [int64]$adapterMemory[$adapterIndex].shared_usage_bytes) {
        $adapterMemory[$adapterIndex].shared_usage_bytes = $shared
    }
}

$adapters = @()
for ($i = 0; $i -lt $controllers.Count; $i++) {
    $controller = $controllers[$i]
    $memory = $adapterMemory[$i]
    try { $adapterRam = [int64]$controller.AdapterRAM } catch { $adapterRam = $null }
    $adapters += [pscustomobject]@{
        index = $i
        name = $controller.Name
        driver_version = $controller.DriverVersion
        video_processor = $controller.VideoProcessor
        adapter_ram_bytes = $adapterRam
        utilization_percent = if ($adapterUtil.ContainsKey($i)) { [math]::Round([double]$adapterUtil[$i], 1) } else { 0.0 }
        dedicated_usage_bytes = if ($null -ne $memory) { [int64]$memory.dedicated_usage_bytes } else { $null }
        shared_usage_bytes = if ($null -ne $memory) { [int64]$memory.shared_usage_bytes } else { $null }
    }
}

$primary = $adapters | Sort-Object utilization_percent -Descending | Select-Object -First 1

[pscustomobject]@{
    available = ($adapters.Count -gt 0)
    percent = if ($null -ne $primary) { $primary.utilization_percent } else { 0.0 }
    primary_index = if ($null -ne $primary) { $primary.index } else { $null }
    primary_name = if ($null -ne $primary) { $primary.name } else { $null }
    adapters = @($adapters)
    top_processes = @()
} | ConvertTo-Json -Compress -Depth 5
""".strip()

    try:
        result = run_hidden_subprocess(["powershell", "-NoProfile", "-Command", command], timeout=10)
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            return {}

        adapters: list[dict[str, Any]] = []
        raw_adapters = payload.get("adapters")
        if isinstance(raw_adapters, dict):
            raw_adapters = [raw_adapters]
        for item in raw_adapters or []:
            if not isinstance(item, dict):
                continue
            adapter_ram_bytes = _coerce_int(item.get("adapter_ram_bytes"))
            dedicated_usage_bytes = _coerce_int(item.get("dedicated_usage_bytes"))
            shared_usage_bytes = _coerce_int(item.get("shared_usage_bytes"))
            utilization_percent = _coerce_float(item.get("utilization_percent")) or 0.0
            memory_percent = None
            if adapter_ram_bytes and dedicated_usage_bytes is not None and adapter_ram_bytes > 0:
                memory_percent = round(min(100.0, max(0.0, (dedicated_usage_bytes / adapter_ram_bytes) * 100.0)), 1)

            adapters.append(
                {
                    "index": _coerce_int(item.get("index")),
                    "name": clean_system_identity_value(item.get("name")) or "Unknown GPU",
                    "driver_version": clean_system_identity_value(item.get("driver_version")),
                    "video_processor": clean_system_identity_value(item.get("video_processor")),
                    "adapter_ram_bytes": adapter_ram_bytes,
                    "adapter_ram": format_bytes_compact(adapter_ram_bytes),
                    "utilization_percent": round(min(100.0, max(0.0, utilization_percent)), 1),
                    "dedicated_usage_bytes": dedicated_usage_bytes,
                    "dedicated_usage": format_bytes_compact(dedicated_usage_bytes),
                    "shared_usage_bytes": shared_usage_bytes,
                    "shared_usage": format_bytes_compact(shared_usage_bytes),
                    "memory_percent": memory_percent,
                }
            )

        primary_index = _coerce_int(payload.get("primary_index"))
        primary_name = clean_system_identity_value(payload.get("primary_name"))
        primary_adapter = None
        for adapter in adapters:
            if primary_index is not None and adapter.get("index") == primary_index:
                primary_adapter = adapter
                break
        if primary_adapter is None and adapters:
            primary_adapter = max(adapters, key=lambda item: item.get("utilization_percent") or 0.0)

        overall_percent = _coerce_float(payload.get("percent"))
        if overall_percent is None:
            overall_percent = float(primary_adapter.get("utilization_percent", 0.0)) if primary_adapter else 0.0

        return {
            "available": bool(adapters),
            "percent": round(min(100.0, max(0.0, overall_percent)), 1),
            "primary_index": primary_adapter.get("index") if primary_adapter else primary_index,
            "primary_name": primary_adapter.get("name") if primary_adapter else primary_name,
            "adapter_count": len(adapters),
            "adapters": adapters,
            "top_processes": [],
        }
    except Exception:
        return {}


def get_gpu_snapshot(force_refresh: bool = False) -> dict[str, Any]:
    with gpu_snapshot_lock:
        cached = dict(gpu_snapshot_cache.get("data") or {})
        timestamp = float(gpu_snapshot_cache.get("timestamp") or 0.0)
        if cached and not force_refresh and time.time() - timestamp < GPU_CACHE_SECONDS:
            return cached

    windows_snapshot = read_powershell_gpu_snapshot()
    nvidia_snapshot = read_nvidia_smi_snapshot()

    snapshot = dict(windows_snapshot or {})
    if not snapshot:
        snapshot = {
            "available": False,
            "percent": None,
            "primary_index": None,
            "primary_name": None,
            "adapter_count": 0,
            "adapters": [],
            "top_processes": [],
            "source": "windows",
        }

    adapters = [dict(item) for item in snapshot.get("adapters") or [] if isinstance(item, dict)]

    if nvidia_snapshot.get("available"):
        nvidia_adapters = [dict(item) for item in nvidia_snapshot.get("adapters") or [] if isinstance(item, dict)]
        for vendor_adapter in nvidia_adapters:
            matched = None
            vendor_name = str(vendor_adapter.get("name") or "").lower()
            for adapter in adapters:
                current_name = str(adapter.get("name") or "").lower()
                if "nvidia" in current_name or (vendor_name and vendor_name in current_name):
                    matched = adapter
                    break
            if matched is None:
                matched = {
                    "index": len(adapters),
                    "name": vendor_adapter.get("name") or "NVIDIA GPU",
                    "driver_version": None,
                    "video_processor": vendor_adapter.get("name"),
                    "shared_usage_bytes": None,
                    "shared_usage": None,
                }
                adapters.append(matched)

            matched["name"] = vendor_adapter.get("name") or matched.get("name")
            matched["video_processor"] = vendor_adapter.get("name") or matched.get("video_processor")
            matched["utilization_percent"] = vendor_adapter.get("utilization_percent")
            matched["dedicated_usage_bytes"] = vendor_adapter.get("dedicated_usage_bytes")
            matched["dedicated_usage"] = format_bytes_compact(vendor_adapter.get("dedicated_usage_bytes"))
            matched["adapter_ram_bytes"] = vendor_adapter.get("adapter_ram_bytes")
            matched["adapter_ram"] = format_bytes_compact(vendor_adapter.get("adapter_ram_bytes"))
            matched["memory_percent"] = vendor_adapter.get("memory_percent")
            matched["temperature_c"] = vendor_adapter.get("temperature_c")
            matched["power_draw_w"] = vendor_adapter.get("power_draw_w")
            matched["graphics_clock_mhz"] = vendor_adapter.get("graphics_clock_mhz")
            matched["source"] = "nvidia-smi"

        snapshot["source"] = "nvidia-smi"
        snapshot["top_processes"] = []

    adapters.sort(key=_gpu_stable_order_key)
    snapshot["adapters"] = adapters
    snapshot["adapter_count"] = len(adapters)
    snapshot["available"] = bool(adapters)

    primary_adapter = max(adapters, key=lambda item: item.get("utilization_percent") or 0.0) if adapters else None
    snapshot["percent"] = primary_adapter.get("utilization_percent") if primary_adapter else None
    snapshot["primary_index"] = (_coerce_int(primary_adapter.get("index")) if primary_adapter else None)
    if snapshot["primary_index"] is None and primary_adapter:
        snapshot["primary_index"] = _coerce_int(primary_adapter.get("gpu_index"))
    snapshot["primary_name"] = primary_adapter.get("name") if primary_adapter else None

    with gpu_snapshot_lock:
        gpu_snapshot_cache["timestamp"] = time.time()
        gpu_snapshot_cache["data"] = dict(snapshot)
    return dict(snapshot)


def record_cpu_sample(sample: float) -> float:
    normalized = max(0.0, min(100.0, float(sample)))
    with _cpu_state.lock:
        _cpu_state.latest = normalized
        _cpu_state.has_sample = True
        _cpu_state.history.append(normalized)
        averaged = sum(_cpu_state.history) / len(_cpu_state.history)
    return round(averaged, 1)


def get_stable_cpu_percent() -> float:
    with _cpu_state.lock:
        if _cpu_state.has_sample and _cpu_state.history:
            averaged = sum(_cpu_state.history) / len(_cpu_state.history)
            return round(averaged, 1)

    # Cold-start fallback before the background sampler has produced its first value.
    sample = float(psutil.cpu_percent(interval=0.6))
    return record_cpu_sample(sample)


def build_system_snapshot() -> dict[str, Any]:
    now = datetime.now()
    hostname = socket.gethostname()
    system_drive = os.environ.get("SystemDrive", "C:")
    disk_root = f"{system_drive}\\"
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage(disk_root)
    cpu_percent = get_stable_cpu_percent()
    battery_report = get_battery_report_snapshot()
    battery_live_details = get_battery_live_details()
    battery_snapshot = get_battery_snapshot(battery_report, battery_live_details)
    gpu_snapshot = get_gpu_snapshot()
    system_identity = get_windows_system_identity()

    return {
        "timestamp": now.isoformat(),
        "timestamp_ms": int(now.timestamp() * 1000),
        "system": {
            "product": system_identity.get("product") or hostname,
            "manufacturer": system_identity.get("manufacturer"),
            "display_name": system_identity.get("display_name") or hostname,
            "hostname": hostname,
            "username": getpass.getuser(),
            "os": f"{platform.system()} {platform.release()}",
        },
        "cpu": {
            "percent": cpu_percent,
            "cores": psutil.cpu_count(logical=True) or 0,
        },
        "ram": {
            "percent": round(ram.percent, 1),
            "used": format_gb(float(ram.used)),
            "total": format_gb(float(ram.total)),
        },
        "disk": {
            "main": {
                "percent": round(disk.percent, 1),
                "used": format_gb(float(disk.used)),
                "total": format_gb(float(disk.total)),
            }
        },
        "battery": battery_snapshot,
        "battery_wmi": battery_live_details,
        "battery_report": battery_report,
        "gpu": gpu_snapshot,
        "network": get_network_speed_snapshot(),
        "temperatures": get_temperature_snapshot(),
        "fans": get_fan_snapshot(),
    }


def refresh_system_snapshot(force_refresh: bool = False) -> dict[str, Any]:
    with _system_snapshot_state.lock:
        cached = deepcopy(_system_snapshot_state.data)
        cached_at = float(_system_snapshot_state.timestamp or 0.0)
        if cached and not force_refresh and time.time() - cached_at < SYSTEM_SNAPSHOT_STALE_SECONDS:
            return cached

    with _system_snapshot_refresh_lock:
        with _system_snapshot_state.lock:
            cached = deepcopy(_system_snapshot_state.data)
            cached_at = float(_system_snapshot_state.timestamp or 0.0)
            if cached and not force_refresh and time.time() - cached_at < SYSTEM_SNAPSHOT_STALE_SECONDS:
                return cached

        snapshot = build_system_snapshot()
        with _system_snapshot_state.lock:
            _system_snapshot_state.timestamp = time.time()
            _system_snapshot_state.data = deepcopy(snapshot)
        return deepcopy(snapshot)


def get_system_snapshot(force_refresh: bool = False) -> dict[str, Any]:
    return refresh_system_snapshot(force_refresh=force_refresh)


def get_google_user_profile(credentials: Credentials) -> dict[str, Any]:
    service = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
    profile = service.userinfo().get().execute()
    return {
        "email": str(profile.get("email", "")).strip(),
        "name": str(profile.get("name", "")).strip(),
        "picture": str(profile.get("picture", "")).strip(),
        "verified_email": bool(profile.get("verified_email")),
    }


def send_email_via_gmail(subject: str, body: str) -> None:
    credentials = build_credentials(refresh=True)
    if credentials is None:
        raise RuntimeError("Please sign in with Google to continue.")

    auth_state = load_saved_google_auth_state()
    if GMAIL_SCOPE not in auth_state.get("scopes", []):
        raise RuntimeError("Please sign in again to refresh email access.")

    delivery_email = get_delivery_email(auth_state)
    if not delivery_email:
        raise RuntimeError("Please sign in with Google to continue.")

    message = MIMEText(body, "plain", "utf-8")
    message["to"] = delivery_email
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def send_alert(title: str, body: str, settings: dict[str, Any] | None = None) -> bool:
    current = settings or get_notification_settings_snapshot()
    if not email_alerts_ready(current):
        raise RuntimeError("Please sign in again to refresh email access.")

    prefix = current.get("email_subject_prefix", "Device Health Alert")
    subject = f"{prefix}: {title}"
    send_email_via_gmail(subject, body)
    return True


def monitor_alerts_loop() -> None:
    while not monitor_stop_event.is_set():
        settings = get_notification_settings_snapshot()
        wait_seconds = max(settings.get("alert_check_seconds", 60), 5)
        cooldown_seconds = max(settings.get("cooldown_minutes", 0), 0) * 60

        if email_alerts_ready(settings):
            cpu_percent = get_stable_cpu_percent()
            ram_percent = round(psutil.virtual_memory().percent, 1)
            now = time.time()

            if (
                settings["cpu_alerts_enabled"]
                and cpu_percent >= settings["cpu_high"]
                and now - alert_cooldown["cpu"] > cooldown_seconds
            ):
                try:
                    if send_alert(
                        "High CPU",
                        f"CPU usage is high: {cpu_percent}% (threshold {settings['cpu_high']}%)",
                        settings=settings,
                    ):
                        alert_cooldown["cpu"] = now
                        log.info("Automatic CPU alert sent at %s%%", cpu_percent)
                except Exception as exc:
                    log.warning(
                        "Automatic CPU alert trigger met at %s%% but the email could not be sent: %s",
                        cpu_percent,
                        exc,
                    )

            if (
                settings["ram_alerts_enabled"]
                and ram_percent >= settings["ram_high"]
                and now - alert_cooldown["ram"] > cooldown_seconds
            ):
                try:
                    if send_alert(
                        "High RAM",
                        f"RAM usage is high: {ram_percent}% (threshold {settings['ram_high']}%)",
                        settings=settings,
                    ):
                        alert_cooldown["ram"] = now
                        log.info("Automatic RAM alert sent at %s%%", ram_percent)
                except Exception as exc:
                    log.warning(
                        "Automatic RAM alert trigger met at %s%% but the email could not be sent: %s",
                        ram_percent,
                        exc,
                    )

        monitor_stop_event.wait(wait_seconds)


def _safe_monitor_alerts_loop() -> None:
    try:
        monitor_alerts_loop()
    except Exception:
        log.exception("Alert monitor thread crashed.")


def cpu_sampler_loop() -> None:
    log.info("CPU sampler started.")
    while not monitor_stop_event.is_set():
        sample = float(psutil.cpu_percent(interval=1.0))
        averaged = record_cpu_sample(sample)
        log.debug("CPU sampler updated raw=%s averaged=%s", sample, averaged)
    log.info("CPU sampler stopped.")


def _safe_cpu_sampler_loop() -> None:
    try:
        cpu_sampler_loop()
    except Exception:
        log.exception("CPU sampler thread crashed.")


def system_snapshot_loop() -> None:
    log.info("System snapshot sampler started.")
    while not monitor_stop_event.is_set():
        cycle_started = time.monotonic()
        refresh_system_snapshot(force_refresh=True)
        elapsed = time.monotonic() - cycle_started
        wait_seconds = max(0.25, SYSTEM_SNAPSHOT_INTERVAL_SECONDS - elapsed)
        monitor_stop_event.wait(wait_seconds)
    log.info("System snapshot sampler stopped.")


def _safe_system_snapshot_loop() -> None:
    try:
        system_snapshot_loop()
    except Exception:
        log.exception("System snapshot sampler crashed.")


def _monitor_supervisor_loop() -> None:
    global monitor_thread, cpu_sampler_thread, system_snapshot_thread
    while not monitor_stop_event.is_set():
        if cpu_sampler_thread is None or not cpu_sampler_thread.is_alive():
            log.warning("CPU sampler is not running, starting or restarting it.")
            cpu_sampler_thread = threading.Thread(target=_safe_cpu_sampler_loop, daemon=True, name="cpu-sampler")
            cpu_sampler_thread.start()
        if system_snapshot_thread is None or not system_snapshot_thread.is_alive():
            log.warning("System snapshot sampler is not running, starting or restarting it.")
            system_snapshot_thread = threading.Thread(
                target=_safe_system_snapshot_loop,
                daemon=True,
                name="system-snapshot-sampler",
            )
            system_snapshot_thread.start()
        if monitor_thread is None or not monitor_thread.is_alive():
            log.warning("Alert monitor is not running, starting or restarting it.")
            monitor_thread = threading.Thread(target=_safe_monitor_alerts_loop, daemon=True, name="alert-monitor")
            monitor_thread.start()
        monitor_stop_event.wait(5)


def start_background_services() -> None:
    global background_services_started, monitor_supervisor_thread
    with background_lock:
        if background_services_started and monitor_supervisor_thread and monitor_supervisor_thread.is_alive():
            return
        monitor_stop_event.clear()
        should_prime_cpu = False
        with _cpu_state.lock:
            should_prime_cpu = not _cpu_state.has_sample
        if should_prime_cpu:
            record_cpu_sample(psutil.cpu_percent(interval=0.4))
        threading.Thread(
            target=lambda: refresh_system_snapshot(force_refresh=True),
            daemon=True,
            name="system-snapshot-primer",
        ).start()
        monitor_supervisor_thread = threading.Thread(
            target=_monitor_supervisor_loop,
            daemon=True,
            name="alert-monitor-supervisor",
        )
        monitor_supervisor_thread.start()
        background_services_started = True
        log.info("Background services started.")


def stop_background_services() -> None:
    global background_services_started, monitor_thread, monitor_supervisor_thread, cpu_sampler_thread, system_snapshot_thread
    monitor_stop_event.set()
    monitor_thread = None
    monitor_supervisor_thread = None
    cpu_sampler_thread = None
    system_snapshot_thread = None
    background_services_started = False


@app.route("/")
def home():
    if not get_current_user():
        return redirect(url_for("login", desktop=1))
    return render_template(
        "index.html",
        current_user=get_current_user(),
        phone_access=get_phone_access_context(),
    )


@app.route("/login")
def login():
    if not google_login_enabled():
        return render_template(
            "login.html",
            oauth_enabled=False,
            error="Google OAuth setup is missing. Add google_oauth_client.json and rebuild the app.",
            next_path="/",
            desktop_mode=coerce_bool(request.args.get("desktop"), False),
            desktop_login_url="#",
            phone_access=get_phone_access_context(),
        )
    if get_current_user():
        return redirect(url_for("home"))

    desktop_mode = coerce_bool(request.args.get("desktop"), False)
    next_path = get_safe_next_path(request.args.get("next", "/"))
    desktop_login_url = url_for("auth_google_start", next=url_for("auth_desktop_complete"))
    return render_template(
        "login.html",
        oauth_enabled=True,
        error=get_public_login_error_message(request.args.get("error", "").strip()),
        next_path=next_path,
        desktop_mode=desktop_mode,
        desktop_login_url=desktop_login_url,
        phone_access=get_phone_access_context(),
    )


@app.route("/logout")
def logout():
    clear_google_auth_state()
    session.clear()
    for key in alert_cooldown:
        alert_cooldown[key] = 0.0
    if coerce_bool(request.args.get("desktop"), False):
        return redirect(url_for("login", desktop=1))
    return redirect(url_for("login"))


@app.route("/auth/status")
def auth_status():
    auth_state = load_saved_google_auth_state()
    user = get_current_user()
    return jsonify(
        {
            "ok": True,
            "logged_in": bool(user.get("email")),
            "email": user.get("email", ""),
            "name": user.get("name", ""),
            "gmail_ready": gmail_auth_ready(auth_state),
        }
    )


@app.route("/auth/desktop-complete")
def auth_desktop_complete():
    return render_template("desktop_auth_complete.html", current_user=get_current_user())


@app.route("/auth/google/start")
def auth_google_start():
    if not google_login_enabled():
        return redirect(url_for("login", error="google configuration missing"))

    next_path = get_safe_next_path(request.args.get("next", "/"))
    redirect_uri = get_google_redirect_uri()
    try:
        flow = Flow.from_client_config(load_client_config(required_redirect_uri=redirect_uri), scopes=SCOPES)
        flow.redirect_uri = redirect_uri

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        session["oauth_state"] = state
        session["oauth_next"] = next_path
        session["oauth_code_verifier"] = getattr(flow, "code_verifier", None)
        append_auth_debug_log(
            f"OAuth start ok host={request.host} redirect_uri={redirect_uri} next={next_path}"
        )
        return redirect(authorization_url)
    except Exception as exc:
        append_auth_debug_log(f"OAuth start failed: {type(exc).__name__}: {exc}")
        return redirect(url_for("login", desktop=1, error=str(exc)))


@app.route("/auth/google/callback")
def auth_google_callback():
    if request.args.get("error"):
        append_auth_debug_log(f"OAuth callback returned error={request.args.get('error')}")
        return redirect(url_for("login", desktop=1, error=request.args.get("error")))

    redirect_uri = get_google_redirect_uri()
    try:
        expected_state = session.get("oauth_state")
        code_verifier = session.get("oauth_code_verifier")
        if not expected_state:
            raise RuntimeError("state missing from desktop login session")
        if not code_verifier:
            raise RuntimeError("code verifier missing from desktop login session")
        flow = Flow.from_client_config(
            load_client_config(required_redirect_uri=redirect_uri),
            scopes=SCOPES,
            state=expected_state,
        )
        flow.redirect_uri = redirect_uri
        flow.code_verifier = code_verifier
        append_auth_debug_log(
            f"OAuth callback code received host={request.host} redirect_uri={redirect_uri}"
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        profile = get_google_user_profile(credentials)
        state = json.loads(credentials.to_json())
        state.update(profile)
        state["scope"] = " ".join(state.get("scopes", []))
        save_google_auth_state(state)
        append_auth_debug_log(f"OAuth callback success email={profile.get('email', '')}")
    except Exception as exc:
        append_auth_debug_log(f"OAuth callback failed: {type(exc).__name__}: {exc}")
        return redirect(url_for("login", desktop=1, error=str(exc)))

    next_path = get_safe_next_path(session.pop("oauth_next", "/"))
    session.pop("oauth_state", None)
    session.pop("oauth_code_verifier", None)
    return redirect(next_path)


@app.route("/health")
def health():
    if not get_current_user():
        return make_login_required_response()
    return jsonify(get_system_snapshot())


@app.route("/battery-report/raw")
def battery_report_raw():
    if not get_current_user():
        return redirect(url_for("login", desktop=1))

    report = get_battery_report_snapshot(force_refresh=coerce_bool(request.args.get("refresh"), False))
    report_path = get_battery_report_file_path()

    if report.get("available") and report_path.exists():
        response = send_file(report_path, mimetype="text/html", max_age=0, conditional=False)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        return response

    return app.response_class(
        build_battery_report_placeholder_html(report.get("error", "")),
        mimetype="text/html",
    )


@app.route("/notification-settings", methods=["GET", "POST"])
def notification_settings_endpoint():
    if not get_current_user():
        return make_login_required_response()

    if request.method == "GET":
        return jsonify(build_public_notification_settings())

    payload = request.get_json(silent=True) or {}
    try:
        settings = update_notification_settings(payload)
        message = "Alert rules updated."
        if coerce_bool(payload.get("send_test_email"), False):
            send_alert(
                "Test Alert",
                f"This is a test message from {APP_DISPLAY_NAME}. CPU and RAM alert delivery is ready.",
                settings=settings,
            )
            message = "Alert rules saved and a test email was sent."
        return jsonify({"ok": True, "message": message, "settings": build_public_notification_settings()})
    except Exception as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": get_public_notification_error_message(str(exc)),
                }
            ),
            400,
        )


def initialize_state() -> None:
    settings = load_notification_settings()
    with notification_settings_lock:
        notification_settings.clear()
        notification_settings.update(settings)


initialize_state()


if __name__ == "__main__":
    start_background_services()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
