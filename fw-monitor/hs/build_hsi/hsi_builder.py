"""
Программный модуль формирования, калибровки и повышения качества ГСИ (ПМ ФКПК ГСИ)
"""
import copy

from pathlib import Path
from typing import Any, Literal, Union, List, Callable, Optional, Type, Iterable
import numpy as np

from tqdm import tqdm

import hs
from hs.build_hsi.raw_data_reader import RawImagesDataReader, RawVideosDataReader, GPSReader
from hs.build_hsi.builder_params import BuildParams, BuildUAVParams
from hs.build_hsi.uav_utils import build_hypercube_with_gps, build_hypercube_with_gps_triangle
from hs.build_hsi.preprocessing_frames import (get_roi, get_vertical_orient_frame, rotate_frame, remove_dark_current)

SourceDataTypes = Literal['images', 'video']


class HSBuilder:
    """
    Данный класс используется для формирования ГСИ.

    Parameters
    ----------
    path_to_hs_source: Union[Path, str]
        путь к видеофайлам или изображениям, содержащим гиперспектральную развертку
    source_data_type: SOURCE_DATA_TYPES = 'images' ['images', 'video']
        тип данных, содержащих гиперспектральную развертку
    path_to_gps: Path = None
        путь к csv файлу, хранящему GPS данные
    build_params: BuildParams = None
        класс, содержащий параметры формирования ГСИ
    dark_current: np.ndarray
        Кадр темновых токов
    preprocess_funcs: List[Callable[[np.ndarray], np.ndarray]] = None
        пользовательский список функций предобработки кадров

    Attributes
    ----------
    _hsi: HSImage
        Сформированное ГСИ
    build_params: BuildParams
        Параметры формирования ГСИ
    dark_current: np.ndarray
        Кадр темновых токов
    preprocess_funcs: Optional[List[Callable]]
        Список функций предобработки кадров, содержащих спектральную развёртку
    frame_iterator: Type[Iterable]
        Итератор кадров, содержащих спектральную развёртку
    gps_iterator: Type[Iterable]
        Итератор GPS данных

    Methods
    -------
    build_hsi()
        Запуск процесса формирования ГСИ
    get_hsi()
        Получение сформированного ГСИ
    save(path, key=None)
        Сохранение полученного ГСИ
    """

    def __init__(self,
                 path_to_hs_source: Union[str, Path],
                 source_data_type: SourceDataTypes = 'images',
                 path_to_gps: Optional[Union[str, Path]] = None,
                 build_params: Optional[BuildParams] = None,
                 dark_current: np.ndarray = None,
                 preprocess_funcs: Optional[List[Callable[[np.ndarray], np.ndarray]]] = None,
                 postprocess_funcs: Optional[List[Callable[[np.ndarray], np.ndarray]]] = None):
        self._hsi: Optional[hs.hsimage] = None
        self.build_params: Optional[BuildParams] = build_params
        self.preprocess_funcs: Optional[List[Callable]] = preprocess_funcs
        self.postprocess_funcs: Optional[List[Callable]] = postprocess_funcs
        self.dark_current = dark_current

        self.frame_iterator: Type[Iterable]
        self.gps_iterator: Optional[Type[Iterable]] = None
        self.build_uav_type: Optional[Literal['knn', 'triangle']] = None

        if source_data_type == 'images':
            self.frame_iterator = RawImagesDataReader(path_to_source=path_to_hs_source)
        elif source_data_type == 'video':
            self.frame_iterator = RawVideosDataReader(path_to_source=path_to_hs_source)
        else:
            raise ValueError(f'Incorrect source_data_type: {source_data_type}.')

        if path_to_gps and source_data_type == 'video':
            self.gps_iterator = GPSReader(path_to_gps=path_to_gps,
                                          video_files_names=self.frame_iterator.paths_to_videos,
                                          count_frames=len(self.frame_iterator))

    def build_hsi(self,
                  build_uav_type: Optional[Literal['knn', 'triangle']] = None,
                  build_uav_params: Optional[BuildUAVParams] = None):
        """
        build_hsi()

            Метод для запуска процесса формирования ГСИ
        """
        self.build_uav_type = build_uav_type
        if build_uav_params:
            self.build_params.build_uav_params = build_uav_params
        preproc_frames = self._get_preprocessed_frames_set()
        preproc_frames = np.array(preproc_frames)
        self._hsi = self._get_postprocessed_hsi(preproc_frames)
        self._hsi.wavelengths = self.build_params.hyper_device_params.wavelengths

    def _get_prepoc_functions(self) -> List[Callable[[np.ndarray], np.ndarray]]:
        """
        _get_preproc_functions()

            Формирует список предобработок кадров, имеющих гиперспектральную развертку
            снимаемой сцены

            Returns
            -------
            List[Callable[[np.ndarray], np.ndarray]]
        """
        preproc_funcs = []

        if self.build_params.hyper_device_params.frame_orientation:
            f = get_vertical_orient_frame(frame_orientation=self.build_params.hyper_device_params.frame_orientation)
            preproc_funcs.append(f)

        if self.build_params.hyper_device_params.roi:
            if self.build_params.hyper_device_params.roi.top_left \
                    and self.build_params.hyper_device_params.roi.bottom_right:
                f = get_roi(top_left=self.build_params.hyper_device_params.roi.top_left,
                            bottom_right=self.build_params.hyper_device_params.roi.bottom_right)
            else:
                raise ValueError("Some problems with ROI params")

            preproc_funcs.append(f)

        if self.build_params.hyper_device_params.rotation_angle:
            f = rotate_frame(rotation_angle=self.build_params.hyper_device_params.rotation_angle)
            preproc_funcs.append(f)

        if self.dark_current is not None:
            f = remove_dark_current(dc_frame=self.dark_current)
            preproc_funcs.append(f)

        return preproc_funcs

    def _get_preprocessed_frames_set(self) -> List[np.ndarray]:
        """
        _get_preprocessed_frames_set()

            Формирует список предобработанных кадров

            Returns
            -------
            List[np.ndarray]
        """
        preproc_frames = []
        if self.preprocess_funcs is None:
            self.preprocess_funcs = self._get_prepoc_functions()
        for frame in tqdm(self.frame_iterator,
                          total=len(self.frame_iterator),
                          desc='Preprocessing frames',
                          colour='blue'):
            for preproc_func in self.preprocess_funcs:
                frame = preproc_func(frame)
            preproc_frames.append(frame)
        return preproc_frames

    def _get_postprocessed_hsi(self,
                               frames: np.ndarray) -> hs.hsimage:

        if self.postprocess_funcs is None:
            self.postprocess_funcs = self._get_postproc_functions()

        tmp = copy.deepcopy(frames)
        for post_proc_func in self.postprocess_funcs:
            tmp = post_proc_func(tmp)

        if self.build_uav_type and self.gps_iterator:
            coordinates = self.gps_iterator.get_corner_coordinates()
        else:
            coordinates = None

        post_proc_hsi = hs.hsimage(data_array=tmp,
                                   coordinates=coordinates)
        return post_proc_hsi

    def _get_postproc_functions(self) -> List[Callable[[Union[np.ndarray, hs.hsimage]],
                                                       Union[np.ndarray, hs.hsimage]]]:
        post_proc_functions = []
        if self.build_uav_type and self.gps_iterator:
            post_proc_functions.append(self.build_with_gps)

        return post_proc_functions

    def build_with_gps(self,
                       data: Union[np.ndarray, hs.hsimage]) -> np.ndarray:
        """
        build_with_gps(data)
            Формирование ГСИ с учетом телеметрии
        """
        if self.build_uav_type == 'knn':
            return self._build_with_gps_knn(data)
        if self.build_uav_type == 'triangle':
            return self._build_with_gps_triangle(data)
        raise ValueError(f"Unsupported build type {self.build_uav_type}")

    def _build_with_gps_knn(self,
                            data: Union[np.ndarray, hs.hsimage]) -> np.ndarray:
        """
        _build_with_gps(data)

            Сборка входного набора гиперспектральных кадров с учетом GPS

            Parameters
            ----------
            data: np.ndarray
                Массив кадров (Frame_i, Y, X)

            Returns
            -------
            np.ndarray
        """
        telemetry: dict[str, Any] = {'latitude': self.gps_iterator.latitude,
                                     'longitude': self.gps_iterator.longitude,
                                     'rel_alt': self.gps_iterator.rel_alt,
                                     'angle': self.gps_iterator.angle,
                                     'corner_coordinates': self.gps_iterator.get_corner_coordinates()}
        builded_hypercube = build_hypercube_with_gps(cube=data.astype("uint8"),
                                                     telemetry=telemetry,
                                                     hyper_device=self.build_params.hyper_device_params,
                                                     uav_bp=self.build_params.build_uav_params)
        return builded_hypercube

    def _build_with_gps_triangle(self,
                                 data: np.ndarray) -> np.ndarray:
        """
        _build_with_gps_triangle(data)

            Сборка входного набора гиперспектральных кадров с учетом GPS, используя триангуляцию
            Parameters
            ----------
            data: np.ndarray
                Массив кадров (Frame_i, Y, X)

            Returns
            -------
            np.ndarray

        """
        builded_hypercube = build_hypercube_with_gps_triangle(data.astype("uint8"),
                                                              self.gps_iterator,
                                                              uav_bp=self.build_params.build_uav_params)

        return builded_hypercube

    def get_hsi(self) -> hs.hsimage:
        """
        get_hsi()

            Возвращает сформированное ГСИ

            Returns
            -------
            hs.hsimage
        """
        return self._hsi

    def save(self,
             path: Union[str, Path],
             key: Optional[str] = None,
             metadata_ext: str = 'json'):
        """
        save(path, key=None)

            Запись ГСИ на устройство

            Parameters
            ----------
            path: Union[str, Path]
                путь до сохраняемого файла. Разрешенные форматы MAT, TIFF, NPY
            key: Optional[str]
                при сохранении в MAT формат требуется указывать ключ поля,
                в которое будет записано ГСИ
            metadata_ext: str

        """
        hs.save_hsi(path=path,
                    hsi=self._hsi,
                    key=key,
                    metadata_ext=metadata_ext)
