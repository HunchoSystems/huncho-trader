#!/usr/bin/env python3
"""Kalshi trade API v2 signed client.

Auth comes from the environment, never from this repo:
  KALSHI_KEY_ID          your API key id (required)
  KALSHI_KEY_PATH        path to the base64 private key file (default ~/.kalshi/key.b64)
  KALSHI_PRIVATE_KEY_B64 raw base64 private key (alternative to KEY_PATH)

Usage:
  kalshi_client.py "/trade-api/v2/<path>" [--raw]                        # GET
  kalshi_client.py "/trade-api/v2/portfolio/orders" POST '<json>' [--raw]  # POST
Order body example (prices in cents):
  {"ticker":"KXETH15M-...","action":"buy","side":"yes","count":5,"type":"limit",
   "yes_price":36,"client_order_id":"<uuid>"}
"""
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

HOST = "https://api.elections.kalshi.com"


def _config():
    key_id = os.environ.get("KALSHI_KEY_ID", "").strip()
    if not key_id:
        raise SystemExit("Set KALSHI_KEY_ID (see docs/SETUP.md).")
    key_b64 = os.environ.get("KALSHI_PRIVATE_KEY_B64", "").strip()
    if not key_b64:
        key_path = os.environ.get(
            "KALSHI_KEY_PATH", os.path.expanduser("~/.kalshi/key.b64"))
        try:
            with open(key_path) as f:
                key_b64 = f.read().strip()
        except OSError:
            raise SystemExit(
                f"Private key not found at {key_path}. "
                "Set KALSHI_KEY_PATH or KALSHI_PRIVATE_KEY_B64 (see docs/SETUP.md).")
    pem = ("-----BEGIN RSA PRIVATE KEY-----\n" + key_b64 +
           "\n-----END RSA PRIVATE KEY-----\n")
    key = serialization.load_pem_private_key(pem.encode(), password=None)
    return key_id, key


def signed_headers(method, path, key_id, key):
    ts = str(int(time.time() * 1000))
    bare = path.split("?")[0]  # sign bare path only; query params unsigned
    msg = (ts + method + bare).encode()
    sig = key.sign(
        msg,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
        "Content-Type": "application/json",
    }


def kalshi_get(path):
    """Signed GET, returns parsed JSON. Importable for screen.py / score.py."""
    key_id, key = _config()
    req = urllib.request.Request(
        HOST + path, headers=signed_headers("GET", path, key_id, key),
        method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GET {path}: HTTP {e.code} {e.read().decode()[:300]}")


def kalshi_post(path, body):
    key_id, key = _config()
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        HOST + path, data=data,
        headers=signed_headers("POST", path, key_id, key), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]


if __name__ == "__main__":
    raw = "--raw" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "--raw"]
    path = args[0] if len(args) > 0 else "/trade-api/v2/portfolio/balance"
    method = args[1].upper() if len(args) > 1 else "GET"
    body = json.loads(args[2]) if len(args) > 2 else None
    if method == "GET":
        resp, code = kalshi_get(path), 200
    else:
        code, resp = kalshi_post(path, body)
    if raw:
        print(json.dumps(resp) if isinstance(resp, dict)
              else json.dumps({"http_status": code, "error": resp}))
    else:
        print(f"HTTP {code}")
        print(json.dumps(resp, indent=1)[:4000] if isinstance(resp, dict) else resp)
