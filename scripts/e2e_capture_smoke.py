"""E2E smoke: real stereo pair → capture session → analysis job → pipeline log.

Drives the same REST endpoints as the desktop capture screen, but headless, so the
real CV pipeline (rectification → IGEV++/SGBM depth → point cloud → SAM3) can be
exercised with a saved ZED 2 frame pair without clicking through the UI.

    desktop\\.venv\\Scripts\\python.exe scripts\\e2e_capture_smoke.py --password changeme

Requires: stack up, dev seed enabled (ENABLE_DEV_SEED), frames captured to data/raw
(see README in scripts/register_zed_device.py for the device/calibration step — it
is invoked automatically here when the serial is not registered yet).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "desktop"))

from zmetrics_desktop.capture.zed_calibration import (  # noqa: E402
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


def ensure_device(client: httpx.Client, serial: str, conf_path: Path, resolution: str) -> tuple[str, str]:
    """Return (device_id, calibration_id), creating both if missing."""
    devices = client.get("/devices", params={"page_size": 100}).json()["items"]
    device = next((d for d in devices if d["serial_number"] == serial), None)
    if device is None:
        device = client.post(
            "/devices",
            json={"serial_number": serial, "model": "ZED 2",
                  "notes": f"Factory calibration ({resolution})"},
        ).raise_for_status().json()
        print(f"device created: {device['id']}")
    else:
        print(f"device exists: {device['id']}")

    cals = client.get(f"/devices/{device['id']}/calibrations", params={"page_size": 100}).json()["items"]
    cal = next((c for c in cals if c["image_width_px"] == 2208), None)
    if cal is None:
        payload = build_calibration_payload(parse_zed_conf(conf_path.read_text()), resolution)
        cal = client.post(f"/devices/{device['id']}/calibrations", json=payload).raise_for_status().json()
        print(f"calibration created: {cal['id']} (baseline {cal['baseline_mm']} mm)")
    else:
        print(f"calibration exists: {cal['id']}")
    return device["id"], cal["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--keycloak-url", default="http://localhost:8080")
    parser.add_argument("--realm", default="zmetrics")
    parser.add_argument("--client-id", default="zmetrics-mobile")
    parser.add_argument("--username", default="admin-user")
    parser.add_argument("--password", required=True)
    parser.add_argument("--serial", default="21907252")
    parser.add_argument("--conf", default=str(REPO / "infra" / "zed_calibration_SN21907252.conf"))
    parser.add_argument("--resolution", default="2K")
    parser.add_argument("--left", default=str(REPO / "data" / "raw" / "zed_test_left.jpg"))
    parser.add_argument("--right", default=str(REPO / "data" / "raw" / "zed_test_right.jpg"))
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()

    client = httpx.Client(
        base_url=args.backend_url,
        headers={"Authorization": f"Bearer {get_token(args)}"},
        timeout=60,
    )

    seed = client.post("/admin/dev-seed").raise_for_status().json()
    print(f"seed: quarry {seed['quarry_id']}, passport {seed['passport_id']} "
          f"(existed: {seed['already_existed']})")

    device_id, calibration_id = ensure_device(client, args.serial, Path(args.conf), args.resolution)

    session = client.post(
        f"/quarries/{seed['quarry_id']}/passports/{seed['passport_id']}/blast-event/capture-sessions",
        json={"device_id": device_id, "calibration_id": calibration_id},
    ).raise_for_status().json()
    print(f"capture session: {session['id']}")

    for artifact_type, path in [("left_frame", Path(args.left)), ("right_frame", Path(args.right))]:
        client.post(
            f"/capture-sessions/{session['id']}/artifacts",
            data={"artifact_type": artifact_type, "frame_index": "0"},
            files={"file": (path.name, path.read_bytes(), "image/jpeg")},
        ).raise_for_status()
        print(f"uploaded {artifact_type} ({path.stat().st_size // 1024} KiB)")

    job = client.post(f"/captures/{session['id']}/jobs", json={}).raise_for_status().json()
    print(f"job queued: {job['id']}")

    deadline = time.monotonic() + args.timeout_s
    while time.monotonic() < deadline:
        job = client.get(f"/captures/{session['id']}/jobs/{job['id']}").raise_for_status().json()
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(5)

    print(f"\njob status: {job['status']}")
    if job.get("error_message"):
        print(f"error: {job['error_message']}")
    for step in (job.get("pipeline_log") or {}).get("steps", []):
        meta = {k: v for k, v in (step.get("metadata") or {}).items()}
        print(f"  {step['status']:5} {step['name']:18} {step['duration_s']:8.2f}s  {json.dumps(meta, ensure_ascii=False)}")

    if job["status"] == "completed":
        result = client.get(f"/captures/{session['id']}/jobs/{job['id']}/result").raise_for_status().json()
        print(f"\nP10/P50/P80: {result['p10_mm']} / {result['p50_mm']} / {result['p80_mm']} mm")
        print(f"confidence: {result['confidence_score']} — {result.get('confidence_notes', '')}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
