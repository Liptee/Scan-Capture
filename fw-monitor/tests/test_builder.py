"""
Модуль предназначен для тестирования модуля формирования ГСИ


Требования:
1) Входные данные:
- видеофайлы, например AVI или аналогичные, или набор растровых изображений, например PNG/JPEG,
  содержащие развёртки гиперспектральной информации на каждом кадре;
- метаданные, содержащие параметры формирования ГСИ, например JSON/TOML или аналогичные.
2) Выходные данные:
- ГСИ в формате NPY/MAT/TIFF и метаданные в формате JSON/TOML или аналогичном,
  хранящие параметры формирования и характеристики ГСИ.


- программные модули должны обеспечивать проверку корректности входных данных.
  В случае несоответствия должно быть выведено сообщение об ошибке
  с указанием выявленного несоответствия;
- должна быть обеспечена проверка на совместимость модулей с помощью проверки форматов входных
  и выходных файлов;
- должна быть обеспечена проверка корректного функционирования модулей на тестовых данных.
"""

import os
import shutil

import numpy as np

from conftest import PathToData, get_layers_from_hsi
from hs import load_hsi, save_hsi, hsbuilder
from hs.build_hsi.raw_data_reader import RawImagesDataReader, RawVideosDataReader


# Todo Добавить тесты записи/чтения метаинформации ГСИ


def test_raw_images_reader_png(get_hsi_paviau):
    """
        Проверка корректности работы итератора кадров по набору изображений формата PNG
    """
    raw_data = RawImagesDataReader(path_to_source=PathToData.images_paviau_png_16bit)
    target = np.array(get_layers_from_hsi(get_hsi_paviau))
    assert np.all(target == np.array(get_layers_from_hsi(raw_data)))


def test_raw_videos_reader_avi(get_hsi_from_video):
    """
            Проверка корректности работы итератора кадров по видеофайлу
            или набору видеофайлов формата AVI
    """
    raw_data = RawVideosDataReader(path_to_source=PathToData.one_video_source)
    builded = np.array(get_layers_from_hsi(raw_data))
    target = np.array(get_layers_from_hsi(get_hsi_from_video)).transpose((0, 2, 1))
    assert target.shape == builded.shape
    assert np.all(target == builded)


def test_input_png(get_hsi_paviau,
                   get_simple_vertical_image_mock_build_metadata):
    """
        Проверка корректности чтения набора кадров, содержащих спектральную развёртку,
        из набора растровых изображений формата PNG
    """
    hsb = hsbuilder(path_to_hs_source=PathToData.images_paviau_png_16bit,
                    source_data_type='images',
                    build_params=get_simple_vertical_image_mock_build_metadata)
    hsb.build_hsi()
    assert np.all(get_hsi_paviau == hsb.get_hsi().data)


def test_input_one_video_avi(get_hsi_from_video, get_simple_video_mock_build_metadata):
    """
        Проверка корректности чтения набора кадров, содержащих спектральную развёртку,
        из видеофайла (-ов) формата AVI
    """

    hsb = hsbuilder(path_to_hs_source=PathToData.one_video_source,
                    source_data_type='video',
                    build_params=get_simple_video_mock_build_metadata)
    hsb.build_hsi()
    assert np.all(get_hsi_from_video == hsb.get_hsi().data)


def test_input_two_video_sequence_avi(get_hsi_from_two_videos,
                                      get_simple_video_mock_build_metadata):
    """
        Проверка корректности чтения набора кадров, содержащих спектральную развёртку,
        из видеофайла (-ов) формата AVI
    """

    hsb = hsbuilder(path_to_hs_source=PathToData.two_video_source,
                    source_data_type='video',
                    build_params=get_simple_video_mock_build_metadata)
    hsb.build_hsi()
    assert get_hsi_from_two_videos.shape == hsb.get_hsi().data.shape
    assert np.all(get_hsi_from_two_videos == hsb.get_hsi().data)


def test_input_video_with_gps(get_hsi_heli_from_uav_one_video,
                              get_gps_mock_build_metadata):
    """
    Проверка формирования ГСИ с учетом траектории по данным GPS
    """
    hsb = hsbuilder(path_to_hs_source=PathToData.videos_uav_gps,
                    path_to_gps=PathToData.gps_file,
                    source_data_type='video',
                    build_params=get_gps_mock_build_metadata)
    hsb.build_hsi()
    builded_hsi = hsb.get_hsi()
    assert get_hsi_heli_from_uav_one_video.shape == builded_hsi.data.shape
    assert np.mean(get_hsi_heli_from_uav_one_video - builded_hsi.data) < 1


def test_save_builded_hsi_to_mat(get_hsi_paviau,
                                 get_simple_vertical_image_mock_build_metadata):
    """
    Проверка записи ГСИ в MAT файл
    """
    if not PathToData.path_to_save_test_hsi.exists():
        os.mkdir(PathToData.path_to_save_test_hsi.as_posix())
    test_name = 'test.mat'
    hsb = hsbuilder(path_to_hs_source=PathToData.images_paviau_png_16bit,
                    source_data_type='images',
                    build_params=get_simple_vertical_image_mock_build_metadata)
    hsb.build_hsi()
    hsi = hsb.get_hsi()
    save_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', hsi, key='test')
    tmp = load_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', key='test')
    shutil.rmtree(PathToData.path_to_save_test_hsi.as_posix())
    assert np.all(tmp.data == get_hsi_paviau)


def test_save_builded_hsi_to_tiff(get_hsi_paviau,
                                  get_simple_vertical_image_mock_build_metadata):
    """
    Проверка записи ГСИ в TIFF файл
    """
    if not PathToData.path_to_save_test_hsi.exists():
        os.mkdir(PathToData.path_to_save_test_hsi.as_posix())
    test_name = 'test.tiff'
    hsb = hsbuilder(path_to_hs_source=PathToData.images_paviau_png_16bit,
                    source_data_type='images',
                    build_params=get_simple_vertical_image_mock_build_metadata)
    hsb.build_hsi()
    hsi = hsb.get_hsi()
    save_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', hsi, key='test')
    tmp = load_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', key='test')
    shutil.rmtree(PathToData.path_to_save_test_hsi.as_posix())
    assert np.all(tmp.data == get_hsi_paviau)


def test_save_builded_hsi_to_npy(get_hsi_paviau,
                                 get_simple_vertical_image_mock_build_metadata):
    """
    Проверка записи ГСИ в MAT файл
    """
    if not PathToData.path_to_save_test_hsi.exists():
        os.mkdir(PathToData.path_to_save_test_hsi.as_posix())
    test_name = 'test.npy'
    hsb = hsbuilder(path_to_hs_source=PathToData.images_paviau_png_16bit,
                    source_data_type='images',
                    build_params=get_simple_vertical_image_mock_build_metadata)
    hsb.build_hsi()
    hsi = hsb.get_hsi()
    save_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', hsi, key='test')
    tmp = load_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', key='test')
    shutil.rmtree(PathToData.path_to_save_test_hsi.as_posix())
    assert np.all(tmp.data == get_hsi_paviau)


# def test_input_jpeg(path_to_source: Path):
#     '''
#         Проверка корректности чтения набора кадров, содержащих спектральную развёртку,
#         из набора растровых изображений формата JPEG/JPG
#     '''
#     assert True
#
#
# def test_input_json(path_to_source: Path):
#     '''
#         Проверка корректности чтения метаинформации из файла формата JSON, а именно:
#         - информации для корректного формирования ГСИ, из набора кадров,
#           содержащих спектральную развёртку,
#           полученных определенной ГСА;
#         - информации для учёта траектории движения БАС по его телеметрии при формировании ГСИ.
#     '''
#     assert True
#
#
# def test_input_toml(path_to_source: Path):
#     '''
#         Проверка корректности чтения метаинформации из файла формата TOML, а именно:
#         - информации для корректного формирования ГСИ, из набора кадров,
#           содержащих спектральную развёртку,
#           полученных определенной ГСА;
#         - информации для учёта траектории движения БАС по его телеметрии при формировании ГСИ.
#     '''
#     assert True
#
#
# def test_save_json(path_to_save: Path):
#     '''
#         Проверка корректности записи файла метаинформации на ПЗУ в формате JSON
#
#     '''
#     assert True
#
#
# def test_save_toml(path_to_save: Path):
#     assert True
