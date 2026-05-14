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
The screen settings tab in the configuration dialog
"""
from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.display.screens import ScreenList
from openlp.core.lib.settingstab import SettingsTab
from openlp.core.common.registry import Registry
from openlp.core.ui.icons import UiIcons
from openlp.core.widgets.widgets import ScreenSelectionWidget

STAGE_SCREEN_NONE = -1

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
        self.setMinimumSize(280, 158)
        policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.setSizePolicy(policy)
        self.setFixedHeight(175)

    def set_values(self, text_mode: str, text_size: int, clock_px: int, next_h: int):
        self._text_mode = text_mode
        self._text_size = text_size
        self._clock_px = clock_px
        self._next_h = next_h
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Reference geometry (matches StageDisplayWindow margins)
        REF_W, REF_H = 700, 394
        sx = w / REF_W
        sy = h / REF_H

        # Background
        p.fillRect(0, 0, w, h, QtGui.QColor('#111111'))

        # --- Header (clock) --------------------------------------------------
        real_header_h = max(20, self._clock_px + 8) + 12
        header_h = int(real_header_h * sy)

        clock_font = QtGui.QFont()
        clock_font.setPixelSize(max(8, int(self._clock_px * sy)))
        clock_font.setBold(True)
        p.setFont(clock_font)
        p.setPen(QtGui.QColor('#ffffff'))
        p.drawText(
            QtCore.QRect(0, 0, w - 6, header_h),
            int(QtCore.Qt.AlignmentFlag.AlignRight) | int(QtCore.Qt.AlignmentFlag.AlignVCenter),
            '14:10:35',
        )

        # --- Footer (next slide) ---------------------------------------------
        real_footer_h = self._next_h + 10
        footer_h = max(18, int(real_footer_h * sy))
        sep_y = h - footer_h - 1

        # --- Main text area --------------------------------------------------
        main_top = header_h
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
                # Auto-fit: find the largest font that fits
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

        # --- Footer label + next text ----------------------------------------
        next_lbl_font = QtGui.QFont()
        next_lbl_font.setPixelSize(max(6, int(10 * sy)))
        next_lbl_font.setBold(True)
        p.setFont(next_lbl_font)
        p.setPen(QtGui.QColor('#555555'))
        p.drawText(
            QtCore.QRect(4, sep_y + 3, 30, footer_h - 3),
            int(QtCore.Qt.AlignmentFlag.AlignLeft) | int(QtCore.Qt.AlignmentFlag.AlignVCenter),
            'NEXT',
        )

        next_txt_font = QtGui.QFont()
        next_txt_font.setPixelSize(max(6, int(13 * sy)))
        p.setFont(next_txt_font)
        p.setPen(QtGui.QColor('#888888'))
        p.drawText(
            QtCore.QRect(38, sep_y + 3, w - 42, footer_h - 3),
            int(QtCore.Qt.AlignmentFlag.AlignLeft) | int(QtCore.Qt.AlignmentFlag.AlignVCenter),
            _PREVIEW_SAMPLE_NEXT,
        )
        p.end()


class ScreensTab(SettingsTab):
    """
    ScreensTab is the screen settings tab in the configuration dialog
    """
    def __init__(self, parent):
        """
        Initialise the screen settings tab
        """
        self.icon_path = UiIcons().desktop
        screens_translated = translate('OpenLP.ScreensTab', 'Screens')
        super(ScreensTab, self).__init__(parent, 'Screens', screens_translated)
        self.settings_section = 'core'

    def setup_ui(self):
        """
        Set up the user interface elements
        """
        self.setObjectName('self')
        self.tab_layout = QtWidgets.QVBoxLayout(self)
        self.tab_layout.setObjectName('tab_layout')
        self.screen_selection_widget = ScreenSelectionWidget(self, ScreenList())
        self.tab_layout.addWidget(self.screen_selection_widget)
        self.generic_group_box = QtWidgets.QGroupBox(self)
        self.generic_group_box.setObjectName('generic_group_box')
        self.generic_group_layout = QtWidgets.QVBoxLayout(self.generic_group_box)
        self.display_on_monitor_check = QtWidgets.QCheckBox(self.generic_group_box)
        self.display_on_monitor_check.setObjectName('monitor_combo_box')
        self.generic_group_layout.addWidget(self.display_on_monitor_check)
        self.tab_layout.addWidget(self.generic_group_box)

        # Stage display screen selector + appearance
        self.stage_group_box = QtWidgets.QGroupBox(self)
        self.stage_group_box.setObjectName('stage_group_box')
        stage_layout = QtWidgets.QFormLayout(self.stage_group_box)

        self._lbl_screen = QtWidgets.QLabel(self.stage_group_box)
        self.stage_screen_combo = QtWidgets.QComboBox(self.stage_group_box)
        self.stage_screen_combo.setObjectName('stage_screen_combo')
        stage_layout.addRow(self._lbl_screen, self.stage_screen_combo)

        # Preview spans both columns (no label)
        self.stage_preview = _StagePreviewWidget(self.stage_group_box)
        stage_layout.addRow(self.stage_preview)

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
        self.stage_clock_size_spin.setRange(12, 500)  # Practical upper limit; no hard cap
        self.stage_clock_size_spin.setSuffix(' px')
        stage_layout.addRow(self._lbl_clock_size, self.stage_clock_size_spin)

        self._lbl_clock_color = QtWidgets.QLabel(self.stage_group_box)
        self.stage_clock_color_button = QtWidgets.QPushButton(self.stage_group_box)
        self.stage_clock_color_button.setObjectName('stage_clock_color_button')
        self.stage_clock_color_button.setFixedWidth(80)
        stage_layout.addRow(self._lbl_clock_color, self.stage_clock_color_button)

        self._lbl_next_height = QtWidgets.QLabel(self.stage_group_box)
        self.stage_next_height_spin = QtWidgets.QSpinBox(self.stage_group_box)
        self.stage_next_height_spin.setRange(30, 2000)
        self.stage_next_height_spin.setSuffix(' px')
        stage_layout.addRow(self._lbl_next_height, self.stage_next_height_spin)

        self.tab_layout.addWidget(self.stage_group_box)

        self.stage_text_auto_radio.toggled.connect(self._on_text_mode_changed)
        self.stage_text_size_spin.valueChanged.connect(self._update_stage_preview)
        self.stage_clock_size_spin.valueChanged.connect(self._update_stage_preview)
        self.stage_next_height_spin.valueChanged.connect(self._update_stage_preview)
        self.stage_clock_color_button.clicked.connect(self._on_clock_color_clicked)

        Registry().register_function('config_screen_changed', self._on_screen_changed)

    def retranslate_ui(self):
        self.generic_group_box.setTitle(translate('OpenLP.ScreensTab', 'Generic screen settings'))
        self.display_on_monitor_check.setText(translate('OpenLP.ScreensTab', 'Display if a single screen'))
        self.stage_group_box.setTitle(translate('OpenLP.ScreensTab', 'Stage Display'))
        self._lbl_screen.setText(translate('OpenLP.ScreensTab', 'Screen:'))
        self._lbl_text_mode.setText(translate('OpenLP.ScreensTab', 'Text size:'))
        self.stage_text_auto_radio.setText(translate('OpenLP.ScreensTab', 'Best fit'))
        self.stage_text_fixed_radio.setText(translate('OpenLP.ScreensTab', 'Fixed:'))
        self._lbl_clock_size.setText(translate('OpenLP.ScreensTab', 'Clock size:'))
        self._lbl_clock_color.setText(translate('OpenLP.ScreensTab', 'Clock color:'))
        self._lbl_next_height.setText(translate('OpenLP.ScreensTab', 'Next slide area:'))
        self.stage_screen_combo.setToolTip(
            translate('OpenLP.ScreensTab', 'Screen to use for the Stage Display window')
        )
        self.stage_text_auto_radio.setToolTip(
            translate('OpenLP.ScreensTab', 'Automatically fit the text to fill the available space')
        )
        self.stage_text_fixed_radio.setToolTip(
            translate('OpenLP.ScreensTab', 'Use a fixed font size (text may be clipped if too large)')
        )
        self.stage_text_size_spin.setToolTip(
            translate('OpenLP.ScreensTab', 'Fixed font size for the current-slide text')
        )
        self.stage_clock_size_spin.setToolTip(
            translate('OpenLP.ScreensTab', 'Font size for the clock')
        )
        self.stage_next_height_spin.setToolTip(
            translate('OpenLP.ScreensTab', 'Height of the next-slide preview area')
        )

    def _build_stage_screen_combo(self):
        """Rebuild the stage screen combo with the current list of detected screens."""
        self.stage_screen_combo.blockSignals(True)
        saved = self.settings.value('core/stage screen')
        self.stage_screen_combo.clear()
        self.stage_screen_combo.addItem(
            translate('OpenLP.ScreensTab', 'None (windowed / remember position)'),
            STAGE_SCREEN_NONE,
        )
        screens = QtWidgets.QApplication.screens()
        for i, screen in enumerate(screens):
            label = translate('OpenLP.ScreensTab', 'Screen {number} ({res})').format(
                number=i + 1,
                res='{w}×{h}'.format(w=screen.geometry().width(), h=screen.geometry().height()),
            )
            self.stage_screen_combo.addItem(label, i)
        # Restore selection
        idx = self.stage_screen_combo.findData(saved if isinstance(saved, int) else STAGE_SCREEN_NONE)
        self.stage_screen_combo.setCurrentIndex(max(idx, 0))
        self.stage_screen_combo.blockSignals(False)

    def _on_text_mode_changed(self, auto_checked: bool):
        self.stage_text_size_spin.setEnabled(not auto_checked)
        self._update_stage_preview()

    def _on_clock_color_clicked(self):
        """Open color picker dialog and save selected color to settings."""
        settings = Registry().get('settings')
        current_color_hex = settings.value('core/stage clock color')
        current_color = QtGui.QColor(current_color_hex)
        color = QtWidgets.QColorDialog.getColor(current_color, self, translate('OpenLP.ScreensTab', 'Choose clock color'))
        if color.isValid():
            hex_color = color.name()
            settings.setValue('core/stage clock color', hex_color)
            self._update_clock_color_button()
            self._update_stage_preview()

    def _update_clock_color_button(self):
        """Update the button's visual representation of the selected clock color."""
        settings = Registry().get('settings')
        color_hex = settings.value('core/stage clock color')
        color = QtGui.QColor(color_hex)
        pixmap = QtGui.QPixmap(64, 20)
        pixmap.fill(color)
        self.stage_clock_color_button.setIcon(QtGui.QIcon(pixmap))

    def _update_stage_preview(self, *_args):
        mode = 'auto' if self.stage_text_auto_radio.isChecked() else 'fixed'
        self.stage_preview.set_values(
            mode,
            self.stage_text_size_spin.value(),
            self.stage_clock_size_spin.value(),
            self.stage_next_height_spin.value(),
        )

    def _on_screen_changed(self):
        self.screen_selection_widget.load()
        self._build_stage_screen_combo()

    def resizeEvent(self, event=None):
        """
        Override resizeEvent() to adjust the position of the identify_button.

        NB: Don't call SettingsTab's resizeEvent() because we're not using its widgets.
        """
        QtWidgets.QWidget.resizeEvent(self, event)

    def load(self):
        """
        Load the settings to populate the tab
        """
        self.screen_selection_widget.load()
        self.display_on_monitor_check.setChecked(self.settings.value('core/display on monitor'))
        self._build_stage_screen_combo()
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
        self._update_stage_preview()

    def save(self):
        self.screen_selection_widget.save()
        self.settings.setValue('core/display on monitor', self.display_on_monitor_check.isChecked())
        self.settings.setValue('core/stage screen', self.stage_screen_combo.currentData())
        mode = 'fixed' if self.stage_text_fixed_radio.isChecked() else 'auto'
        self.settings.setValue('core/stage text mode', mode)
        self.settings.setValue('core/stage text size', self.stage_text_size_spin.value())
        self.settings.setValue('core/stage clock size', self.stage_clock_size_spin.value())
        self.settings.setValue('core/stage next height', self.stage_next_height_spin.value())
        # On save update the screens as well
        if self.tab_visited:
            self.settings_form.register_post_process('config_screen_changed')
        self.tab_visited = False
