---
name: flask
description: Flask/Werkzeug-specific testing for debug-mode RCE, route & blueprint enumeration, session cookie forging, and config-secret abuse
---

# Flask (Werkzeug) Security Testing

Flask is a minimalist WSGI framework. Its flexibility means security is left to
the developer, and the Werkzeug dev server ships dangerous defaults. Focus on
debug mode, the routing model, the signed-session design, and common extension
misconfigurations.

## Attack Surface

**Direct scope**
- Werkzeug debugger (`/console`, PIN-protected RCE)
- Route table and blueprint prefixes (`app.url_map`)
- `flask.session` (itsdangerous signed cookies)
- `SECRET_KEY` / config leakage via `/config` or stack traces
- `render_template_string` / `Markup` (SSTI sink)
- File uploads handled by `werkzeug.datastructures.FileStorage`
- `send_file` / `send_from_directory` (path traversal)

**Entry points**
- Any `request.args`, `request.form`, `request.json`, `request.files`, `request.cookies`
- `url_for` / `redirect` targets built from user input (open redirect)
- `Flask(jinja_env=...)` custom loaders (SSTI escalation)

## Key Techniques

**1. Debug-mode RCE (`werkzeug.debug`)**
- Detect: look for the Werkzeug "Powered by" debugger frame, a `__debugger__`
  cookie, or a traceback page with an interactive console.
- The console is PIN-gated. Recover the PIN deterministically from:
  - `username` running the process (`getpass.getuser()`)
  - `getattr(mod, '__file__', None)` for `app.py` / `flask.app`
  - `uuid.getnode()` (MAC) and `get_machine_id()` (`/etc/machine-id` +
    `/proc/sys/kernel/random/boot_id`)
- Build the PIN with the same algorithm Werkzeug uses, then POST to
  `/console?__wzh=<pin>` with a `code` body for arbitrary Python execution.

**2. Session cookie forging**
- Flask sessions are *signed but not encrypted* by default (`itsdangerous.URLSafeTimedSerializer`).
- If `SECRET_KEY` leaks (env dump, `.env` in repo, stack trace, default
  `"dev"`), forge arbitrary session data: `{"user_id": 1, "admin": True}`.
- Verify by re-signing with the recovered key and confirming the app accepts it.
- Note Flask 2.x+ uses `TaggedJSONSerializer`; booleans/ints are tagged
  (`b"..."`, `i"..."`). Match the serialization when forging.

**3. Route & blueprint enumeration**
- Query `app.url_map.iter_rules()` via a leaked shell, or brute force common
  blueprint prefixes (`/api`, `/admin`, `/auth`, `/v1`).
- Look for `@app.route` registered without `methods=["GET"]` allowing
  state-changing `POST` via GET (CSRF-free).

**4. SSTI via Jinja2**
- Sinks: `render_template_string`, `| safe`, `Markup(...)`, `{{ ... }}` in
  user-controlled templates.
- Bypass filters with attribute access: `{{ self._TemplateReference__context }}`,
  `{{ request.application.__globals__ }}`, `{{ cycler.__init__.__globals__ }}`.
- Confirm with a benign expression (e.g. `7*7`) before escalating to RCE.

## Validation

- **Debug RCE**: only assert in an authorized test sandbox; confirm command
  output returns through the console. Never run destructive commands.
- **Session forge**: re-sign and replay; confirm the app grants the forged role.
- **SSTI**: confirm a benign arithmetic payload renders; do not auto-execute
  system commands in unowned environments.
- **False-positive guards**: a `Set-Cookie: session=...` alone is not evidence of
  forging; prove the key or demonstrate a forged token is accepted.

## Environment Nuances

- Flask 2.2+ enables `app.json` provider; `SECRET_KEY` may be a bytes object.
- `SESSION_COOKIE_SECURE`/`HTTPONLY`/`SAMESITE` default to lax on modern Flask —
  check them; missing `Secure` over HTTPS is a finding.
- Werkzeug 2.1+ changed the debugger PIN algorithm (adds `get_machine_id`).
- Async routes (`async def` + `asgiref`) change stack frames; adapt SSTI payloads.
