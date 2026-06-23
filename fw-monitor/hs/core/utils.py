"""
Модуль содержит вспомогательные структуры и функции
для работы классов HSImage и HSMask из пакета hs.core
"""
import json
import os
import re

from copy import copy
from pathlib import Path
from typing import Any, Dict, Callable, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field
import rasterio
import toml

from scipy.io import loadmat, savemat


def save_decorator(func: Callable):
    """
        Декоратор для создания каскада директорий к записываемому файлу
    """
    def wrapper(*args, **kwargs):
        path_file = kwargs.get("path_to_file", None)
        path_dir = os.path.dirname(path_file)
        if not os.path.exists(path_dir):
            os.makedirs(path_dir)
        func(*args, **kwargs)
    return wrapper


def load_mat(path_to_file: Union[str, Path]) -> Dict[str, Any]:
    """
    load_mat(path_to_file)

        Чтение словаря из MAT файлов

        Parameters
        ----------
        path_to_file: Union[str, Path]
            путь к файлу формата MAT

        Returns
        -------
        Dict[str, Any]
            словарь, хранящийся в MAT-файле
    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    if not path_to_file.exists():
        raise FileExistsError("File does not exists!")

    data = loadmat(path_to_file.as_posix())
    return data
# --------------------------------------------------------------------------------------------------


def load_tiff(path_to_file: Union[str, Path]) -> np.ndarray:
    """
    load_tiff(path_to_file)

        Чтение массива из TIFF файлов

        Parameters
        ----------
        path_to_file: Union[str, Path]
            путь к файлу формата TIFF

        Returns
        -------
        np.ndarray
            2D или 3D массив
    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    if not path_to_file.exists():
        raise FileExistsError("File does not exists!")

    with rasterio.open(path_to_file.as_posix()) as raster:
        band = raster.read()
        if len(band.shape) == 3:
            data = band.transpose((1, 2, 0))
        elif len(band.shape) == 2:
            data = band
        else:
            raise ValueError(f"Unsupported data shape: {band.shape}")

    return data
# --------------------------------------------------------------------------------------------------


def load_npy(path_to_file: Union[str, Path]) -> np.ndarray:
    """
    load_npy(path_to_file)

        Чтение массива из NPY файлов

        Parameters
        ----------
        path_to_file: Union[str, Path]
            путь к файлу формата NPY

        Returns
        -------
        np.ndarray
            2D или 3D массив
    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    if not path_to_file.exists():
        raise FileExistsError("File does not exists!")

    data = np.load(path_to_file.as_posix())
    return data
# --------------------------------------------------------------------------------------------------


def load_raw_dat(path_to_file: Union[str, Path],
                 dtype='uint8') -> np.ndarray:
    """
        load_raw_dat(path_to_file)

            Чтение массива из DAT или RAW файлов

            Parameters
            ----------
            path_to_file: Union[str, Path]
                путь к файлу формата DAT или RAW
            dtype: str
                тип данных
            Returns
            -------
            np.ndarray
                1D массив
    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    if not path_to_file.exists():
        raise FileExistsError("File does not exists!")

    data = np.fromfile(path_to_file.as_posix(), dtype=dtype)
    return data


@save_decorator
def save_mat(path_to_file: Union[str, Path],
             data: Dict[str, Any]):
    """
    save_mat(path_to_file, data)

        Запись массива в MAT файл

        Parameters
        ----------
        path_to_file: Union[str, Path]
            путь к записываемому файлу формата MAT
        data: Dict[str, Any]
            2D или 3D массив
    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    savemat(path_to_file.as_posix(), data)
# --------------------------------------------------------------------------------------------------


@save_decorator
def save_tiff(path_to_file: Union[str, Path],
              data: np.ndarray,
              coordinates: Dict[str, Tuple[float, float]] = None):
    """
    save_tiff(path_to_file, data, coordinates=None)

        Запись массива в TIFF файл

        Parameters
        ----------
        path_to_file: Union[str, Path]
            путь к записываемому файлу формата TIFF
        data: np.ndarray
            2D или 3D массив
        coordinates: Dict[str, Tuple[float, float]]
            координаты геопривязки массива
            требуются координаты левого верхнего угла и правого нижнего в EPSG 4326: WGS84
            {"upper_left": (latitude_float, longitude_float),
             "lower_right": (latitude_float, longitude_float)}
    """

    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    if len(data.shape) == 2:
        data = data[:, :, None]

    dt = 'uint8'
    if data.dtype.name in ('uint8', 'int8'):
        dt = 'uint8'
    elif data.dtype.name in ('uint16', 'int16'):
        dt = 'uint16'
    elif data.dtype.name in ('uint32', 'int32'):
        dt = 'uint32'
    elif data.dtype.name in ('float16', 'float32', 'float64'):
        data = data.astype('float32')
        dt = 'float32'

    d = {'driver': 'GTiff',
         'dtype': dt,
         'nodata': None,
         'height': data.shape[0],
         'width': data.shape[1],
         'count': data.shape[2],
         'interleave': 'band'}
    if coordinates:
        y1, x1 = coordinates['upper_left']
        y2, x2 = coordinates['lower_right']
        x_width, y_width = (x2 - x1) / data.shape[1], (y2 - y1) / data.shape[0]

        d['crs'] = rasterio.CRS.from_epsg(4326)
        d['transform'] = rasterio.Affine(x_width, 0.0, x1, 0.0, y_width, y1)

    with rasterio.open(path_to_file.as_posix(), 'w', **d) as dst:
        dst.write(data.transpose((2, 0, 1)))
# --------------------------------------------------------------------------------------------------


@save_decorator
def save_npy(path_to_file: Union[str, Path],
             data: np.ndarray):
    """
    save_npy(path_to_file, data)

        Запись массива в NPY файл

        Parameters
        ----------
        path_to_file: Union[str, Path]
            путь к записываемому файлу формата NPY
        data: np.ndarray
            2D или 3D массив

    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    np.save(path_to_file.as_posix(), data)
# --------------------------------------------------------------------------------------------------


def load_json(path_to_file: Union[str, Path]) -> Dict[str, Any]:
    """
    load_json(path_to_file)

        Чтение данных из JSON файла.
        Возвращает словарь данных

        Parameters
        ----------
        path_to_file: Union[str, Path]
            путь к файлу формата JSON

        Returns
        -------
        Dict[str, Any]
    """

    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    with open(path_to_file.as_posix(), encoding='utf-8') as f:
        data = json.load(f)

    return data


def load_toml(path_to_file: Union[str, Path]) -> Dict[str, Any]:
    """
    load_toml(path_to_file)

        Чтение данных из TOML файла.
        Возвращает словарь данных

        Parameters
        ----------
        path_to_file: Union[str, Path]
            путь к файлу формата TOML

        Returns
        -------
        Dict[str, Any]
    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    with open(path_to_file.as_posix(), encoding='utf-8') as f:
        data = toml.load(f)

    return data


def save_json(path_to_file: Union[str, Path],
              data: Dict[str, Any]):
    """
    save_json(path_to_file, data)

        Запись данных в JSON файл

        Parameters
        ----------
        path_to_file: Union[str, Path]
            путь к записываемому файлу формата JSON
        data: Dict[str, Any]
            словарь данных

    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    with open(path_to_file.as_posix(), 'w', encoding='utf-8') as outfile:
        outfile.write(json.dumps(data, indent=4))


def save_toml(path_to_file: Union[str, Path],
              data: Dict[str, Any]):
    """
    save_toml(path_to_file, data)

        Запись данных в TOML файл

        Parameters
        ----------
        path_to_file: Union[str, Path]
            путь к записываемому файлу формата TOML
        data: Dict[str, Any]
            словарь данных

    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    with open(path_to_file.as_posix(), 'w', encoding='utf-8') as outfile:
        outfile.write(toml.dumps(data))


def rotate_image_90(img: np.ndarray,
                    n: int = 1):
    return np.rot90(img, k=n, axes=(0, 1))


def rotate_coordinates_90(coordinates: Dict[str, Any]) -> dict[str, Any]:
    new_upper_left = copy(coordinates["upper_right"])
    new_lower_right = copy(coordinates["lower_left"])

    new_upper_right = copy(coordinates["lower_right"])
    new_lower_left = copy(coordinates["upper_left"])

    new_coordinates = {
            "upper_left": new_upper_left,
            "lower_left": new_lower_left,
            "upper_right": new_upper_right,
            "lower_right": new_lower_right,
            "center": copy(coordinates["center"])
            }
    return new_coordinates


def parse_specim_hdr(path_to_hdr) -> dict:
    class File(BaseModel):
        samples: int
        lines: int
        bands: int
        header_offset: int
        file_type: str
        data_type: int
        interleave: str
        sensor_type: str
        byte_order: int
        latitude: float
        longitude: float
        acquisition_date: str
        errors: str
        tint: int
        fps: float
        wavelength: list = Field(default_factory=list)
        default_bands: tuple = Field(default_factory=tuple)
        binning: tuple = Field(default_factory=tuple)

    simple_s = r"([\w ]+ = [^{].*)"
    tuples_s = r"([ \w]+ = {[\s\w]+}|[ \w]+ = {[\s\d.,]+})"
    if not isinstance(path_to_hdr, Path):
        path_to_hdr = Path(path_to_hdr)

    with open(path_to_hdr) as file:
        hdr_data = file.read()

    match = re.findall(simple_s, hdr_data)
    lines = [item.replace("\n", "").split(" = ") for item in match]
    d = {k.replace(" ", "_"): v for k, v in lines}

    match = re.findall(tuples_s, hdr_data)
    lines = [item.replace("\n", "").split(" = ") for item in match]
    d_ = {k.replace(" ", "_"): v.replace("{", "[").replace("}", "]") for k, v in lines}
    d_["wavelength"] = [float(el) for el in d_["wavelength"].replace("[", "").replace("]", "").split(",")]
    d_["default_bands"] = [int(el) for el in d_["default_bands"].replace("[", "").replace("]", "").split(",")]
    d_["binning"] = [int(el) for el in d_["binning"].replace("[", "").replace("]", "").split(",")]

    united_d = d | d_
    file = File.model_validate(united_d)

    return file.model_dump()
