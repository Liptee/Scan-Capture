from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass
from typing import Sequence

from .device_info import DMM_37UX252_ML, DeviceSpec
from .modes import CaptureMode, static_preset_modes
from .raw_writer import RawCaptureMetadata, utc_now_iso, write_raw_capture

SUPPORTED_PLATFORMS = ("win32", "linux", "linux2")


class PlatformNotSupportedError(RuntimeError):
    pass


class BackendNotAvailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConnectedDeviceInfo:
    model: str
    serial: str
    vendor: str
    spec: DeviceSpec


@dataclass(frozen=True)
class ModeInfo:
    mode: CaptureMode
    source: str
    pixel_formats: tuple[str, ...]


def ensure_platform_supported() -> None:
    if sys.platform not in SUPPORTED_PLATFORMS:
        raise PlatformNotSupportedError(
            "IC Imaging Control 4 supports Windows and Linux only. "
            "macOS is not supported by the official GenTL driver for USB3 Vision cameras. "
            "Run capture on Windows or Linux with the IC4 GenTL USB3 Vision driver installed."
        )


def import_ic4():
    ensure_platform_supported()
    try:
        import imagingcontrol4 as ic4
    except ImportError as exc:
        raise BackendNotAvailableError(
            "Package 'imagingcontrol4' is not installed. "
            "Install it with: python -m pip install imagingcontrol4"
        ) from exc
    return ic4


def init_library():
    ic4 = import_ic4()
    ic4.Library.init()
    return ic4


def shutdown_library(ic4) -> None:
    ic4.Library.exit()


def _read_vendor_from_property_map(prop_map, ic4, default: str) -> str:
    try:
        value = prop_map.get_value(ic4.PropId.DEVICE_VENDOR_NAME)
        if value:
            return str(value)
    except Exception:
        pass
    return default


def _align_integer_property(value: int, prop) -> int:
    if prop is None:
        return value
    try:
        increment_mode = prop.increment_mode
        mode_name = increment_mode.name if hasattr(increment_mode, "name") else str(increment_mode)
        if mode_name == "INCREMENT":
            increment = max(1, int(prop.increment))
            value -= value % increment
    except Exception:
        pass
    return value


def list_connected_devices(ic4) -> list[ConnectedDeviceInfo]:
    devices: list[ConnectedDeviceInfo] = []
    for device in ic4.DeviceEnum.devices():
        model = device.model_name or "unknown"
        serial = device.serial or "unknown"
        devices.append(
            ConnectedDeviceInfo(
                model=model,
                serial=serial,
                vendor=DMM_37UX252_ML.vendor,
                spec=DMM_37UX252_ML,
            )
        )
    return devices


def open_device(ic4, serial: str | None = None):
    devices = ic4.DeviceEnum.devices()
    if not devices:
        raise RuntimeError("No Imaging Source cameras found")

    if serial is None:
        return devices[0]

    serial_lower = serial.lower()
    for device in devices:
        if device.serial and device.serial.lower() == serial_lower:
            return device
        if device.model_name and serial_lower in device.model_name.lower():
            return device

    available = ", ".join(
        f"{device.model_name or 'unknown'} [{device.serial or 'no-serial'}]"
        for device in devices
    )
    raise RuntimeError(f"Camera with serial/model '{serial}' not found. Available: {available}")


def _safe_find_float(prop_map, prop_id: str):
    try:
        return prop_map.find_float(prop_id)
    except Exception:
        return None


def _safe_find_integer(prop_map, prop_id: str):
    try:
        return prop_map.find_integer(prop_id)
    except Exception:
        return None


def _safe_find_enumeration(prop_map, prop_id: str):
    try:
        return prop_map.find_enumeration(prop_id)
    except Exception:
        return None


def _safe_prop_increment(prop):
    try:
        return prop.increment
    except Exception:
        return None


def _safe_integer_limits(prop) -> dict | None:
    if prop is None:
        return None
    try:
        return {
            "min": int(prop.minimum),
            "max": int(prop.maximum),
            "increment": _safe_prop_increment(prop),
        }
    except Exception:
        return None


def _safe_float_limits(prop) -> dict | None:
    if prop is None:
        return None
    try:
        return {
            "min": float(prop.minimum),
            "max": float(prop.maximum),
            "increment": _safe_prop_increment(prop),
        }
    except Exception:
        return None


def _safe_integer_range(prop) -> tuple[int, int] | None:
    if prop is None:
        return None
    try:
        return int(prop.minimum), int(prop.maximum)
    except Exception:
        return None


def _safe_float_range(prop) -> tuple[float, float] | None:
    if prop is None:
        return None
    try:
        return float(prop.minimum), float(prop.maximum)
    except Exception:
        return None


def enumerate_live_modes(prop_map) -> list[ModeInfo]:
    try:
        pixel_formats: list[str] = []
        pixel_format_prop = _safe_find_enumeration(prop_map, "PixelFormat")
        if pixel_format_prop is not None:
            pixel_formats = [entry.name for entry in pixel_format_prop.entries]

        width_prop = _safe_find_integer(prop_map, "Width")
        height_prop = _safe_find_integer(prop_map, "Height")
        fps_prop = _safe_find_float(prop_map, "AcquisitionFrameRate")

        width_range = _safe_integer_range(width_prop)
        height_range = _safe_integer_range(height_prop)
        fps_range = _safe_float_range(fps_prop)

        modes: list[ModeInfo] = []

        if width_range and height_range and fps_range:
            width_min, width_max = width_range
            height_min, height_max = height_range
            fps_min, fps_max = fps_range

            width_values = {width_max, width_max // 2, 1280, 1024, 800, 640}
            height_values = {height_max, height_max // 2, 1024, 768, 600, 480}
            fps_values = {
                fps_max,
                min(60.0, fps_max),
                min(30.0, fps_max),
                min(15.0, fps_max),
            }

            seen: set[str] = set()
            for width in sorted(width_values):
                width = _align_integer_property(
                    max(width_min, min(width_max, width)),
                    width_prop,
                )
                for height in sorted(height_values):
                    height = _align_integer_property(
                        max(height_min, min(height_max, height)),
                        height_prop,
                    )
                    for fps in sorted(fps_values, reverse=True):
                        fps = max(fps_min, min(fps_max, fps))
                        mode = CaptureMode(width=width, height=height, fps=fps)
                        key = mode.as_string()
                        if key in seen:
                            continue
                        seen.add(key)
                        modes.append(
                            ModeInfo(
                                mode=mode,
                                source="device-range",
                                pixel_formats=tuple(pixel_formats or DMM_37UX252_ML.pixel_formats),
                            )
                        )

        if modes:
            return modes
    except Exception:
        pass

    return [
        ModeInfo(
            mode=mode,
            source="preset",
            pixel_formats=tuple(DMM_37UX252_ML.pixel_formats),
        )
        for mode in static_preset_modes()
    ]


def resolve_pixel_format(ic4, pixel_format: str):
    normalized = pixel_format.strip().lower()
    if normalized in {"mono8", "8"}:
        return ic4.PixelFormat.Mono8
    if normalized in {"mono16", "16"}:
        return ic4.PixelFormat.Mono16
    raise ValueError("pixel_format must be 'mono8' or 'mono16'")


def apply_capture_settings(
    ic4,
    prop_map,
    mode: CaptureMode,
    exposure_us: float,
    pixel_format: str,
) -> None:
    prop_map.set_value(ic4.PropId.PIXEL_FORMAT, resolve_pixel_format(ic4, pixel_format))
    prop_map.set_value(ic4.PropId.WIDTH, mode.width)
    prop_map.set_value(ic4.PropId.HEIGHT, mode.height)

    try:
        prop_map.set_value(ic4.PropId.OFFSET_AUTO_CENTER, "Off")
        prop_map.set_value(ic4.PropId.OFFSET_X, 0)
        prop_map.set_value(ic4.PropId.OFFSET_Y, 0)
    except Exception:
        pass

    fps_prop = _safe_find_float(prop_map, ic4.PropId.ACQUISITION_FRAME_RATE)
    fps_range = _safe_float_range(fps_prop)
    if fps_range is not None:
        fps_min, fps_max = fps_range
        target_fps = max(fps_min, min(fps_max, mode.fps))
        try:
            prop_map.set_value(ic4.PropId.ACQUISITION_FRAME_RATE, target_fps)
        except Exception:
            pass

    prop_map.set_value(ic4.PropId.EXPOSURE_AUTO, "Off")
    prop_map.set_value(ic4.PropId.EXPOSURE_TIME, float(exposure_us))


def image_buffer_to_bytes(image) -> bytes:
    return ctypes.string_at(image.pointer, image.buffer_size)


def capture_to_raw(
    mode: CaptureMode,
    duration_s: float,
    exposure_us: float,
    output_path,
    pixel_format: str = "mono16",
    serial: str | None = None,
) -> tuple:
    ic4 = init_library()
    grabber = ic4.Grabber()
    sink = ic4.SnapSink()

    try:
        device_info = open_device(ic4, serial=serial)
        grabber.device_open(device_info)
        prop_map = grabber.device_property_map

        apply_capture_settings(ic4, prop_map, mode, exposure_us, pixel_format)
        grabber.stream_setup(sink, setup_option=ic4.StreamSetupOption.ACQUISITION_START)

        frame_count = max(1, int(round(duration_s * mode.fps)))
        timeout_ms = int(duration_s * 1000) + 5000
        images = sink.snap_sequence(frame_count, timeout_ms)

        if not images:
            raise RuntimeError("No frames received from camera")

        frames = [image_buffer_to_bytes(image) for image in images]
        first_image = images[0]
        image_type = first_image.image_type
        frame_size = first_image.buffer_size
        pitch = first_image.pitch
        timestamps = [image.meta_data.device_timestamp_ns for image in images]
        frame_numbers = [image.meta_data.device_frame_number for image in images]

        bits_per_pixel = 16 if pixel_format.lower() in {"mono16", "16"} else 8
        metadata = RawCaptureMetadata(
            device_model=device_info.model_name or DMM_37UX252_ML.model,
            device_serial=device_info.serial or "unknown",
            mode=mode.as_string(),
            width=image_type.width,
            height=image_type.height,
            fps=mode.fps,
            duration_s=duration_s,
            exposure_us=exposure_us,
            pixel_format=image_type.pixel_format.name,
            bits_per_pixel=bits_per_pixel,
            frame_count=len(frames),
            frame_size_bytes=frame_size,
            pitch_bytes=pitch,
            created_at_utc=utc_now_iso(),
            frame_timestamps_ns=timestamps,
            frame_numbers=frame_numbers,
        )

        return write_raw_capture(output_path, frames, metadata)
    finally:
        try:
            grabber.stream_stop()
        except Exception:
            pass
        try:
            grabber.device_close()
        except Exception:
            pass
        shutdown_library(ic4)


def probe_device(serial: str | None = None, ic4=None) -> tuple[ConnectedDeviceInfo, list[ModeInfo], dict]:
    owns_library = ic4 is None
    if ic4 is None:
        ic4 = init_library()
    grabber = ic4.Grabber()
    try:
        device_info = open_device(ic4, serial=serial)
        grabber.device_open(device_info)
        prop_map = grabber.device_property_map
        modes = enumerate_live_modes(prop_map)

        width_prop = _safe_find_integer(prop_map, "Width")
        height_prop = _safe_find_integer(prop_map, "Height")
        fps_prop = _safe_find_float(prop_map, "AcquisitionFrameRate")
        exposure_prop = _safe_find_float(prop_map, "ExposureTime")
        pixel_format_prop = _safe_find_enumeration(prop_map, "PixelFormat")

        limits = {
            "width": _safe_integer_limits(width_prop),
            "height": _safe_integer_limits(height_prop),
            "fps": _safe_float_limits(fps_prop),
            "exposure_us": _safe_float_limits(exposure_prop),
            "pixel_formats": []
            if pixel_format_prop is None
            else [entry.name for entry in pixel_format_prop.entries],
        }

        connected = ConnectedDeviceInfo(
            model=device_info.model_name or DMM_37UX252_ML.model,
            serial=device_info.serial or "unknown",
            vendor=_read_vendor_from_property_map(prop_map, ic4, DMM_37UX252_ML.vendor),
            spec=DMM_37UX252_ML,
        )
        return connected, modes, limits
    finally:
        try:
            grabber.device_close()
        except Exception:
            pass
        if owns_library:
            shutdown_library(ic4)
