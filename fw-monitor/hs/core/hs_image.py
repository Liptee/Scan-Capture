"""
Модуль предназначен для хранения класса ГСИ и методов его записи/чтения
"""

import copy

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union, NamedTuple

import numpy as np

from osgeo import gdal, osr
from utm import from_latlon

from hs.utils import BaseDescriptorClass
from hs.core.utils import load_mat, load_npy, load_tiff, save_tiff, \
                          save_mat, save_npy, load_json, load_toml, save_json, save_toml, \
                          load_raw_dat, parse_specim_hdr

HSISupportedExtensions = ('.mat', '.npy', '.tiff')
CoordinatesKeys = {"upper_left", "upper_right", "lower_left", "lower_right", "center"}
METERS_IN_ONE_WGS_DEGREE = 111_000
DEGREES_IN_ONE_RADIAN = 57.2958


class _CorrectPathToOpen(BaseDescriptorClass):  # pylint: disable=too-few-public-methods
    """
    Класс-дескриптор для проверки корректности пути для чтения ГСИ

        Проверка на корректное расширение файла
    """
    def __set__(self, instance, value):
        if value.suffix in HSISupportedExtensions:
            instance.__dict__[self.name] = value
        else:
            raise ValueError('Unsupported extension')


class _CorrectPathToSave(BaseDescriptorClass):  # pylint: disable=too-few-public-methods
    """
    Класс-дескриптор для проверки корректности пути для записи ГСИ

        Проверка на корректное расширение файла
    """
    def __set__(self, instance, value):
        if value.suffix in HSISupportedExtensions:
            instance.__dict__[self.name] = value
        else:
            raise ValueError('Unsupported extension')


class _CorrectWavelengths(BaseDescriptorClass):  # pylint: disable=too-few-public-methods
    """
    Класс-дескриптор для проверки корректности длин волн

        Проверка на корректный тип данных: List или None
    """
    def __set__(self, instance, value):
        if isinstance(value, (List, np.ndarray)):
            instance.__dict__[self.name] = list(value)
        elif not value:
            instance.__dict__[self.name] = None
        else:
            raise ValueError('Incorrect wavelengths')


class _CorrectCoordinates(BaseDescriptorClass):  # pylint: disable=too-few-public-methods
    """
    Класс-дескриптор для проверки корректности координат

        Проверка на корректный тип данных Dict или None
        Проверка на корректную схему словаря
    """
    def __set__(self, instance, value):
        if isinstance(value, Dict) and set(value.keys()) == CoordinatesKeys:
            instance.__dict__[self.name] = value
        elif not value:
            instance.__dict__[self.name] = None
        else:
            raise ValueError('Incorrect coordinates')


class HSImage:
    """
    Класс для хранения и представления ГСИ

    ГСИ представляет собой трёхмерный массив, где по осям XY представлены пространственные признаки,
    а по оси Z спектральные.

    Attributes
    ----------
    data: np.ndarray
        Трёхмерный массив гиперспектрального изображения
    wavelengths: List[int]
        Длины волн, соответствующие каналам ГСИ
    coordinates: Dict[str, Tuple[float, float]]
        Угловые координаты ГСИ

    shape(): property Tuple[int, int, int]
        Размерность ГСИ
    metadata(): property Dict[str, Any]
        Словарь длин волн и угловых координат
    count_channels(): property Int
        Количество каналов ГСИ

    Methods
    -------
    load(path, path_to_metadata, key)
         Чтение ГСИ с ПЗУ
    save(path)
        Запись ГСИ на ПЗУ
    flip_x()
        Инверсия ГСИ по оси Х
    flip_y()
        Инверсия ГСИ по оси Y
    flip_z()
        Инверсия ГСИ по оси Z
    rot90(n=1)
        Поворот ГСИ на 90 против часовой стрелки n-раз
    """
    path_to_open = _CorrectPathToOpen()
    path_to_save = _CorrectPathToSave()
    wavelengths = _CorrectWavelengths()
    coordinates = _CorrectCoordinates()

    def __init__(self,
                 data_array: np.ndarray,
                 wavelengths: Optional[List[int]] = None,
                 coordinates: Optional[Dict[str, Tuple[float, float]]] = None):
        self.data = data_array
        self.wavelengths = wavelengths
        self.coordinates = coordinates

    def __getitem__(self, item):
        return self.data[:, :, item]

    def __len__(self):
        return self.data.shape[-1]

    def __mul__(self, other):
        if len(other.shape) == 1 and other.shape[0] == self.count_channels:
            tmp = copy.deepcopy(self)
            tmp.data = tmp.data * other[None, None, :]
            return tmp
        if len(other.shape) == 2 and other.shape == self.shape[1:]:
            tmp = copy.deepcopy(self)
            tmp.data = tmp.data * other[None, :, :]
            return tmp
        if len(other.shape) == 2 and other.shape == self.shape[0::2]:
            tmp = copy.deepcopy(self)
            tmp.data = tmp.data * other[0, None, :]
            return tmp
        raise ValueError(f"Incomparable shape of value {other.shape} with HSI {self.shape}")

    @property
    def shape(self) -> Tuple[int, int, int]:
        """
        Размерность ГСИ (x,y,z)

        Returns
        -------
        tuple(int, int, int)
        """
        return self.data.shape

    @property
    def count_channels(self) -> int:
        """
        Количество каналов ГСИ

        Returns
        -------
        int
        """
        return self.data.shape[-1]

    @property
    def height_in_wgs_degree(self) -> Optional[float]:
        """
        Высота ГСИ в градусах WGS-84

        Returns
        -------
        float
        """
        if self.coordinates:
            return np.abs(self.coordinates['upper_left'][0] - self.coordinates['lower_right'][0])
        return None

    @property
    def height_in_meters(self) -> Optional[float]:
        """
        Высота ГСИ в метрах

        Returns
        -------
        float
        """
        if self.coordinates:
            return self.height_in_wgs_degree * METERS_IN_ONE_WGS_DEGREE
        return None

    @property
    def width_in_wgs_degree(self) -> Optional[float]:
        """
        Ширина ГСИ в градусах WGS-84

        Returns
        -------
        float
        """
        if self.coordinates:
            return np.abs(self.coordinates['upper_left'][1] - self.coordinates['lower_right'][1])
        return None

    @property
    def width_in_meters(self) -> Optional[float]:
        """
        Ширина ГСИ в метрах

        Returns
        -------
        float
        """
        if self.coordinates:
            lat_in_radian = self.coordinates['center'][0] / DEGREES_IN_ONE_RADIAN
            return self.width_in_wgs_degree * METERS_IN_ONE_WGS_DEGREE * np.cos(lat_in_radian)
        return None

    @property
    def metadata(self):
        """
        Представление метаданных ГСИ в виде словаря
        - wavelengths: Optional[List[int]]
        - coordinates: Optional[Dict[str, Tuple[float, float]]]

        Returns
        -------
        Dict(str, Any)
        """
        return {
            "wavelengths": self.wavelengths,
            "coordinates": self.coordinates
        }

    @metadata.setter
    def metadata(self, value: Dict[str, Any]):
        """
        Задает метадананные ГСИ при помощи словаря

        Parameters
        ----------
        value: Dict[str, Any]
            Словарь метаданных ГСИ
            {"wavelengths: Optional[List[int]]",
            "coordinates": Optional[Dict[str, Tuple[float, float]]]}
        """
        if isinstance(value, dict):
            self.wavelengths = value.get("wavelengths", None)
            self.coordinates = value.get("coordinates", None)

    def save(self,
             path: Union[str, Path],
             key: Optional[str] = None,
             metadata_ext: str = 'json'):
        """
        Запись ГСИ в файл

        Parameters
        ----------
        path: Union[str, Path]
            путь к файлу ГСИ
        key: Optional[str]
            ключ для сохранения в MAT файл
        metadata_ext: str
            формат записи метаданных в файл JSON или TOML ['json', 'TOML']
        """
        if not isinstance(path, Path):
            path = Path(path)

        self.path_to_save = path
        save_hsi(path=path,
                 hsi=self,
                 key=key,
                 metadata_ext=metadata_ext)

    def flip_x(self):
        """
        Отразить ГСИ по горизонтали

        Returns
        -------
        HSImage
        """
        tmp_self = copy.deepcopy(self)
        tmp_self.data = tmp_self.data[:, ::-1, :]
        return tmp_self

    def flip_y(self):
        """
        Отразить ГСИ по вертикали

        Returns
        -------
        HSImage
        """
        tmp_self = copy.deepcopy(self)
        tmp_self.data = tmp_self.data[::-1, :, :]
        return tmp_self

    def flip_z(self):
        """
        Инвертировать каналы ГСИ

        Returns
        -------
        HSImage
        """
        tmp_self = copy.deepcopy(self)
        tmp_self.data = tmp_self.data[:, :, ::-1]
        return tmp_self

    def rot90(self,
              n: int = 1):
        """
        Повернуть ГСИ на 90 градусов против часовой стрелки

        Parameters
        ----------
        n: int
            Количество поворотов ГСИ (от 1 до 3)

        Returns
        -------
        HSImage
        """
        tmp_self = copy.deepcopy(self)
        for _ in range(n):
            tmp_self.data = np.rot90(tmp_self.data, axes=(0, 1))
        return tmp_self


def save_hsi_metadata(path_to_metadata: Union[str, Path],
                      metadata: Dict[str, Any],
                      metadata_ext: str = 'json'):
    """
    Запись метаинформации в JSON файл

    Parameters
    ----------
    path_to_metadata: Union[str, Path]
        путь к файлу метаданных ГСИ
    metadata: Dict[str, Any]
        словарь метаданных гси, содержащий информацию о длинах волн и угловых координатах
        {"wavelengths: Optional[List[int]]",
         "coordinates": Optional[Dict[str, Tuple[float, float]]]}
    metadata_ext: str

    """

    if not isinstance(path_to_metadata, Path):
        path_to_metadata = Path(path_to_metadata)

    wavelengths = metadata.get("wavelengths", None)
    if isinstance(wavelengths, np.ndarray):
        wavelengths = list(wavelengths)

    data = {
        "wavelengths": wavelengths,
        "coordinates": metadata.get("coordinates", None)
            }
    if metadata_ext == 'json':
        save_json(path_to_metadata, data)
    elif metadata_ext == 'toml':
        save_toml(path_to_metadata, data)
    else:
        raise ValueError(f"Unsupported extension: {metadata_ext}")


def load_hsi_metadata(path_to_metadata: Union[str, Path]) -> Dict[str, Any]:
    """
    Чтение метаинформации из JSON файла

    Parameters
    ----------
    path_to_metadata: Union[str, Path]
        Путь к файлу метаданных ГСИ

    Returns
    -------
    Dict[str, Any]
    """

    path_to_metadata = Path(path_to_metadata)

    if path_to_metadata.suffix == '.json':
        data = load_json(path_to_metadata)
    elif path_to_metadata.suffix == '.toml':
        data = load_toml(path_to_metadata)
    else:
        raise ValueError(f"Unsupported extension: {path_to_metadata.suffix}")

    metadata = {"wavelengths": data.get('wavelengths', None),
                "coordinates": data.get("coordinates", None)}

    return metadata


def save_hsi(path: Union[Path, str],
             hsi: HSImage,
             key: Optional[str] = None,
             metadata_ext: str = 'json',
             envi_metadata: bool = False):
    """
    Запись ГСИ в файл на ПЗУ

    Parameters
    ----------
    path: Union[Path, str]
        Путь к файлу ГСИ
    hsi: HSImage
        ГСИ
    key: Optional[str]
        Ключ для файла ГСИ, при использовании формата MAT
    metadata_ext: str

    """
    if not isinstance(path, Path):
        path = Path(path)
    data = hsi.data
    metadata = hsi.metadata

    if metadata_ext in ['toml', 'json']:
        path_to_metadata = Path(path.with_suffix('').as_posix() + f'_metadata.{metadata_ext}')
    else:
        raise ValueError(f"Unsupported metadata extension: {metadata_ext}")

    if path.suffix == '.mat':
        dict_data = {key: data}
        save_mat(path_to_file=path,
                 data=dict_data)
    elif path.suffix == '.npy':
        save_npy(path_to_file=path,
                 data=data)
    elif path.suffix == '.tiff':
        save_tiff(path_to_file=path,
                  data=data,
                  coordinates=hsi.metadata.get("coordinates", None))
    else:
        raise ValueError('Unsupported extension!')

    if metadata:
        save_hsi_metadata(path_to_metadata=path_to_metadata,
                          metadata=metadata,
                          metadata_ext=metadata_ext)
    if metadata and envi_metadata:
        path_to_envi_metadata = Path(path.with_suffix('').as_posix() + f'.hdr')
        save_hsi_envi_metadata(path_to_metadata=path_to_envi_metadata,
                               hsi_shape=hsi.shape,
                               wls=hsi.wavelengths)


def save_hsi_envi_metadata(path_to_metadata: Path, hsi_shape, wls):
    lines, samples, bands = hsi_shape
    wls_s = ', '.join(str(el) for el in wls)
    with open(path_to_metadata.as_posix(), mode='w', encoding="utf-8") as f:
        s = f"ENVI\n" \
            f"samples = {samples}\n" \
            f"lines = {lines}\n" \
            f"bands = {bands}\n" \
            "interleave = bil\n"\
            "file type = TIFF"\
            "wavelength units = nanometers\n" \
            f"wavelength = {{{wls_s}}}"
        f.write(s)


def load_hsi(path: Union[Path, str],
             path_to_metadata: Optional[Union[str, Path]] = None,
             key: Optional[str] = None,
             path_to_hdr: Optional[Union[str, Path]] = None) -> HSImage:
    """
    Чтение ГСИ из файла

    Parameters
    ----------
    path: Union[str, Path]
        путь к файлу ГСИ
    path_to_metadata: Optional[Union[str, Path]]
        путь к метаданным ГСИ
    key: Optional[str]
        ключ к файлу ГСИ, если он представлен в формате MAT
    path_to_hdr
    Returns
    -------
    HSImage
    """
    if not isinstance(path, Path):
        path = Path(path)
    if path_to_hdr:
        if not isinstance(path_to_hdr, Path):
            path_to_hdr = Path(path_to_hdr)

    if path.suffix == '.mat':
        mat_data = load_mat(path_to_file=path)
        if key not in mat_data:
            raise ValueError(f"Incorrect key for MAT file. {list(mat_data.keys())} is/are available")
        data = mat_data[key]
    elif path.suffix == '.npy':
        data = load_npy(path_to_file=path)
    elif path.suffix == '.tiff':
        data = load_tiff(path_to_file=path)
    elif path.suffix in ('.dat', '.raw') and path_to_hdr.suffix == ".hdr":
        hdr_d = parse_specim_hdr(path_to_hdr)
        dtype_r = hdr_d.get("data_type", 0)
        if dtype_r == 12:
            dtype = "uint16"
        elif dtype_r == 4:
            dtype = "float32"
        else:
            dtype = "uint8"
        target_shape = tuple([hdr_d.get("samples"), hdr_d.get("bands"), hdr_d.get("lines")])
        raw_data = load_raw_dat(path_to_file=path, dtype=dtype)
        data = np.reshape(raw_data, newshape=target_shape)
        data = np.transpose(data, axes=[2, 0, 1])
        data = data[:, ::-1, :]

        hsimage = HSImage(data_array=data)
        wavelengths = hdr_d.get("wavelength", [])
        if wavelengths:
            hsimage.wavelengths = [int(w) for w in wavelengths]
        return hsimage

    else:
        raise ValueError('Unsupported extension!')

    if path_to_metadata:
        if not isinstance(path_to_metadata, Path):
            path_to_metadata = Path(path_to_metadata)
        metadata = load_hsi_metadata(path_to_metadata)
    else:
        metadata = None

    hsimage = HSImage(data_array=data)
    hsimage.metadata = metadata

    return hsimage

# ---------------------------------Integration IPPI GeoTIFF-----------------------------------------


class UTMCoordinate(NamedTuple):
    easting: float
    northing: float
    zone_number: int
    zone_letter: str

    @classmethod
    def from_latlon(cls,
                    latitude: float,
                    longitude: float):

        easting, northing, zone_number, zone_letter = from_latlon(latitude=latitude,
                                                                  longitude=longitude)
        return cls(easting, northing, zone_number, zone_letter)


class GeoInfo(NamedTuple):
    top_left_coordinate: UTMCoordinate
    resolution_px_per_m: float


class HSImageWithGeoInfo(HSImage):
    geo_info: GeoInfo

    def __init__(self,
                 data,
                 wavelengths: Optional[List[int]],
                 geo_info: GeoInfo):
        super().__init__(data, wavelengths)
        self.geo_info = geo_info


def _np_dtype_to_gdal_dtype(dtype: np.dtype):
    """
    Get dgal datatype from numpy datatype.

    Returns
    -------
    output : int
        A number that encodes the gdal data type.

    Parameters
    ----------
    dtype : np.dtype

        Numpy datatype.
    """

    if dtype == np.uint8:
        return gdal.GDT_Byte
    if dtype == np.uint16:
        return gdal.GDT_UInt16
    if dtype == np.uint32:
        return gdal.GDT_UInt32
    if dtype == np.int16:
        return gdal.GDT_Int16
    if dtype == np.int32:
        return gdal.GDT_Int32
    if dtype == np.float32:
        return gdal.GDT_Float32
    if dtype == np.float64:
        return gdal.GDT_Float64
    raise TypeError(f"{dtype} not supported")


def _save(hsi: Union[HSImage, HSImageWithGeoInfo],
          path: Union[str, Path],
          driver_name: Literal["GTiff", "HFA", "ENVI"]):
    height, width, channels = hsi.data.shape
    gdal.UseExceptions()
    driver = gdal.GetDriverByName(driver_name)
    gdal_type = _np_dtype_to_gdal_dtype(hsi.data.dtype)
    dataset_output = driver.Create(
        str(path), width, height, channels, gdal_type
    )
    if hasattr(hsi, "geo_info"):
        assert hsi.geo_info
        coordinate = hsi.geo_info.top_left_coordinate
        spatial_reference = osr.SpatialReference()
        spatial_reference.SetUTM(
            hsi.geo_info.top_left_coordinate.zone_number, True
        )
        x_res = y_res = 1.0 / hsi.geo_info.resolution_px_per_m
        geotransform = (
            coordinate.easting,
            x_res,
            0,
            coordinate.northing,
            0,
            -y_res,
        )
        dataset_output.SetGeoTransform(geotransform)
        dataset_output.SetProjection(spatial_reference.ExportToWkt())
    for channel_idx in range(channels):
        dataset_output.GetRasterBand(channel_idx + 1).WriteArray(
            hsi.data[:, :, channel_idx]
        )


def save_hsi_to_geotiff(hsi: Union[HSImage, HSImageWithGeoInfo],
                        path: Union[str, Path] = "output_tiff.tiff"):
    """
    Save hyperspectral image to GeoTIFF format.

    Parameters
    ----------
    hsi: HSImage or HSImageWithGeoInfo
        Hyperspectral image object.
    path: str or Path
        Path to save the file.
    """
    return _save(hsi, path, "GTiff")


def save_hsi_to_erdas_img(hsi: Union[HSImage, HSImageWithGeoInfo],
                          path: Union[str, Path] = "erdas_output.img"):
    """
    Save hyperspectral image to ERDAS IMAGINE format (.img) with georeferencing.

    Parameters
    ----------
    hsi: HSImage or HSImageWithGeoInfo
        Hyperspectral image object.
    path: str or Path
        Path to save the file.
    """
    return _save(hsi, path, "HFA")


def save_hsi_to_envi(hsi: Union[HSImage, HSImageWithGeoInfo],
                     path: Union[str, Path] = "envi_output"):
    """
    Save hyperspectral image to ENVI format (.hdr).

    Parameters
    ----------
    hsi: HSImage or HSImageWithGeoInfo
        Hyperspectral image object.
    path: str or Path
        Path to save the file (without extension).
    """
    return _save(hsi, path, "ENVI")
