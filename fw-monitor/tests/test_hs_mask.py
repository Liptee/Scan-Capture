"""
Модуль содержит юнит-тесты для функционала объекта класса hsmask
"""
import os
import shutil

import numpy as np

from conftest import PathToData
from hs import hsmask, load_mask, save_mask


def test_load_mask_from_mat(get_mask_paviau):
    """
    Проверка корректности чтения ГСИ из файла формата MAT
    """
    mask = load_mask(PathToData.paviau_gt_mat, key='paviaU_gt')
    assert np.all(mask.get_2d() == get_mask_paviau)


def test_load_mask_from_npy(get_mask_paviau):
    """
    Проверка корректности чтения ГСИ из файла формата NPY
    """
    mask = load_mask(PathToData.paviau_gt_npy)
    assert np.all(mask.data == get_mask_paviau)


def test_save_mask_to_mat_as2d(get_mask_paviau):
    """
    Проверка корректности записи ГСИ в файл формата MAT
    """
    if not PathToData.path_to_save_test_mask.exists():
        os.mkdir(PathToData.path_to_save_test_mask.as_posix())
    test_name = 'test.mat'
    mask = hsmask(get_mask_paviau)
    save_mask(f'{PathToData.path_to_save_test_mask.as_posix()}/{test_name}',
              mask,
              as_2d=True,
              key='test')
    tmp = load_mask(f'{PathToData.path_to_save_test_mask.as_posix()}/{test_name}', key='test')
    assert np.all(tmp.get_2d() == get_mask_paviau)
    shutil.rmtree(PathToData.path_to_save_test_mask.as_posix())


def test_save_mask_to_mat_as3d(get_mask_paviau):
    """
    Проверка корректности записи ГСИ в файл формата MAT
    """
    if not PathToData.path_to_save_test_mask.exists():
        os.mkdir(PathToData.path_to_save_test_mask.as_posix())
    test_name = 'test.mat'
    mask = hsmask(get_mask_paviau)
    save_mask(f'{PathToData.path_to_save_test_mask.as_posix()}/{test_name}',
              mask,
              as_2d=False,
              key='test')
    tmp = load_mask(f'{PathToData.path_to_save_test_mask.as_posix()}/{test_name}', key='test')
    assert np.all(tmp.get_2d() == get_mask_paviau)
    shutil.rmtree(PathToData.path_to_save_test_mask.as_posix())


def test_save_mask_to_npy_as2d(get_mask_paviau):
    """
    Проверка корректности записи ГСИ в файл формата NPY
    """
    if not PathToData.path_to_save_test_mask.exists():
        os.mkdir(PathToData.path_to_save_test_mask.as_posix())
    test_name = 'test.npy'
    mask = hsmask(get_mask_paviau)
    save_mask(f'{PathToData.path_to_save_test_mask.as_posix()}/{test_name}',
              mask,
              as_2d=True)
    tmp = load_mask(f'{PathToData.path_to_save_test_mask.as_posix()}/{test_name}', key='test')
    assert np.all(tmp.get_2d() == get_mask_paviau)
    shutil.rmtree(PathToData.path_to_save_test_mask.as_posix())


def test_save_mask_to_npy_as3d(get_mask_paviau):
    """
    Проверка корректности записи ГСИ в файл формата NPY
    """
    if not PathToData.path_to_save_test_mask.exists():
        os.mkdir(PathToData.path_to_save_test_mask.as_posix())
    test_name = 'test.npy'
    mask = hsmask(get_mask_paviau)
    save_mask(f'{PathToData.path_to_save_test_mask.as_posix()}/{test_name}',
              mask,
              as_2d=False)
    tmp = load_mask(f'{PathToData.path_to_save_test_mask.as_posix()}/{test_name}', key='test')
    assert np.all(tmp.get_2d() == get_mask_paviau)
    shutil.rmtree(PathToData.path_to_save_test_mask.as_posix())
