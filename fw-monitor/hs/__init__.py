"""
HSI core library — subset for web capture/build/viewer pipeline.

See SCOPE.md for retained modules and removed components.
"""

from hs.build_hsi.builder_params import (
    BuildParams,
    BuildUAVParams,
    HyperDevice,
    ROI,
    load_build_metadata,
    load_hyper_device,
    save_build_metadata,
    save_hyper_device,
)
from hs.build_hsi.hsi_builder import HSBuilder

hsbuilder = HSBuilder
from hs.core.hs_image import HSImage as hsimage
from hs.core.hs_image import (
    load_hsi,
    save_hsi,
    save_hsi_to_envi,
    save_hsi_to_geotiff,
)
from hs.core.hs_mask import HSMask as hsmask
from hs.core.hs_mask import load_mask, save_mask
from hs.data_complex.complexed_data import ComplexedData
from hs.viewer.color_synthesis import hsi_to_rgb

__all__ = [
    "HSBuilder",
    "hsbuilder",
    "hsimage",
    "hsmask",
    "load_hsi",
    "save_hsi",
    "save_hsi_to_geotiff",
    "save_hsi_to_envi",
    "load_mask",
    "save_mask",
    "BuildParams",
    "BuildUAVParams",
    "HyperDevice",
    "ROI",
    "load_build_metadata",
    "save_build_metadata",
    "load_hyper_device",
    "save_hyper_device",
    "ComplexedData",
    "hsi_to_rgb",
]
