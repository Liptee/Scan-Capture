#!/usr/bin/env python3
"""Quick camera connectivity check for Windows/Linux."""

from __future__ import annotations

import sys

from tis_camera.ic4_backend import (
    BackendNotAvailableError,
    PlatformNotSupportedError,
    init_library,
    list_connected_devices,
    probe_device,
    shutdown_library,
)


def main() -> int:
    try:
        ic4 = init_library()
    except (PlatformNotSupportedError, BackendNotAvailableError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        devices = list_connected_devices(ic4)
        if not devices:
            print("No Imaging Source cameras found.")
            print("Check USB connection and IC4 GenTL USB3 Vision driver.")
            return 1

        print(f"Found {len(devices)} camera(s):")
        for index, device in enumerate(devices, start=1):
            print(f"  {index}. {device.model}  serial={device.serial}")

        connected, modes, limits = probe_device(ic4=ic4)
        print()
        print("Opened successfully:")
        print(f"  Model:  {connected.model}")
        print(f"  Serial: {connected.serial}")
        print(f"  Vendor: {connected.vendor}")
        if limits.get("width"):
            print(
                "  Resolution max: "
                f"{limits['width']['max']} x {limits['height']['max']}"
            )
        if limits.get("fps"):
            print(f"  FPS max: {limits['fps']['max']:g}")
        print(f"  Modes listed: {len(modes)}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        shutdown_library(ic4)


if __name__ == "__main__":
    raise SystemExit(main())
