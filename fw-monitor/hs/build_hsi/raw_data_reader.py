"""
Модуль предназначен для хранения инструментов итеративного чтения данных из исходников
для дальнейшего формирования ГСИ
"""

import re

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple, Union

import cv2
import pandas as pd

from hs.utils import BaseDescriptorClass


@dataclass
class CSVConstants:  # pylint: disable=too-many-instance-attributes
    """
    Класс для хранения констант чтения CSV файла, хранящего GPS информацию

    Attributes
        csv_delimiter: str
            Разделитель в GPS файле формата CSV
        gps_hypercam_frame: str
            Ключ в GPS файле для кадров с гиперспектрометра
        header_cam_id: str
            Заголовок файла GPS для типа камеры
        header_x: str
            Заголовок файла GPS внутренней координаты БАС X
        header_y: str
            Заголовок файла GPS внутренней координаты БАС Y
        header_rel_alt: str
            Заголовок файла GPS Относительная высота БАС
        header_angle: str
            Заголовок файла GPS Угол между направлением движения и севером
        header_lat: str
            Заголовок файла GPS широты WGS84
        header_lon: str
            Заголовок файла GPS долготы WGS84
    """
    csv_delimiter: str = ';'
    gps_hypercam_frame: str = "Hypercam frame"
    header_cam_id: str = "cam_ID"
    header_x: str = "x"
    header_y: str = "y"
    header_rel_alt: str = "rel_alt"
    header_angle: str = "compass_hdg"
    header_lat: str = "latitude"
    header_lon: str = "longitude"


@dataclass(frozen=True)
class SupportedExtensions:
    """
    Класс для хранения поддерживаемых форматов файлов для чтения

    Attributes
        video: Tuple[str, str]
            Поддерживаемые форматы видеофайлов
        images: Tuple[str, str, str]
            Поддерживаемые форматы растровых изображений
        gps: Tuple[str]
            Поддерживаемые форматы GPS файлов
    """
    video: Tuple[str, str] = (".mp4", ".avi")
    images: Tuple[str, str, str] = (".jpg", ".jpeg", ".png", ".bmp")
    gps: Tuple[str] = (".csv",)


class CorrectImagesPath(BaseDescriptorClass):  # pylint: disable=too-few-public-methods
    """
    Класс-дескриптор для проверки корректности пути к директории, хранящей изображения
    """
    def __set__(self, instance, value):
        value = Path(value)
        if value.is_dir() and list(value.rglob("*.png")) + list(value.rglob('*.jpeg')) + list(value.rglob('*.jpg')):
            instance.__dict__[self.name] = value
        else:
            raise ValueError(f'Incorrect source data type: {value.as_posix()}')


class CorrectVideosPath(BaseDescriptorClass):  # pylint: disable=too-few-public-methods
    """
    Класс-дескриптор для проверки корректности пути к директории, хранящей видеофайлы
    """
    def __set__(self, instance, value):
        value = Path(value)
        if value.is_file() and value.suffix in SupportedExtensions.video:
            instance.__dict__[self.name] = value
        elif value.is_dir() and list(value.rglob("*.avi")):
            instance.__dict__[self.name] = value
        else:
            raise ValueError(f'Incorrect source data type: {value.as_posix()}')


class CorrectGPSPath(BaseDescriptorClass):  # pylint: disable=too-few-public-methods
    """
    Класс-дескриптор для проверки корректности пути к файлу, хранящему GPS информацию
    """
    def __set__(self, instance, value):
        value = Path(value)
        if value.is_file() and value.suffix in SupportedExtensions.gps:
            instance.__dict__[self.name] = value
        else:
            raise ValueError(f'Incorrect source data type: {value.as_posix()}')


class RawDataReader(ABC):
    """
    Абстрактный класс для итеративного чтения данных
    """
    @abstractmethod
    def __iter__(self):
        raise NotImplementedError('Not implemented!')

    @abstractmethod
    def __next__(self):
        raise NotImplementedError('Not implemented!')

    @abstractmethod
    def __len__(self):
        raise NotImplementedError('Not implemented!')

    @staticmethod
    def load_data(path: Path,
                  exts: Union[List, Tuple]) -> List:
        """
        load_data(path, exts)

            Чтение данных по указанному пути. Если это единичный файл, то будет возвращен список
            с одним именем. Если это директория, то из нее будут считаны все файлы выбранного
            формата и отсортированы в алфавитном порядке

            Parameters
            ----------
            path: Path
                Путь к данным
            exts: Union[List, Tuple]
                Список/кортеж допустимых форматов
        """
        if not isinstance(path, Path):
            path = Path(path)
        if path.is_file():
            return [str(path)]
        return [str(p) for p in path.glob("*") if p.suffix in exts]


class RawImagesDataReader(RawDataReader):
    """
    Класс для итеративного чтения изображений из директории
    """
    path_to_source = CorrectImagesPath()

    def __init__(self, path_to_source: Path):
        super().__init__()
        self.path_to_source = path_to_source
        self.paths_to_images = super().load_data(self.path_to_source, SupportedExtensions.images)
        self.paths_to_images.sort(key=lambda f: int(re.sub(r'\D', '', f)))
        self.current_step = 0

    def __iter__(self):
        self.current_step = 0
        return self

    def __next__(self):

        if self.current_step >= len(self):
            raise StopIteration
        # raw_img = Image.open(self.paths_to_images[self.current_step]).convert("L")
        # img = Image.fromarray(np.array(raw_img).astype("uint16"))
        img = cv2.imread(self.paths_to_images[self.current_step], cv2.IMREAD_UNCHANGED)
        self.current_step += 1
        return img

    def __len__(self):
        return len(self.paths_to_images)


class RawVideosDataReader(RawDataReader):
    """
    Класс для итеративного чтения отдельного видеофайла или видеофайлов из директории
    """
    path_to_source = CorrectVideosPath()

    def __init__(self, path_to_source: Path):
        self.path_to_source = path_to_source
        self.paths_to_videos = super().load_data(self.path_to_source, SupportedExtensions.video)
        self.caps = [cv2.VideoCapture(file) for file in self.paths_to_videos]
        self.current_step = 0

    def __iter__(self):
        self.current_step = 0
        return self

    def __len__(self):
        length = 0
        for cap in self.caps:
            length += int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return length

    def __next__(self):  # pylint: disable=inconsistent-return-statements
        if self.current_step < len(self):
            self.current_step += 1
            for cap in self.caps:
                ret, frame = cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    return frame
        else:
            raise StopIteration


class GPSReader:
    """
    Класс для итеративного чтения GPS данных

    Parameters
    ----------
    path_to_gps: Union[str, Path]
        путь к CSV файлу, содержащему GPS
    video_files_names: List[str]
        Список названий видеофайлов
    count_frames: int
        Суммарное количество кадров видеофайлов

    Attributes
    ----------
    gps: pd.DataFrame
        Таблица, содержащая GPS данные
    latitude: List[float]
        Широта
    longitude: List[float]
        Долгота
    rel_alt: List[float]
        Относительная высота
    angle: List[float]
        Угол рысканья относительно севера
    """
    path_to_source = CorrectGPSPath()

    def __init__(self,
                 path_to_gps: Union[str, Path],
                 video_files_names: List[str] = None,
                 count_frames: int = None):
        super().__init__()

        if video_files_names and count_frames:
            self.gps = self._get_gps_from_csv(path_to_gps=path_to_gps,
                                              video_files=video_files_names,
                                              count_frames=count_frames)
        else:
            self.gps = self._get_gps_from_csv_all(path_to_gps=path_to_gps)

        self.latitude = self.gps[CSVConstants.header_x].tolist()
        self.longitude = self.gps[CSVConstants.header_y].tolist()
        self.rel_alt = self.gps[CSVConstants.header_rel_alt].tolist()
        self.angle = self.gps[CSVConstants.header_angle].tolist()

    def __getitem__(self, item):
        return tuple([self.latitude[item],
                      self.longitude[item],
                      self.rel_alt,
                      self.angle])

    def __len__(self):
        return len(self.gps)

    def get_corner_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """
        get_corner_coordinates()

            Возвращает угловые координаты ГСИ в виде словаря
            {
            "upper_left": (lat_max, lon_min),
            "lower_left": (lat_min, lon_min),
            "upper_right": (lat_max, lon_max),
            "lower_right": (lat_min, lon_max),
            "center": (lat_center, lon_center)
            }

        Returns
        -------
        Dict[str, Tuple[float, float]]
        """
        lat = self.gps[CSVConstants.header_lat].to_list()
        lon = self.gps[CSVConstants.header_lon].to_list()
        lat_max = max(lat)
        lat_min = min(lat)
        lon_max = max(lon)
        lon_min = min(lon)
        lat_center = (lat_max + lat_min) / 2.0
        lon_center = (lon_max + lon_min) / 2.0

        corner_coordinates = {
            "upper_left": (lat_max, lon_min),
            "lower_left": (lat_min, lon_min),
            "upper_right": (lat_max, lon_max),
            "lower_right": (lat_min, lon_max),
            "center": (lat_center, lon_center)
        }
        return corner_coordinates

    @staticmethod
    def _get_gps_from_csv(path_to_gps: Union[str, Path],
                          video_files: List[str],
                          count_frames: int) -> pd.DataFrame:
        """
        _get_gps_from_csv()

        Возвращает GPS данные из CSV

        Parameters
        ----------
        path_to_gps: Union[str, Path]
            Путь к CSV файлу, содержащему GPS
        video_files: List[str]
            Список имен видеофайлов
        count_frames: int
            Суммарное количество кадров видеофайлов
        """
        if not isinstance(path_to_gps, Path):
            path_to_gps = Path(path_to_gps)

        gps = pd.read_csv(path_to_gps.as_posix(), delimiter=CSVConstants.csv_delimiter)

        start_points = gps[gps[CSVConstants.header_cam_id] == "Hypercam start point"]
        start_points = start_points["timing"].tolist()
        start_indexes = gps.loc[gps[CSVConstants.header_cam_id] == "Hypercam start point"]
        start_indexes = start_indexes.index.tolist()

        end_indexes = gps.loc[gps[CSVConstants.header_cam_id] == "Hypercam end point"]
        end_indexes = end_indexes.index.tolist()

        start_points_dict = {}
        for i, el in enumerate(start_points):
            for file in video_files:
                if el in file:
                    start_points_dict[el] = gps.loc[start_indexes[i]: end_indexes[i]]

        gps = pd.concat(start_points_dict.values(), ignore_index=True)
        gps = gps.loc[gps[CSVConstants.header_cam_id] == CSVConstants.gps_hypercam_frame]
        gps = gps.head(count_frames)
        return gps

    @staticmethod
    def _get_gps_from_csv_all(path_to_gps: Union[str, Path]) -> pd.DataFrame:
        """
        _get_gps_from_csv()

        Возвращает GPS данные из CSV

        Parameters
        ----------
        path_to_gps: Union[str, Path]
            Путь к CSV файлу, содержащему GPS
        """
        if not isinstance(path_to_gps, Path):
            path_to_gps = Path(path_to_gps)

        gps = pd.read_csv(path_to_gps.as_posix(), delimiter=CSVConstants.csv_delimiter)

        start_points = gps[gps[CSVConstants.header_cam_id] == "Hypercam start point"]
        start_points = start_points["timing"].tolist()
        start_indexes = gps.loc[gps[CSVConstants.header_cam_id] == "Hypercam start point"]
        start_indexes = start_indexes.index.tolist()

        end_indexes = gps.loc[gps[CSVConstants.header_cam_id] == "Hypercam end point"]
        end_indexes = end_indexes.index.tolist()

        start_points_dict = {}
        for i, el in enumerate(start_points):
            start_points_dict[el] = gps.loc[start_indexes[i]: end_indexes[i]]

        gps = pd.concat(start_points_dict.values(), ignore_index=True)
        gps = gps.loc[gps[CSVConstants.header_cam_id] == CSVConstants.gps_hypercam_frame]
        return gps
