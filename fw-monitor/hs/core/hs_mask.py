"""
Модуль содержит структуры и функции для реализации представления маски разметки ГСИ
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

from hs.core.utils import load_mat, load_npy, save_mat, save_npy, \
                          load_json, load_toml, save_json, save_toml
from hs.utils import BaseDescriptorClass


HSMaskSupportedExtensions = ['.mat', '.npy']


class _CorrectPathToOpen(BaseDescriptorClass):  # pylint: disable=too-few-public-methods
    """
    Класс-дескриптор для проверки корректности пути для чтения ГСИ

        Проверка поддерживаемых форматов
    """
    def __set__(self, instance, value):
        if not isinstance(value, Path):
            value = Path(value)
        if value.suffix in HSMaskSupportedExtensions:
            instance.__dict__[self.name] = value
        else:
            raise ValueError('Unsupported extension')


class _CorrectPathToSave(BaseDescriptorClass):  # pylint: disable=too-few-public-methods
    """
    Класс-дескриптор для проверки корректности пути для записи ГСИ

        Проверка поддерживаемых форматов
    """
    def __set__(self, instance, value):
        if not isinstance(value, Path):
            value = Path(value)

        if value.suffix in HSMaskSupportedExtensions:
            instance.__dict__[self.name] = value
        else:
            raise ValueError('Unsupported extension')


def convert_2d_to_3d_array(arr: np.ndarray) -> np.ndarray:
    """
    convert_2d_to_3d_array(arr)
        Преобразует 2D массив (XY) в 3D one-hot-encoding представление (XYZ)

        Parameters
        ----------
        arr: np.ndarray
            2D массив

        Returns
        -------
        np.ndarray

    """
    h, w = arr.shape
    count_classes = np.max(arr) + 1
    mask_3d = np.zeros((h, w, count_classes))

    for cl in np.unique(arr):
        mask_3d[:, :, cl] = (arr == cl).astype('uint8')

    return mask_3d


def convert_3d_to_2d_array(arr: np.ndarray) -> np.ndarray:
    """
    convert_3d_to_2d_array(arr)

        Преобразует 3D one-hot-encoding массив (XYZ) в 2D представление (XY)

        Parameters
        ----------
        arr: np.ndarray
            3D one-hot-encoding массив

        Returns
        -------
        np.ndarray
    """
    mask_2d = np.zeros(arr.shape[:2])
    for cl, layer in enumerate(np.transpose(arr, (2, 0, 1))):
        mask_2d[layer == 1] = cl

    return mask_2d.astype('uint8')


def is_correct_2d_mask(mask: np.ndarray) -> bool:
    """
    is_correct_2d_mask(mask)

        Проверка корректности 2D маски (размерность и тип данных).

        Parameters
        ----------
        mask: np.ndarray
            входная маска

        Returns
        -------
        bool
    """
    # input mask must have 2 dimensions
    valid_types = ["uint8", "uint16", "uint32", "uint64", "int8", "int16", "int32", "int64"]
    return len(mask.shape) == 2 and mask.dtype in valid_types


def is_correct_3d_mask(mask: np.ndarray) -> bool:
    """
    is_correct_3d_mask(mask)
        3D представление маски должно иметь N-слоев бинарного вида
        Минимальная размерность по оси Z = 2

        Parameters
        ----------
        mask: np.ndarray
            входная маска
        Returns
        -------
        bool
    """
    # check 3D-condition and layer (class) count
    if len(mask.shape) != 3 or mask.shape[-1] < 2:
        return False

    # check each layer that it's binary
    for layer in np.transpose(mask, (2, 0, 1)):
        if np.all(np.unique(layer) != np.array([0, 1])):
            return False
    return True


class Correct3DMask(BaseDescriptorClass):  # pylint: disable=too-few-public-methods
    """
    Проверка корректных данных для инициализации маски разметки ГСИ

        Проверка корректности 3D представления
        Проверка корректности 2D представления
    """
    def __set__(self, instance, value):
        if is_correct_3d_mask(value):
            instance.__dict__[self.name] = value
        elif is_correct_2d_mask(value):
            instance.__dict__[self.name] = convert_2d_to_3d_array(value)
        else:
            raise ValueError('Incorrect mask!')


class HSMask:
    """
    Класс маски разметки ГСИ

    Маска разметки ГСИ хранится в 3D one-hot-encoding представлении
    XY - пространственные координаты
    Z - метка класса

    Attributes
    ----------
    data: np.ndarray
        3D представление маски разметки
    label_class: Dict[int, str]
        Метки классов и их название

    count_classes(): property int
        Количество классов
    shape(): property Tuple[int, int, int]

    Methods
    -------
    get_2d()
        возвращает 2D представление маски разметки
    get_3d()
        возвращает 3D one-hot-encoding представление маски разметки
    save(path)
        запись маски разметки на ПЗУ

    """
    data = Correct3DMask()
    path_to_open = _CorrectPathToOpen()
    path_to_save = _CorrectPathToSave()

    def __init__(self,
                 data: Optional[np.array] = None,
                 label_class: Optional[Dict[int, str]] = None):
        self.data = data
        self.label_class = label_class

    def __getitem__(self, item):
        if item >= len(self):
            raise IndexError(f"{item} is too much for {len(self)} channels in hsi")
        return self.data[:, :, item]

    def __len__(self):
        if self.data is not None:
            return self.count_classes
        return 0

    @property
    def count_classes(self) -> int:
        """
        Количество классов разметки
        """
        return self.data.shape[-1]

    @property
    def shape(self) -> Tuple[int, int, int]:
        """
        Размерность маски разметки в 3D представлении
        """
        return self.data.shape

    @property
    def metadata(self) -> Dict[str, Any]:
        """
        Метаданные маски
        """
        return {
            "label_class": self.label_class
        }

    @metadata.setter
    def metadata(self, value: Dict[str, Any]):
        if isinstance(value, dict):
            self.label_class = value.get("label_class", None)

    def get_2d(self) -> np.ndarray:
        """
        get_2d()
            returns 2d-mask with values in [0,1,2...]

        """
        return convert_3d_to_2d_array(arr=self.data)

    def get_3d(self) -> np.ndarray:
        """
        get_3d()
            returns 3d-mask where each layer (Z-axe) is binary image
        """
        return self.data

    def save(self,
             path: Union[str, Path],
             as_2d: bool = False,
             key: Optional[str] = None,
             metadata_ext: str = 'json'):
        """
        save(path, as_2D=False, key=None)

            Запись маски разметки ГСИ на устройство.
            Поддерживаемые форматы MAT и NPY

            Parameters
            ----------
            path: Union[str, Path] - путь к файлу
            key: str = None - ключ, если используется формат MAT
            as_2d: bool = False - сохранение маски разметки в 2D или 3D представлении
            metadata_ext: str
        """
        if not isinstance(path, Path):
            path = Path(path)
        self.path_to_save = path
        save_mask(path=path, mask=self, as_2d=as_2d, key=key, metadata_ext=metadata_ext)


def save_mask_metadata(path_to_metadata: Union[str, Path],
                       metadata: Dict[str, Any]):
    """
    Запись метаинформации в JSON файл

    Parameters
    ----------
    path_to_metadata: Union[str, Path]
        путь к файлу метаданных маски разметки
    metadata: Dict[str, Any]
        словарь метаданных маски разметки, содержащий информацию о метках классов
        {
            "label_class": Optional[Dict[str, str]]
        }
    """

    if not isinstance(path_to_metadata, Path):
        path_to_metadata = Path(path_to_metadata)

    data = {
        "label_class": metadata.get("label_class", None)
    }

    if path_to_metadata.suffix == '.json':
        save_json(path_to_metadata, data)
    elif path_to_metadata.suffix == '.toml':
        save_toml(path_to_metadata, data)
    else:
        raise ValueError(f"Unsupported extension: {path_to_metadata.suffix}")


def load_mask_metadata(path_to_metadata: Union[str, Path]) -> Dict[str, Any]:
    """
    Чтение метаинформации из JSON файла

    Parameters
    ----------
    path_to_metadata: Union[str, Path]
        Путь к файлу метаданных маски разметки

    Returns
    -------
    Dict[str, str]
    """
    path_to_metadata = Path(path_to_metadata)
    if path_to_metadata.suffix == '.json':
        data = load_json(path_to_metadata)
    elif path_to_metadata.suffix == '.toml':
        data = load_toml(path_to_metadata)
    else:
        raise ValueError(f"Unsupported extension: {path_to_metadata.suffix}")

    metadata = {
        "label_class": data.get("label_class", None)
        }
    return metadata


def load_mask(path: Union[str, Path],
              path_to_metadata: Optional[Union[str, Path]] = None,
              key: Optional[str] = None) -> HSMask:
    """
    load_mask(path, key=None)

        Чтение маски разметки ГСИ с устройства.
        Поддерживаемые форматы MAT и NPY
        Возвращает объект hs.core.HSMask

        Parameters
        ----------
        path: Union[str, Path]
            путь к файлу маски разметки
        path_to_metadata: Optional[Union[str, Path]]
            путь к метаданным маски разметки
        key: Optional[str] = None
            ключ, если используется формат MAT

        Returns
        -------
        HSMask
    """
    if not isinstance(path, Path):
        path = Path(path)

    if path.suffix == '.mat':
        mat_data = load_mat(path_to_file=path)
        if key not in mat_data:
            raise ValueError(f"Incorrect key for MAT file. {list(mat_data.keys())} is/are available")
        data = mat_data[key]
    elif path.suffix == '.npy':
        data = load_npy(path_to_file=path)
    else:
        raise ValueError('Unsupported extension!')

    if path_to_metadata:
        if not isinstance(path_to_metadata, Path):
            path_to_metadata = Path(path_to_metadata)

        metadata = load_mask_metadata(path_to_metadata)
    else:
        metadata = None

    hsmask = HSMask(data=data)
    hsmask.metadata = metadata

    return hsmask


def save_mask(path: Union[str, Path],
              mask: HSMask,
              key: Optional[str] = None,
              as_2d: bool = False,
              metadata_ext: str = 'json'):
    """
    save_mask(path, mask, key=None, as_2d=False)

        Запись маски разметки ГСИ на устройство.
        Поддерживаемые форматы MAT и NPY

        path: Union[str, Path]
            путь к файлу
        mask: HSMask
            объект маски разметки ГСИ
        key: str = None
            ключ, если используется формат MAT
        as_2d: bool = False
            сохранение маски разметки в 2D представлении или 3D
    """
    if not isinstance(path, Path):
        path = Path(path)

    if as_2d:
        data = mask.get_2d()
    else:
        data = mask.data

    metadata = mask.metadata
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
    else:
        raise ValueError(f"Usupported extenstion: {path.suffix}")

    if metadata:
        save_mask_metadata(path_to_metadata=path_to_metadata,
                           metadata=metadata)
