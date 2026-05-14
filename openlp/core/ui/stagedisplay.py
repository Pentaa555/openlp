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
Native stage display for the presenter monitor.

StageDisplayWindow is a pure-Qt widget — no WebEngine, no Reveal.js.
It reads slide text directly from the live controller and auto-sizes the
current-slide text to fill the available area.

Layout (black background):
  ┌───────────────────────────────────────────────────────┐
  │  Text size: [━━━━●━━━]                    14:10:35    │  ← header
  ├───────────────────────────────────────────────────────┤
  │                                                       │
  │            C U R R E N T   L Y R I C S               │  ← auto-sized
  │                                                       │
  ├───────────────────────────────────────────────────────┤
  │  NEXT ▸  next slide text …                            │  ← footer
  └───────────────────────────────────────────────────────┘

LivePreviewWindow (single-monitor simulation) is still a DisplayWindow
subclass with Qt::Window flags — it renders the full themed audience view.
"""
import datetime
import logging
import re

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.display.window import DisplayWindow

log = logging.getLogger(__name__)

# Geometry for single-monitor simulation mode
_SIM_W = 700
_SIM_H = 394       # 16:9 at 700 px wide

_STRIP_HTML = re.compile(r'<[^>]+>', re.IGNORECASE)
_MULTI_NL = re.compile(r'\n{3,}')


def _plain(html_text: str) -> str:
    """Convert OpenLP slide HTML to plain text, preserving line structure."""
    text = html_text or ''
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?p[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = _STRIP_HTML.sub('', text)
    text = (text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                .replace('&nbsp;', ' ').replace('&#160;', ' '))
    text = _MULTI_NL.sub('\n\n', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Audience simulation window (single-monitor test mode)
# ---------------------------------------------------------------------------

class LivePreviewWindow(DisplayWindow):
    """
    Simulates the audience-facing screen as a normal window.
    Receives the same content as the live display via stage_displays.
    Used only by the single-monitor test / simulation mode.
    """

    def __init__(self):
        super().__init__(
            parent=None,
            can_show_startup_screen=False,
            after_loaded_callback=self._on_display_ready,
        )
        # DisplayWindow forces Tool | FramelessWindowHint | WindowStaysOnTopHint.
        # Override immediately (before show()) so this behaves as a normal window.
        self.setWindowFlags(QtCore.Qt.WindowType.Window)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle(translate('OpenLP.StageDisplay', 'Audience View  [simulation]'))

    def _on_display_ready(self):
        try:
            Registry().get('live_controller').add_stage_display(self)
        except Exception:
            self.log_exception('LivePreviewWindow: failed to register with live controller')

    def show_at(self, rect: QtCore.QRect):
        self.setGeometry(rect)
        self.show()
        self.raise_()
        if self._is_initialised:
            self._on_display_ready()

    def closeEvent(self, event):
        try:
            Registry().get('live_controller').remove_stage_display(self)
        except Exception:
            pass
        event.accept()


# ---------------------------------------------------------------------------
# Stage display window — pure Qt, no WebEngine
# ---------------------------------------------------------------------------

class StageDisplayWindow(QtWidgets.QWidget):
    """
    Presenter monitor window.

    Reads slide text from the live controller and displays it with
    auto-sized font (largest that fits).  A slider lets the operator
    scale the text down from the auto-fit maximum.

    Because there is no WebEngine involved, _is_initialised always
    returns True and registration with the live controller is immediate.
    """

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(QtCore.Qt.WindowType.Window)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle(translate('OpenLP.StageDisplay', 'Stage Display'))
        self.setStyleSheet('background-color: #000000;')
        self._connected = False
        self._current_text = ''
        self._text_mode = 'auto'
        self._text_size = 48
        self._clock_px = 20
        self._next_h = 50

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 0, 16, 6)  # No top margin (header removed)
        root.setSpacing(4)

        # --- Current slide text -------------------------------------------
        self._current_label = QtWidgets.QLabel()
        self._current_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._current_label.setWordWrap(True)
        self._current_label.setStyleSheet('color: #ffffff;')
        root.addWidget(self._current_label, 1)

        # --- Separator -------------------------------------------------------
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet('background-color: #333333; max-height: 1px;')
        root.addWidget(sep)

        # --- Footer: next slides (1-3) + clock at bottom-right ---------------
        self._footer = QtWidgets.QWidget()
        self._footer.setFixedHeight(self._next_h)
        ftr = QtWidgets.QVBoxLayout(self._footer)
        ftr.setContentsMargins(0, 4, 0, 0)
        ftr.setSpacing(0)

        # Next slide text display (will show 1-3 slides)
        self._next_label = QtWidgets.QLabel()
        self._next_label.setStyleSheet('color: #888888; font-size: 13px;')
        self._next_label.setWordWrap(True)
        self._next_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        ftr.addWidget(self._next_label, 1)

        # Clock label - positioned at bottom-right
        self._clock_label = QtWidgets.QLabel()
        self._clock_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignBottom)
        self._clock_label.setStyleSheet('color: #FFFF00; font-size: 20px; font-weight: bold;')
        ftr.addWidget(self._clock_label, 0)

        root.addWidget(self._footer)

        # --- Clock timer -----------------------------------------------------
        self._clock_timer = QtCore.QTimer(self)
        self._clock_timer.timeout.connect(self._tick)
        self._clock_timer.start(1000)
        self._tick()

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------

    def _tick(self):
        self._clock_label.setText(datetime.datetime.now().strftime('%H:%M:%S'))

    # ------------------------------------------------------------------
    # Auto-sizing font
    # ------------------------------------------------------------------

    def _fit_font(self, text: str, rect: QtCore.QRect) -> QtGui.QFont:
        """Return the largest QFont (pixel size) that fits text in rect."""
        if not text or rect.width() <= 0 or rect.height() <= 0:
            return QtGui.QFont()
        font = QtGui.QFont()
        font.setBold(True)
        if self._text_mode == 'fixed':
            font.setPixelSize(max(12, self._text_size))
            return font
        max_px = max(14, int(min(rect.height(), rect.width() // 2)))
        flags = int(QtCore.Qt.TextFlag.TextWordWrap) | int(QtCore.Qt.AlignmentFlag.AlignCenter)
        for px in range(max_px, 14, -2):
            font.setPixelSize(px)
            br = QtGui.QFontMetrics(font).boundingRect(rect, flags, text)
            if br.height() <= rect.height():
                return font
        font.setPixelSize(14)
        return font

    def _apply_font(self):
        if not self._current_text:
            return
        rect = self._current_label.contentsRect()
        self._current_label.setFont(self._fit_font(self._current_text, rect))

    def _apply_settings(self, *_args):
        """Read stage display settings and update widget geometry / styles."""
        try:
            s = Registry().get('settings')
            self._text_mode = s.value('core/stage text mode')
            self._text_size = s.value('core/stage text size')
            self._clock_px = s.value('core/stage clock size')
            self._next_h = s.value('core/stage next height')
        except Exception:
            pass
        self._clock_label.setStyleSheet(
            f'color: #ffffff; font-size: {self._clock_px}px; font-weight: bold;'
        )
        self._header.setFixedHeight(max(20, self._clock_px + 8))
        self._footer.setFixedHeight(self._next_h)
        self._apply_font()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QtCore.QTimer.singleShot(0, self._apply_font)

    # ------------------------------------------------------------------
    # Content methods (called by SlideController)
    # ------------------------------------------------------------------

    @property
    def _is_initialised(self):
        return True   # no webview — always ready

    def set_theme(self, *args, **kwargs):
        pass

    def load_verses(self, slides):
        pass

    def load_images(self, slides):
        pass

    def show_display(self):
        pass

    def finish_with_current_item(self):
        self._current_text = ''
        self._current_label.clear()
        self._next_label.clear()

    def reload_theme(self):
        pass

    def set_background_image(self, path):
        pass

    def go_to_slide(self, row):
        self._refresh_content(row)

    # ------------------------------------------------------------------
    # Content refresh
    # ------------------------------------------------------------------

    def _refresh_content(self, row=None, *_args):
        """Read current + next slide text from the live controller and display it."""
        try:
            live = Registry().get('live_controller')
            item = live.service_item
            if not item or not item.is_text():
                self._current_text = ''
                self._current_label.clear()
                self._next_label.clear()
                return

            if row is None:
                row = live.selected_row

            slides = item.display_slides
            # Current slide
            if 0 <= row < len(slides):
                self._current_text = _plain(slides[row].get('text', ''))
            else:
                self._current_text = ''
            # Next slide
            next_row = row + 1
            if next_row < len(slides):
                self._next_label.setText(_plain(slides[next_row].get('text', '')))
            else:
                self._next_label.clear()

            self._current_label.setText(self._current_text)
            self._apply_font()
        except Exception:
            log.exception('StageDisplayWindow: error refreshing content')

    # ------------------------------------------------------------------
    # Show
    # ------------------------------------------------------------------

    def show_stage(self):
        settings = Registry().get('settings')
        screen_number = settings.value('core/stage screen')
        screens = QtWidgets.QApplication.screens()
        saved = settings.value('core/stage geometry')

        if saved:
            self.restoreGeometry(saved)
            # If a specific screen is configured, move there only when not already on it
            if isinstance(screen_number, int) and 0 <= screen_number < len(screens):
                target = screens[screen_number].availableGeometry()
                if not target.contains(self.geometry().center()):
                    self.move(target.topLeft())
        elif isinstance(screen_number, int) and 0 <= screen_number < len(screens):
            target = screens[screen_number].availableGeometry()
            self.resize(_SIM_W, _SIM_H)
            self.move(target.center() - self.rect().center())
        else:
            avail = QtWidgets.QApplication.primaryScreen().availableGeometry()
            self.resize(_SIM_W, _SIM_H)
            self.move(avail.center() - self.rect().center())

        self._apply_settings()
        self.show()
        self.raise_()
        self._register_with_live_controller()

    # ------------------------------------------------------------------
    # Live controller registration
    # ------------------------------------------------------------------

    def _register_with_live_controller(self):
        try:
            live = Registry().get('live_controller')
            live.add_stage_display(self)
            if not self._connected:
                live.slidecontroller_changed.connect(self._on_slide_changed)
                Registry().register_function('config_screen_changed', self._apply_settings)
                self._connected = True
        except Exception:
            log.exception('StageDisplayWindow: failed to register with live controller')

    def _unregister_from_live_controller(self):
        try:
            live = Registry().get('live_controller')
            live.remove_stage_display(self)
            if self._connected:
                live.slidecontroller_changed.disconnect(self._on_slide_changed)
                self._connected = False
        except Exception:
            pass

    def _on_slide_changed(self, *_args):
        self._refresh_content()

    # ------------------------------------------------------------------
    # Window lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        try:
            Registry().get('settings').setValue('core/stage geometry', self.saveGeometry())
        except Exception:
            pass
        self._unregister_from_live_controller()
        event.accept()
