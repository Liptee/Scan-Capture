"""
Модуль для хранения методов предобработки кадров, содержащих спектральную развертку

методы реализуются на замыкании, где внешняя функция принимает статичный набор параметров обработки,
а внутренняя функция принимает только кадр

Спектральная развертка должна быть ориентирована строго вертикально!

Пример:

def outer(*args, **kwargs):
    def inner(frame):
        ... *manipulations with args and kwargs*
        return frame
    return inner

"""
import copy

from typing import Callable, Literal, Optional, Tuple

import cv2
import discorpy.post.postprocessing as post
import numpy as np


FrameOrientation = Literal['v', 'h']


def get_vertical_orient_frame(frame_orientation: FrameOrientation) \
        -> Callable[[np.ndarray], np.ndarray]:
    """
    get_horizontal_orient_frame(frame_orientation)

        Возвращает вертикально расположенный кадр, содержащий спектральную развёртку

        Parameters
        ----------
        frame_orientation: FrameOrientation
            изначальная ориентация кадра вертикальная - 'v' или горизонтальная - 'h'

        Returns
        -------
        Callable[[np.ndarray], np.ndarray]
    """
    is_horizontal_frame = frame_orientation == 'h'

    def _get_vertical_orient_frame(frame):
        if is_horizontal_frame:
            frame = frame.T
        return frame
    return _get_vertical_orient_frame


def get_roi(top_left: Tuple[int, int],
            bottom_right: Tuple[int, int]):
    """
    get_roi(top_left, bottom_right)
        Возвращает вырезанную область интереса (ROI) с кадра.

        top_left: Tuple[int, int]
            Координаты X, Y верхнего левого угла
        bottom_right: Tuple[int, int]
            Координаты X,Y нижнего правого угла

    """
    def _inner_get_roi(frame):
        x_tl, y_tl = top_left
        x_br, y_br = bottom_right
        return frame[slice(x_tl, x_br), slice(y_tl, y_br)]
    return _inner_get_roi


def get_roi_legacy(slit_coordinate: int,
                   distance_to_diffraction_order: int,
                   channels_count: int,
                   left_border_spectrum: int,
                   right_border_spectrum: int) -> Callable[[np.ndarray], np.ndarray]:
    """
    get_roi_legacy(slit_coordinate,
                   distance_to_diffraction_order,
                   channels_count,
                   left_border_spectrum,
                   right_border_spectrum)

        Возвращает вырезанную область интереса (ROI) с кадра

        Parameters
        ----------
        slit_coordinate: int
            координата по оси Y максимума 0-го порядка (изображение щели)
        distance_to_diffraction_order: int
            расстояние от максимума 0-го порядка до максимума 1-го порядка
        channels_count: int
            количество каналов
        left_border_spectrum: int
            левая граница по оси X максимума 1-го порядка
        right_border_spectrum: int
            правая граница по оси X максимума 1-го порядка

        Returns
        -------
        Callable[[np.ndarray], np.ndarray]
    """
    def _inner_get_roi(frame):
        upper_bound = slit_coordinate + distance_to_diffraction_order
        down_bound = upper_bound + channels_count

        width_diffraction_order = slice(left_border_spectrum, right_border_spectrum)
        depth_diffraction_order = slice(upper_bound, down_bound)

        return frame[width_diffraction_order, depth_diffraction_order]
    return _inner_get_roi


def rotate_frame(rotation_angle: float) -> Callable[[np.ndarray], np.ndarray]:
    """
    rotate_frame(rotation_angle)

        Поворачивает кадр на заданный угол

        Parameters
        ----------
        rotation_angle: float
            Угол поворота изображения

        Returns
        -------
        Callable[[np.ndarray], np.ndarray]
    """
    def _rotate_frame(frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape
        center_x, center_y = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D((center_x, center_y), rotation_angle, 1.0)
        frame = cv2.warpAffine(frame, rotation_matrix, (w, h))
        return frame
    return _rotate_frame


def apply_barrel_distortion(coeffs: np.ndarray,
                            powers: np.ndarray,
                            factors: np.ndarray,
                            center_xy: Optional[np.ndarray] = None,
                            line_step: int = 40,
                            line_val: float = 0.25) -> np.ndarray:
    """
    Метод компенсации дисторсии кадра
        В разработке...
    """
    def _apply_barrel_distortion(frame: np.ndarray):
        image_src = frame.astype(np.float32) / 255.0
        height, width = image_src.shape[0:2]
        xcenter = width // 2
        ycenter = height // 2

        if center_xy is not None:
            if len(center_xy) == 2:
                xcenter, ycenter = center_xy

        line_offset_x = 50
        line_offset_y = 50
        line_count_x = int(np.ceil((width - 2 * line_offset_x - width // 2 + xcenter) // line_step) // 2)
        line_count_y = int(np.ceil((height - 2 * line_offset_y - height // 2 + ycenter) // line_step) // 2)

        # Create a line-pattern image
        image_grid = np.zeros((height, width), dtype=np.float32)

        for i in range(-line_count_y, line_count_y):
            y = int(ycenter + i * line_step)
            image_grid[y - 1:y + 1] = line_val
        for i in range(-line_count_x, line_count_x):
            x = int(xcenter + i * line_step)
            image_grid[:, x - 1:x + 1] = line_val

        pad = max(width // 2, height // 2)  # Need padding as lines are shrunk after warping.
        image_grid_padded = np.pad(image_grid, pad, mode='edge')

        # Prepare powers and coeffs arrays
        j = 0
        powers_prep = []
        coeffs_prep = []
        factors_prep = np.array([10 ** f for f in factors])
        for i in range(powers[-1] + 1):
            if i in powers:
                powers_prep.append(factors_prep[j])
                coeffs_prep.append(coeffs[j])
                j += 1
            else:
                powers_prep.append(0)
                coeffs_prep.append(0)
        powers_prep = np.array(powers_prep)
        coeffs_prep = np.array(coeffs_prep)

        list_ffact = powers_prep * coeffs_prep
        image_grid_warped = post.unwarp_image_backward(image_grid_padded,
                                                       xcenter + pad,
                                                       ycenter + pad,
                                                       list_ffact)
        image_grid_warped = image_grid_warped[pad: pad + height, pad: pad + width]
        image_in_grid_warped = copy.deepcopy(image_src)

        if len(image_src.shape) == 3:
            for i in range(3):
                image_in_grid_warped[:, :, i] = image_in_grid_warped[:, :, i] + 0.5 * image_grid_warped
            image_in_grid_warped[image_in_grid_warped > 1] = 1
        else:
            image_in_grid_warped = image_src + 0.5 * image_grid_warped

        image_in_grid_warped = (image_in_grid_warped * 255).astype(np.uint8)

        return image_in_grid_warped
    return _apply_barrel_distortion


def blur_image(window: Tuple[int, int]) -> Callable[[np.ndarray], np.ndarray]:
    """
    blur_image(window)

        Размытие входного изображения по заданному окну

        Parameters
        ----------
        window: Tuple[int, int]
            размер окна размытия

        Returns
        -------
        Callable[[np.ndarray], np.ndarray]
    """
    def inner_blur_image(image):
        return cv2.blur(image, window)
    return inner_blur_image


def remove_dark_current(dc_frame: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
    """
    remove_dark_current(dc_frame)

        Удаление темновых токов и горячих пикселов с ГС-кадра.

        Parameters
        ----------
        dc_frame: np.ndarray
            Кадр содержащий темновые токи и горячие пикселы

        Returns
        -------
        Callable[[np.ndarray], np.ndarray]
    """
    def inner_dark_current(frame: np.ndarray) -> np.ndarray:
        if dc_frame.shape == frame.shape:
            return frame - dc_frame
    return inner_dark_current
