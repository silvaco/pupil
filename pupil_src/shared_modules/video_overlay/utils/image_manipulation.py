"""
(*)~---------------------------------------------------------------------------
Pupil - eye tracking platform
Copyright (C) 2012-2020 Pupil Labs

Distributed under the terms of the GNU
Lesser General Public License (LGPL v3.0).
See COPYING and COPYING.LESSER for license details.
---------------------------------------------------------------------------~(*)
"""

import abc

import cv2
import numpy as np


class ImageManipulator(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def apply_to(self, image, parameter, **kwargs):
        raise NotImplementedError


class ScaleTransform(ImageManipulator):
    def apply_to(self, image, parameter, **kwargs):
        """parameter: scale factor as float"""
        return cv2.resize(image, (0, 0), fx=parameter, fy=parameter)


class HorizontalFlip(ImageManipulator):
    def apply_to(self, image, parameter, *, is_fake_frame, **kwargs):
        """parameter: boolean indicating if image should be flipped"""
        if parameter and not is_fake_frame:
            return np.fliplr(image)
        else:
            return image


class VerticalFlip(ImageManipulator):
    def apply_to(self, image, parameter, *, is_fake_frame, **kwargs):
        """parameter: boolean indicating if image should be flipped"""
        if parameter and not is_fake_frame:
            return np.flipud(image)
        else:
            return image


class PupilRenderer(ImageManipulator):
    __slots__ = "pupil_getter"

    def __init__(self, pupil_getter):
        self.pupil_getter = pupil_getter

    def apply_to(self, image, parameter, *, is_fake_frame, **kwargs):
        """parameter: boolean indicating if pupil should be rendered"""
        if parameter and not is_fake_frame:
            pupil_pos_2d, pupil_pos_3d = self.pupil_getter()
            if pupil_pos_2d:
                self.render_pupil_2d(image, pupil_pos_2d)
            if pupil_pos_3d:
                self.render_pupil_3d(image, pupil_pos_3d)
        return image

    def render_pupil_2d(self, image, pupil_position):
        el = pupil_position["ellipse"]

        conf = int(pupil_position["confidence"] * 255)
        self.render_ellipse(image, el, color=(255, 127, 0, conf))

    def render_pupil_3d(self, image, pupil_position):
        el = pupil_position["ellipse"]

        conf = int(pupil_position["confidence"] * 255)
        self.render_ellipse(image, el, color=(0, 0, 255, conf))

        eye_ball = pupil_position.get("projected_sphere", None)
        if eye_ball is not None:
            try:
                cv2.ellipse(
                    image,
                    center=tuple(int(v) for v in eye_ball["center"]),
                    axes=tuple(int(v / 2) for v in eye_ball["axes"]),
                    angle=int(eye_ball["angle"]),
                    startAngle=0,
                    endAngle=360,
                    color=(26, 230, 0, 255 * pupil_position["model_confidence"]),
                    thickness=2,
                )
            except ValueError:
                # Happens when converting 'nan' to int
                # TODO: Investigate why results are sometimes 'nan'
                pass

    def render_ellipse(self, image, ellipse, color):
        outline = self.get_ellipse_points(
            ellipse["center"], ellipse["axes"], ellipse["angle"]
        )
        outline = [np.asarray(outline, dtype="i")]
        cv2.polylines(image, outline, True, color, thickness=1)

        center = (int(ellipse["center"][0]), int(ellipse["center"][1]))
        cv2.circle(image, center, 5, color, thickness=-1)

    @staticmethod
    def get_ellipse_points(center, axes, angle, num_pts=10):
        c1 = center[0]
        c2 = center[1]
        a = axes[0]
        b = axes[1]

        steps = np.linspace(0, 2 * np.pi, num=num_pts, endpoint=False)
        rot = cv2.getRotationMatrix2D((0, 0), -angle, 1)

        pts1 = a / 2.0 * np.cos(steps)
        pts2 = b / 2.0 * np.sin(steps)
        pts = np.column_stack((pts1, pts2, np.ones(pts1.shape[0])))

        pts_rot = np.matmul(rot, pts.T)
        pts_rot = pts_rot.T

        pts_rot[:, 0] += c1
        pts_rot[:, 1] += c2

        return pts_rot
