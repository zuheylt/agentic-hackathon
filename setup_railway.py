"""
Runs once at container startup on Railway.
Creates the ATK config from environment variables.
"""

import os
import shutil
from pathlib import Path


def setup_atk():
    api_key    = os.environ.get("OKX_API_KEY", "")
    secret_key = os.environ.get("OKX_SECRET_KEY", "")
    passphrase = os.environ.get("OKX_PASSPHRASE", "")

    if not api_key:
        print("[setup] OKX_API_KEY not set — ATK will run in dry-run mode.")
        return

    config_dir = Path.home() / ".okx"
    config_dir.mkdir(parents=True, exist_ok=True)

    config = (
        f"[profiles.default]\n"
        f'apiKey = "{api_key}"\n'
        f'secretKey = "{secret_key}"\n'
        f'passphrase = "{passphrase}"\n'
        f"demo = true\n"
    )
    (config_dir / "config.toml").write_text(config)
    print(f"[setup] ATK config written to {config_dir / 'config.toml'}")


def verify_atk():
    bin_path = shutil.which("okx")
    if bin_path:
        print(f"[setup] ATK binary found: {bin_path}")
    else:
        print("[setup] ATK binary not found — live OKX features unavailable.")


if __name__ == "__main__":
    setup_atk()
    verify_atk()
    print("[setup] Ready.")
