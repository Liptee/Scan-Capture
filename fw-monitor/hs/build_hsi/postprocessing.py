"""
Модуль хранит методы пост-обработки ГСИ
"""

import json
import warnings

from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, Union

import numpy as np

from scipy.interpolate import interp1d

import hs
from hs import load_hsi, hsimage
from hs.build_hsi.uav_utils import build_hypercube_with_gps, build_hypercube_with_gps_triangle, \
    _guided_image_filtering, _create_guided_image


class GPSBuild:
    # ToDo требуется апдейт! Не используется на текущий момент
    def __init__(self,
                 gps_reader,
                 build_params,
                 builder_type='knn'):
        self.gps_reader = gps_reader
        self.build_params = build_params
        if builder_type == 'knn':
            self._gps_builder = self._build_with_gps_knn
        elif builder_type == 'triangle':
            self._gps_builder = self._build_with_gps_triangle
        else:
            raise Exception("!!!")

    def __call__(self, data):
        return self._gps_builder(data, self.gps_reader, self.build_params)

    def _build_with_gps_knn(self,
                            data: Union[np.ndarray, hs.hsimage],
                            gps_iterator,
                            build_params) -> np.ndarray:
        """
        _build_with_gps_knn(data)

            Сборка входного набора гиперспектральных кадров с учетом GPS на основе KNN

            Parameters
            ----------
            data: np.ndarray
                Массив кадров (Frame_i, Y, X)
            gps_iterator:

            build_params:


            Returns
            -------
            np.ndarray
        """
        telemetry: dict[str, Any] = {'latitude': gps_iterator.latitude,
                                     'longitude': gps_iterator.longitude,
                                     'rel_alt': gps_iterator.rel_alt,
                                     'angle': gps_iterator.angle}
        builded_hypercube = build_hypercube_with_gps(data.astype("uint8"),
                                                     telemetry,
                                                     uav_bp=build_params.uav_params)
        return builded_hypercube

    def _build_with_gps_triangle(self,
                                 data: np.ndarray,
                                 gps_iterator,
                                 build_params) -> np.ndarray:
        """
        _build_with_gps_triangle(data)

            Сборка входного набора гиперспектральных кадров с учетом GPS на основе триангуляции

            Parameters
            ----------
            data: np.ndarray
                Массив кадров (Frame_i, Y, X)
            gps_iterator:

            build_params:

            Returns
            -------
            np.ndarray
        """
        builded_hypercube = build_hypercube_with_gps_triangle(data.astype("uint8"),
                                                              gps_iterator,
                                                              uav_bp=build_params.uav_params)

        return builded_hypercube


class PostFilter:
    """
        Класс для пост-фильтарции гиперспектрального изобржения

        hsi: HSImage
            гиперспектральное изобржения,
        channels: Union[Literal["default", "full"], list[int]]
            Список каналов для постобработки.

        """

    def __init__(self, processing_type: Literal["inversion_epsilon"] = "inversion_epsilon",
                 channels: Union[Literal["default", "full"], list[int]] = "default",
                 filt_size: tuple[int, int] = None,
                 inversion_epsilon: float = None,
                 ):
        self._channels = channels
        self._filt_size = filt_size
        self._inversion_epsilon = inversion_epsilon
        if processing_type == 'inversion_epsilon':
            self._post_filter = self._filter_image
        else:
            raise Exception("!!!")

    def __call__(self, data: np.ndarray):
        return self._post_filter(data, self._channels, self._filt_size, self._inversion_epsilon)

    def _filter_image(
            self,
            data: np.ndarray,
            channels: Union[Literal["default", "full"], list[int]],
            filt_size: tuple[int, int],
            inversion_epsilon: float
    ) -> np.ndarray:
        """
        Function to filter a hyperspectral image.
        :param filt_size: Filter size.
        :param inversion_epsilon: Inversion parameter.

        Usage example:
        ```
        image = HSImage.from_npy_and_markup("example_image.npy")
        filter_image(image, (5, 5), 0.1)
        ```
        """
        output_data = deepcopy(data)
        if channels == "full":
            channels = list(range(data.shape[2]))
        elif channels == "default":
            channels = [0]
        else:
            channels = channels
        try:
            for i in channels:
                output_data[:, :, i] = _guided_image_filtering(
                    output_data[:, :, i],
                    _create_guided_image(output_data[:, :, i], filter_mode="box"),
                    filt_size,
                    inversion_epsilon,
                )
        except Exception as e:
            warnings.warn(
                f"Error: An exception occurred during hyperspectral image filtering - {e}"
            )
        return output_data


class PostNormalisation:
    """
        Класс для пост-нормализации гиперспектрального изобржения

        hsi: HSImage
            гиперспектральное изобржения,
        channels: Literal["default", "full"] | list[int]
            Список каналов для постобработки.

    """

    def __init__(self,
                 normalisation_type: Literal["strip"] = "strip",
                 channels: Union[Literal["default", "full"], list[int]] = "default",
                 norm_param: Union[int, np.ndarray] = None,
                 ):
        self._channels = channels
        self._norm_param = norm_param

        if normalisation_type == 'strip':
            self._post_normaliser = self._data_normalization

        else:
            raise Exception("!!!")

    def __call__(self, data):
        return self._post_normaliser(data, self._channels, self._norm_param)

    def _data_normalization(
            self,
            data: np.ndarray,
            channels: Union[Literal["default", "full"], list[int]],
            norm_param: Union[int, np.ndarray],
    ) -> np.ndarray:
        """
        Function to normalize data by a specific band or a given strip.
        :param norm_param: Band number for normalization or vertical strip for normalization.

        Usage example:
        ```
        image = HSImage.from_npy_and_markup("example_image.npy")
        data_normalization(image, norm_param=5)
        data_normalization(image, norm_param=data_for_normalization)
        ```
        """
        output_data = deepcopy(data)
        if channels == "full":
            channels = list(range(data.shape[2]))
        elif channels == "default":
            channels = [0]
        else:
            channels = channels
        try:
            # _normalization(hsi, channels)
            if isinstance(norm_param, np.ndarray):
                if norm_param.shape[0] != output_data.shape[0]:
                    raise ValueError(
                        "The height of the strip must match the height of the image."
                    )
                for i in channels:
                    np.divide(
                        output_data[:, :, i],
                        norm_param[:, None, i],
                        out=output_data[:, :, i],
                        where=norm_param[:, None, i] != 0,
                    )
            elif isinstance(norm_param, int):
                strip = output_data[:, norm_param, channels]
                for i in channels:
                    np.divide(
                        output_data[:, :, i],
                        strip[:, None, i],
                        out=output_data[:, :, i],
                        where=strip[:, None, i] != 0,
                    )
            else:
                raise ValueError(
                    "norm_param must be either an integer or a numpy array."
                )
        except IndexError:
            warnings.warn("Error: Index out of range during data normalization.")
        except ValueError as e:
            warnings.warn(f"Error: {e}")
        return output_data


def calibrate_hsi(hsi: hsimage,
                  white_point: np.ndarray,
                  calibration_path: Union[str, Path]):
    """

    :param hsi:
    :param white_point:
    :param calibration_path:
    :return:
    """
    if hsi.shape[-1] != white_point.shape[0]:
        raise ValueError(f"HSI shape {hsi.shape[-1]} and White Point shape {white_point.shape} not equal")

    with open(calibration_path, mode="r", encoding="utf-8") as f:
        data = json.loads(f.read())
        d = dict(zip([int(i) for i in list(data.keys())], list(data.values())))

    interp_ = interp1d(np.array(list(d.keys())), np.array(list(d.values())), fill_value='extrapolate', kind='linear')
    r_ref_corrected = interp_(hsi.wavelengths)
    hsi_corrected = hsi * (1 / white_point) * (r_ref_corrected * 0.01)

    return hsi_corrected


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    PATH_TO_DEMO_HSI = "..."
    hsi = load_hsi(PATH_TO_DEMO_HSI)
    print(hsi.shape)
    original = np.copy(hsi.data)

    strip = np.copy(hsi.data[:, 500, :])

    post_orthotrop = PostNormalisation(
        normalisation_type="strip",
        channels="full",
        norm_param=strip
    )

    strip_corrected = post_orthotrop(original)

    post_filter = PostFilter(
        processing_type="inversion_epsilon",
        channels="full",
        filt_size=(8, 8),
        inversion_epsilon=0.001 ** 2
    )

    filtered_image = post_filter(strip_corrected)

    fig, ax = plt.subplots(1, 3, figsize=(20, 20))
    ax[0].imshow(hsi.data[:, :, 0], cmap='gray')
    ax[0].set_title("Original image")

    ax[1].imshow(strip_corrected.data[:, :, 0], cmap='gray')
    ax[1].set_title("Strip corrected image")

    ax[2].imshow(filtered_image.data[:, :, 0], cmap='gray')
    ax[2].set_title("Filtered image")

    plt.show()
