#!/usr/bin/env python3
"""
spotify.py -- Spotify auth, now-playing, and playback control for Desky.

One-time login:
    ~/desky-venv/bin/python spotify.py

After that bridge.py imports this module and refreshes the token itself.

Uses the Authorization Code flow with PKCE, so there is no client secret to
store -- only your Client ID. Spotify no longer accepts plain HTTP redirect
URIs except loopback literals, and 'localhost' does not count, so the
redirect below must be registered EXACTLY as written.

Note: reading what's playing works on any account, but play/pause/skip
requires Spotify Premium. Free accounts get 403 on control calls.
"""

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

CLIENT_FILE = os.path.expanduser("~/.desky-spotify-client")
TOKENS_FILE = os.path.expanduser("~/.desky-spotify.json")

REDIRECT_URI = "http://127.0.0.1:8888/callback"
REDIRECT_PORT = 8888
SCOPES = ("user-read-playback-state user-modify-playback-state "
          "user-read-currently-playing")

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API = "https://api.spotify.com/v1"

_tokens = None


# ------------------------------------------------------------- credentials
def client_id():
    cid = os.environ.get("DESKY_SPOTIFY_CLIENT_ID")
    if cid:
        return cid.strip()
    try:
        with open(CLIENT_FILE) as f:
            return f.read().strip()
    except Exception:
        return None


def load_tokens():
    global _tokens
    if _tokens is None:
        try:
            with open(TOKENS_FILE) as f:
                _tokens = json.load(f)
        except Exception:
            _tokens = {}
    return _tokens


def save_tokens(data):
    global _tokens
    _tokens = data
    with open(TOKENS_FILE, "w") as f:
        json.dump(data, f)
    try:
        os.chmod(TOKENS_FILE, 0o600)
    except Exception:
        pass


# ------------------------------------------------------------------ tokens
def _post_form(url, fields):
    body = urllib.parse.urlencode(fields).encode()
    request = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read())


def access_token():
    """Current access token, refreshed if it's within a minute of expiring."""
    tokens = load_tokens()
    if not tokens.get("refresh_token"):
        return None

    if tokens.get("expires_at", 0) - 60 > time.time():
        return tokens.get("access_token")

    cid = client_id()
    if not cid:
        return None
    try:
        fresh = _post_form(TOKEN_URL, {
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": cid,
        })
    except Exception as exc:
        print("Spotify refresh failed:", exc)
        return None

    tokens["access_token"] = fresh["access_token"]
    tokens["expires_at"] = time.time() + int(fresh.get("expires_in", 3600))
    if fresh.get("refresh_token"):          # Spotify sometimes rotates it
        tokens["refresh_token"] = fresh["refresh_token"]
    save_tokens(tokens)
    return tokens["access_token"]


# --------------------------------------------------------------- API calls
def _api(path, method="GET"):
    token = access_token()
    if not token:
        return None, "no auth"

    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if method in ("PUT", "POST"):
        # Spotify's playback endpoints take no body, but urllib needs an
        # explicit empty one to send the right headers for PUT/POST.
        data = b""
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = "0"

    request = urllib.request.Request(API + path, data=data,
                                     method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
            if not raw:
                return {}, None          # 204 No Content -- normal for controls
            try:
                return json.loads(raw), None
            except ValueError:
                return {}, None          # 2xx with a non-JSON body is still fine
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, "no device"
        if exc.code == 403:
            return None, "premium required"
        if exc.code == 429:
            return None, "rate limited"
        return None, f"http {exc.code}"
    except Exception as exc:
        return None, str(exc)


def now_playing():
    """What's on, in a shape the Pico can render directly."""
    blank = {"sp_ok": False, "sp_active": False, "sp_playing": False,
             "sp_track": "", "sp_artist": "", "sp_progress": 0}

    if not load_tokens().get("refresh_token"):
        return blank

    data, error = _api("/me/player")
    if error:
        return blank
    if not data or not data.get("item"):
        return {"sp_ok": True, "sp_active": False, "sp_playing": False,
                "sp_track": "", "sp_artist": "", "sp_progress": 0}

    item = data["item"]
    artists = ", ".join(a.get("name", "") for a in item.get("artists", []))
    duration = item.get("duration_ms") or 0
    progress = data.get("progress_ms") or 0
    pct = int(100 * progress / duration) if duration else 0

    return {
        "sp_ok": True,
        "sp_active": True,
        "sp_playing": bool(data.get("is_playing")),
        "sp_track": item.get("name", "")[:40],
        "sp_artist": artists[:40],
        "sp_progress": max(0, min(100, pct)),
    }


def control(action):
    """action: 'playpause' | 'next' | 'previous'. Returns (ok, message)."""
    if action == "next":
        _, error = _api("/me/player/next", method="POST")
    elif action == "previous":
        _, error = _api("/me/player/previous", method="POST")
    elif action == "playpause":
        state, error = _api("/me/player")
        if error:
            return False, error
        playing = bool(state and state.get("is_playing"))
        _, error = _api("/me/player/pause" if playing else "/me/player/play",
                        method="PUT")
    else:
        return False, "unknown action"
    return (error is None), (error or "ok")


# ------------------------------------------------------------ login (once)
class _CallbackHandler(BaseHTTPRequestHandler):
    code = None
    state = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        _CallbackHandler.code = (params.get("code") or [None])[0]
        _CallbackHandler.state = (params.get("state") or [None])[0]
        message = ("Desky is connected. You can close this tab."
                   if _CallbackHandler.code else
                   "Authorization failed or was denied.")
        body = f"<html><body><h2>{message}</h2></body></html>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def login():
    cid = client_id()
    if not cid:
        print(f"No Client ID found. Put it in {CLIENT_FILE}:")
        print("    echo 'YOUR_CLIENT_ID' > ~/.desky-spotify-client")
        return

    verifier = secrets.token_urlsafe(64)[:96]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    state = secrets.token_urlsafe(16)

    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": cid,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
    })

    server = HTTPServer(("127.0.0.1", REDIRECT_PORT), _CallbackHandler)
    print("Opening your browser to approve access...")
    print("If nothing opens, paste this into a browser:\n")
    print(url + "\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    server.handle_request()          # serves exactly one callback, then stops
    server.server_close()

    if not _CallbackHandler.code:
        print("No authorization code came back. Nothing saved.")
        return
    if _CallbackHandler.state != state:
        print("State mismatch -- aborting for safety.")
        return

    try:
        tokens = _post_form(TOKEN_URL, {
            "grant_type": "authorization_code",
            "code": _CallbackHandler.code,
            "redirect_uri": REDIRECT_URI,
            "client_id": cid,
            "code_verifier": verifier,
        })
    except urllib.error.HTTPError as exc:
        print("Token exchange failed:", exc.read().decode(errors="replace"))
        return

    save_tokens({
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_at": time.time() + int(tokens.get("expires_in", 3600)),
    })
    print(f"Saved to {TOKENS_FILE}")

    state_now = now_playing()
    if state_now["sp_active"]:
        print(f"Now playing: {state_now['sp_track']} - {state_now['sp_artist']}")
    else:
        print("Connected. Nothing is playing right now.")


if __name__ == "__main__":
    login()
