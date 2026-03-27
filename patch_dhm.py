from pathlib import Path

project = Path(r"C:\Users\mkpra\Downloads\Device-Health-Monitor-PRO-main")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"{label} not found")
    return text.replace(old, new, 1)


def patch_app() -> None:
    path = project / "app.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "RAM_ALERTS_ENABLED = get_env_bool('RAM_ALERTS_ENABLED', False)",
        "RAM_ALERTS_ENABLED = get_env_bool('RAM_ALERTS_ENABLED', True)",
    )
    text = replace_once(
        text,
        """def build_public_notification_settings():
    settings = get_notification_settings_snapshot()
    auth_state = get_saved_google_auth_state() or {}
    delivery_email = get_delivery_email(auth_state)
    return {
        'email_alerts_enabled': settings['email_alerts_enabled'],
        'delivery_email': delivery_email,
        'signed_in_name': auth_state.get('name', ''),
        'signed_in_email': delivery_email,
        'google_logged_in': bool(auth_state),
        'gmail_ready': gmail_auth_ready(auth_state),
        'cpu_high': settings['cpu_high'],
        'cooldown_minutes': settings['cooldown_minutes'],
        'alert_check_seconds': settings['alert_check_seconds'],
        'email_ready': email_alerts_ready(settings),
        'channels': notification_channels(settings),
        'monitor_running': bool(monitor_thread and monitor_thread.is_alive())
    }
""",
        """def build_public_notification_settings():
    settings = get_notification_settings_snapshot()
    auth_state = get_saved_google_auth_state() or {}
    delivery_email = get_delivery_email(auth_state)
    return {
        'email_alerts_enabled': settings['email_alerts_enabled'],
        'delivery_email': delivery_email,
        'signed_in_name': auth_state.get('name', ''),
        'signed_in_email': delivery_email,
        'google_logged_in': bool(auth_state),
        'gmail_ready': gmail_auth_ready(auth_state),
        'cpu_alerts_enabled': settings['cpu_alerts_enabled'],
        'ram_alerts_enabled': settings['ram_alerts_enabled'],
        'cpu_high': settings['cpu_high'],
        'ram_high': settings['ram_high'],
        'cooldown_minutes': settings['cooldown_minutes'],
        'alert_check_seconds': settings['alert_check_seconds'],
        'email_ready': email_alerts_ready(settings),
        'channels': notification_channels(settings),
        'monitor_running': bool(monitor_thread and monitor_thread.is_alive())
    }
""",
        "build_public_notification_settings",
    )
    text = replace_once(
        text,
        """def update_notification_settings(payload):
    global cooldown_seconds
    with notification_settings_lock:
        updated = dict(notification_settings)
        updated['email_alerts_enabled'] = coerce_bool(payload.get('email_alerts_enabled'), updated['email_alerts_enabled'])
        updated['cpu_alerts_enabled'] = True
        updated['ram_alerts_enabled'] = False
        updated['battery_alerts_enabled'] = False
        updated['cpu_high'] = coerce_int(payload.get('cpu_high'), updated['cpu_high'], 1, 100)
        updated['cooldown_minutes'] = coerce_int(payload.get('cooldown_minutes'), updated['cooldown_minutes'], 0, 1440)
        updated['alert_check_seconds'] = coerce_int(payload.get('alert_check_seconds'), updated['alert_check_seconds'], 5, 3600)
        validate_notification_settings(updated)
        notification_settings.update(updated)
        cooldown_seconds = updated['cooldown_minutes'] * 60
        save_notification_settings_file(notification_settings)
    for key in alert_cooldown:
        alert_cooldown[key] = 0
    return updated
""",
        """def update_notification_settings(payload):
    global cooldown_seconds
    with notification_settings_lock:
        updated = dict(notification_settings)
        updated['email_alerts_enabled'] = coerce_bool(payload.get('email_alerts_enabled'), updated['email_alerts_enabled'])
        updated['cpu_alerts_enabled'] = coerce_bool(payload.get('cpu_alerts_enabled'), updated['cpu_alerts_enabled'])
        updated['ram_alerts_enabled'] = coerce_bool(payload.get('ram_alerts_enabled'), updated['ram_alerts_enabled'])
        updated['battery_alerts_enabled'] = False
        updated['cpu_high'] = coerce_int(payload.get('cpu_high'), updated['cpu_high'], 1, 100)
        updated['ram_high'] = coerce_int(payload.get('ram_high'), updated['ram_high'], 1, 100)
        updated['cooldown_minutes'] = coerce_int(payload.get('cooldown_minutes'), updated['cooldown_minutes'], 0, 1440)
        updated['alert_check_seconds'] = coerce_int(payload.get('alert_check_seconds'), updated['alert_check_seconds'], 5, 3600)
        validate_notification_settings(updated)
        notification_settings.update(updated)
        cooldown_seconds = updated['cooldown_minutes'] * 60
        save_notification_settings_file(notification_settings)
    for key in alert_cooldown:
        alert_cooldown[key] = 0
    return updated
""",
        "update_notification_settings",
    )
    text = replace_once(
        text,
        """            if (
                settings['cpu_alerts_enabled'] and
                cpu_percent >= settings['cpu_high'] and
                now - alert_cooldown['cpu'] > cooldown_seconds
            ):
                if send_alert(
                    'High CPU',
                    f"CPU usage is high: {cpu_percent}% (threshold {settings['cpu_high']}%)",
                    settings=settings
                ):
                    alert_cooldown['cpu'] = now

            if (
                settings['ram_alerts_enabled'] and
                ram_percent >= settings['ram_high'] and
                now - alert_cooldown['ram'] > cooldown_seconds
            ):
                if send_alert(
                    'High RAM',
                    f"RAM usage is high: {ram_percent}% (threshold {settings['ram_high']}%)",
                    settings=settings
                ):
                    alert_cooldown['ram'] = now
""",
        """            if (
                settings['cpu_alerts_enabled'] and
                cpu_percent >= settings['cpu_high'] and
                now - alert_cooldown['cpu'] > cooldown_seconds
            ):
                if send_alert(
                    'High CPU',
                    f"CPU usage is high: {cpu_percent}% (threshold {settings['cpu_high']}%)",
                    settings=settings
                ):
                    alert_cooldown['cpu'] = now
                    print(f"Automatic CPU alert sent at {cpu_percent}%")
                else:
                    print(f"Automatic CPU alert trigger met at {cpu_percent}% but the email could not be sent")

            if (
                settings['ram_alerts_enabled'] and
                ram_percent >= settings['ram_high'] and
                now - alert_cooldown['ram'] > cooldown_seconds
            ):
                if send_alert(
                    'High RAM',
                    f"RAM usage is high: {ram_percent}% (threshold {settings['ram_high']}%)",
                    settings=settings
                ):
                    alert_cooldown['ram'] = now
                    print(f"Automatic RAM alert sent at {ram_percent}%")
                else:
                    print(f"Automatic RAM alert trigger met at {ram_percent}% but the email could not be sent")
""",
        "monitor alerts",
    )
    text = replace_once(
        text,
        """@app.route('/login')
def login():
    if not google_login_enabled():
        return redirect(url_for('home'))
    if get_current_user():
        return redirect(url_for('home'))
    return render_template(
        'login.html',
        oauth_enabled=True,
        error=request.args.get('error', '').strip(),
        next_path=get_safe_next_path(request.args.get('next', '')),
    )


@app.route('/auth/google/start')
def auth_google_start():
""",
        """@app.route('/login')
def login():
    if not google_login_enabled():
        return redirect(url_for('home'))
    if get_current_user():
        return redirect(url_for('home'))
    desktop_mode = coerce_bool(request.args.get('desktop'), False)
    next_path = get_safe_next_path(request.args.get('next', ''))
    desktop_login_url = url_for('auth_google_start', next=url_for('auth_desktop_complete'))
    return render_template(
        'login.html',
        oauth_enabled=True,
        error=request.args.get('error', '').strip(),
        next_path=next_path,
        desktop_mode=desktop_mode,
        desktop_login_url=desktop_login_url,
    )


@app.route('/auth/status')
def auth_status():
    auth_state = get_saved_google_auth_state() or {}
    user = get_current_user() or load_saved_google_user() or {}
    return jsonify({
        'ok': True,
        'logged_in': bool(user.get('email')),
        'email': (user.get('email') or auth_state.get('email') or '').strip(),
        'name': (user.get('name') or auth_state.get('name') or '').strip(),
        'gmail_ready': gmail_auth_ready(auth_state),
    })


@app.route('/auth/desktop-complete')
def auth_desktop_complete():
    return render_template('desktop_auth_complete.html', current_user=load_saved_google_user() or get_current_user() or {})


@app.route('/auth/google/start')
def auth_google_start():
""",
        "login/auth routes",
    )
    path.write_text(text, encoding="utf-8")


def patch_index() -> None:
    path = project / "templates" / "index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        """                <div class="settings-subtitle">
                    Alert emails are sent automatically to your signed-in Google account. No SMTP email or app password is required in this page.
                </div>
""",
        """                <div class="settings-subtitle">
                    Alert emails are sent automatically to your signed-in Google account. Configure CPU and RAM thresholds here. No SMTP email or app password is required in this page.
                </div>
""",
    )
    text = replace_once(
        text,
        """            <div class="settings-form">
                <div class="settings-field">
                    <label for="deliveryEmail">Signed-in Google email</label>
                    <div class="settings-readonly" id="deliveryEmail">Checking Google login...</div>
                </div>
                <div class="settings-field">
                    <label for="cpuHigh">CPU alert threshold %</label>
                    <input id="cpuHigh" type="number" min="1" max="100" placeholder="90">
                </div>
                <div class="settings-field">
                    <label for="cooldownMinutes">Cooldown minutes</label>
                    <input id="cooldownMinutes" type="number" min="0" max="1440" placeholder="60">
                </div>
                <div class="settings-field">
                    <label for="alertCheckSeconds">Check every seconds</label>
                    <input id="alertCheckSeconds" type="number" min="5" max="3600" placeholder="60">
                </div>
                <div class="settings-field checkbox-field">
                    <div class="checkbox-row">
                        <input id="emailAlertsEnabled" type="checkbox">
                        <label for="emailAlertsEnabled">Enable automatic email alerts</label>
                    </div>
                </div>
            </div>
""",
        """            <div class="settings-form">
                <div class="settings-field">
                    <label for="deliveryEmail">Signed-in Google email</label>
                    <div class="settings-readonly" id="deliveryEmail">Checking Google login...</div>
                </div>
                <div class="settings-field">
                    <label for="cpuHigh">CPU alert threshold %</label>
                    <input id="cpuHigh" type="number" min="1" max="100" placeholder="90">
                </div>
                <div class="settings-field">
                    <label for="ramHigh">RAM alert threshold %</label>
                    <input id="ramHigh" type="number" min="1" max="100" placeholder="90">
                </div>
                <div class="settings-field">
                    <label for="cooldownMinutes">Cooldown minutes</label>
                    <input id="cooldownMinutes" type="number" min="0" max="1440" placeholder="60">
                </div>
                <div class="settings-field">
                    <label for="alertCheckSeconds">Check every seconds</label>
                    <input id="alertCheckSeconds" type="number" min="5" max="3600" placeholder="60">
                </div>
                <div class="settings-field checkbox-field">
                    <div class="checkbox-row">
                        <input id="emailAlertsEnabled" type="checkbox">
                        <label for="emailAlertsEnabled">Enable automatic email alerts</label>
                    </div>
                </div>
                <div class="settings-field checkbox-field">
                    <div class="checkbox-row">
                        <input id="cpuAlertsEnabled" type="checkbox">
                        <label for="cpuAlertsEnabled">Enable CPU alerts</label>
                    </div>
                </div>
                <div class="settings-field checkbox-field">
                    <div class="checkbox-row">
                        <input id="ramAlertsEnabled" type="checkbox">
                        <label for="ramAlertsEnabled">Enable RAM alerts</label>
                    </div>
                </div>
            </div>
""",
        "settings form",
    )
    text = replace_once(
        text,
        """        function renderNotificationStatus(settings) {
            if (!settings) {
                notificationStatus.textContent = 'Alert settings unavailable';
                notificationStatus.className = 'settings-status pending';
                return;
            }
            if (!settings.google_logged_in) {
                notificationStatus.textContent = 'Google sign-in required';
                notificationStatus.className = 'settings-status pending';
                return;
            }
            if (!settings.gmail_ready) {
                notificationStatus.textContent = 'Logout and sign in again to grant Gmail send permission';
                notificationStatus.className = 'settings-status pending';
                return;
            }
            if (settings.email_ready && settings.monitor_running) {
                notificationStatus.textContent = `Automatic Gmail alerts active at ${settings.cpu_high}% CPU`;
                notificationStatus.className = 'settings-status ready';
                return;
            }
            notificationStatus.textContent = `Signed in as ${settings.delivery_email || 'Google user'}. Save settings to start alerts.`;
            notificationStatus.className = 'settings-status pending';
        }

        function fillNotificationForm(settings) {
            deliveryEmail.textContent = settings.delivery_email || 'Google login required';
            document.getElementById('cpuHigh').value = settings.cpu_high ?? 90;
            document.getElementById('cooldownMinutes').value = settings.cooldown_minutes ?? 60;
            document.getElementById('alertCheckSeconds').value = settings.alert_check_seconds ?? 60;
            document.getElementById('emailAlertsEnabled').checked = !!settings.email_alerts_enabled;
            renderNotificationStatus(settings);
        }

        function collectNotificationPayload(sendTestEmail = false) {
            return {
                email_alerts_enabled: document.getElementById('emailAlertsEnabled').checked,
                cpu_high: document.getElementById('cpuHigh').value,
                cooldown_minutes: document.getElementById('cooldownMinutes').value,
                alert_check_seconds: document.getElementById('alertCheckSeconds').value,
                send_test_email: sendTestEmail
            };
        }
""",
        """        function describeNotificationRules(settings) {
            const rules = [];
            if (settings.cpu_alerts_enabled) {
                rules.push(`CPU ${settings.cpu_high}%`);
            }
            if (settings.ram_alerts_enabled) {
                rules.push(`RAM ${settings.ram_high}%`);
            }
            return rules.length ? rules.join(' · ') : 'No automatic rules selected';
        }

        function renderNotificationStatus(settings) {
            if (!settings) {
                notificationStatus.textContent = 'Alert settings unavailable';
                notificationStatus.className = 'settings-status pending';
                return;
            }
            if (!settings.google_logged_in) {
                notificationStatus.textContent = 'Google sign-in required';
                notificationStatus.className = 'settings-status pending';
                return;
            }
            if (!settings.gmail_ready) {
                notificationStatus.textContent = 'Logout and sign in again to grant Gmail send permission';
                notificationStatus.className = 'settings-status pending';
                return;
            }
            if (settings.email_ready && settings.monitor_running) {
                notificationStatus.textContent = `Automatic Gmail alerts active for ${describeNotificationRules(settings)}`;
                notificationStatus.className = 'settings-status ready';
                return;
            }
            notificationStatus.textContent = `Signed in as ${settings.delivery_email || 'Google user'}. Save settings to start alerts.`;
            notificationStatus.className = 'settings-status pending';
        }

        function fillNotificationForm(settings) {
            deliveryEmail.textContent = settings.delivery_email || 'Google login required';
            document.getElementById('cpuHigh').value = settings.cpu_high ?? 90;
            document.getElementById('ramHigh').value = settings.ram_high ?? 90;
            document.getElementById('cooldownMinutes').value = settings.cooldown_minutes ?? 60;
            document.getElementById('alertCheckSeconds').value = settings.alert_check_seconds ?? 60;
            document.getElementById('emailAlertsEnabled').checked = !!settings.email_alerts_enabled;
            document.getElementById('cpuAlertsEnabled').checked = !!settings.cpu_alerts_enabled;
            document.getElementById('ramAlertsEnabled').checked = !!settings.ram_alerts_enabled;
            renderNotificationStatus(settings);
        }

        function collectNotificationPayload(sendTestEmail = false) {
            return {
                email_alerts_enabled: document.getElementById('emailAlertsEnabled').checked,
                cpu_alerts_enabled: document.getElementById('cpuAlertsEnabled').checked,
                ram_alerts_enabled: document.getElementById('ramAlertsEnabled').checked,
                cpu_high: document.getElementById('cpuHigh').value,
                ram_high: document.getElementById('ramHigh').value,
                cooldown_minutes: document.getElementById('cooldownMinutes').value,
                alert_check_seconds: document.getElementById('alertCheckSeconds').value,
                send_test_email: sendTestEmail
            };
        }
""",
        "notification js",
    )
    text = text.replace(
        """                if (settings.delivery_email) {
                    setNotificationMessage(`Alert emails will be delivered automatically to ${settings.delivery_email}.`);
                }
""",
        """                if (settings.delivery_email) {
                    setNotificationMessage(`Alert emails will be delivered automatically to ${settings.delivery_email} when the selected CPU or RAM thresholds are reached.`);
                }
""",
    )
    path.write_text(text, encoding="utf-8")


def patch_login() -> None:
    path = project / "templates" / "login.html"
    path.write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Device Health Monitor PRO · Google Login</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg-gradient: radial-gradient(circle at top, rgba(56, 189, 248, 0.2), transparent 35%), linear-gradient(150deg, #020617 0%, #0f172a 42%, #111827 100%);
            --panel-bg: rgba(15, 23, 42, 0.84);
            --panel-border: rgba(148, 163, 184, 0.22);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --danger-bg: rgba(248, 113, 113, 0.12);
            --danger-border: rgba(248, 113, 113, 0.28);
            --info-bg: rgba(56, 189, 248, 0.12);
            --info-border: rgba(56, 189, 248, 0.24);
        }
        body {
            min-height: 100vh; display: grid; place-items: center; padding: 24px;
            font-family: 'Inter', system-ui, sans-serif; background: var(--bg-gradient); color: var(--text-primary);
        }
        .shell {
            width: min(980px, 100%); display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
            border-radius: 32px; overflow: hidden; border: 1px solid var(--panel-border);
            background: rgba(2, 6, 23, 0.64); box-shadow: 0 28px 80px rgba(2, 6, 23, 0.55); backdrop-filter: blur(18px);
        }
        .hero { padding: 56px; border-right: 1px solid rgba(148, 163, 184, 0.12); background: linear-gradient(160deg, rgba(56, 189, 248, 0.14), rgba(236, 72, 153, 0.08)); }
        .badge { display: inline-flex; align-items: center; gap: 10px; padding: 10px 16px; border-radius: 999px; background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(96, 165, 250, 0.28); color: #bfdbfe; font-size: 0.92rem; font-weight: 600; margin-bottom: 22px; }
        h1 { font-size: clamp(2.3rem, 4vw, 3.8rem); line-height: 1.04; letter-spacing: -0.04em; margin-bottom: 18px; }
        .hero p { max-width: 36rem; color: var(--text-secondary); font-size: 1.04rem; line-height: 1.75; }
        .hero-list { display: grid; gap: 14px; margin-top: 28px; }
        .hero-list div { padding: 14px 16px; border-radius: 18px; background: rgba(15, 23, 42, 0.35); border: 1px solid rgba(148, 163, 184, 0.12); color: #dbeafe; }
        .signin { padding: 42px 36px; display: flex; flex-direction: column; justify-content: center; background: var(--panel-bg); }
        .signin h2 { font-size: 1.5rem; margin-bottom: 12px; }
        .signin p { color: var(--text-secondary); line-height: 1.7; margin-bottom: 24px; }
        .error-banner, .info-banner { margin-bottom: 18px; padding: 14px 16px; border-radius: 16px; font-size: 0.94rem; line-height: 1.6; }
        .error-banner { background: var(--danger-bg); border: 1px solid var(--danger-border); color: #fecaca; }
        .info-banner { background: var(--info-bg); border: 1px solid var(--info-border); color: #bae6fd; }
        .google-btn {
            width: 100%; display: inline-flex; align-items: center; justify-content: center; gap: 12px;
            padding: 16px 18px; border-radius: 18px; text-decoration: none; font-size: 1rem; font-weight: 700;
            color: #111827; background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(241, 245, 249, 0.94));
            border: 1px solid rgba(255, 255, 255, 0.12); box-shadow: 0 16px 40px rgba(15, 23, 42, 0.28);
            transition: transform 0.2s ease, box-shadow 0.2s ease; cursor: pointer;
        }
        .google-btn:hover { transform: translateY(-2px); box-shadow: 0 22px 46px rgba(15, 23, 42, 0.34); }
        .google-btn svg { width: 22px; height: 22px; flex-shrink: 0; }
        .note { margin-top: 18px; color: var(--text-secondary); font-size: 0.93rem; line-height: 1.7; }
        .note strong { color: #e2e8f0; }
        @media (max-width: 860px) {
            .shell { grid-template-columns: 1fr; }
            .hero, .signin { padding: 34px 24px; }
            .hero { border-right: none; border-bottom: 1px solid rgba(148, 163, 184, 0.12); }
        }
    </style>
</head>
<body>
    <main class="shell">
        <section class="hero">
            <div class="badge">Portable Google-Secured Monitor</div>
            <h1>Sign in to Device Health Monitor PRO.</h1>
            <p>After Google sign-in, this app automatically uses your signed-in Gmail account for alert delivery. CPU and RAM alerts are configured inside the dashboard without SMTP fields.</p>
            <div class="hero-list">
                <div>Device health dashboard runs locally on your desktop</div>
                <div>CPU and RAM alerts email the signed-in Google account automatically</div>
                <div>Login is remembered locally until you click logout</div>
            </div>
        </section>
        <section class="signin">
            <h2>Continue With Google</h2>
            <p>{% if desktop_mode %}Google login opens in your default browser for security. This desktop window will continue automatically after sign-in.{% else %}Google will ask for profile access and Gmail send permission so alert emails can be sent automatically from the signed-in account.{% endif %}</p>
            {% if error %}<div class="error-banner">{{ error }}</div>{% endif %}
            {% if desktop_mode %}<div class="info-banner" id="desktopStatus">Click the button below. After Google sign-in completes in the browser, this desktop app will switch to the dashboard automatically.</div>{% endif %}
            <a class="google-btn" id="googleSignInBtn" href="{{ desktop_login_url if desktop_mode else url_for('auth_google_start', next=next_path) }}">
                <svg viewBox="0 0 48 48" aria-hidden="true">
                    <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12S17.4 12 24 12c3 0 5.7 1.1 7.8 3l5.7-5.7C34.1 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5Z"/>
                    <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 18.9 12 24 12c3 0 5.7 1.1 7.8 3l5.7-5.7C34.1 6.1 29.3 4 24 4c-7.7 0-14.3 4.3-17.7 10.7Z"/>
                    <path fill="#4CAF50" d="M24 44c5.2 0 10-2 13.5-5.2l-6.2-5.2c-2.1 1.6-4.7 2.4-7.3 2.4-5.3 0-9.8-3.3-11.5-8l-6.5 5C9.3 39.5 16.1 44 24 44Z"/>
                    <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4 5.5l6.2 5.2C36.9 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5Z"/>
                </svg>
                <span>{% if desktop_mode %}Sign in with Google in browser{% else %}Sign in with Google{% endif %}</span>
            </a>
            <div class="note"><strong>Use your Gmail test user.</strong> If Google blocks access, add that Gmail account in <em>Audience → Test users</em> and enable the Gmail API in your Google Cloud project.</div>
        </section>
    </main>
    <script>
        const desktopMode = {{ 'true' if desktop_mode else 'false' }};
        const googleSignInBtn = document.getElementById('googleSignInBtn');
        const desktopStatus = document.getElementById('desktopStatus');

        async function checkDesktopLogin() {
            if (!desktopMode) {
                return;
            }
            try {
                const response = await fetch('/auth/status', { cache: 'no-store' });
                const data = await response.json();
                if (data.logged_in && data.gmail_ready) {
                    window.location.href = '/';
                    return;
                }
            } catch (error) {
                console.error('Desktop auth poll failed', error);
            }
            window.setTimeout(checkDesktopLogin, 1500);
        }

        if (desktopMode) {
            checkDesktopLogin();
            googleSignInBtn.addEventListener('click', async (event) => {
                if (!(window.pywebview && window.pywebview.api && window.pywebview.api.start_google_login)) {
                    return;
                }
                event.preventDefault();
                if (desktopStatus) {
                    desktopStatus.textContent = 'Opening Google sign-in in your browser. Finish login there and this desktop app will continue automatically.';
                }
                try {
                    await window.pywebview.api.start_google_login();
                } catch (error) {
                    if (desktopStatus) {
                        desktopStatus.textContent = 'Could not open the browser automatically. Use the button again or open the link in your browser.';
                    }
                }
            });
        }
    </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def add_desktop_complete() -> None:
    path = project / "templates" / "desktop_auth_complete.html"
    path.write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Device Health Monitor PRO · Sign-In Complete</title>
    <style>
        body {
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(160deg, #020617 0%, #0f172a 45%, #111827 100%);
            color: #f8fafc;
            padding: 24px;
        }
        .card {
            width: min(560px, 100%);
            background: rgba(15, 23, 42, 0.88);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 24px;
            padding: 32px;
            box-shadow: 0 24px 60px rgba(2, 6, 23, 0.42);
        }
        h1 { margin: 0 0 12px; font-size: 2rem; }
        p { margin: 0 0 12px; color: #cbd5e1; line-height: 1.7; }
        .email { color: #67e8f9; font-weight: 700; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Google sign-in complete.</h1>
        <p>{% if current_user and current_user.email %}Signed in as <span class="email">{{ current_user.email }}</span>.{% else %}Your Google account is now connected.{% endif %}</p>
        <p>Return to the Device Health Monitor PRO desktop app. The dashboard will open there automatically.</p>
        <p>You can close this browser tab now.</p>
    </div>
</body>
</html>
""",
        encoding="utf-8",
    )


def patch_desktop_app() -> None:
    path = project / "desktop_app.py"
    path.write_text(
        """import json
import socket
import threading
import time
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen

from app import app, start_background_services

try:
    import webview
except ImportError:  # pragma: no cover
    webview = None

HOST = '127.0.0.1'
PORT = 5000
APP_URL = f'http://{HOST}:{PORT}/'
LOGIN_URL = f'http://{HOST}:{PORT}/login?desktop=1'
AUTH_STATUS_URL = f'http://{HOST}:{PORT}/auth/status'
DESKTOP_AUTH_URL = f'http://{HOST}:{PORT}/auth/google/start?next=/auth/desktop-complete'


def start_flask():
    start_background_services()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


def wait_for_server(timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def fetch_auth_status():
    with urlopen(AUTH_STATUS_URL, timeout=5) as response:
        return json.loads(response.read().decode('utf-8'))


class DesktopApi:
    def start_google_login(self):
        webbrowser.open(DESKTOP_AUTH_URL)
        return {'ok': True}


class DesktopShell:
    def __init__(self):
        self.window = None
        self.last_logged_in = None
        self.stop_event = threading.Event()

    def create_window(self):
        if webview is None:
            webbrowser.open(LOGIN_URL)
            raise RuntimeError('pywebview is not installed. Browser fallback opened instead.')
        if hasattr(webview, 'settings') and 'OPEN_EXTERNAL_LINKS_IN_BROWSER' in webview.settings:
            webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True
        self.window = webview.create_window(
            'Device Health Monitor PRO',
            LOGIN_URL,
            js_api=DesktopApi(),
            width=1420,
            height=920,
            min_size=(1024, 720),
        )
        self.window.events.closed += self.on_closed
        webview.start(self.start_watchers, self.window, debug=False)

    def on_closed(self):
        self.stop_event.set()

    def start_watchers(self, window):
        self.window = window
        threading.Thread(target=self.watch_auth_state, daemon=True).start()

    def watch_auth_state(self):
        while not self.stop_event.is_set():
            try:
                status = fetch_auth_status()
                logged_in = bool(status.get('logged_in'))
                if self.last_logged_in is None:
                    self.last_logged_in = logged_in
                elif logged_in != self.last_logged_in:
                    self.last_logged_in = logged_in
                    target = APP_URL if logged_in else LOGIN_URL
                    self.window.load_url(target)
                elif logged_in and self.window.get_current_url().rstrip('/') == LOGIN_URL.rstrip('/'):
                    self.window.load_url(APP_URL)
            except (OSError, URLError, ValueError):
                pass
            time.sleep(1.5)


if __name__ == '__main__':
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    if not wait_for_server():
        raise RuntimeError('Server failed to start in time.')
    DesktopShell().create_window()
""",
        encoding="utf-8",
    )


def patch_requirements() -> None:
    path = project / "requirements.txt"
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if "pywebview" not in lines:
        lines.append("pywebview")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def patch_build() -> None:
    path = project / "build_portable.ps1"
    text = path.read_text(encoding="utf-8")
    if "--collect-submodules webview" not in text:
        text = text.replace(
            "    --specpath $project `\n",
            "    --specpath $project `\n    --collect-submodules webview `\n",
        )
    path.write_text(text, encoding="utf-8")


def patch_settings() -> None:
    path = project / "notification_settings.json"
    text = path.read_text(encoding="utf-8")
    text = text.replace('"ram_alerts_enabled": false', '"ram_alerts_enabled": true')
    path.write_text(text, encoding="utf-8")


patch_app()
patch_index()
patch_login()
add_desktop_complete()
patch_desktop_app()
patch_requirements()
patch_build()
patch_settings()
