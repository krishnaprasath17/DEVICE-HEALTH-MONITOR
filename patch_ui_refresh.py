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
        "friendly_error = 'Could not send the alert email right now. Please try again.'",
        "friendly_error = 'We could not send the notification right now. Please try again.'",
    )
    text = text.replace(
        "friendly_error = 'Email service setup is not complete yet. Finish the Google mail setup and try again in a few minutes.'",
        "friendly_error = 'Email delivery is getting ready. Try again in a moment.'",
    )
    text = text.replace(
        "friendly_error = 'Google login is missing Gmail send permission. Logout and sign in again.'",
        "friendly_error = 'Please sign in again to refresh email access.'",
    )
    text = text.replace(
        "friendly_error = 'Google login expired or was revoked. Logout and sign in again.'",
        "friendly_error = 'Your Google session needs to be refreshed. Please sign in again.'",
    )

    text = replace_once(
        text,
        """def notification_channels(settings=None):
    settings = settings or get_notification_settings_snapshot()
    return ['email'] if email_alerts_ready(settings) else []


def build_public_notification_settings():
""",
        """def notification_channels(settings=None):
    settings = settings or get_notification_settings_snapshot()
    return ['email'] if email_alerts_ready(settings) else []


def get_public_notification_error_message(message=''):
    text = str(message or '').strip().lower()
    if 'sign in with google' in text or 'google sign-in required' in text:
        return 'Please sign in with Google to continue.'
    if 'permission' in text or 'logout and sign in again' in text or 'refresh email access' in text:
        return 'Please sign in again to refresh email access.'
    if 'setup' in text or 'getting ready' in text:
        return 'Email delivery is getting ready. Try again in a moment.'
    if 'expired' in text or 'revoked' in text:
        return 'Your Google session needs to be refreshed. Please sign in again.'
    return 'We could not complete that action right now. Please try again.'


def get_public_login_error_message(message=''):
    text = str(message or '').strip().lower()
    if not text:
        return ''
    if 'access_denied' in text or 'cancel' in text:
        return 'Google sign-in was cancelled. Please try again.'
    if 'expired' in text or 'authorization code' in text:
        return 'Google sign-in expired. Please try again.'
    return 'We could not finish Google sign-in. Please try again.'


def build_public_notification_settings():
""",
        "public message helpers",
    )

    text = text.replace(
        "error=request.args.get('error', '').strip(),",
        "error=get_public_login_error_message(request.args.get('error', '').strip()),",
    )
    text = text.replace(
        "return redirect(url_for('login', error=f\"Google sign-in failed: {request.args.get('error')}\"))",
        "return redirect(url_for('login', error=get_public_login_error_message(request.args.get('error'))))",
    )
    text = text.replace(
        "return redirect(url_for('login', error=str(exc)))",
        "return redirect(url_for('login', error=get_public_login_error_message(str(exc))))",
    )
    text = text.replace(
        "'error': str(exc),",
        "'error': get_public_notification_error_message(str(exc)),",
    )
    text = text.replace(
        "'error': 'Could not complete the request right now. Please try again.',",
        "'error': 'We could not update alerts right now. Please try again.',",
    )

    path.write_text(text, encoding="utf-8")


def patch_index() -> None:
    path = project / "templates" / "index.html"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        """        .settings-panel {
            background: var(--card-bg);
            backdrop-filter: var(--card-blur);
            -webkit-backdrop-filter: var(--card-blur);
            border: 1px solid var(--card-border);
            border-radius: 32px;
            padding: 24px;
            margin: 26px 0 10px;
            box-shadow: var(--card-shadow);
        }

        .settings-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 18px;
            margin-bottom: 18px;
            flex-wrap: wrap;
        }

        .settings-header h2 {
            font-size: 1.4rem;
            margin-bottom: 6px;
        }

        .settings-subtitle {
            color: var(--text-secondary);
            max-width: 720px;
        }

        .settings-status {
            padding: 8px 14px;
            border-radius: 999px;
            border: 1px solid var(--card-border);
            font-size: 0.92rem;
            font-weight: 600;
            background: rgba(255,255,255,0.06);
        }

        .settings-status.ready {
            color: #34d399;
            border-color: rgba(52, 211, 153, 0.45);
        }

        .settings-status.pending {
            color: #fbbf24;
            border-color: rgba(251, 191, 36, 0.45);
        }

        .settings-form {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }

        .settings-field {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .settings-field label {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        .settings-field input {
            width: 100%;
            border: 1px solid var(--card-border);
            border-radius: 16px;
            background: rgba(15, 23, 42, 0.42);
            color: var(--text-primary);
            padding: 13px 14px;
            font-size: 0.98rem;
            outline: none;
            transition: var(--transition-smooth);
        }

        body.light-mode .settings-field input {
            background: rgba(255, 255, 255, 0.7);
        }

        .settings-field input:focus {
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.2);
        }

        .settings-field.checkbox-field {
            justify-content: flex-end;
        }

        .checkbox-row {
            display: flex;
            align-items: center;
            gap: 10px;
            min-height: 48px;
            padding: 0 4px;
            color: var(--text-primary);
        }

        .checkbox-row input {
            width: 18px;
            height: 18px;
            accent-color: var(--accent-primary);
        }

        .settings-readonly {
            min-height: 52px;
            display: flex;
            align-items: center;
            border: 1px solid var(--card-border);
            border-radius: 16px;
            background: rgba(15, 23, 42, 0.42);
            color: var(--text-primary);
            padding: 13px 14px;
            font-size: 0.98rem;
        }

        body.light-mode .settings-readonly {
            background: rgba(255, 255, 255, 0.7);
        }

        .settings-actions {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 18px;
        }

        .action-btn {
            background: linear-gradient(135deg, rgba(167, 139, 250, 0.24), rgba(236, 72, 153, 0.18));
            border: 1px solid var(--card-border);
            color: var(--text-primary);
            padding: 12px 18px;
            border-radius: 18px;
            cursor: pointer;
            font-size: 0.96rem;
            font-weight: 600;
            transition: var(--transition-smooth);
        }

        .action-btn:hover {
            transform: translateY(-2px);
            border-color: var(--accent-primary);
        }

        .action-btn.secondary {
            background: rgba(255,255,255,0.06);
        }

        .settings-message {
            margin-top: 14px;
            min-height: 24px;
            color: var(--text-secondary);
        }

        .settings-message.error {
            color: #f87171;
        }

        .settings-message.success {
            color: #34d399;
        }
""",
        """        .settings-panel {
            position: relative;
            overflow: hidden;
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.92), rgba(17, 24, 39, 0.84));
            backdrop-filter: var(--card-blur);
            -webkit-backdrop-filter: var(--card-blur);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 32px;
            padding: 26px;
            margin: 26px 0 10px;
            box-shadow: var(--card-shadow), 0 0 0 1px rgba(255, 255, 255, 0.03) inset;
        }

        .settings-panel::before,
        .settings-panel::after {
            content: '';
            position: absolute;
            pointer-events: none;
            border-radius: 50%;
            filter: blur(10px);
            opacity: 0.35;
        }

        .settings-panel::before {
            width: 220px;
            height: 220px;
            top: -110px;
            right: -60px;
            background: radial-gradient(circle, rgba(96, 165, 250, 0.42) 0%, rgba(96, 165, 250, 0) 72%);
        }

        .settings-panel::after {
            width: 180px;
            height: 180px;
            bottom: -90px;
            left: -30px;
            background: radial-gradient(circle, rgba(236, 72, 153, 0.34) 0%, rgba(236, 72, 153, 0) 72%);
        }

        .settings-panel > * {
            position: relative;
            z-index: 1;
        }

        .settings-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 18px;
            margin-bottom: 18px;
            flex-wrap: wrap;
        }

        .settings-header h2 {
            font-size: 1.45rem;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .settings-subtitle {
            color: var(--text-secondary);
            max-width: 760px;
            line-height: 1.7;
        }

        .settings-status {
            padding: 10px 16px;
            border-radius: 999px;
            border: 1px solid var(--card-border);
            font-size: 0.92rem;
            font-weight: 700;
            background: rgba(255,255,255,0.06);
            box-shadow: 0 10px 24px -18px rgba(15, 23, 42, 0.9);
        }

        .settings-status.ready {
            color: #34d399;
            border-color: rgba(52, 211, 153, 0.45);
            background: rgba(22, 163, 74, 0.12);
        }

        .settings-status.pending {
            color: #fbbf24;
            border-color: rgba(251, 191, 36, 0.45);
            background: rgba(234, 179, 8, 0.12);
        }

        .settings-band {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-bottom: 20px;
        }

        .settings-mini-card {
            padding: 16px 18px;
            border-radius: 22px;
            border: 1px solid rgba(148, 163, 184, 0.16);
            background: linear-gradient(160deg, rgba(15, 23, 42, 0.78), rgba(30, 41, 59, 0.62));
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }

        .settings-mini-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }

        .settings-mini-value {
            font-size: 1.02rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.45;
        }

        .settings-mini-note {
            margin-top: 8px;
            font-size: 0.8rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }

        .settings-form {
            display: grid;
            grid-template-columns: repeat(12, minmax(0, 1fr));
            gap: 16px;
        }

        .settings-field {
            display: flex;
            flex-direction: column;
            gap: 8px;
            grid-column: span 3;
        }

        .settings-field.wide {
            grid-column: span 6;
        }

        .settings-field label {
            font-size: 0.86rem;
            font-weight: 600;
            color: var(--text-secondary);
        }

        .settings-field-note {
            font-size: 0.79rem;
            color: var(--text-secondary);
            line-height: 1.45;
        }

        .settings-field input {
            width: 100%;
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            background: rgba(15, 23, 42, 0.48);
            color: var(--text-primary);
            padding: 14px 16px;
            font-size: 0.98rem;
            outline: none;
            transition: var(--transition-smooth);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
        }

        body.light-mode .settings-field input {
            background: rgba(255, 255, 255, 0.74);
        }

        .settings-field input:focus {
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.18), 0 18px 36px -24px rgba(167, 139, 250, 0.9);
        }

        .settings-field.checkbox-field {
            justify-content: flex-end;
        }

        .checkbox-row {
            display: flex;
            align-items: center;
            gap: 12px;
            min-height: 56px;
            padding: 0 16px;
            color: var(--text-primary);
            border-radius: 18px;
            border: 1px solid rgba(148, 163, 184, 0.16);
            background: rgba(15, 23, 42, 0.38);
        }

        .checkbox-row input {
            width: 18px;
            height: 18px;
            accent-color: var(--accent-primary);
        }

        .settings-readonly {
            min-height: 66px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 4px;
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            background: rgba(15, 23, 42, 0.48);
            color: var(--text-primary);
            padding: 14px 16px;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
        }

        .settings-readonly-main {
            font-size: clamp(0.88rem, 0.2vw + 0.84rem, 1rem);
            font-weight: 700;
            line-height: 1.45;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        .settings-readonly-sub {
            font-size: 0.78rem;
            color: var(--text-secondary);
            line-height: 1.4;
        }

        body.light-mode .settings-readonly {
            background: rgba(255, 255, 255, 0.74);
        }

        .settings-actions {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 20px;
        }

        .action-btn {
            background: linear-gradient(135deg, rgba(167, 139, 250, 0.24), rgba(236, 72, 153, 0.18));
            border: 1px solid rgba(148, 163, 184, 0.16);
            color: var(--text-primary);
            padding: 13px 20px;
            border-radius: 18px;
            cursor: pointer;
            font-size: 0.96rem;
            font-weight: 700;
            transition: var(--transition-smooth);
            box-shadow: 0 18px 30px -24px rgba(167, 139, 250, 0.9);
        }

        .action-btn:hover {
            transform: translateY(-2px);
            border-color: var(--accent-primary);
        }

        .action-btn.secondary {
            background: rgba(255,255,255,0.06);
            box-shadow: none;
        }

        .settings-message {
            margin-top: 16px;
            padding: 14px 16px;
            border-radius: 18px;
            border: 1px solid rgba(148, 163, 184, 0.12);
            background: rgba(15, 23, 42, 0.32);
            color: var(--text-secondary);
            line-height: 1.6;
        }

        .settings-message.hidden {
            display: none;
        }

        .settings-message.error {
            color: #fecaca;
            background: rgba(127, 29, 29, 0.22);
            border-color: rgba(248, 113, 113, 0.26);
        }

        .settings-message.success {
            color: #d1fae5;
            background: rgba(6, 95, 70, 0.22);
            border-color: rgba(52, 211, 153, 0.26);
        }

        @media (max-width: 1180px) {
            .settings-field {
                grid-column: span 4;
            }

            .settings-field.wide {
                grid-column: span 8;
            }
        }

        @media (max-width: 820px) {
            .settings-form {
                grid-template-columns: 1fr;
            }

            .settings-field,
            .settings-field.wide {
                grid-column: auto;
            }

            .settings-status {
                width: 100%;
                text-align: center;
            }
        }
""",
        "settings CSS",
    )
    text = replace_once(
        text,
        """    <div class="settings-panel">
        <div class="settings-header">
            <div>
                <h2><i class="fas fa-bell"></i> Alert Settings</h2>
                <div class="settings-subtitle">
                    Alert emails are sent automatically to your signed-in Google account. Configure CPU and RAM thresholds here. No SMTP email or app password is required in this page.
                </div>
            </div>
            <div class="settings-status pending" id="notificationStatus">Loading alert settings...</div>
        </div>

        <form id="notificationForm">
            <div class="settings-form">
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

            <div class="settings-actions">
                <button class="action-btn" type="submit">Save Alert Settings</button>
                <button class="action-btn secondary" id="testEmailBtn" type="button">Send Test Email</button>
            </div>
            <div class="settings-message" id="notificationMessage"></div>
        </form>
    </div>
""",
        """    <div class="settings-panel">
        <div class="settings-header">
            <div>
                <h2><i class="fas fa-bell"></i> Alert Command Center</h2>
                <div class="settings-subtitle">
                    Your signed-in Google account receives alerts automatically. Tune CPU and RAM protection here and keep the alert engine ready without exposing any mail credentials.
                </div>
            </div>
            <div class="settings-status pending" id="notificationStatus">Preparing alert center...</div>
        </div>

        <div class="settings-band">
            <div class="settings-mini-card">
                <div class="settings-mini-label">Delivery Route</div>
                <div class="settings-mini-value" id="alertDeliveryState">Checking account...</div>
                <div class="settings-mini-note">Notifications stay linked to the Google account that is currently signed in.</div>
            </div>
            <div class="settings-mini-card">
                <div class="settings-mini-label">Coverage</div>
                <div class="settings-mini-value" id="alertCoverageState">Loading rules...</div>
                <div class="settings-mini-note">Choose the watchlist you want active before each monitoring cycle begins.</div>
            </div>
            <div class="settings-mini-card">
                <div class="settings-mini-label">Scan Cadence</div>
                <div class="settings-mini-value" id="alertCadenceState">Synchronizing...</div>
                <div class="settings-mini-note">The monitor wakes on save so updated rules take effect immediately.</div>
            </div>
            <div class="settings-mini-card">
                <div class="settings-mini-label">Protection State</div>
                <div class="settings-mini-value" id="alertProtectionState">Stand by</div>
                <div class="settings-mini-note">A focused summary of whether alerts are armed, paused, or need sign-in attention.</div>
            </div>
        </div>

        <form id="notificationForm">
            <div class="settings-form">
                <div class="settings-field wide">
                    <label for="deliveryEmail">Signed-in Google email</label>
                    <div class="settings-readonly" id="deliveryEmail">
                        <span class="settings-readonly-main">Checking Google login...</span>
                        <span class="settings-readonly-sub">Alerts will be delivered to the connected Google account automatically.</span>
                    </div>
                    <div class="settings-field-note">This field adapts to long email addresses and always shows the full delivery identity.</div>
                </div>
                <div class="settings-field">
                    <label for="cpuHigh">CPU alert threshold %</label>
                    <input id="cpuHigh" type="number" min="1" max="100" placeholder="90">
                    <div class="settings-field-note">Trigger when CPU load stays above this level during a scan.</div>
                </div>
                <div class="settings-field">
                    <label for="ramHigh">RAM alert threshold %</label>
                    <input id="ramHigh" type="number" min="1" max="100" placeholder="90">
                    <div class="settings-field-note">Trigger when memory usage crosses the selected limit.</div>
                </div>
                <div class="settings-field">
                    <label for="cooldownMinutes">Cooldown minutes</label>
                    <input id="cooldownMinutes" type="number" min="0" max="1440" placeholder="60">
                    <div class="settings-field-note">Avoid repeated alerts for the same condition inside this cooldown window.</div>
                </div>
                <div class="settings-field">
                    <label for="alertCheckSeconds">Check every seconds</label>
                    <input id="alertCheckSeconds" type="number" min="5" max="3600" placeholder="60">
                    <div class="settings-field-note">Lower values react faster. Higher values reduce noise and background work.</div>
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

            <div class="settings-actions">
                <button class="action-btn" type="submit">Apply Alert Rules</button>
                <button class="action-btn secondary" id="testEmailBtn" type="button">Send Test Email</button>
            </div>
            <div class="settings-message hidden" id="notificationMessage"></div>
        </form>
    </div>
""",
        "settings HTML",
    )

    text = text.replace(
        "const deliveryEmail = document.getElementById('deliveryEmail');",
        "const deliveryEmail = document.getElementById('deliveryEmail');\n        const alertDeliveryState = document.getElementById('alertDeliveryState');\n        const alertCoverageState = document.getElementById('alertCoverageState');\n        const alertCadenceState = document.getElementById('alertCadenceState');\n        const alertProtectionState = document.getElementById('alertProtectionState');",
    )
    text = replace_once(
        text,
        """        function setNotificationMessage(message, type = '') {
            notificationMessage.textContent = message || '';
            notificationMessage.className = `settings-message${type ? ' ' + type : ''}`;
        }

        function describeNotificationRules(settings) {
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

        async function saveNotificationSettings(sendTestEmail = false) {
            const response = await fetch('/notification-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(collectNotificationPayload(sendTestEmail))
            });

            const data = await response.json();
            if (response.status === 401 && data.login_url) {
                window.location.href = data.login_url;
                return;
            }
            if (!response.ok || !data.ok) {
                throw new Error(data.error || 'Failed to save notification settings.');
            }

            fillNotificationForm(data.settings);
            setNotificationMessage(data.message, 'success');
        }

        async function loadNotificationSettings() {
            try {
                const response = await fetch('/notification-settings');
                const settings = await response.json();
                if (response.status === 401 && settings.login_url) {
                    window.location.href = settings.login_url;
                    return;
                }
                if (!response.ok) {
                    throw new Error(settings.error || 'Could not load notification settings.');
                }
                fillNotificationForm(settings);
                if (settings.delivery_email) {
                    setNotificationMessage(`Alert emails will be delivered automatically to ${settings.delivery_email} when the selected CPU or RAM thresholds are reached.`);
                }
            } catch (error) {
                console.error('Settings fetch error', error);
                renderNotificationStatus(null);
                setNotificationMessage('Could not load notification settings from the server.', 'error');
            }
        }
""",
        """        function setNotificationMessage(message, type = '') {
            if (!message) {
                notificationMessage.textContent = '';
                notificationMessage.className = 'settings-message hidden';
                return;
            }
            notificationMessage.textContent = message;
            notificationMessage.className = `settings-message${type ? ' ' + type : ''}`;
        }

        function getFriendlyUiMessage(message, fallback = 'We could not complete that action right now. Please try again.') {
            const raw = String(message || '').trim();
            const normalized = raw.toLowerCase();
            if (!normalized) {
                return fallback;
            }
            if (normalized.includes('sign in') || normalized.includes('google')) {
                return 'Please sign in again to keep alert delivery ready.';
            }
            if (normalized.includes('permission') || normalized.includes('access')) {
                return 'Please sign in again to refresh alert access.';
            }
            if (normalized.includes('getting ready') || normalized.includes('setup')) {
                return 'Email delivery is getting ready. Try again in a moment.';
            }
            if (normalized.includes('expired')) {
                return 'Your Google session needs to be refreshed. Please sign in again.';
            }
            return raw.length > 120 ? fallback : raw;
        }

        function describeNotificationRules(settings) {
            const rules = [];
            if (settings.cpu_alerts_enabled) {
                rules.push(`CPU ${settings.cpu_high}%`);
            }
            if (settings.ram_alerts_enabled) {
                rules.push(`RAM ${settings.ram_high}%`);
            }
            return rules.length ? rules.join(' · ') : 'No automatic rules selected';
        }

        function renderDeliveryIdentity(settings) {
            if (!settings || !settings.delivery_email) {
                deliveryEmail.innerHTML = `
                    <span class="settings-readonly-main">Google login required</span>
                    <span class="settings-readonly-sub">Sign in to connect alert delivery to your account.</span>
                `;
                return;
            }
            deliveryEmail.innerHTML = `
                <span class="settings-readonly-main">${settings.delivery_email}</span>
                <span class="settings-readonly-sub">Automatic notifications will be delivered to this Google account.</span>
            `;
        }

        function updateAlertOverview(settings) {
            if (!settings) {
                alertDeliveryState.textContent = 'Unavailable';
                alertCoverageState.textContent = 'No rules loaded';
                alertCadenceState.textContent = 'Waiting for sync';
                alertProtectionState.textContent = 'Stand by';
                return;
            }
            alertDeliveryState.textContent = settings.delivery_email || 'Sign-in needed';
            alertCoverageState.textContent = describeNotificationRules(settings);
            alertCadenceState.textContent = `Every ${settings.alert_check_seconds || 60}s · Cooldown ${settings.cooldown_minutes || 0}m`;
            if (!settings.google_logged_in) {
                alertProtectionState.textContent = 'Sign-in needed';
            } else if (!settings.email_alerts_enabled) {
                alertProtectionState.textContent = 'Paused';
            } else if (settings.email_ready && settings.monitor_running) {
                alertProtectionState.textContent = 'Armed';
            } else {
                alertProtectionState.textContent = 'Ready to apply';
            }
        }

        function renderNotificationStatus(settings) {
            if (!settings) {
                notificationStatus.textContent = 'Alert center unavailable';
                notificationStatus.className = 'settings-status pending';
                return;
            }
            if (!settings.google_logged_in) {
                notificationStatus.textContent = 'Sign in to activate alerts';
                notificationStatus.className = 'settings-status pending';
                return;
            }
            if (!settings.gmail_ready) {
                notificationStatus.textContent = 'Sign in again to refresh alert access';
                notificationStatus.className = 'settings-status pending';
                return;
            }
            if (settings.email_ready && settings.monitor_running) {
                notificationStatus.textContent = `Shield active · ${describeNotificationRules(settings)}`;
                notificationStatus.className = 'settings-status ready';
                return;
            }
            notificationStatus.textContent = 'Review the rules below and apply them to arm alerts';
            notificationStatus.className = 'settings-status pending';
        }

        function fillNotificationForm(settings) {
            renderDeliveryIdentity(settings);
            updateAlertOverview(settings);
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

        async function saveNotificationSettings(sendTestEmail = false) {
            const response = await fetch('/notification-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(collectNotificationPayload(sendTestEmail))
            });

            const data = await response.json();
            if (response.status === 401 && data.login_url) {
                window.location.href = data.login_url;
                return;
            }
            if (!response.ok || !data.ok) {
                throw new Error(getFriendlyUiMessage(data.error, 'We could not save the alert rules right now. Please try again.'));
            }

            fillNotificationForm(data.settings);
            setNotificationMessage(getFriendlyUiMessage(data.message, 'Alert rules updated.'), 'success');
        }

        async function loadNotificationSettings() {
            try {
                const response = await fetch('/notification-settings');
                const settings = await response.json();
                if (response.status === 401 && settings.login_url) {
                    window.location.href = settings.login_url;
                    return;
                }
                if (!response.ok) {
                    throw new Error(getFriendlyUiMessage(settings.error, 'We could not load the alert center right now.'));
                }
                fillNotificationForm(settings);
                if (settings.delivery_email) {
                    setNotificationMessage(`Alerts will be delivered automatically to ${settings.delivery_email}.`, 'success');
                } else {
                    setNotificationMessage('Sign in to connect automatic alert delivery.', 'error');
                }
            } catch (error) {
                console.error('Settings fetch error', error);
                renderNotificationStatus(null);
                updateAlertOverview(null);
                renderDeliveryIdentity(null);
                setNotificationMessage('We could not load the alert center right now. Please refresh and try again.', 'error');
            }
        }
""",
        "notification JS",
    )

    path.write_text(text, encoding="utf-8")


def patch_login() -> None:
    path = project / "templates" / "login.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "<div class=\"note\"><strong>Use your Gmail test user.</strong> If Google blocks access, add that Gmail account in <em>Audience → Test users</em> and enable the Gmail API in your Google Cloud project.</div>",
        "<div class=\"note\"><strong>Use the Google account that should receive alerts.</strong> If sign-in does not finish, close the browser window and try once more from the desktop app.</div>",
    )
    path.write_text(text, encoding="utf-8")


patch_app()
patch_index()
patch_login()
