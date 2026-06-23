"""
Модуль содержит вспомогательные структуры и функции для работы модуля формирования ГСИ
"""

import ast
import json
import os

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal, Tuple, Optional, Union

import toml


FrameOrientation = Literal['h', 'v']
BuildMetadataExtension = ['.json', '.toml']


@dataclass
class ClassDictRepr:
    """
    Базовый класс для корректной конвертации датакласса в словарь
    """
    def __str__(self):
        s = "".join([f"{k}: {v}\n" for k, v in self.__dict__.items()])
        return s

    def __repr__(self):
        return str(self.__dict__)


@dataclass(repr=False)
class DistortionCoefficients(ClassDictRepr):
    """
    Заготовка для хранения параметров для компенсации дисторсии кадров
    """
    k_0: float = None
    # ToDo прописать коэффициенты дисторсии


@dataclass(repr=False)
class ROI(ClassDictRepr):
    """
    Хранит параметры получения зоны интереса (ROI) из кадра, полученного гиперспектрометром.

    top_left: Tuple[int, int]
        координаты левого верхнего угла области интереса X,Y
    bottom_right: Tuple[int, int]
        координаты правого нижнего угла области интереса X,Y
    """
    top_left: Tuple[int, int] = None
    bottom_right: Tuple[int, int] = None


@dataclass(repr=False)
class HyperDevice(ClassDictRepr):
    """
    Хранит параметры гиперспектральной аппаратуры

    pitch: float
        угол наклона камеры, при установке на БАС, относительно перпендикуляра к поверхности земли.
        Пока используется только при сборке с учетом телеметрии
    tangent: float
        тангенс угла обзора камеры.
        Пока используется только при сборке с учетом телеметрии
    focus_distance: float
        фокусное расстояние объектива. Пока не используется.
    roi: ROI
        набор параметров для получения области интереса с кадра.
        Если выставлено значение None, то будет браться вся область кадра
    flip_wavelengths: Optional[bool]
        нужна ли инверсия порядка каналов
    frame_orientation: FrameOrientation
        ориентация области интереса на кадре горизонтально или вертикально
    distortion_coefficients: DistortionCoefficients
        коэффициенты дисторсии кадра (подушка/бочка)
    wavelengths: Optional[list]
        набор длин волн, соответствующий каналам ГСИ
    rotation_angle: Optional[float]
        угол поворота области интереса относительно оси Х
    """
    pitch: float = None
    tangent: float = None
    focus_distance: float = None
    roi: Optional[ROI] = None
    flip_wavelengths: bool = False
    frame_orientation: FrameOrientation = None
    distortion_coefficients: Optional[DistortionCoefficients] = None
    wavelengths: Optional[list] = None
    rotation_angle: Optional[float] = None

    def __post_init__(self):
        if self.pitch is None:
            self.pitch = 0.0
        if self.tangent is None:
            self.tangent = 0.30


@dataclass(repr=False)
class KNNBuildAlgParams(ClassDictRepr):
    """
    Параметры для сборщика на основе KNN

        distance_limit: float
            Отсеивание интерполированных и экстраполированных точек на удаленность от эталонных,
            превышающих заданный порог
        blur_shape: Tuple[int, int]
            Размер окна размытия
        n_neighbours: int
            Количество гиперпикселов, используемых для интер-/экстраполяции
        blur_auto: bool
            Вкл/выкл размытие при формировании
    """
    distance_limit: float = 1.0
    blur_shape: Tuple[int, int] = (3, 3)
    n_neighbours: int = 1
    blur_auto: bool = False


@dataclass(repr=False)
class TriangleBuildAlgParams(ClassDictRepr):
    """
    Параметры для сборщика на основе триангуляции

        super_sampling: bool
    """
    super_sampling: bool = False


@dataclass(repr=False)
class BuildUAVParams(ClassDictRepr):
    """
    Хранит параметры для формирования ГСИ, полученного с БАС
    resolution_cm: int
        разрешение итогового ГСИ в сантиметрах на пиксель
    build_algorithm_params: Union[TriangleBuildAlgParams, KNNBuildAlgParams]
        параметры алгоритма геометрической коррекции в зависимости от его типа
    """
    resolution_cm: int = 2
    build_algorithm_params: Union[TriangleBuildAlgParams, KNNBuildAlgParams] = None


@dataclass(repr=False)
class BuildParams(ClassDictRepr):
    """
    Хранит параметры, требуемые при формировании ГСИ из набора кадров,
    получаемых гиперспектрометром.
    hyper_device_params: HyperDevice
        Параметры ГСА
    build_uav_params: BuildUAVParams
        Параметры формирования ГСИ, полученного с БАС
    """

    hyper_device_params: HyperDevice = None
    build_uav_params: BuildUAVParams = None


def load_data_from_json_toml(path_to_data: Union[str, Path]) -> Dict[str, Any]:
    """
    Чтение данных из json/toml файлов

        path_to_data: Union[str, Path]
            путь к файлу формата JSON/TOML
    """
    if not isinstance(path_to_data, Path):
        path_to_data = Path(path_to_data)

    with open(path_to_data.as_posix(), encoding='utf-8') as dict_file:
        if path_to_data.suffix == '.json':
            data = json.load(dict_file)
        elif path_to_data.suffix == '.toml':
            data = toml.load(dict_file)
        else:
            raise ValueError('Unsupported metadata file extension!')
        if isinstance(data, str):
            data = ast.literal_eval(data)
    return data


def load_build_metadata(path_to_metadata: Union[str, Path]) -> BuildParams:
    """
    load_build_metadata(path_to_metadata)

        Чтение параметров формирования ГСИ из JSON файла

        Parameters
        ----------
        path_to_metadata: Union[str, Path]

        Returns
        -------
        BuildParams
    """

    data = load_data_from_json_toml(path_to_data=path_to_metadata)
    metadata = {
        "hyper_device_params": data.get('hyper_device_params', None),
        "build_uav_params": data.get('build_uav_params', None),
    }

    hyper_device_params_raw = metadata.get("hyper_device_params", None)
    build_uav_params_raw = metadata.get("build_uav_params", None)

    roi_raw = hyper_device_params_raw.get("roi", None)
    if roi_raw:
        roi = ROI(top_left=roi_raw.get("top_left"),
                  bottom_right=roi_raw.get("bottom_right"))
    else:
        roi = None

    distortion_coefficients = None  # DistortionCoefficients()

    hyper_device_params = HyperDevice(pitch=hyper_device_params_raw.get("pitch", None),
                                      tangent=hyper_device_params_raw.get("tangent", None),
                                      focus_distance=hyper_device_params_raw.get("focus_distance", None),
                                      roi=roi,
                                      flip_wavelengths=hyper_device_params_raw.get("flip_wavelengths", False),
                                      frame_orientation=hyper_device_params_raw.get("frame_orientation", "h"),
                                      distortion_coefficients=distortion_coefficients,
                                      wavelengths=hyper_device_params_raw.get("wavelengths", None),
                                      rotation_angle=hyper_device_params_raw.get("rotation_angle", None))

    if build_uav_params_raw:
        build_algorithm_params = build_uav_params_raw.get("build_algorithm_params", None)
        if build_algorithm_params.get("distance_limit", None):
            bap = KNNBuildAlgParams(distance_limit=build_algorithm_params.get("distance_limit", None),
                                    blur_shape=build_algorithm_params.get("blur_shape", None),
                                    blur_auto=build_algorithm_params.get("blur_auto", None),
                                    n_neighbours=build_algorithm_params.get("n_neighbours", None))
        else:
            bap = TriangleBuildAlgParams(super_sampling=build_algorithm_params.get("super_sampling", False))

        build_uav_params = BuildUAVParams(resolution_cm=build_uav_params_raw.get("resolution_cm", None),
                                          build_algorithm_params=bap)
    else:
        build_uav_params = None

    bp = BuildParams(hyper_device_params=hyper_device_params,
                     build_uav_params=build_uav_params)
    return bp


def save_build_metadata(path_to_metadata: Union[str, Path],
                        bp: BuildParams):
    """
    save_build_metadata(path_to_metadata, bp)

        Запись параметров формирования ГСИ в JSON файл

        Parameters
        ----------
        path_to_metadata: Union[str, Path]
            Путь к JSON файлу с метаданными (параметрами формирования)
        bp: BuildParams
            Параметры формирования ГСИ
    """

    path_dir = os.path.dirname(path_to_metadata)

    if not os.path.exists(path_dir):
        os.makedirs(path_dir)

    if not isinstance(path_to_metadata, Path):
        path_to_metadata = Path(path_to_metadata)

    with open(path_to_metadata, 'w', encoding='utf-8') as file:
        str_data = repr(bp)
        d_ = ast.literal_eval(str_data)
        if path_to_metadata.suffix == '.json':
            json.dump(d_, file, indent=4)
        elif path_to_metadata.suffix == '.toml':
            toml.dump(d_, file)


def load_hyper_device(path_to_file: Union[str, Path]) -> HyperDevice:
    """
    load_hyper_device(path_to_file)
        Чтение параметров ГСА из файлов формата JSON/TOML

        path_to_file: Union[str, Path]
            Путь к файлу формата JSON/TOML с параметрами ГСА
    """
    data = load_data_from_json_toml(path_to_data=path_to_file)

    roi_raw = data.get("roi", None)
    if roi_raw:
        roi = ROI(top_left=roi_raw.get("top_left"),
                  bottom_right=roi_raw.get("bottom_right"))
    else:
        roi = None

    distortion_coefficients = None  # DistortionCoefficients()

    hyper_device_params = HyperDevice(pitch=data.get("pitch", None),
                                      tangent=data.get("tangent", None),
                                      focus_distance=data.get("focus_distance", None),
                                      roi=roi,
                                      flip_wavelengths=data.get("flip_wavelengths", False),
                                      frame_orientation=data.get("frame_orientation", "h"),
                                      distortion_coefficients=distortion_coefficients,
                                      wavelengths=data.get("wavelengths", None),
                                      rotation_angle=data.get("rotation_angle", None))
    return hyper_device_params


def save_hyper_device(path_to_file: Union[str, Path],
                      hyper_device: HyperDevice):
    """
    save_hyper_device(path_to_file, hyper_device)
        Запись параметров ГСА в файл формата JSON/TOML
        path_to_file: Union[str, Path]
            Путь к сохраняемому файлу
        hyper_device: HyperDevice
            Параметры ГСА
    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    path_dir = os.path.dirname(path_to_file.as_posix())
    if not os.path.exists(path_dir):
        os.makedirs(path_dir)

    with open(path_to_file, 'w', encoding='utf-8') as file:
        str_data = repr(hyper_device)
        d_ = ast.literal_eval(str_data)
        if path_to_file.suffix == '.json':
            json.dump(d_, file, indent=4)
        elif path_to_file.suffix == '.toml':
            toml.dump(d_, file)
