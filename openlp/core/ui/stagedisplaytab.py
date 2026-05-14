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
The stage display settings tab in the configuration dialog.
"""
from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.lib.settingstab import SettingsTab
from openlp.core.ui.icons import UiIcons

_PREVIEW_SAMPLE_CURRENT = 'Amazing grace\nhow sweet the sound\nthat saved a wretch like me'
_PREVIEW_SAMPLE_NEXT = 'I once was lost but now I see…'


class _StagePreviewWidget(QtWidgets.QWidget):
    """
    Paints a miniature replica of the Stage Display window so the user
    can see the effect of the text-mode / text-size / clock-size / next-height
    settings without opening the actual window.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text_mode = 'auto'
        self._text_size = 48
        self._clock_px = 20
        self._next_h = 50
        self._clock_color = '#FFFF00'
        self._next_count = 1
        self._next_display = 'first_line'
        self._preview_width = 480
        self._aspect_ratio = 16 / 9
        self._apply_aspect_ratio_from_primary_screen()

    def _apply_aspect_ratio_from_primary_screen(self):
        screen = QtWidgets.QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            if geom.height() > 0:
                self._aspect_ratio = geom.width() / geom.height()
        self._apply_fixed_size()

    def _apply_fixed_size(self):
        width = self._preview_width
        height = max(120, int(round(width / self._aspect_ratio)))
        self.setFixedSize(width, height)

    def set_screen_aspect_ratio(self, ratio: float):
        """Update preview aspect ratio (call when target screen selection changes)."""
        if ratio and ratio > 0:
            self._aspect_ratio = ratio
            self._apply_fixed_size()
            self.update()

    def set_values(self, text_mode: str, text_size: int, clock_px: int, next_h: int,
                   clock_color: str = '#FFFF00', next_count: int = 1, next_display: str = 'first_line'):
        self._text_mode = text_mode
        self._text_size = text_size
        self._clock_px = clock_px
        self._next_h = next_h
        self._clock_color = clock_color
        self._next_count = next_count
        self._next_display = next_display
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        REF_W, REF_H = 700, 394
        sx = w / REF_W
        sy = h / REF_H

        p.fillRect(0, 0, w, h, QtGui.QColor('#111111'))

        # Header removed — clock moved to footer
        header_h = 0

        # --- Footer (height calculation) -------------------------------------
        real_footer_h = self._next_h + 10
        footer_h = max(18, int(real_footer_h * sy))
        sep_y = h - footer_h - 1

        # --- Main text area --------------------------------------------------
        main_top = 6  # Small top margin, no header
        main_h = sep_y - main_top
        if main_h > 0:
            text = _PREVIEW_SAMPLE_CURRENT
            text_rect = QtCore.QRect(8, main_top, w - 16, main_h)
            font = QtGui.QFont()
            font.setBold(True)
            flags = int(QtCore.Qt.TextFlag.TextWordWrap) | int(QtCore.Qt.AlignmentFlag.AlignCenter)
            if self._text_mode == 'fixed':
                chosen_px = max(8, min(int(self._text_size * sy), main_h))
            else:
                max_px = max(8, int(min(main_h, (w - 16) // 2)))
                chosen_px = 8
                for px in range(max_px, 8, -1):
                    font.setPixelSize(px)
                    br = QtGui.QFontMetrics(font).boundingRect(text_rect, flags, text)
                    if br.height() <= main_h:
                        chosen_px = px
                        break
            font.setPixelSize(chosen_px)
            p.setFont(font)
            p.setPen(QtGui.QColor('#ffffff'))
            p.drawText(text_rect, flags, text)

        # --- Separator -------------------------------------------------------
        p.setPen(QtGui.QColor('#333333'))
        p.drawLine(0, sep_y, w, sep_y)

        # --- Footer: next slides (1-3) + clock at bottom-right ---------
        next_lbl_font = QtGui.QFont()
        next_lbl_font.setPixelSize(max(6, int(10 * sy)))
        next_lbl_font.setBold(True)

        next_txt_font = QtGui.QFont()
        next_txt_font.setPixelSize(max(6, int(13 * sy)))

        next_count = self._next_count
        y_pos = sep_y + 3

        for i in range(next_count):
            if i == 0:
                label = 'NEXT'
            else:
                label = f'NEXT+{i}'

            p.setFont(next_lbl_font)
            p.setPen(QtGui.QColor('#555555'))
            p.drawText(
                QtCore.QRect(4, y_pos, 50, 16),
                int(QtCore.Qt.AlignmentFlag.AlignLeft) | int(QtCore.Qt.AlignmentFlag.AlignVCenter),
                label,
            )

            p.setFont(next_txt_font)
            p.setPen(QtGui.QColor('#888888'))
            text = _PREVIEW_SAMPLE_NEXT
            if self._next_display == 'first_line':
                text = text.split('\n')[0]
                if len(text) > 60:
                    text = text[:57] + '…'

            p.drawText(
                QtCore.QRect(60, y_pos, w - 120, 16),
                int(QtCore.Qt.AlignmentFlag.AlignLeft) | int(QtCore.Qt.AlignmentFlag.AlignVCenter),
                text,
            )
            y_pos += 18

        # Draw clock at bottom-right
        clock_font = QtGui.QFont()
        clock_font.setPixelSize(max(8, int(self._clock_px * sy)))
        clock_font.setBold(True)
        p.setFont(clock_font)
        p.setPen(QtGui.QColor(self._clock_color))
        p.drawText(
            QtCore.QRect(0, sep_y, w - 6, footer_h),
            int(QtCore.Qt.AlignmentFlag.AlignRight) | int(QtCore.Qt.AlignmentFlag.AlignBottom),
            '14:10:35',
        )
        p.end()


class StageDisplayTab(SettingsTab):
    """
    StageDisplayTab is the stage display settings tab in the configuration dialog.

    Contains the screen selector for the stage display window plus all appearance
    options (text size, clock size/color, next slide count/display mode, footer height).
    """
    def __init__(self, parent):
        self.icon_path = UiIcons().desktop
        stage_translated = translate('OpenLP.StageDisplayTab', 'Stage Display')
        super().__init__(parent, 'Stage Display', stage_translated)
        self.settings_section = 'core'

    def setup_ui(self):
        self.setObjectName('self')
        self.tab_layout = QtWidgets.QVBoxLayout(self)
        self.tab_layout.setObjectName('tab_layout')

        self.stage_group_box = QtWidgets.QGroupBox(self)
        self.stage_group_box.setObjectName('stage_group_box')
        stage_layout = QtWidgets.QFormLayout(self.stage_group_box)

        # Hint label spans the full width (both columns)
        self._lbl_screens_hint = QtWidgets.QLabel(self.stage_group_box)
        self._lbl_screens_hint.setWordWrap(True)
        self._lbl_screens_hint.setStyleSheet('color: #777777; font-style: italic;')
        stage_layout.addRow(self._lbl_screens_hint)

        # Screen checkboxes row
        self._lbl_screens = QtWidgets.QLabel(self.stage_group_box)
        self.stage_screens_widget = QtWidgets.QWidget(self.stage_group_box)
        self.stage_screens_layout = QtWidgets.QVBoxLayout(self.stage_screens_widget)
        self.stage_screens_layout.setContentsMargins(0, 0, 0, 0)
        self.stage_screens_layout.setSpacing(4)
        self._stage_screen_checkboxes = []  # populated in _build_stage_screen_checkboxes()
        stage_layout.addRow(self._lbl_screens, self.stage_screens_widget)

        # Preview spans both columns (no label), centered horizontally
        self.stage_preview = _StagePreviewWidget(self.stage_group_box)
        preview_row = QtWidgets.QWidget(self.stage_group_box)
        preview_row_layout = QtWidgets.QHBoxLayout(preview_row)
        preview_row_layout.setContentsMargins(0, 0, 0, 0)
        preview_row_layout.addStretch()
        preview_row_layout.addWidget(self.stage_preview)
        preview_row_layout.addStretch()
        stage_layout.addRow(preview_row)

        # Text size: radio buttons + optional spinbox in one row
        self._lbl_text_mode = QtWidgets.QLabel(self.stage_group_box)
        text_mode_widget = QtWidgets.QWidget(self.stage_group_box)
        text_mode_layout = QtWidgets.QHBoxLayout(text_mode_widget)
        text_mode_layout.setContentsMargins(0, 0, 0, 0)
        text_mode_layout.setSpacing(8)
        self.stage_text_auto_radio = QtWidgets.QRadioButton(text_mode_widget)
        self.stage_text_fixed_radio = QtWidgets.QRadioButton(text_mode_widget)
        self.stage_text_size_spin = QtWidgets.QSpinBox(text_mode_widget)
        self.stage_text_size_spin.setRange(12, 500)
        self.stage_text_size_spin.setSuffix(' px')
        text_mode_layout.addWidget(self.stage_text_auto_radio)
        text_mode_layout.addWidget(self.stage_text_fixed_radio)
        text_mode_layout.addWidget(self.stage_text_size_spin)
        text_mode_layout.addStretch()
        stage_layout.addRow(self._lbl_text_mode, text_mode_widget)

        self._lbl_clock_size = QtWidgets.QLabel(self.stage_group_box)
        self.stage_clock_size_spin = QtWidgets.QSpinBox(self.stage_group_box)
        self.stage_clock_size_spin.setRange(12, 500)
        self.stage_clock_size_spin.setSuffix(' px')
        stage_layout.addRow(self._lbl_clock_size, self.stage_clock_size_spin)

        self._lbl_clock_color = QtWidgets.QLabel(self.stage_group_box)
        self.stage_clock_color_button = QtWidgets.QPushButton(self.stage_group_box)
        self.stage_clock_color_button.setObjectName('stage_clock_color_button')
        self.stage_clock_color_button.setFixedWidth(80)
        stage_layout.addRow(self._lbl_clock_color, self.stage_clock_color_button)

        self._lbl_next_count = QtWidgets.QLabel(self.stage_group_box)
        self.stage_next_count_combo = QtWidgets.QComboBox(self.stage_group_box)
        self.stage_next_count_combo.setObjectName('stage_next_count_combo')
        self.stage_next_count_combo.addItems(['1', '2', '3'])
        stage_layout.addRow(self._lbl_next_count, self.stage_next_count_combo)

        self._lbl_next_display = QtWidgets.QLabel(self.stage_group_box)
        self.stage_next_display_combo = QtWidgets.QComboBox(self.stage_group_box)
        self.stage_next_display_combo.setObjectName('stage_next_display_combo')
        self.stage_next_display_combo.addItems(['First line only', 'Full text'])
        stage_layout.addRow(self._lbl_next_display, self.stage_next_display_combo)

        self._lbl_next_height = QtWidgets.QLabel(self.stage_group_box)
        self.stage_next_height_spin = QtWidgets.QSpinBox(self.stage_group_box)
        self.stage_next_height_spin.setRange(30, 2000)
        self.stage_next_height_spin.setSuffix(' px')
        stage_layout.addRow(self._lbl_next_height, self.stage_next_height_spin)

        self.tab_layout.addWidget(self.stage_group_box)
        self.tab_layout.addStretch()

        self.stage_text_auto_radio.toggled.connect(self._on_text_mode_changed)
        self.stage_text_size_spin.valueChanged.connect(self._update_stage_preview)
        self.stage_clock_size_spin.valueChanged.connect(self._update_stage_preview)
        self.stage_next_height_spin.valueChanged.connect(self._update_stage_preview)
        self.stage_clock_color_button.clicked.connect(self._on_clock_color_clicked)
        self.stage_next_count_combo.currentTextChanged.connect(self._update_stage_preview)
        self.stage_next_display_combo.currentTextChanged.connect(self._update_stage_preview)

        Registry().register_function('config_screen_changed', self._on_screen_changed)

    def retranslate_ui(self):
        self.stage_group_box.setTitle(translate('OpenLP.StageDisplayTab', 'Stage Display'))
        self._lbl_screens.setText(translate('OpenLP.StageDisplayTab', 'Screens:'))
        self._lbl_screens_hint.setText(
            translate(
                'OpenLP.StageDisplayTab',
                'Select one or more screens to show the stage display fullscreen. '
                'Leave all unchecked to use a windowed display.'
            )
        )
        self._lbl_text_mode.setText(translate('OpenLP.StageDisplayTab', 'Text size:'))
        self.stage_text_auto_radio.setText(translate('OpenLP.StageDisplayTab', 'Best fit'))
        self.stage_text_fixed_radio.setText(translate('OpenLP.StageDisplayTab', 'Fixed:'))
        self._lbl_clock_size.setText(translate('OpenLP.StageDisplayTab', 'Clock size:'))
        self._lbl_clock_color.setText(translate('OpenLP.StageDisplayTab', 'Clock color:'))
        self._lbl_next_count.setText(translate('OpenLP.StageDisplayTab', 'Show next slides:'))
        self._lbl_next_display.setText(translate('OpenLP.StageDisplayTab', 'Next slide text:'))
        self._lbl_next_height.setText(translate('OpenLP.StageDisplayTab', 'Next slide area:'))
        self.stage_text_auto_radio.setToolTip(
            translate('OpenLP.StageDisplayTab', 'Automatically fit the text to fill the available space')
        )
        self.stage_text_fixed_radio.setToolTip(
            translate('OpenLP.StageDisplayTab', 'Use a fixed font size (text may be clipped if too large)')
        )
        self.stage_text_size_spin.setToolTip(
            translate('OpenLP.StageDisplayTab', 'Fixed font size for the current-slide text')
        )
        self.stage_clock_size_spin.setToolTip(
            translate('OpenLP.StageDisplayTab', 'Font size for the clock')
        )
        self.stage_next_height_spin.setToolTip(
            translate('OpenLP.StageDisplayTab', 'Height of the next-slide preview area')
        )

    def _build_stage_screen_checkboxes(self):
        """Rebuild the per-screen checkbox list to match currently-detected screens."""
        # Remove old checkboxes immediately (setParent(None) hides them now;
        # deleteLater() schedules cleanup so we don't briefly show duplicates).
        while self._stage_screen_checkboxes:
            cb = self._stage_screen_checkboxes.pop()
            self.stage_screens_layout.removeWidget(cb)
            cb.setParent(None)
            cb.deleteLater()

        saved = self.settings.value('core/stage screens') or []
        if not isinstance(saved, list):
            saved = []
        selected_indices = {int(i) for i in saved if isinstance(i, int) or str(i).lstrip('-').isdigit()}

        screens = QtWidgets.QApplication.screens()
        for i, screen in enumerate(screens):
            label = translate('OpenLP.StageDisplayTab', 'Screen {number} ({res})').format(
                number=i + 1,
                res='{w}×{h}'.format(w=screen.geometry().width(), h=screen.geometry().height()),
            )
            cb = QtWidgets.QCheckBox(label, self.stage_screens_widget)
            cb.setProperty('screen_index', i)
            cb.setChecked(i in selected_indices)
            cb.toggled.connect(self._update_preview_aspect)
            self.stage_screens_layout.addWidget(cb)
            self._stage_screen_checkboxes.append(cb)
        self._update_preview_aspect()

    def _update_preview_aspect(self, *_args):
        """Set preview aspect ratio to first-selected screen, falling back to primary."""
        screens = QtWidgets.QApplication.screens()
        target_screen = None
        for cb in self._stage_screen_checkboxes:
            if cb.isChecked():
                idx = int(cb.property('screen_index'))
                if 0 <= idx < len(screens):
                    target_screen = screens[idx]
                    break
        if target_screen is None:
            target_screen = QtWidgets.QApplication.primaryScreen()
        if target_screen is None:
            return
        geom = target_screen.geometry()
        if geom.height() > 0:
            self.stage_preview.set_screen_aspect_ratio(geom.width() / geom.height())

    def _on_text_mode_changed(self, auto_checked: bool):
        self.stage_text_size_spin.setEnabled(not auto_checked)
        self._update_stage_preview()

    def _on_clock_color_clicked(self):
        """Open color picker dialog and save selected color to settings."""
        current_color_hex = self.settings.value('core/stage clock color')
        current_color = QtGui.QColor(current_color_hex)
        color = QtWidgets.QColorDialog.getColor(
            current_color, self, translate('OpenLP.StageDisplayTab', 'Choose clock color')
        )
        if color.isValid():
            hex_color = color.name()
            self.settings.setValue('core/stage clock color', hex_color)
            self._update_clock_color_button()
            self._update_stage_preview()

    def _update_clock_color_button(self):
        """Update the button's visual representation of the selected clock color."""
        color_hex = self.settings.value('core/stage clock color')
        color = QtGui.QColor(color_hex)
        pixmap = QtGui.QPixmap(64, 20)
        pixmap.fill(color)
        self.stage_clock_color_button.setIcon(QtGui.QIcon(pixmap))

    def _update_stage_preview(self, *_args):
        """Refresh the preview when settings change."""
        try:
            mode = 'auto' if self.stage_text_auto_radio.isChecked() else 'fixed'
            clock_color = self.settings.value('core/stage clock color')
            next_count = int(self.stage_next_count_combo.currentText())
            display_text = self.stage_next_display_combo.currentText()
            next_display = 'first_line' if display_text == 'First line only' else 'full_text'
            self.stage_preview.set_values(
                mode,
                self.stage_text_size_spin.value(),
                self.stage_clock_size_spin.value(),
                self.stage_next_height_spin.value(),
                clock_color=clock_color,
                next_count=next_count,
                next_display=next_display,
            )
        except Exception:
            pass

    def _on_screen_changed(self):
        self._build_stage_screen_checkboxes()

    def resizeEvent(self, event=None):
        QtWidgets.QWidget.resizeEvent(self, event)

    def load(self):
        self._build_stage_screen_checkboxes()
        mode = self.settings.value('core/stage text mode')
        if mode == 'fixed':
            self.stage_text_fixed_radio.setChecked(True)
        else:
            self.stage_text_auto_radio.setChecked(True)
        self.stage_text_size_spin.setValue(self.settings.value('core/stage text size'))
        self.stage_text_size_spin.setEnabled(mode == 'fixed')
        self.stage_clock_size_spin.setValue(self.settings.value('core/stage clock size'))
        self.stage_next_height_spin.setValue(self.settings.value('core/stage next height'))
        self._update_clock_color_button()
        next_count = self.settings.value('core/stage next count')
        self.stage_next_count_combo.setCurrentText(str(next_count))
        display_mode = self.settings.value('core/stage next display')
        display_text = 'First line only' if display_mode == 'first_line' else 'Full text'
        self.stage_next_display_combo.setCurrentText(display_text)
        self._update_stage_preview()

    def save(self):
        selected = [
            int(cb.property('screen_index'))
            for cb in self._stage_screen_checkboxes
            if cb.isChecked()
        ]
        self.settings.setValue('core/stage screens', selected)
        mode = 'fixed' if self.stage_text_fixed_radio.isChecked() else 'auto'
        self.settings.setValue('core/stage text mode', mode)
        self.settings.setValue('core/stage text size', self.stage_text_size_spin.value())
        self.settings.setValue('core/stage clock size', self.stage_clock_size_spin.value())
        self.settings.setValue('core/stage next height', self.stage_next_height_spin.value())
        self.settings.setValue('core/stage next count', int(self.stage_next_count_combo.currentText()))
        display_text = self.stage_next_display_combo.currentText()
        next_display = 'first_line' if display_text == 'First line only' else 'full_text'
        self.settings.setValue('core/stage next display', next_display)
        if self.tab_visited:
            self.settings_form.register_post_process('config_screen_changed')
        self.tab_visited = False
