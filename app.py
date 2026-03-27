from __future__ import annotations

import base64
import getpass
import html as html_lib
import json
import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
import warnings
from copy import deepcopy
from datetime import datetime
from email.mime.text import MIMEText
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

warnings.filterwarnings(
    "ignore",
    message="You are using a Python version",
    category=FutureWarning,
    module=r"google\.api_core\._python_version_support",
)

import psutil
from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None

HOST = "127.0.0.1"
PORT = 5000
REDIRECT_URI = f"http://{HOST}:{PORT}/auth/google/callback"

SOURCE_ROOT = Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", SOURCE_ROOT))
EXE_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else SOURCE_ROOT
LOCAL_APPDATA_ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
DATA_ROOT = (LOCAL_APPDATA_ROOT / "DeviceHealthMonitorPRO") if getattr(sys, "frozen", False) else SOURCE_ROOT
LEGACY_DIST_ROOT = SOURCE_ROOT / "dist"

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
    "battery_alerts_enabled": False,
    "cpu_high": 90,
    "ram_high": 90,
    "battery_low": 20,
    "cooldown_minutes": 60,
    "alert_check_seconds": 60,
}

app = Flask(__name__, template_folder=str(TEMPLATE_ROOT))
app.secret_key = os.environ.get(
    "DEVICE_HEALTH_MONITOR_SECRET",
    "device-health-monitor-pro-local-secret",
)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

notification_settings_lock = threading.Lock()
notification_settings: dict[str, Any] = {}

background_services_started = False
background_lock = threading.Lock()
monitor_thread: threading.Thread | None = None
monitor_stop_event = threading.Event()
alert_cooldown = {"cpu": 0.0, "ram": 0.0}

network_lock = threading.Lock()
last_network_totals: tuple[int, int] | None = None
last_network_timestamp = 0.0

BATTERY_REPORT_CACHE_SECONDS = 180
battery_report_lock = threading.Lock()
battery_report_cache: dict[str, Any] = {"timestamp": 0.0, "data": None}


def get_read_data_file_path(filename: str) -> Path:
    primary = DATA_ROOT / filename
    candidates = [primary]
    if getattr(sys, "frozen", False):
        candidates.append(EXE_ROOT / filename)
    else:
        candidates.append(LEGACY_DIST_ROOT / filename)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return primary


def get_write_data_file_path(filename: str) -> Path:
    return DATA_ROOT / filename


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


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
    path = get_write_data_file_path("auth_debug.log")
    ensure_parent_dir(path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


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


def load_client_config() -> dict[str, Any]:
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
    redirect_uris = config.get("web", {}).get("redirect_uris", [])
    if REDIRECT_URI not in redirect_uris:
        raise ValueError(
            f"Google OAuth web client is missing redirect URI {REDIRECT_URI}."
        )
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


def load_saved_google_auth_state() -> dict[str, Any]:
    path = get_read_data_file_path("google_auth_state.json")
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            state = normalize_auth_state(json.load(handle))
    except (OSError, json.JSONDecodeError):
        return {}
    return state


def save_google_auth_state(state: dict[str, Any]) -> None:
    path = get_write_data_file_path("google_auth_state.json")
    ensure_parent_dir(path)
    normalized = normalize_auth_state(state)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(normalized, handle, indent=2)


def clear_google_auth_state() -> None:
    seen: set[Path] = set()
    for candidate in [
        get_write_data_file_path("google_auth_state.json"),
        get_read_data_file_path("google_auth_state.json"),
    ]:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            candidate.unlink()


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
        return None
    try:
        credentials = Credentials.from_authorized_user_info(state, SCOPES)
    except Exception:
        return None

    if refresh and credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleRequest())
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
        credentials = Credentials.from_authorized_user_info(normalize_auth_state(updated), SCOPES)
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
    if "another device health monitor pro instance is already using port 5000" in text:
        return "Close the older Device Health Monitor PRO app window first, then try again."
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
    settings["battery_alerts_enabled"] = False
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


def format_seconds(value: int | None) -> str | None:
    try:
        seconds = int(float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None
    if seconds is None or seconds < 0:
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


@lru_cache(maxsize=1)
def get_windows_system_identity() -> dict[str, str | None]:
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

    return {
        "manufacturer": manufacturer,
        "product": product or model,
        "model": model,
        "display_name": " · ".join(display_parts) if display_parts else None,
    }


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


def parse_recent_battery_usage(report_html: str, limit: int = 6) -> list[dict[str, Any]]:
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


def parse_capacity_history(report_html: str, limit: int = 7) -> list[dict[str, Any]]:
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


def get_battery_report_snapshot(force_refresh: bool = False) -> dict[str, Any]:
    battery = psutil.sensors_battery()
    with battery_report_lock:
        cached = battery_report_cache.get("data")
        cached_at = float(battery_report_cache.get("timestamp") or 0.0)
        if cached and not force_refresh and time.time() - cached_at < BATTERY_REPORT_CACHE_SECONDS:
            return deepcopy(cached)

        if not battery:
            empty = build_empty_battery_report("No battery detected on this device.")
            battery_report_cache["timestamp"] = time.time()
            battery_report_cache["data"] = deepcopy(empty)
            return empty

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

        battery_report_cache["timestamp"] = time.time()
        battery_report_cache["data"] = deepcopy(data)
        return deepcopy(data)


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


def get_battery_snapshot(report: dict[str, Any] | None = None) -> dict[str, Any]:
    report_summary = (report or {}).get("summary", {})
    battery = psutil.sensors_battery()
    if not battery:
        return {
            "percent": None,
            "plugged": None,
            "secsleft": None,
            "time_remaining": None,
            "time_to_full": None,
            "health": report_summary.get("health_percent"),
            "design_capacity": report_summary.get("design_capacity"),
            "full_capacity": report_summary.get("full_charge_capacity"),
            "cycle_count": report_summary.get("cycle_count"),
            "wear": report_summary.get("wear_percent"),
            "chemistry": report_summary.get("chemistry"),
            "manufacturer": report_summary.get("manufacturer"),
            "connection_status": None,
            "state_label": None,
            "time_status": None,
            "status_text": "Battery not detected",
        }

    secsleft = battery.secsleft
    if secsleft in {psutil.POWER_TIME_UNKNOWN, psutil.POWER_TIME_UNLIMITED}:
        secsleft = None

    percent = round(float(battery.percent), 1)
    plugged = bool(battery.power_plugged)
    connection_status, state_label = describe_battery_state(percent, plugged)
    time_remaining = None if plugged else format_seconds(secsleft)
    time_to_full = format_seconds(secsleft) if plugged else None
    time_status = None

    status_parts = [part for part in [connection_status, state_label] if part]
    if plugged and time_to_full and state_label != "Fully charged":
        time_status = f"{time_to_full} to full"
        status_parts.append(time_status)
    elif not plugged and time_remaining:
        time_status = f"{time_remaining} left"
        status_parts.append(time_status)

    return {
        "percent": percent,
        "plugged": plugged,
        "secsleft": secsleft,
        "time_remaining": time_remaining,
        "time_to_full": time_to_full,
        "health": report_summary.get("health_percent"),
        "design_capacity": report_summary.get("design_capacity"),
        "full_capacity": report_summary.get("full_charge_capacity"),
        "cycle_count": report_summary.get("cycle_count"),
        "wear": report_summary.get("wear_percent"),
        "chemistry": report_summary.get("chemistry"),
        "manufacturer": report_summary.get("manufacturer"),
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
    global last_network_timestamp, last_network_totals

    counters = psutil.net_io_counters()
    now = time.time()
    upload_speed = 0.0
    download_speed = 0.0

    with network_lock:
        if last_network_totals is not None and last_network_timestamp:
            elapsed = max(now - last_network_timestamp, 0.001)
            previous_sent, previous_recv = last_network_totals
            upload_speed = max(0.0, (counters.bytes_sent - previous_sent) / 1024 / elapsed)
            download_speed = max(0.0, (counters.bytes_recv - previous_recv) / 1024 / elapsed)

        last_network_totals = (counters.bytes_sent, counters.bytes_recv)
        last_network_timestamp = now

    return {
        "upload_speed": round(upload_speed, 1),
        "download_speed": round(download_speed, 1),
    }


def get_system_snapshot() -> dict[str, Any]:
    now = datetime.now()
    hostname = socket.gethostname()
    system_drive = os.environ.get("SystemDrive", "C:")
    disk_root = f"{system_drive}\\"
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage(disk_root)
    cpu_percent = round(psutil.cpu_percent(interval=0.2), 1)
    battery_report = get_battery_report_snapshot()
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
        "battery": get_battery_snapshot(battery_report),
        "battery_report": battery_report,
        "network": get_network_speed_snapshot(),
        "temperatures": get_temperature_snapshot(),
        "fans": get_fan_snapshot(),
    }


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
    psutil.cpu_percent(interval=None)
    while not monitor_stop_event.is_set():
        settings = get_notification_settings_snapshot()
        wait_seconds = max(settings.get("alert_check_seconds", 60), 5)
        cooldown_seconds = max(settings.get("cooldown_minutes", 0), 0) * 60

        if email_alerts_ready(settings):
            cpu_percent = round(psutil.cpu_percent(interval=None), 1)
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
                        print(f"Automatic CPU alert sent at {cpu_percent}%")
                except Exception as exc:
                    print(f"Automatic CPU alert trigger met at {cpu_percent}% but the email could not be sent: {exc}")

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
                        print(f"Automatic RAM alert sent at {ram_percent}%")
                except Exception as exc:
                    print(f"Automatic RAM alert trigger met at {ram_percent}% but the email could not be sent: {exc}")

        monitor_stop_event.wait(wait_seconds)


def start_background_services() -> None:
    global background_services_started, monitor_thread
    with background_lock:
        if background_services_started and monitor_thread and monitor_thread.is_alive():
            return
        monitor_stop_event.clear()
        monitor_thread = threading.Thread(target=monitor_alerts_loop, daemon=True, name="alert-monitor")
        monitor_thread.start()
        background_services_started = True


def stop_background_services() -> None:
    monitor_stop_event.set()


@app.route("/")
def home():
    if not get_current_user():
        return redirect(url_for("login", desktop=1))
    return render_template("index.html", current_user=get_current_user())


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
    try:
        flow = Flow.from_client_config(load_client_config(), scopes=SCOPES)
        flow.redirect_uri = REDIRECT_URI

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        session["oauth_state"] = state
        session["oauth_next"] = next_path
        session["oauth_code_verifier"] = getattr(flow, "code_verifier", None)
        append_auth_debug_log(
            f"OAuth start ok host={request.host} redirect_uri={REDIRECT_URI} next={next_path}"
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

    try:
        expected_state = session.get("oauth_state")
        code_verifier = session.get("oauth_code_verifier")
        if not expected_state:
            raise RuntimeError("state missing from desktop login session")
        if not code_verifier:
            raise RuntimeError("code verifier missing from desktop login session")
        flow = Flow.from_client_config(
            load_client_config(),
            scopes=SCOPES,
            state=expected_state,
        )
        flow.redirect_uri = REDIRECT_URI
        flow.code_verifier = code_verifier
        append_auth_debug_log(
            f"OAuth callback code received host={request.host} redirect_uri={REDIRECT_URI}"
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
                "This is a test message from Device Health Monitor PRO. CPU and RAM alert delivery is ready.",
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
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
