"""
Модуль содержит юнит-тесты для функционала объекта класса hsimage
"""
import os
import shutil

import numpy as np

from conftest import PathToData
from hs import hsimage, load_hsi, save_hsi


# Todo Добавить тесты записи/чтения метаинформации ГСИ


def test_load_hsi_from_mat(get_hsi_paviau):
    """
    Проверка корректности чтения ГСИ из файла формата MAT
    """
    hsi = load_hsi(PathToData.paviau_mat, key='paviaU')
    assert np.all(hsi.data == get_hsi_paviau)


def test_load_hsi_from_npy(get_hsi_paviau):
    """
    Проверка корректности чтения ГСИ из файла формата NPY
    """
    hsi = load_hsi(PathToData.paviau_npy, key='paviaU')
    assert np.all(hsi.data == get_hsi_paviau)


def test_load_hsi_from_tiff(get_hsi_paviau):
    """
    Проверка корректности чтения ГСИ из файла формата TIFF
    """
    hsi = load_hsi(PathToData.paviau_tiff, key='paviaU')
    assert np.all(hsi.data == get_hsi_paviau)


def test_save_hsi_to_mat(get_hsi_paviau):
    """
    Проверка корректности записи ГСИ в файл формата MAT
    """
    if not PathToData.path_to_save_test_hsi.exists():
        os.mkdir(PathToData.path_to_save_test_hsi.as_posix())
    test_name = 'test.mat'
    hsi = hsimage(get_hsi_paviau)
    save_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', hsi, key='test')
    tmp = load_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', key='test')
    assert np.all(tmp.data == get_hsi_paviau)
    shutil.rmtree(PathToData.path_to_save_test_hsi.as_posix())


def test_save_hsi_to_npy(get_hsi_paviau):
    """
    Проверка корректности записи ГСИ в файл формата NPY
    """
    if not PathToData.path_to_save_test_hsi.exists():
        os.mkdir(PathToData.path_to_save_test_hsi.as_posix())
    test_name = 'test.npy'
    hsi = hsimage(get_hsi_paviau)
    save_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', hsi, key='test')
    tmp = load_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', key='test')
    assert np.all(tmp.data == get_hsi_paviau)
    shutil.rmtree(PathToData.path_to_save_test_hsi.as_posix())


def test_save_hsi_to_tiff(get_hsi_paviau):
    """
    Проверка корректности записи ГСИ в файл формата TIFF
    """
    if not PathToData.path_to_save_test_hsi.exists():
        os.mkdir(PathToData.path_to_save_test_hsi.as_posix())
    test_name = 'test.tiff'
    hsi = hsimage(get_hsi_paviau)
    save_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', hsi, key='test')
    tmp = load_hsi(f'{PathToData.path_to_save_test_hsi.as_posix()}/{test_name}', key='test')
    assert np.all(tmp.data == get_hsi_paviau)
    shutil.rmtree(PathToData.path_to_save_test_hsi.as_posix())
