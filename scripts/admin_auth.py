from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "data" / "config"
AUTH_FILE = CONFIG_DIR / "admin_auth.json"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"
PBKDF2_ITERATIONS = 260_000


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hash_password(password: str, salt: bytes | None = None) -> dict[str, str | int]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": PBKDF2_ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "password_hash": base64.b64encode(digest).decode("ascii"),
    }


def ensure_auth_file() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if AUTH_FILE.exists():
        return load_auth()

    payload = {
        "username": DEFAULT_USERNAME,
        **hash_password(DEFAULT_PASSWORD),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "must_change_password": True,
    }
    save_auth(payload)
    return payload


def load_auth() -> dict:
    return json.loads(AUTH_FILE.read_text(encoding="utf-8"))


def save_auth(payload: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def verify_login(username: str, password: str) -> bool:
    payload = ensure_auth_file()
    if username != payload.get("username"):
        return False

    salt = base64.b64decode(payload["salt"])
    expected = base64.b64decode(payload["password_hash"])
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(payload.get("iterations", PBKDF2_ITERATIONS)),
    )
    return hmac.compare_digest(actual, expected)


def change_password(current_password: str, new_password: str) -> tuple[bool, str]:
    payload = ensure_auth_file()
    if not verify_login(str(payload.get("username", DEFAULT_USERNAME)), current_password):
        return False, "Current password is incorrect."
    return reset_password(new_password)


def reset_password(new_password: str, username: str = DEFAULT_USERNAME) -> tuple[bool, str]:
    if len(new_password) < 5:
        return False, "Password must be at least 5 characters."

    payload = {
        "username": username,
        **hash_password(new_password),
        "created_at": ensure_auth_file().get("created_at", utc_now()),
        "updated_at": utc_now(),
        "must_change_password": new_password == DEFAULT_PASSWORD,
    }
    save_auth(payload)
    return True, "Password updated."


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset Indian Heritage AI admin password.")
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    args = parser.parse_args()

    ok, message = reset_password(args.password, username=args.username)
    if not ok:
        raise SystemExit(message)
    print(message)
    print(f"Username: {args.username}")
    print(f"Auth file: {AUTH_FILE}")


if __name__ == "__main__":
    main()
