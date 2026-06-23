from __future__ import annotations

from bisect import bisect_left
from typing import Literal, TypeAlias

import colour
import numpy as np
import numpy.typing as npt
from scipy import ndimage
from scipy.interpolate import interp1d

from hs.core.hs_image import HSImage

U8Array: TypeAlias = npt.NDArray[np.uint8]
U16Array: TypeAlias = npt.NDArray[np.uint16]
F32Array: TypeAlias = npt.NDArray[np.float32]
F64Array: TypeAlias = npt.NDArray[np.float64]


def hsi_to_rgb(
    hsi: HSImage,
    gray_patch: F32Array | None = None,
    awb: Literal["grey-world", "grey-edge", "simplified"] | None = None,
    dtype: type = np.uint8,
) -> F64Array:
    match dtype:
        case np.uint8:
            data = _uint8_to_float32(hsi.data)
        case np.uint16:
            data = _uint16_to_float32(hsi.data)
        case np.float32 | np.float64:
            data = hsi.data
            assert data.max() <= 1.0 and data.min() >= 0.0, "data out of range [0, 1]"
        case _:
            raise ValueError(f"unknown dtype: {dtype}")

    if gray_patch is not None:
        assert gray_patch.max() <= 1 and gray_patch.min() > 0, "patch data out of range [0, 1]"
        assert gray_patch.shape[0] == data.shape[2], (
            f"patch channels {gray_patch.shape[0]} != image channels {data.shape[2]}"
        )
        data /= gray_patch

    if awb == "simplified":
        if not hsi.wavelengths:
            raise ValueError("simplified RGB requires wavelengths metadata")
        return simplified_rgb(data, hsi.wavelengths).clip(0, 1)

    if not hsi.wavelengths:
        raise ValueError("RGB synthesis requires wavelengths metadata")

    xyz = _hsi_to_xyz(data, hsi.wavelengths)
    srgb = colour.XYZ_to_sRGB(xyz)

    if awb is not None:
        srgb = AWB[awb](srgb)
    return srgb.clip(0, 1)


def simplified_rgb(hsi: F32Array, wavelengths: list[int]) -> F64Array:
    illuminant = 100
    b_idx = bisect_left(wavelengths, 460)
    g_idx = bisect_left(wavelengths, 531)
    r_idx = bisect_left(wavelengths, 705)
    bgr = np.dstack((hsi[:, :, r_idx], hsi[:, :, g_idx], hsi[:, :, b_idx]))
    k = illuminant * np.max(bgr[..., 0])
    return bgr * k


def _hsi_to_xyz(hsi: F32Array, wavelengths: list[int]) -> F64Array:
    cmfs = colour.MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
    illuminant = 100
    cmfs_wavelengths = cmfs.shape.range()

    f_0 = interp1d(cmfs_wavelengths, cmfs.values[:, 0], bounds_error=False, fill_value=0.0)
    f_1 = interp1d(cmfs_wavelengths, cmfs.values[:, 1], bounds_error=False, fill_value=0.0)
    f_2 = interp1d(cmfs_wavelengths, cmfs.values[:, 2], bounds_error=False, fill_value=0.0)

    xyz_0 = f_0(wavelengths)
    xyz_1 = f_1(wavelengths)
    xyz_2 = f_2(wavelengths)
    xyz_b = np.array([xyz_0, xyz_1, xyz_2]).T

    r, c, w = hsi.shape
    flat = hsi.reshape(r * c, w)
    k = 100 / np.maximum(np.sum(xyz_b[..., 1] * illuminant), 0.0001)
    xyz = k * np.dot(flat * illuminant, xyz_b)
    return xyz.reshape(r, c, 3) / 100


def _grey_world(srgb: F64Array) -> F64Array:
    return srgb * (srgb.mean() / srgb.mean(axis=(0, 1)))


def _grey_edge(srgb: F64Array) -> F64Array:
    def grad(channel: F64Array) -> F64Array:
        sx = ndimage.sobel(channel, axis=0, mode="constant")
        sy = ndimage.sobel(channel, axis=1, mode="constant")
        return np.hypot(sx, sy)

    mean_grad_r = np.mean(grad(srgb[..., 0]))
    mean_grad_g = np.mean(grad(srgb[..., 1]))
    mean_grad_b = np.mean(grad(srgb[..., 2]))
    mean_grad_avg = (mean_grad_r + mean_grad_g + mean_grad_b) / 3.0
    out = np.zeros_like(srgb)
    out[..., 0] = srgb[..., 0] * (mean_grad_avg / mean_grad_r)
    out[..., 1] = srgb[..., 1] * (mean_grad_avg / mean_grad_g)
    out[..., 2] = srgb[..., 2] * (mean_grad_avg / mean_grad_b)
    return out


AWB: dict[str, object] = {"grey-world": _grey_world, "grey-edge": _grey_edge}


def _uint8_to_float32(data: U8Array) -> F32Array:
    assert data.max() <= 255 and data.min() >= 0, "data out of range [0, 255]"
    return (data / 255.0).astype(np.float32)


def _uint16_to_float32(data: U16Array) -> F32Array:
    assert data.max() <= 65535 and data.min() >= 0, "data out of range [0, 65535]"
    return (data / 65535.0).astype(np.float32)
