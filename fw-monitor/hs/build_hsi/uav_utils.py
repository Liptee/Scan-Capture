"""
Модуль предназначен для хранения методов формирования ГСИ
с учетом траектории движения по GPS данным
"""
from __future__ import annotations
import itertools
import math
import warnings

from typing import List, Tuple, Dict, Literal, NamedTuple, NewType

import cv2
import numpy as np
import pandas as pd

from scipy.ndimage import gaussian_filter1d
from sklearn import neighbors
from utm import from_latlon

from hsirs.raster import triangle_fill
from hs.build_hsi.builder_params import BuildUAVParams, HyperDevice
from hs.build_hsi.preprocessing_frames import blur_image
from hs.build_hsi.raw_data_reader import GPSReader



def build_hypercube_with_gps(cube: np.ndarray,
                             telemetry: Dict,
                             hyper_device: HyperDevice,
                             uav_bp: BuildUAVParams) -> np.ndarray:
    """
    build_hypercube_with_gps(cube, telemetry, uav_bp)

        Производит геокоррекцию ГСИ по данным GPS

        Parameters
        ----------
        cube: np.ndarray
            ГСИ без геокоррекции
        telemetry: Dict[str, Any]
            GPS данные в формате словаря
            {'latitude': List[float],
             'longitude': List[float],
             'rel_alt': List[float],
             'angle': List[float]}
        hyper_device: HyperDevice
            Параметры ГСА
             camera_pitch: float
            camera_tangent: float
        uav_bp: BuildUAVConstants
            Параметры для формирования ГСИ с учетом телеметрии
            resolution_cm: int
            build_algorithm_params
                blur_auto: bool
                target_resolution: int
                distance_limit: float
                blur_shape: Tuple[int, int]
                n_neighbours: int

        Returns
        --------
        np.ndarray
    """
    _, _, z = cube.shape

    latitude = telemetry['latitude']
    longitude = telemetry['longitude']
    rel_alt = telemetry['rel_alt']
    angle = telemetry['angle']
    corner_coordinates = telemetry['corner_coordinates']

    lat_lon = (latitude, longitude)

    corrected_rel_alt = _calculate_corrected_rel_alt(rel_alt,
                                                     hyper_device.pitch)

    corrected_lat_lon = _calculate_corrected_lat_lon(lat_lon,
                                                     corrected_rel_alt,
                                                     angle,
                                                     hyper_device.pitch)

    coordinates_and_hyperpixel = _coordinates_and_hyperpixels(cube,
                                                              corrected_lat_lon,
                                                              corrected_rel_alt,
                                                              angle,
                                                              hyper_device.tangent)
    _width_in_wgs_degree = np.abs(corner_coordinates['upper_left'][1] - corner_coordinates['lower_right'][1])
    center_long_in_degree = corner_coordinates['center'][0]
    _width_in_meters = _width_in_wgs_degree * 111_000 * np.cos(center_long_in_degree / 57.2958)
    _target_res_pixels = int(_width_in_meters * 100 / uav_bp.resolution_cm)
    geocorr_hsi = _interpolate(cube=cube,
                               coordinates_and_hyperpixel=coordinates_and_hyperpixel,
                               n_neighbours=uav_bp.build_algorithm_params.n_neighbours,
                               target_resolution_x=_target_res_pixels,
                               distance_limit=uav_bp.build_algorithm_params.distance_limit)

    if uav_bp.build_algorithm_params.blur_auto:
        blur = blur_image(uav_bp.build_algorithm_params.blur_shape)
        geocorr_hsi = list(map(blur, [geocorr_hsi[:, :, i] for i in range(z)]))
        geocorr_hsi = np.array(geocorr_hsi)

    geocorr_hsi = np.transpose(geocorr_hsi, (1, 0, 2))
    return geocorr_hsi


# --------------------------------------------------------------------------------------------------


def _interpolate(cube: np.ndarray,
                 coordinates_and_hyperpixel: Tuple[np.ndarray, np.ndarray, np.ndarray],
                 n_neighbours: int,
                 target_resolution_x: int,
                 distance_limit: float = 1.0) -> np.ndarray:
    """
    _interpolate(cube,
                coordinates,
                n_neighbours,
                target_resolution_x,
                distance_limit=1.0)

        Формирование ГСИ по заданным координатам

        Parameters:
        -----------
        cube: np.ndarray
            ГСИ без геокоррекции
        coordinates_and_hyperpixel: Tuple[np.ndarray, np.ndarray, np.ndarray]
            кортеж из координат X, Y и соответствующего им значения гиперпикселя (x, y, hyperpixel)
        n_neighbours: int
            количество соседних гиперпикселей, по которым будет усредняться значение текущего
            при значении 1 - будет браться значение ближайшего пикселя
        target_resolution_x: int
            целевое разрешение ГСИ по оси X
        distance_limit: float
            параметр удаления гиперпикселов после интерполяции.
            показывает максимально возможную удаленность гиперпикселя на регулярной сетке
            от гиперпикселя с реальными координатами

        Returns:
        --------
        np.ndarray
    """
    _, _, k = cube.shape
    x, y, hyperpixels = coordinates_and_hyperpixel
    model = _knn_for_interpolate(x,
                                 y,
                                 hyperpixels,
                                 n_neighbours=n_neighbours)
    test, n_target, m_target = _generate_test_points(x,
                                                     y,
                                                     target_resolution_x=target_resolution_x)
    prediction = model.predict(test)
    nearest_dit, _ = model.kneighbors(test,
                                      n_neighbors=1,
                                      return_distance=True)

    # check if the nearest distance is greater than the limit
    prediction[nearest_dit[:, 0] > distance_limit, :] = np.zeros(k)

    prediction = prediction.reshape(m_target, n_target, k)[:, ::-1, :]

    return prediction


# --------------------------------------------------------------------------------------------------


def _calculate_corrected_rel_alt(rel_alt: List[float],
                                 camera_pitch: float) -> List[float]:
    """
    _calculate_corrected_rel_alt(rel_alt, camera_pitch)

        Рассчёт относительной высоты с учетом угла установки камеры на БАС

        Parameters:
        ------------
        rel_alt: List[float]
            список значений высоты
        camera_pitch: float
            угол установки камеры на БАС

        Returns:
        -----------
        List[float]
    """
    cos_pitch = math.cos(math.radians(camera_pitch))
    return [alt / cos_pitch for alt in rel_alt]


# --------------------------------------------------------------------------------------------------


def _calculate_corrected_lat_lon(lat_lon: Tuple[List[float], List[float]],
                                 rel_alt: List[float],
                                 angle: List[float],
                                 camera_pitch: float) -> Tuple[List[float], List[float]]:
    """
    calculate_lat_lon(latitude, longitude, rel_alt, angle, camera_pitch)

        Рассчёт угловых координат с учетом высоты и угла установки камеры на БАС

        Parameters:
        ----------
        lat_lon: Tuple[List[float], List[float]]
            Кортеж списков значений широты и долготы
        rel_alt: List[float]
            список значений высоты
        angle: List[float]
            список значений угла рысканья относительно направления на север
        camera_pitch: float
            угол установки камеры на БАС

        Returns:
        --------
        Tuple[List[float], List[float]]
    """
    tan_pitch = math.tan(math.radians(camera_pitch))

    latitude, longitude = lat_lon

    latitude = [lat + alt * tan_pitch * math.cos(ang)
                for lat, alt, ang
                in zip(latitude, rel_alt, angle)]
    longitude = [lon + alt * tan_pitch * math.sin(ang)
                 for lon, alt, ang
                 in zip(longitude, rel_alt, angle)]

    return latitude, longitude


# --------------------------------------------------------------------------------------------------


def _coordinates_and_hyperpixels(cube: np.ndarray,
                                 lat_lon: Tuple[List[float], List[float]],
                                 rel_alt: List[float],
                                 angle: List[float],
                                 camera_tangent: float) \
        -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    coordinates_for_frame(cube, lat_lon, rel_alt, angle, camera_tangent)

        Рассчет координат X,Y для каждого гиперпикселя ГСИ.
        Возвращает кортеж из координат и соответствующих им гиперпикселей

        Parameters:
        -----------
        cube: np.ndarray
            ГСИ без геокоррекции
        lat_lon: Tuple[List[float], List[float]]
            Кортеж списков значений широты и долготы
        rel_alt: list
            список значений высоты
        angle: list
            список значений угла рысканья относительно направления на север
        camera_tangent: float
            тангенс угла обзора камеры

        Returns:
        --------
        Tuple[np.ndarray, np.ndarray, np.ndarray]
    """
    n, m, k = cube.shape

    distance = np.array(rel_alt) * camera_tangent / 2.0

    latitude, longitude = lat_lon

    x = np.linspace(np.array(latitude) + distance * np.cos(np.array(angle) + math.pi / 2.0),
                    np.array(latitude) + distance * np.cos(np.array(angle) - math.pi / 2.0),
                    m).T.reshape((n * m))
    y = np.linspace(np.array(longitude) + distance * np.sin(np.array(angle) + math.pi / 2.0),
                    np.array(longitude) + distance * np.sin(np.array(angle) - math.pi / 2.0),
                    m).T.reshape((n * m))

    hyperpixels = cube.reshape((n * m, k))

    return x, y, hyperpixels


# --------------------------------------------------------------------------------------------------


def _knn_for_interpolate(x: np.ndarray,
                         y: np.ndarray,
                         hyperpixels: np.ndarray,
                         n_neighbours: int = 1) -> neighbors.KNeighborsRegressor:
    """
    knn_for_interpolate(x, y, hyperpixels, n_neighbours=1)

        Возвращает обученную модель KNN-Regressor

        Parameters:
        -----------
            x: np.ndarray
                массив значений координаты X
            y: np.ndarray
                массив значений координаты Y
            hyperpixels: np.ndarray
                массив гиперпикселей
            n_neighbours: int
                количество соседних гиперпикселей, по которым будет усредняться значение текущего
                при значении 1 - будет браться значение ближайшего пикселя
        Returns:
        ----------
        neighbors.KNeighborsRegressor
    """
    model = neighbors.KNeighborsRegressor(n_neighbors=n_neighbours, n_jobs=-1)
    data = np.stack((np.array(x), np.array(y))).T
    model.fit(data, hyperpixels)
    return model


# --------------------------------------------------------------------------------------------------


def _generate_test_points(x: np.ndarray,
                          y: np.ndarray,
                          target_resolution_x: int = 1080) -> Tuple[List, int, int]:
    """
    generate_test_points(x, y, target_resolution_x=1080)

        Генерация тестовых точек регулярной координатной сетки с учетом целевого разрешения.
        Возвращает список координат и итоговые значения размерности ГСИ.

        Parameters:
        -----------
        x: np.ndarray
            массив значений координаты X
        y: np.ndarray
            массив значений координаты Y
        target_resolution_x: int
            целевое разрешение ГСИ по оси X
        Returns:
        --------
        Tuple[List, int, int]
    """
    x_min, x_max = np.min(x), np.max(x)
    y_min, y_max = np.min(y), np.max(y)

    n_target = target_resolution_x
    m_target = int(n_target * (y_max - y_min) / (x_max - x_min))
    x_linspace = np.linspace(x_min, x_max, n_target)
    y_linspace = np.linspace(y_min, y_max, m_target)
    test_points = list(itertools.product(x_linspace, y_linspace))

    return test_points, m_target, n_target


# --------------------------------------------------------------------------------------------------
def _create_guided_image(
        input_image: np.ndarray,
        low_pass_filter_size: int = 31,
        filter_mode: Literal["median", "gaussian", "box"] = "box",
) -> np.ndarray:
    """
    Function to create a guided image for artifact suppression (horizontal case only).

    :param input_image: Input image as a numpy array.
    :param low_pass_filter_size: Low pass filter window size.
    :param filter_mode: Filter mode to use ("median", "gaussian", "box").
    :return: Guided image.

    Usage example:
    ```
    input_image = np.random.rand(100, 100)
    guided_image = create_guided_image(input_image, 0.1, filter_mode="gaussian")
    ```
    """
    try:
        derivative = np.diff(input_image, axis=0)

        if filter_mode == "median":
            filtered_derivative = np.expand_dims(
                np.median(derivative, axis=1), axis=1
            )
            filtered_derivative = np.repeat(
                filtered_derivative, input_image.shape[1], axis=1
            )

        elif filter_mode == "gaussian":
            sigma = 0
            kernel = cv2.getGaussianKernel(
                low_pass_filter_size, sigma
            ).reshape(1, low_pass_filter_size)
            filtered_derivative = cv2.filter2D(
                derivative, -1, kernel, borderType=cv2.BORDER_REFLECT
            )
        elif filter_mode == "box":
            kernel = np.full(
                (1, low_pass_filter_size), 1.0 / low_pass_filter_size
            )
            filtered_derivative = cv2.filter2D(
                derivative, -1, kernel, borderType=cv2.BORDER_REFLECT
            )
        else:
            raise ValueError(
                "Invalid filter mode. Choose 'median', 'gaussian', or 'box'."
            )

        integrated_image = np.cumsum(filtered_derivative, axis=0)
        guided_image = input_image - np.vstack(
            (np.zeros((1, integrated_image.shape[1])), integrated_image)
        )

        return guided_image
    except Exception as e:
        warnings.warn(
            f"Error: An exception occurred during guided image creation - {e}"
        )


# --------------------------------------------------------------------------------------------------


def _guided_image_filtering(
        A: np.ndarray,
        G: np.ndarray,
        filt_size: tuple[int, int],
        inversion_epsilon: float,
) -> np.ndarray:
    """
    Function to perform guided image filtering.

    :param A: Input image as a floating point numpy array [0, 1], [h,w].
    :param G: Input image as a floating point numpy array [0, 1], [h,w].
    :param filt_size: Tuple of 2 elements defining the filter size (h, w).
    :param inversion_epsilon: Inversion parameter.
    :return: Filtered image.

    Usage example:
    ```
    A = np.random.rand(100, 100)
    G = np.random.rand(100, 100)
    filtered_image = guided_image_filtering(A, G, (5, 5), 0.1)
    ```
    """
    try:
        size_a = A.shape
        size_g = G.shape

        if size_a != size_g:
            raise ValueError(
                "Input images A and G must have the same dimensions"
            )

        original_class_a = A.dtype
        A = A.astype(np.double)
        G = G.astype(np.double)

        B = np.zeros(A.shape, dtype=A.dtype)

        I = G

        mean_i = cv2.boxFilter(I, -1, filt_size)
        mean_p = cv2.boxFilter(A, -1, filt_size)
        corr_i = cv2.boxFilter(I * I, -1, filt_size)
        corr_ip = cv2.boxFilter(I * A, -1, filt_size)

        var_i = corr_i - mean_i * mean_i
        cov_ip = corr_ip - mean_i * mean_p

        a = cov_ip / (var_i + inversion_epsilon)
        b = mean_p - a * mean_i

        mean_a = cv2.boxFilter(a, -1, filt_size)
        mean_b = cv2.boxFilter(b, -1, filt_size)

        B = mean_a * I + mean_b

        return B
    except Exception as e:
        warnings.warn(
            f"Error: An exception occurred during guided image filtering - {e}"
        )


# ----------- Integration IPPI builder--------------------------------------------------------------


class Point(NamedTuple):
    x: float
    y: float

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, coef: float) -> Point:
        return Point(self.x * coef, self.y * coef)

    def __truediv__(self, coef: float) -> Point:
        return Point(self.x / coef, self.y / coef)

    def inv_y(self, val: float) -> Point:
        return Point(self.x, val - self.y)


class Line(NamedTuple):
    pt1: Point
    pt2: Point

    def mid(self, other: Line) -> Line:
        return Line(
            (self.pt1 + other.pt1) * 0.5,
            (self.pt2 + other.pt2) * 0.5,
        )


class UTMCoordinate(NamedTuple):
    easting: float
    northing: float
    zone_number: int
    zone_letter: str

    @classmethod
    def from_latlon(cls, latitude: float, longitude: float):
        easting, northing, zone_number, zone_letter = from_latlon(
            latitude=latitude, longitude=longitude
        )
        return cls(easting, northing, zone_number, zone_letter)


class ReferencePoint(NamedTuple):
    coordinate: UTMCoordinate
    local: Point
    row: pd.DataFrame


class GeoInfo(NamedTuple):
    top_left_coordinate: UTMCoordinate
    resolution_px_per_m: float


def gps_to_lines(
        rows: pd.DataFrame, pitch_rad: float = 0.0, gamma: float = 0.3
) -> tuple[list[Line], ReferencePoint]:
    xs_raw = np.asarray([row.x for row in rows.itertuples()], dtype=np.float64)
    ys_raw = np.asarray([row.y for row in rows.itertuples()], dtype=np.float64)
    xs_raw -= xs_raw[0]
    ys_raw -= ys_raw[0]
    xs = gaussian_filter1d(xs_raw, 3.0, mode="nearest")
    ys = gaussian_filter1d(ys_raw, 3.0, mode="nearest")

    lines: list[Line] = []
    for row, x, y in zip(rows.itertuples(), xs, ys):
        OC = row.rel_alt
        OP = OC / math.cos(pitch_rad)
        CP = OC * math.tan(pitch_rad)
        B = row.compass_hdg
        sin_b = math.sin(B)
        cos_b = math.cos(B)
        eastingP = float(x) + CP * sin_b
        northingP = float(y) + CP * cos_b
        distance = OP * math.tan(gamma / 2)

        e1 = eastingP + distance * math.cos(B + math.pi / 2)
        n1 = northingP + distance * math.sin(B + math.pi / 2)

        e2 = eastingP + distance * math.cos(B - math.pi / 2)
        n2 = northingP + distance * math.sin(B - math.pi / 2)
        lines.append(Line(Point(e1, n1), Point(e2, n2)))

    # expecting good coordinates in the middle of the flight
    ref_row_idx = len(rows) * 25 // 30
    ref_row = rows.iloc[ref_row_idx]
    reference_point = ReferencePoint(
        coordinate=UTMCoordinate.from_latlon(
            ref_row.latitude,
            ref_row.longitude,
        ),
        local=Point(float(xs[ref_row_idx]), float(ys[ref_row_idx])),
        row=ref_row,
    )

    return lines, reference_point


WidthPx = NewType("WidthPx", int)
HeightPx = NewType("HeightPx", int)


def lines_to_canvas(
        lines: list[Line], ref_point: ReferencePoint, resolution_cm: float = 2.0
) -> tuple[WidthPx, HeightPx, list[Line], GeoInfo]:
    pt1s, pt2s = zip(*lines)
    e1s, n1s = zip(*pt1s)
    e2s, n2s = zip(*pt2s)

    resolution_px_per_m = 100.0 / resolution_cm
    min_pt = Point(min(*e1s, *e2s), min(*n1s, *n2s))
    width_m = max(*e1s, *e2s) - min_pt.x
    height_m = max(*n1s, *n2s) - min_pt.y

    width_px = WidthPx(math.ceil(width_m * resolution_px_per_m))
    height_px = HeightPx(math.ceil(height_m * resolution_px_per_m))

    lines_px = [
        Line(
            ((line.pt1 - min_pt).inv_y(height_m)) * resolution_px_per_m,
            ((line.pt2 - min_pt).inv_y(height_m)) * resolution_px_per_m,
        )
        for line in lines
    ]
    x0_m = min_pt.x - ref_point.local.x
    y0_m = min_pt.y + height_m - ref_point.local.y

    geo_info = GeoInfo(
        top_left_coordinate=UTMCoordinate(
            easting=ref_point.coordinate.easting + x0_m,
            northing=ref_point.coordinate.northing + y0_m,
            zone_number=ref_point.coordinate.zone_number,
            zone_letter=ref_point.coordinate.zone_letter,
        ),
        resolution_px_per_m=resolution_px_per_m,
    )
    return width_px, height_px, lines_px, geo_info


def _scale_down_by_a_factor(arr: np.ndarray, factor: int = 2) -> np.ndarray:
    h, w, c = arr.shape
    assert h % factor == 0, (h, factor)
    assert w % factor == 0, (w, factor)
    return arr.reshape((h // factor, factor, w // factor, factor, c)).mean(
        axis=(1, 3)
    )


DPoint = [("x", "<f4"), ("y", "<f4")]  # DGroovy
DColor = [("r", "<u1"), ("g", "<u1"), ("b", "<u1")]
DLine = [("pt0", DPoint), ("pt1", DPoint)]


class HSIRasterizer:
    def __init__(
            self,
            gps: pd.DataFrame,
            resolution_cm: int = 4,
            supersampling: bool = False,
            channels: int = 0,
            wavelengths: list[int] | None = None,
    ) -> None:

        self._supersampling = supersampling
        self._wavelengths = wavelengths
        if supersampling:
            self._factor = 2.0
        else:
            self._factor = 1.0
        lines, pt = gps_to_lines(gps)
        width_px, height_px, self._lines_px, self._geo_info = lines_to_canvas(
            lines, pt, resolution_cm=resolution_cm / self._factor
        )
        if width_px % 2:
            width_px += 1
        if height_px % 2:
            height_px += 1
        self._sum_img = np.zeros(
            (height_px, width_px, channels), dtype=np.float32
        )
        self._count_img = np.zeros((height_px, width_px), dtype=np.uint8)

    def draw_image(self, data: np.ndarray) -> None:
        data = np.ascontiguousarray(data)

        lines_px = self._lines_px

        lines_np = np.asarray(lines_px, dtype=DLine)
        triangle_fill(lines_np, data, self._sum_img, self._count_img)

    def render(self) -> np.ndarray:

        mask = self._count_img != 0
        out = np.zeros_like(self._sum_img, dtype=np.uint8)
        out[mask] = self._sum_img[mask] / self._count_img[mask, np.newaxis]

        if self._supersampling:
            data = _scale_down_by_a_factor(out).astype(np.uint8)
        else:
            data = out.astype(np.uint8)

        return data


def build_hypercube_with_gps_triangle(
        cube: np.ndarray,
        telemetry: GPSReader,
        uav_bp: BuildUAVParams,
) -> list[np.ndarray] | np.ndarray:
    """
        build_hypercube_with_gps(cube, telemetry, uav_bp)

            Производит геокоррекцию ГСИ по данным GPS

            Parameters
            ----------
            cube: np.ndarray
                ГСИ без геокоррекции
            telemetry: GPSReader
                GPS данные в формате GPSReader для доступа до DataFrame с данными gps
            uav_bp: BuildUAVConstants
                Параметры ГСА, установленной на БАС:
                camera_pitch: float
                camera_tangent: float
                blur_auto: bool
                target_resolution: int
                distance_limit: float
                blur_shape: Tuple[int, int]
                n_neighbours: int
            Returns
            --------
            np.ndarray
        """

    hsi_visualizer = HSIRasterizer(
        gps=telemetry.gps,
        resolution_cm=uav_bp.resolution_cm,
        supersampling=uav_bp.build_algorithm_params.super_sampling,
        channels=cube.shape[2],
    )
    hsi_visualizer.draw_image(cube)
    return hsi_visualizer.render()  # Возвращаем общий холст
