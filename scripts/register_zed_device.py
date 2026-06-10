"""Register a ZED camera + its factory calibration with the backend (dev helper).

Downloads the factory calibration by serial (or reads a local .conf), converts it
via zmetrics_desktop.capture.zed_calibration, then creates the Device (reusing an
existing one on duplicate serial) and posts the Calibration.

Run from the desktop venv (it has httpx + the zmetrics_desktop package):

    desktop\\.venv\\Scripts\\python.exe scripts\\register_zed_device.py `
        --serial 21907252 --resolution 2K `
        --username admin-user --password changeme

Auth is the dev password grant (see STATUS.md); pass --client-id zmetrics-desktop
once the realm has directAccessGrantsEnabled for it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "desktop"))

from zmetrics_desktop.capture.zed_calibration import (  # noqa: E402
    CALIBRATION_URL_TEMPLATE,
    build_calibration_payload,
    parse_zed_conf,
)


def get_token(args: argparse.Namespace) -> str:
    resp = httpx.post(
        f"{args.keycloak_url}/realms/{args.realm}/protocol/openid-connect/token",
        data={
            "client_id": args.client_id,
            "grant_type": "password",
            "username": args.username,
            "password": args.password,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def load_conf_text(args: argparse.Namespace) -> str:
    if args.conf:
        return Path(args.conf).read_text(encoding="utf-8")
    url = CALIBRATION_URL_TEMPLATE.format(serial=args.serial)
    print(f"Downloading factory calibration: {url}")
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    if "[STEREO]" not in resp.text:
        raise SystemExit(f"Unexpected response from {url} — not a ZED conf file")
    return resp.text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="ZED serial number (on the sticker / USB descriptor)")
    parser.add_argument("--conf", help="Local .conf path; downloaded by serial when omitted")
    parser.add_argument("--resolution", default="2K", choices=["2K", "FHD", "HD", "VGA"])
    parser.add_argument("--model", default="ZED 2")
    parser.add_argument("--backend-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--keycloak-url", default="http://localhost:8080")
    parser.add_argument("--realm", default="zmetrics")
    parser.add_argument("--client-id", default="zmetrics-mobile")
    parser.add_argument("--username", default="admin-user")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    conf = parse_zed_conf(load_conf_text(args))
    calibration_body = build_calibration_payload(conf, args.resolution)

    client = httpx.Client(
        base_url=args.backend_url,
        headers={"Authorization": f"Bearer {get_token(args)}"},
        timeout=30,
    )

    device_resp = client.post(
        "/devices",
        json={
            "serial_number": args.serial,
            "model": args.model,
            "notes": f"Factory calibration from calib.stereolabs.com ({args.resolution})",
        },
    )
    if device_resp.status_code == 409:
        devices = client.get("/devices", params={"page_size": 100}).json()["items"]
        device = next(d for d in devices if d["serial_number"] == args.serial)
        print(f"Device already registered: {device['id']}")
    else:
        device_resp.raise_for_status()
        device = device_resp.json()
        print(f"Device created: {device['id']}")

    cal_resp = client.post(f"/devices/{device['id']}/calibrations", json=calibration_body)
    cal_resp.raise_for_status()
    cal = cal_resp.json()
    print(
        f"Calibration created: {cal['id']} "
        f"({cal['image_width_px']}x{cal['image_height_px']}, baseline {cal['baseline_mm']} mm)"
    )


if __name__ == "__main__":
    main()
