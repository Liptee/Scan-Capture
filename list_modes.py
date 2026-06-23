#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from tis_camera.device_info import DMM_37UX252_ML, KNOWN_PRESET_MODES
from tis_camera.ic4_backend import (
    BackendNotAvailableError,
    PlatformNotSupportedError,
    list_connected_devices,
    probe_device,
    init_library,
    shutdown_library,
)
from tis_camera.modes import static_preset_modes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List capture modes for The Imaging Source cameras."
    )
    parser.add_argument(
        "--serial",
        default=None,
        help="Camera serial number or model substring",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Show documented presets without opening the camera",
    )
    return parser


def print_offline_modes(as_json: bool) -> int:
    payload = {
        "device": {
            "model": DMM_37UX252_ML.model,
            "vendor": DMM_37UX252_ML.vendor,
            "sensor": DMM_37UX252_ML.sensor,
            "max_resolution": f"{DMM_37UX252_ML.max_width}x{DMM_37UX252_ML.max_height}",
            "max_fps": DMM_37UX252_ML.max_fps,
            "pixel_formats": list(DMM_37UX252_ML.pixel_formats),
            "exposure_us": {
                "min": DMM_37UX252_ML.exposure_min_us,
                "max": DMM_37UX252_ML.exposure_max_us,
            },
        },
        "modes": [
            {
                "mode": mode.as_string(),
                "width": mode.width,
                "height": mode.height,
                "fps": mode.fps,
                "source": "preset",
            }
            for mode in static_preset_modes()
        ],
        "note": (
            "Offline presets for DMM 37UX252-ML. "
            "Run without --offline on Windows/Linux with IC4 driver installed "
            "to query live device limits."
        ),
    }

    if as_json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Model: {DMM_37UX252_ML.model}")
    print(f"Vendor: {DMM_37UX252_ML.vendor}")
    print(f"Sensor: {DMM_37UX252_ML.sensor} ({DMM_37UX252_ML.shutter} shutter)")
    print(
        f"Max resolution: {DMM_37UX252_ML.max_width}x{DMM_37UX252_ML.max_height} "
        f"@ {DMM_37UX252_ML.max_fps:g} fps"
    )
    print(f"Pixel formats: {', '.join(DMM_37UX252_ML.pixel_formats)}")
    print(f"Exposure range: {DMM_37UX252_ML.exposure_min_us:g} .. {DMM_37UX252_ML.exposure_max_us:g} us")
    print()
    print("Preset modes:")
    for width, height, fps in KNOWN_PRESET_MODES:
        print(f"  {width}x{height}@{fps:g}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.offline:
        return print_offline_modes(args.json)

    try:
        ic4 = init_library()
    except PlatformNotSupportedError as exc:
        print(exc, file=sys.stderr)
        print("Falling back to offline presets. Use: list_modes.py --offline", file=sys.stderr)
        return print_offline_modes(args.json)
    except BackendNotAvailableError as exc:
        print(exc, file=sys.stderr)
        print("Falling back to offline presets. Use: list_modes.py --offline", file=sys.stderr)
        return print_offline_modes(args.json)

    try:
        devices = list_connected_devices(ic4)
        if not devices:
            print("No cameras found", file=sys.stderr)
            return 1

        connected, modes, limits = probe_device(serial=args.serial)
        payload = {
            "device": {
                "model": connected.model,
                "serial": connected.serial,
                "vendor": connected.vendor,
                "sensor": connected.spec.sensor,
                "limits": limits,
            },
            "modes": [
                {
                    "mode": mode_info.mode.as_string(),
                    "width": mode_info.mode.width,
                    "height": mode_info.mode.height,
                    "fps": mode_info.mode.fps,
                    "source": mode_info.source,
                    "pixel_formats": list(mode_info.pixel_formats),
                }
                for mode_info in modes
            ],
        }

        if args.json:
            print(json.dumps(payload, indent=2))
            return 0

        print(f"Model: {connected.model}")
        print(f"Serial: {connected.serial}")
        print(f"Vendor: {connected.vendor}")
        print(f"Sensor: {connected.spec.sensor}")
        if limits["width"]:
            print(
                "Width range: "
                f"{limits['width']['min']} .. {limits['width']['max']} "
                f"(step {limits['width']['increment']})"
            )
        if limits["height"]:
            print(
                "Height range: "
                f"{limits['height']['min']} .. {limits['height']['max']} "
                f"(step {limits['height']['increment']})"
            )
        if limits["fps"]:
            print(
                "FPS range: "
                f"{limits['fps']['min']:g} .. {limits['fps']['max']:g} "
                f"(step {limits['fps']['increment']:g})"
            )
        if limits["exposure_us"]:
            print(
                "Exposure range: "
                f"{limits['exposure_us']['min']:g} .. {limits['exposure_us']['max']:g} us"
            )
        if limits["pixel_formats"]:
            print(f"Pixel formats: {', '.join(limits['pixel_formats'])}")
        print()
        print("Modes:")
        for mode_info in modes:
            print(f"  {mode_info.mode.as_string()} [{mode_info.source}]")
        return 0
    finally:
        shutdown_library(ic4)


if __name__ == "__main__":
    raise SystemExit(main())
