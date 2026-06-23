"""
4.1.3.1.2 Программный модуль комплексирования ГСИ и данных
различных модальностей, включающий в себя комплексирование с RGB
(ПМ КомпГСИ)
1) Входные данные (один или несколько из предложенных варинтов):
- ГСИ в формате NPY/MAT/TIFF и метаданные в формате JSON/ TOML или аналогичном, хранящие параметры формирования и характеристики ГСИ;
- RGB данные, соответствующие области интереса на ГСИ;
- опционально: видеофайлы или набор изображений (формат PNG/BMP/TIFF/JPEG);
- опционально: файлы метаданных в формате JSON, содержащие информацию о видеофайлах или наборах изображений.

2) Выходные данные:
- комплексированные данные, сохраняемые на ПЗУ как директория связанных файлов в соответствующих форматах (ГСИ, данные RGB);
- файл метаданных комплексированных данных, в формате JSON/TOML или аналогичном.
"""
import json
from pathlib import Path
from typing import Callable, Union, Optional, Dict, Any
import os

import toml
import numpy as np
from PIL import Image

from hs import load_hsi, save_hsi, load_mask, save_mask


def save_decorator(func: Callable):
    """
        Декоратор для создания каскада директорий к записываемому файлу
    """
    def wrapper(*args, **kwargs):
        path_file = kwargs.get("path_to_cd", None)
        path_dir = os.path.dirname(path_file)
        if not os.path.exists(path_dir):
            os.makedirs(path_dir)
        func(*args, **kwargs)
    return wrapper


def load_rgb(path_to_file: Union[str, Path]) -> np.ndarray:
    """
    Чтение RGB изображения из файла

    Parameters
    ----------
    path_to_file: Union[str, Path]
        Путь к файлу RGB изображения
    Returns
    -------
    np.ndarray
    """
    img = Image.open(path_to_file)
    return np.array(img)


def save_rgb(path_to_save: Union[str, Path], image: np.ndarray):
    """
    Запись RGB изображения в файл на ПЗУ

    Parameters
    ----------
    path_to_save: Union[str, Path]
        Путь к файлу RGB изображения
    image: np.ndarray
        Массив RGB изображения
    """
    if not isinstance(path_to_save, Path):
        path_to_save = Path(path_to_save)

    Image.fromarray(image).save(path_to_save.as_posix())
    # cv2.imwrite(path_to_save.as_posix(), (255 * image).astype(np.uint8))


def load_cd_metadata(path_to_file: Union[str, Path]) -> Dict[str, Any]:
    """
    Чтение метаданных ГСИ и маски разметки ГСИ из файла

    Parameters
    ----------
    path_to_file: Union[str, Path]
        Путь к файлу метаданных
    Returns
    -------
    Dict[str, Any]
    """
    if not isinstance(path_to_file, Path):
        path_to_file = Path(path_to_file)

    if path_to_file.suffix == ".json":
        with open(path_to_file.as_posix(), 'r', encoding='utf-8') as file:
            data = json.load(file)
    elif path_to_file.suffix == ".toml":
        with open(path_to_file.as_posix(), 'r', encoding='utf-8') as file:
            data = toml.load(file)
    else:
        raise ValueError(f"Unsupported extension: {path_to_file.suffix}")

    return data


def save_cd_metadata(path_to_save: Union[str, Path], data):
    """
    Запись метаданных ГСИ и маски разметки ГСИ в файл на ПЗУ

    Parameters
    ----------
    path_to_save: Union[str, Path]
        Путь к файлу метаданных
    data
        Словарь метаданных гси и маски разметки ГСИ
    """
    if not isinstance(path_to_save, Path):
        path_to_save = Path(path_to_save)

    if path_to_save.suffix == ".json":
        with open(path_to_save.as_posix(), 'w', encoding="utf-8") as file:
            file.write(json.dumps(data, indent=4))
    if path_to_save.suffix == ".toml":
        with open(path_to_save.as_posix(), 'w', encoding="utf-8") as file:
            file.write(toml.dumps(data))


class ComplexedData:
    """
    Класс представления объекта для комплексирования ГСИ

    Attributes
    ----------
    hsi: np.ndarray
        Массив ГСИ
    mask: np.ndarray
        Массив маски разметки ГСИ
    rgb_image
        RGB изображение
    cd_metadata
        Представление метаданных ГСИ и маски разметки ГСИ в виде словаря
    """
    def __init__(self,
                 hsi,
                 rgb_image,
                 mask=None,
                 cd_metadata = None):
        self.hsi = hsi
        self.mask = mask
        self.rgb_image = rgb_image
        if cd_metadata is None:
            self.cd_metadata = {
                    "hsi metadata": self.hsi.metadata,
                    "mask metadata": self.mask.metadata if mask is not None else None
                }
        else:
            self.cd_metadata = cd_metadata

    def load_cd(self,
                path_to_cd,
                cd_name="complexed",
                hsi_ext="mat",
                mask_ext=None,
                key: Optional[str] = None,
                rgb_ext="png",
                metadata_ext="json"):
        """
        Чтение ГСИ и сопутствующих данных из файла

        Parameters
        ----------
        path_to_cd
            Путь к файлам данных
        cd_name
            Имя файлов
        hsi_ext
            Расширение файла ГСИ
        mask_ext
            Расширение файла маски
        key
            Ключ для файлов ГСИ и маски, при использовании формата MAT
        rgb_ext
            Расширение файла RGB изображения
        metadata_ext
            Расширения файла метаданных
        """
        if not isinstance(path_to_cd, Path):
            path_to_cd = Path(path_to_cd)

        if path_to_cd.is_dir():
            path_to_hsi = f"{path_to_cd}/hsi_{cd_name}.{hsi_ext}"
            path_to_mask = f"{path_to_cd}/mask_{cd_name}.{mask_ext}"
            path_to_rgb = f"{path_to_cd}/rgb_{cd_name}.{rgb_ext}"
            path_to_metadata = f"{path_to_cd}/cd_metadata_{cd_name}.{metadata_ext}"

            hsi_kwargs = {
                "path": path_to_hsi,
                "path_to_metadata": path_to_metadata}
            mask_kwargs = {
                "path": path_to_mask}

            if hsi_ext == "mat":
                hsi_kwargs["key"] = key
                mask_kwargs["key"] = key

            hsi = load_hsi(**hsi_kwargs)
            self.hsi = hsi

            if mask_ext is not None:
                mask = load_mask(**mask_kwargs)
                self.mask = mask

            rgb_image = load_rgb(path_to_file=path_to_rgb)
            self.rgb_image = rgb_image

            cd_metadata = load_cd_metadata(path_to_file=path_to_metadata)
            self.cd_metadata = cd_metadata


        else:
            raise TypeError("Path must be a directory")

    def save_cd(self,
                path_to_cd,
                cd_name="complexed",
                hsi_ext="mat",
                mask_ext="mat",
                key: Optional[str] = None,
                rgb_ext="png",
                metadata_ext="json"):
        """
        Запись ГСИ и сопутствующих данных в файл на ПЗУ

        Parameters
        ----------
        path_to_cd
            Путь к файлам данных
        cd_name
            Имя сохраняемых файлов
        hsi_ext
            Расширение файла ГСИ
        mask_ext
            Расширение файла маски
        key
            Ключ для файлов ГСИ и маски, при использовании формата MAT
        rgb_ext
            Расширение файла RGB изображения
        metadata_ext
            Расширение файла метаданных
        """
        path_to_hsi = f"{path_to_cd}/hsi_{cd_name}.{hsi_ext}"
        path_to_mask = f"{path_to_cd}/mask_{cd_name}.{mask_ext}"
        path_to_rgb = f"{path_to_cd}/rgb_{cd_name}.{rgb_ext}"
        path_to_metadata = f"{path_to_cd}/cd_metadata_{cd_name}.{metadata_ext}"

        hsi_kwargs = {
            "hsi": self.hsi,
            "path": path_to_hsi,
            "metadata_ext": metadata_ext
        }
        mask_kwargs = {
            "mask": self.mask,
            "path": path_to_mask,
            "metadata_ext": metadata_ext
        }

        if hsi_ext == "mat":
            hsi_kwargs["key"] = key
            mask_kwargs["key"] = key

        save_hsi(**hsi_kwargs)
        save_rgb(image=self.rgb_image, path_to_save=path_to_rgb)
        save_cd_metadata(path_to_save=path_to_metadata, data=self.cd_metadata)
        if self.mask is not None:
            save_mask(**mask_kwargs)


if __name__ == "__main__":
    PATH = ...

    hsi_test = load_hsi(f"{PATH}/PaviaU.mat",
                        key="paviaU",
                        path_to_metadata=f"{PATH}/PaviaU_metadata.json")
    mask_test = load_mask(f"{PATH}/PaviaU_gt.mat",
                          key="paviaU_gt",
                          path_to_metadata=f"{PATH}/PaviaU_gt_metadata.json")
    rgb = load_rgb(f"{PATH}/aaa.jpeg")
    metadata = load_cd_metadata(f"{PATH}/PaviaU_metadata.json")

    cd = ComplexedData(hsi=hsi_test,
                       mask=mask_test,
                       rgb_image=rgb,
                       # cd_metadata=metadata
                       )

    cd.save_cd(path_to_cd=f"{PATH}/test_save",
               key="paviaU")
