# -*- coding: utf-8 -*-
##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008 OpenLP Developers                                   #
# ---------------------------------------------------------------------- #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <https://www.gnu.org/licenses/>. #
##########################################################################
"""
Utilities for extracting and caching a static preview frame from a video file.
"""
import logging
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QTransform
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink, QtVideo

from openlp.core.common.applocation import AppLocation
from openlp.core.common.utils import wait_for

log = logging.getLogger(__name__)

PREVIEW_FRAME_OFFSET_MS = 1000
PREVIEW_FRAME_FILENAME = 'preview_frame.png'


def extract_video_frame(video_path: Path, offset_ms: int = PREVIEW_FRAME_OFFSET_MS):
    """
    Extract a single frame from *video_path* at *offset_ms* milliseconds.

    Uses QMediaPlayer + QVideoSink (no visible widget).  Spins the Qt event
    loop via wait_for() until a valid frame arrives or the 5-second timeout
    expires.

    :param video_path: Path to the video file.
    :param offset_ms: Millisecond offset at which to capture the frame.
    :return: QImage on success, None on failure.
    """
    player = QMediaPlayer()
    sink = QVideoSink()
    player.setVideoSink(sink)

    captured = [None]

    def _on_frame(video_frame):
        if captured[0] is None and video_frame.isValid():
            image = video_frame.toImage().convertToFormat(QImage.Format.Format_ARGB32)
            rotation = video_frame.rotation()
            if rotation == QtVideo.Rotation.Clockwise90:
                image = image.transformed(QTransform().rotate(90))
            elif rotation == QtVideo.Rotation.Clockwise180:
                image = image.transformed(QTransform().rotate(180))
            elif rotation == QtVideo.Rotation.Clockwise270:
                image = image.transformed(QTransform().rotate(270))
            captured[0] = image

    def _on_status(status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            player.setPosition(offset_ms)
            player.play()

    sink.videoFrameChanged.connect(_on_frame)
    player.mediaStatusChanged.connect(_on_status)
    player.setSource(QUrl.fromLocalFile(str(video_path)))

    success = wait_for(lambda: captured[0] is not None, timeout=5)
    player.stop()

    if not success:
        log.warning('extract_video_frame timed out for %s', video_path)
        return None
    return captured[0]


def _frame_path(theme) -> Path:
    return AppLocation.get_section_data_path('themes') / theme.theme_name / PREVIEW_FRAME_FILENAME


def get_video_preview_frame(theme) -> Path | None:
    """
    Return the path to the cached preview frame PNG for *theme*, extracting it
    if it does not exist yet (lazy fallback for pre-existing themes).

    :return: Path to the PNG, or None if extraction failed.
    """
    path = _frame_path(theme)
    if path.exists():
        return path
    return _extract_and_save(theme, path)


def get_cached_video_preview_frame(theme) -> Path | None:
    """
    Return the cached preview frame path only if it already exists on disk.
    Never triggers extraction — safe to call on the main/UI thread.

    :return: Path to the PNG, or None if not yet cached.
    """
    path = _frame_path(theme)
    return path if path.exists() else None


def cache_video_preview_frame(theme) -> Path | None:
    """
    (Re-)extract and save the preview frame for *theme*, overwriting any
    previously cached file.  Call this at theme-save time so the frame is
    always in sync with the video file.

    :return: Path to the PNG, or None if extraction failed.
    """
    return _extract_and_save(theme, _frame_path(theme))


_MAX_PREVIEW_WIDTH = 854   # 480p-wide — fast to base64-encode and load in WebEngine


def _extract_and_save(theme, path: Path) -> Path | None:
    if not theme.background_filename or not Path(theme.background_filename).exists():
        log.warning('Video background file missing for theme "%s"', theme.theme_name)
        return None
    image = extract_video_frame(Path(theme.background_filename))
    if image is None:
        return None
    if image.width() > _MAX_PREVIEW_WIDTH:
        image = image.scaled(
            _MAX_PREVIEW_WIDTH, _MAX_PREVIEW_WIDTH,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(path)):
        log.warning('Failed to save preview frame for theme "%s"', theme.theme_name)
        return None
    return path
