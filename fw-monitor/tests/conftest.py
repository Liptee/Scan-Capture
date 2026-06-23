"""
Модуль хранит фикстуры и вспомогательные классы/объекты для работы тестов на основе PyTest
"""

from dataclasses import dataclass
from pathlib import Path
from pytest import fixture

import numpy as np

from scipy.io import loadmat


from hs.build_hsi.builder_params import BuildParams, BuildUAVParams


@dataclass
class PathToData:
    """
    Класс для хранения путей к тестовым данным
    """
    paviau_mat: Path = Path('../test_data/build/target/PaviaU/PaviaU.mat')
    paviau_npy: Path = Path('../test_data/build/target/PaviaU/PaviaU.npy')
    paviau_tiff: Path = Path('../test_data/build/target/PaviaU/PaviaU.tiff')

    paviau_gt_mat: Path = Path('../test_data/build/target/PaviaU/PaviaU_gt.mat')
    paviau_gt_npy: Path = Path('../test_data/build/target/PaviaU/PaviaU_gt.npy')
    path_to_save_test_mask = Path('../test_data/saving_temp/')

    images_paviau_png_16bit: Path = Path('../test_data/build/source/images_png/PaviaU_layers_y_png')
    hsi_from_video = Path('../test_data/build/target/from_video/hsi_from_video_avi.mat')
    one_video_source = Path('../test_data/build/source/videos/one_video_avi/rec_2022-06-06-12-24-02.avi')
    two_video_source = Path('../test_data/build/source/videos/some_videos_avi')
    videos_uav_gps = Path('../test_data/build/source/videos/videos_with_gps')
    gps_file = Path('../test_data/build/source/videos/videos_with_gps/gps_2023-03-07-11-32-08.csv')
    hsi_from_uav_gps = Path('../test_data/build/target/helicopter_uav_gps/helicopter.mat')
    path_to_save_test_hsi = Path('../test_data/saving_temp/')


def get_layers_from_hsi(hsi):
    """
    Нарезает ГСИ на фреймов по оси Y и возвращает список фреймов
    """
    return list(hsi)


@fixture
def get_hsi_paviau():
    """
    Фикстура, возвращающая эталонное ГСИ PaviaU
    """
    return loadmat(PathToData.paviau_mat.as_posix())['paviaU']


@fixture
def get_mask_paviau():
    """
    Фикстура, возвращающая эталонное ГСИ PaviaU
    """
    return loadmat(PathToData.paviau_gt_mat.as_posix())['paviaU_gt']


@fixture
def get_hsi_from_video():
    """
    Фикстура, возвращающая эталонное ГСИ полученное из видеофайла
    """
    return loadmat(PathToData.hsi_from_video.as_posix())['image']


@fixture
def get_hsi_from_two_videos():
    """
    Фикстура, возвращающая эталонное ГСИ полученное из двух видеофайлов
    """
    vid_1 = loadmat(PathToData.hsi_from_video.as_posix())['image']
    return np.concatenate((vid_1, vid_1), axis=0)


@fixture
def get_hsi_heli_from_uav_one_video():
    """
    Фикстура, возвращающая эталонное ГСИ полученное с БАС с учетом GPS
    """
    return loadmat(PathToData.hsi_from_uav_gps.as_posix())['image']


@fixture()
def get_simple_video_mock_build_metadata():
    """
    Фикстура, возвращающая простые параметры для сборки ГСИ для горизонтальных кадров из видео
    """
    mock_build_metadata = BuildParams(wavelengths=list(range(420, 980)),
                                      coefficients_light_heterogeneity=None,
                                      rotation_angle=None,
                                      flip_wavelengths=False,
                                      roi=None,
                                      frame_orientation='h')
    return mock_build_metadata


@fixture()
def get_simple_vertical_image_mock_build_metadata():
    """
    Фикстура, возвращающая простые параметры для сборки ГСИ для вертикальных кадров
    """
    mock_build_metadata = BuildParams(wavelengths=list(range(420, 980)),
                                      coefficients_light_heterogeneity=None,
                                      rotation_angle=None,
                                      flip_wavelengths=False,
                                      roi=None,
                                      frame_orientation='v')
    return mock_build_metadata


@fixture()
def get_gps_mock_build_metadata():
    """
    Фикстура, возвращающая простые параметры для сборки ГСИ для горизонтальных кадров из видео
    """
    buavp = BuildUAVParams(camera_pitch=0,
                           camera_tangent=0.3,
                           blur_auto=True,
                           target_resolution=1080,
                           distance_limit=1.0,
                           blur_shape=(3, 3),
                           n_neighbours=1)

    mock_build_metadata = BuildParams(wavelengths=list(np.linspace(420, 980, 250).astype(int)),
                                      coefficients_light_heterogeneity=None,
                                      rotation_angle=None,
                                      frame_orientation='h',
                                      flip_wavelengths=False,
                                      uav_params=buavp,
                                      roi=None)

    return mock_build_metadata
