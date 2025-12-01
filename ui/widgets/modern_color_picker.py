from __future__ import annotations

import json
import math
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPointF, QRectF
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QConicalGradient,
    QMouseEvent,
    QBrush,
    QPen,
    QPainterPath,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QSpinBox,
    QLineEdit,
    QFrame,
    QPushButton,
    QSlider,
    QApplication,
)


# ==============================================================
#   Widgets auxiliares
# ==============================================================

class HueRing(QWidget):
    """
    Selector circular de matiz (Hue).
    Emite hueChanged(int) cuando el usuario mueve el selector.
    """

    hueChanged = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hue = 0
        self.ring_width = 18
        self.setFixedSize(220, 220)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # API pública -----------------------------------------------------

    def hue(self) -> int:
        return self._hue

    def set_hue(self, hue: int) -> None:
        hue = int(max(0, min(359, hue)))
        if hue == self._hue:
            return
        self._hue = hue
        self.hueChanged.emit(self._hue)
        self.update()

    # Helpers internos ------------------------------------------------

    def _pos_to_hue(self, pos: QPoint) -> int:
        rect = self.rect()
        center = rect.center()
        dx = pos.x() - center.x()
        dy = center.y() - pos.y()  # invertimos Y para que 0° sea a la derecha

        angle = math.degrees(math.atan2(dy, dx))  # [-180, 180]
        if angle < 0:
            angle += 360
        return int(round(angle)) % 360

    # Eventos ---------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.set_hue(self._pos_to_hue(event.pos()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.set_hue(self._pos_to_hue(event.pos()))

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(4, 4, -4, -4)

        # Anillo con gradiente cónico HSV
        gradient = QConicalGradient(rect.center(), 0)
        for i, deg in enumerate(range(0, 360, 60)):
            gradient.setColorAt(i / 6.0, QColor.fromHsv(deg, 255, 255))
        gradient.setColorAt(1.0, QColor.fromHsv(0, 255, 255))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))

        path = QPainterPath()
        path.addEllipse(rect)
        inner_rect = rect.adjusted(self.ring_width, self.ring_width,
                                   -self.ring_width, -self.ring_width)
        path.addEllipse(inner_rect)
        path.setFillRule(Qt.FillRule.OddEvenFill)
        painter.drawPath(path)

        # Handle
        angle_rad = math.radians(self._hue)
        radius = (rect.width() / 2.0) - (self.ring_width / 2.0)
        center = rect.center()
        cx = center.x() + radius * math.cos(angle_rad)
        cy = center.y() - radius * math.sin(angle_rad)

        painter.setPen(QPen(QColor("white"), 2))
        painter.setBrush(Qt.GlobalColor.transparent)
        painter.drawEllipse(QPointF(cx, cy), 8, 8)


class ColorSwatch(QFrame):
    """
    Pequeño recuadro de color clickeable.
    - Click izquierdo: usar color.
    - Click derecho: eliminar (lo maneja ModernColorPicker).
    """

    clicked = pyqtSignal(QColor)
    rightClicked = pyqtSignal(object)  # emite self

    def __init__(self, color: QColor, size: int = 24, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = QColor(color)
        self._size = size
        self.setFixedSize(size, size)
        self._update_style()

    def _update_style(self) -> None:
        self.setStyleSheet(
            f"background-color: {self._color.name()};"
            "border-radius: 4px;"
            "border: 1px solid #555;"
        )

    def color(self) -> QColor:
        return QColor(self._color)

    def set_color(self, rgb: tuple[int, int, int]) -> None:
        """
        Cambia el color actual (modo RGB) y recuerda el último color.

        Regla especial:
        - Si el color es (0, 0, 0) lo interpretamos como
          "Brillo del selector = 0%" → APAGAR la bombilla.
        """
        ip = self._get_active_bulb()
        if not ip:
            return

        async def do():
            bulb = wizlight(ip)

            # Brillo del picker a 0% → color negro.
            # En vez de mandar rgb=(0,0,0) (que la pone blanca),
            # apagamos directamente la ampolleta.
            if rgb == (0, 0, 0):
                await bulb.turn_off()
                logging.info("Color (0,0,0) → bombilla APAGADA (brillo picker 0%)")
                return

            # Para cualquier otro color, se aplica normal
            self.last_rgb = rgb
            await bulb.turn_on(PilotBuilder(rgb=rgb))

        self._run_async(do())


    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(QColor(self._color))
        elif event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit(self)


def _rgb_to_cmyk(r: int, g: int, b: int) -> tuple[int, int, int, int]:
    """
    Conversión sencilla de RGB [0-255] a CMYK [%].
    """
    if r == 0 and g == 0 and b == 0:
        return 0, 0, 0, 100

    r_f, g_f, b_f = r / 255.0, g / 255.0, b / 255.0
    k = 1.0 - max(r_f, g_f, b_f)
    c = (1.0 - r_f - k) / (1.0 - k) if k < 1.0 else 0.0
    m = (1.0 - g_f - k) / (1.0 - k) if k < 1.0 else 0.0
    y = (1.0 - b_f - k) / (1.0 - k) if k < 1.0 else 0.0
    return tuple(int(round(x * 100)) for x in (c, m, y, k))


# ==============================================================
#   ModernColorPicker principal
# ==============================================================

class ModernColorPicker(QWidget):
    """
    Color picker moderno inspirado en tu mockup de Wizz Controller.

    Señal:
        colorChanged((r, g, b))
    """

    colorChanged = pyqtSignal(tuple)

    # ------------------------------------------------------------------
    #  Inicialización
    # ------------------------------------------------------------------
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Estado interno HSV (0-359, 0-255, 0-255)
        self._hue = 0
        self._sat = 255
        self._val = 255
        self._block_signals = False

        # Paleta persistente
        self._saved_swatches: list[ColorSwatch] = []
        self._palette_path = Path(__file__).with_name("saved_colors.json")

        self._build_ui()
        self._load_saved_palette()

        # Estado inicial (rojo saturado, brillo 100%)
        self.slider_sat.setValue(100)
        self.slider_val.setValue(100)
        self._update_all_from_hsv()

    # ------------------------------------------------------------------
    #  Construcción de la UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QLineEdit, QSpinBox {
                background-color: #333;
                color: #eee;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px;
            }
            QLabel {
                color: #ccc;
                font-weight: bold;
            }
            QPushButton {
                background-color: #e67e22;
                color: white;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:pressed {
                background-color: #a84300;
            }
            """
        )

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(18)

        # --------------------------------------------------------------
        #  Columna izquierda: paletas + códigos
        # --------------------------------------------------------------
        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)
        root_layout.addLayout(left_panel, 1)

        # Colores recomendados
        lbl_rec = QLabel("Colores recomendados")
        left_panel.addWidget(lbl_rec)

        rec_widget = QWidget()
        rec_grid = QGridLayout(rec_widget)
        rec_grid.setContentsMargins(0, 0, 0, 0)
        rec_grid.setHorizontalSpacing(6)
        rec_grid.setVerticalSpacing(6)

        recommended_hex = [
            "#F44336", "#E91E63", "#9C27B0", "#673AB7",
            "#3F51B5", "#2196F3", "#03A9F4", "#00BCD4",
            "#009688", "#4CAF50", "#8BC34A", "#CDDC39",
            "#FFC107", "#FF9800", "#FF5722", "#795548",
        ]

        for idx, hx in enumerate(recommended_hex):
            sw = ColorSwatch(QColor(hx), size=22)
            sw.clicked.connect(self._on_swatch_clicked)
            sw.rightClicked.connect(self._remove_saved_color_noop)  # ignorar
            row = idx // 8
            col = idx % 8
            rec_grid.addWidget(sw, row, col)

        left_panel.addWidget(rec_widget)

        # Colores guardados (título + botón vaciar)
        saved_title_row = QHBoxLayout()
        lbl_saved = QLabel("Colores guardados")
        saved_title_row.addWidget(lbl_saved)
        saved_title_row.addStretch()

        self.btn_clear_palette = QPushButton("Vaciar")
        self.btn_clear_palette.setFixedHeight(22)
        self.btn_clear_palette.clicked.connect(self._clear_saved_palette)
        saved_title_row.addWidget(self.btn_clear_palette)

        left_panel.addLayout(saved_title_row)

        # Grilla de colores guardados
        self.saved_widget = QWidget()
        self.saved_grid = QGridLayout(self.saved_widget)
        self.saved_grid.setContentsMargins(0, 0, 0, 0)
        self.saved_grid.setHorizontalSpacing(6)
        self.saved_grid.setVerticalSpacing(6)

        left_panel.addWidget(self.saved_widget)

        # Botón para añadir color actual a la paleta
        self.btn_add_saved = QPushButton("+")
        self.btn_add_saved.setToolTip("Agregar color actual a la paleta")
        self.btn_add_saved.setFixedHeight(26)
        self.btn_add_saved.clicked.connect(self._add_current_to_saved)
        left_panel.addWidget(self.btn_add_saved)

        # ---- Códigos de color ----------------------------------------
        codes_frame = QFrame()
        codes_layout = QVBoxLayout(codes_frame)
        codes_layout.setContentsMargins(0, 6, 0, 0)
        codes_layout.setSpacing(6)

        # HEX
        hex_layout = QHBoxLayout()
        hex_layout.addWidget(QLabel("HEX:"))
        self.hex_input = QLineEdit()
        self.hex_input.setPlaceholderText("#RRGGBB")
        self.hex_input.setMaxLength(7)
        self.hex_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hex_input.editingFinished.connect(self._on_hex_edited)
        hex_layout.addWidget(self.hex_input, 1)
        codes_layout.addLayout(hex_layout)

        # RGB
        rgb_layout = QHBoxLayout()
        rgb_layout.addWidget(QLabel("RGB:"))
        self.rgb_spins: list[QSpinBox] = []
        for label in ("R", "G", "B"):
            rgb_layout.addWidget(QLabel(label))
            spin = QSpinBox()
            spin.setRange(0, 255)
            spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
            spin.setFixedWidth(48)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.valueChanged.connect(self._on_rgb_edited)
            self.rgb_spins.append(spin)
            rgb_layout.addWidget(spin)
        codes_layout.addLayout(rgb_layout)

        # CMYK (solo lectura)
        cmyk_layout = QHBoxLayout()
        cmyk_layout.addWidget(QLabel("CMYK:"))
        self.cmyk_spins: list[QSpinBox] = []
        for label in ("C", "M", "Y", "K"):
            cmyk_layout.addWidget(QLabel(label))
            spin = QSpinBox()
            spin.setRange(0, 100)
            spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
            spin.setFixedWidth(40)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.setReadOnly(True)
            spin.setEnabled(False)
            self.cmyk_spins.append(spin)
            cmyk_layout.addWidget(spin)
        codes_layout.addLayout(cmyk_layout)

        # Botón copiar
        self.btn_copy = QPushButton("Copiar al portapapeles")
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        codes_layout.addWidget(self.btn_copy)

        left_panel.addWidget(codes_frame)
        left_panel.addStretch()

        # --------------------------------------------------------------
        #  Columna derecha: selector de color
        # --------------------------------------------------------------
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)
        root_layout.addLayout(right_panel, 1)

        lbl_chooser = QLabel("Selector de color")
        lbl_chooser.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_panel.addWidget(lbl_chooser)

        # Hue ring
        self.hue_ring = HueRing()
        self.hue_ring.hueChanged.connect(self._on_hue_changed)
        right_panel.addWidget(self.hue_ring, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Sliders de Saturación y Brillo
        self.slider_sat = QSlider(Qt.Orientation.Horizontal)
        self.slider_sat.setRange(0, 100)
        self.slider_sat.valueChanged.connect(self._on_sat_slider_changed)

        self.slider_val = QSlider(Qt.Orientation.Horizontal)
        self.slider_val.setRange(0, 100)
        self.slider_val.valueChanged.connect(self._on_val_slider_changed)

        # Saturación
        sat_row = QHBoxLayout()
        sat_row.addWidget(QLabel("Saturación"))
        self.lbl_sat_value = QLabel("100%")
        self.lbl_sat_value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        sat_row.addWidget(self.lbl_sat_value)
        right_panel.addLayout(sat_row)
        right_panel.addWidget(self.slider_sat)

        # Brillo
        val_row = QHBoxLayout()
        val_row.addWidget(QLabel("Brillo"))
        self.lbl_val_value = QLabel("100%")
        self.lbl_val_value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        val_row.addWidget(self.lbl_val_value)
        right_panel.addLayout(val_row)
        right_panel.addWidget(self.slider_val)

        # Barra de preview
        self.preview_bar = QFrame()
        self.preview_bar.setFixedHeight(12)
        self.preview_bar.setStyleSheet(
            "background-color: #ffffff; border-radius: 6px;"
        )
        right_panel.addWidget(self.preview_bar)

        right_panel.addStretch()

    # ==============================================================
    #   Handlers UI
    # ==============================================================

    def _on_hue_changed(self, hue: int) -> None:
        if self._block_signals:
            return
        self._hue = hue
        self._update_all_from_hsv()

    def _on_sat_slider_changed(self, value: int) -> None:
        if self._block_signals:
            return
        self._sat = int(round(value / 100.0 * 255))
        self.lbl_sat_value.setText(f"{value}%")
        self._update_all_from_hsv()

    def _on_val_slider_changed(self, value: int) -> None:
        if self._block_signals:
            return
        self._val = int(round(value / 100.0 * 255))
        self.lbl_val_value.setText(f"{value}%")
        self._update_all_from_hsv()

    def _on_rgb_edited(self) -> None:
        if self._block_signals:
            return
        r = self.rgb_spins[0].value()
        g = self.rgb_spins[1].value()
        b = self.rgb_spins[2].value()
        color = QColor(r, g, b)
        self._update_internal_from_qcolor(color)
        self._emit_and_update_ui(color, update_rgb=False)

    def _on_hex_edited(self) -> None:
        if self._block_signals:
            return
        text = self.hex_input.text().strip()
        if not text:
            return
        if not text.startswith("#"):
            text = "#" + text
        if QColor.isValidColor(text):
            color = QColor(text)
            self._update_internal_from_qcolor(color)
            self._emit_and_update_ui(color, update_hex=False)

    def _on_swatch_clicked(self, color: QColor) -> None:
        self._update_internal_from_qcolor(color)
        self._emit_and_update_ui(color)

    # ==============================================================
    #   Paleta guardada
    # ==============================================================

    def _add_current_to_saved(self) -> None:
        color = QColor.fromHsv(self._hue, self._sat, self._val)
        hex_color = color.name().upper()

        # Evitar duplicados exactos
        for sw in self._saved_swatches:
            if sw.color().name().upper() == hex_color:
                return

        sw = ColorSwatch(color, size=22)
        sw.clicked.connect(self._on_swatch_clicked)
        sw.rightClicked.connect(self._remove_saved_color)

        self._saved_swatches.append(sw)
        self._rebuild_saved_grid()
        self._save_palette()

    def _remove_saved_color(self, swatch: ColorSwatch) -> None:
        if swatch not in self._saved_swatches:
            return
        self._saved_swatches.remove(swatch)
        swatch.setParent(None)
        swatch.deleteLater()
        self._rebuild_saved_grid()
        self._save_palette()

    def _remove_saved_color_noop(self, swatch: ColorSwatch) -> None:
        """
        Conectado a recuadros de 'colores recomendados' para
        ignorar el click derecho sin romper la señal.
        """
        return

    def _rebuild_saved_grid(self) -> None:
        # Vaciar layout
        while self.saved_grid.count():
            item = self.saved_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(self.saved_widget)

        # Volver a acomodar
        for i, sw in enumerate(self._saved_swatches):
            row = i // 8
            col = i % 8
            self.saved_grid.addWidget(sw, row, col)

    def _clear_saved_palette(self) -> None:
        for sw in self._saved_swatches:
            sw.setParent(None)
            sw.deleteLater()
        self._saved_swatches.clear()
        self._rebuild_saved_grid()
        self._save_palette()

    def _save_palette(self) -> None:
        try:
            colors_hex = [sw.color().name().upper() for sw in self._saved_swatches]
            self._palette_path.write_text(json.dumps(colors_hex, indent=2), encoding="utf-8")
        except Exception:
            # no reventar la app si hay algún problema de permisos, etc.
            pass

    def _load_saved_palette(self) -> None:
        if not self._palette_path.exists():
            return
        try:
            data = json.loads(self._palette_path.read_text(encoding="utf-8"))
        except Exception:
            return

        self._saved_swatches.clear()
        for hx in data:
            if not QColor.isValidColor(hx):
                continue
            color = QColor(hx)
            sw = ColorSwatch(color, size=22)
            sw.clicked.connect(self._on_swatch_clicked)
            sw.rightClicked.connect(self._remove_saved_color)
            self._saved_swatches.append(sw)
        self._rebuild_saved_grid()

    # ==============================================================
    #   Utilidades / sincronización de estado
    # ==============================================================

    def _copy_to_clipboard(self) -> None:
        text = self.hex_input.text().strip()
        if not text:
            color = QColor.fromHsv(self._hue, self._sat, self._val)
            text = color.name().upper()
        QApplication.clipboard().setText(text)

    def _update_internal_from_qcolor(self, color: QColor) -> None:
        self._hue = max(0, color.hue() if color.hue() >= 0 else 0)
        self._sat = color.saturation()
        self._val = color.value()

    def _update_slider_gradients(self) -> None:
        # Saturación: de gris al color actual
        color_min = QColor.fromHsv(self._hue, 0, self._val)
        color_max = QColor.fromHsv(self._hue, 255, self._val)
        grad_sat = (
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 rgb({color_min.red()}, {color_min.green()}, {color_min.blue()}), "
            f"stop:1 rgb({color_max.red()}, {color_max.green()}, {color_max.blue()}))"
        )

        # Brillo: negro al color actual
        color_bright = QColor.fromHsv(self._hue, self._sat, 255)
        grad_val = (
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 rgb(0,0,0), "
            f"stop:1 rgb({color_bright.red()}, {color_bright.green()}, {color_bright.blue()}))"
        )

        slider_style = (
            "QSlider::groove:horizontal {{"
            "height: 8px; border-radius: 4px; background: {grad};"
            "}}"
            "QSlider::handle:horizontal {{"
            "background: white; width: 16px; margin: -5px 0; border-radius: 8px;"
            "}}"
        )

        self.slider_sat.setStyleSheet(slider_style.format(grad=grad_sat))
        self.slider_val.setStyleSheet(slider_style.format(grad=grad_val))

    def _emit_and_update_ui(
        self,
        color: QColor,
        update_hex: bool = True,
        update_rgb: bool = True,
    ) -> None:
        self._block_signals = True

        # Campos HEX / RGB
        if update_hex:
            self.hex_input.setText(color.name().upper())
        if update_rgb:
            self.rgb_spins[0].setValue(color.red())
            self.rgb_spins[1].setValue(color.green())
            self.rgb_spins[2].setValue(color.blue())

        # CMYK
        c, m, y, k = _rgb_to_cmyk(color.red(), color.green(), color.blue())
        for spin, val in zip(self.cmyk_spins, (c, m, y, k)):
            spin.setValue(val)

        # Barra de preview
        self.preview_bar.setStyleSheet(
            f"background-color: {color.name()}; border-radius: 6px;"
        )

        # Sliders / labels
        self.slider_sat.setValue(int(round(self._sat / 255.0 * 100)))
        self.slider_val.setValue(int(round(self._val / 255.0 * 100)))
        self.lbl_sat_value.setText(f"{int(round(self._sat / 255.0 * 100))}%")
        self.lbl_val_value.setText(f"{int(round(self._val / 255.0 * 100))}%")

        # Hue ring
        self.hue_ring.set_hue(self._hue)

        self._block_signals = False

        # Emitir a la app principal
        self.colorChanged.emit((color.red(), color.green(), color.blue()))

    def _update_all_from_hsv(self) -> None:
        color = QColor.fromHsv(self._hue, self._sat, self._val)
        self._update_slider_gradients()
        self._emit_and_update_ui(color)