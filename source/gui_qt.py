"""Futoshiki GUI with PySide6 (macOS Liquid Glass style)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import math
import os
import time

from PySide6.QtCore import QTimer, Qt, QRectF, QPointF, QVariantAnimation, QEasingCurve, QRect, QPropertyAnimation, QParallelAnimationGroup
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from futoshiki_core import Puzzle, inequality_ok, is_valid_solution, read_input, write_output
from solvers import solve

ALGOS: List[Tuple[str, str]] = [
    ("forward", "Forward Chaining"),
    ("backward", "Backward Chaining (SLD)"),
    ("astar", "A* Search"),
    ("backtracking", "Backtracking"),
    ("bruteforce", "Brute Force"),
]


class MeshBackground(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 FPS subtle liquid motion

    def _tick(self) -> None:
        self._phase += 0.018
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Dark base gradient
        lg = QLinearGradient(0, 0, 0, self.height())
        lg.setColorAt(0.0, QColor("#0F1626"))
        lg.setColorAt(0.55, QColor("#101B2F"))
        lg.setColorAt(1.0, QColor("#131D30"))
        p.fillRect(self.rect(), lg)

        # Mesh blobs
        t = self._phase
        blobs = [
            (self.width() * (0.08 + 0.015 * math.sin(t * 0.9)), self.height() * (0.18 + 0.012 * math.cos(t * 1.1)), self.width() * 0.34, "#007AFF", "#007AFF00"),
            (self.width() * (0.78 + 0.012 * math.cos(t * 0.7)), self.height() * (0.22 + 0.015 * math.sin(t * 1.0)), self.width() * 0.38, "#5856D6", "#5856D600"),
            (self.width() * (0.72 + 0.010 * math.sin(t * 1.2)), self.height() * (0.78 + 0.014 * math.cos(t * 0.8)), self.width() * 0.40, "#7C3AED", "#7C3AED00"),
            (self.width() * (0.20 + 0.013 * math.cos(t * 1.3)), self.height() * (0.82 + 0.010 * math.sin(t * 0.9)), self.width() * 0.36, "#3B82F6", "#3B82F600"),
        ]
        for cx, cy, r, c0, c1 in blobs:
            rg = QRadialGradient(cx, cy, r)
            rg.setColorAt(0.0, QColor(c0))
            rg.setColorAt(1.0, QColor(c1))
            p.setBrush(rg)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, cy), r, r)

        # subtle black micro-particles (luxury grain)
        p.setPen(Qt.NoPen)
        for idx in range(120):
            px = (idx * 137 + int(40 * math.sin(t * 0.7 + idx))) % max(1, self.width())
            py = (idx * 83 + int(32 * math.cos(t * 0.9 + idx * 0.31))) % max(1, self.height())
            radius = 0.8 + (idx % 3) * 0.45
            p.setBrush(QColor(0, 0, 0, 30))  # ~0.12 opacity
            p.drawEllipse(QPointF(px, py), radius, radius)


class LiquidButton(QPushButton):
    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(18)
        self._shadow.setOffset(0, 6)
        self._shadow.setColor(QColor(0, 0, 0, 130))
        self.setGraphicsEffect(self._shadow)
        self.setMinimumHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(190)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hover_anim.valueChanged.connect(self._apply_anim_value)
        self._anim_value = 0.0
        self._press_anim = QVariantAnimation(self)
        self._press_anim.setDuration(130)
        self._press_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._press_anim.valueChanged.connect(self._apply_press_value)
        self._press_value = 0.0
        self._fx_phase = 0.0
        self._ripples: List[ButtonRipple] = []
        self._fx_timer = QTimer(self)
        self._fx_timer.timeout.connect(self._tick_fx)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._anim_value)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        # keep rounded-rect shape stable; animate only glow/depth for smoothness
        if not self._fx_timer.isActive():
            self._fx_timer.start(16)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._anim_value)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press_value)
        self._press_anim.setEndValue(1.0)
        self._press_anim.start()
        self._ripples.append(
            ButtonRipple(
                x=float(event.position().x()),
                y=float(event.position().y()),
                age=0.0,
                duration=0.46,
            )
        )
        if not self._fx_timer.isActive():
            self._fx_timer.start(16)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press_value)
        self._press_anim.setEndValue(0.0)
        self._press_anim.start()
        super().mouseReleaseEvent(event)

    def _apply_anim_value(self, v: float) -> None:
        self._anim_value = float(v)
        blur = 18.0 + 13.0 * self._anim_value
        self._shadow.setBlurRadius(blur)
        self._shadow.setOffset(0, 6 + 2.4 * self._anim_value)
        # gradient/brighter border is handled in global QSS via :hover,
        # this animation adds smooth shadow "liquid" response.

    def _apply_press_value(self, v: float) -> None:
        self._press_value = float(v)
        # click bounce feel without repaint artifacts from custom painting
        self._shadow.setOffset(0, 6 + 2.4 * self._anim_value - 2.0 * self._press_value)
        self._shadow.setBlurRadius(18.0 + 13.0 * self._anim_value - 4.0 * self._press_value)

    def _tick_fx(self) -> None:
        self._fx_phase = (self._fx_phase + 0.05) % (2.0 * math.pi)
        keep: List[ButtonRipple] = []
        for rp in self._ripples:
            rp.age += 0.016
            if rp.age < rp.duration:
                keep.append(rp)
        self._ripples = keep
        self.update()
        if self._anim_value <= 0.01 and not self._ripples:
            self._fx_timer.stop()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rr = 11.0
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0), rr, rr)
        p.setClipPath(clip)

        # Crystal refraction stripe (keeps original blue palette)
        ref = QLinearGradient(0, 0, self.width(), self.height())
        ref.setColorAt(0.0, QColor(255, 255, 255, 0))
        ref.setColorAt(0.4, QColor(255, 255, 255, 18))
        ref.setColorAt(0.56, QColor(255, 255, 255, 34))
        ref.setColorAt(0.72, QColor(255, 255, 255, 14))
        ref.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(self.rect(), ref)

        # Hover shimmer sweep
        if self._anim_value > 0.001:
            sweep = (math.sin(self._fx_phase * 1.6) + 1.0) * 0.5
            x0 = -self.width() * 0.35 + sweep * self.width() * 1.45
            shimmer = QLinearGradient(x0, 0, x0 + self.width() * 0.42, self.height())
            a = int(58 * self._anim_value)
            shimmer.setColorAt(0.0, QColor(255, 255, 255, 0))
            shimmer.setColorAt(0.5, QColor(255, 255, 255, a))
            shimmer.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.fillRect(self.rect(), shimmer)

        # Click ripples
        for rp in self._ripples:
            t = max(0.0, min(1.0, rp.age / rp.duration))
            alpha = int((1.0 - t) * 70)
            rad = (0.16 + 0.95 * t) * max(self.width(), self.height())
            rg = QRadialGradient(QPointF(rp.x, rp.y), rad)
            rg.setColorAt(0.0, QColor(255, 255, 255, alpha))
            rg.setColorAt(0.5, QColor(170, 220, 255, int(alpha * 0.62)))
            rg.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(rg)
            p.drawEllipse(QPointF(rp.x, rp.y), rad, rad)

        # Top gloss edge
        p.setPen(QPen(QColor(255, 255, 255, 80), 1.0))
        p.drawLine(12, 2, self.width() - 12, 2)


class AnimatedFileDialog(QFileDialog):
    def __init__(self, parent: Optional[QWidget] = None, start_dir: str = "") -> None:
        super().__init__(parent, "Select input file", start_dir, "Text Files (*.txt);;All Files (*)")
        self.setFileMode(QFileDialog.ExistingFile)
        self.setOption(QFileDialog.DontUseNativeDialog, True)
        # Helps reduce stalls from shell icon resolution on Windows.
        self.setOption(QFileDialog.DontUseCustomDirectoryIcons, True)
        self.setWindowModality(Qt.ApplicationModal)
        self._animated_once = False
        self._anim_group: Optional[QParallelAnimationGroup] = None
        self._closing = False
        self._pending_result = QFileDialog.Rejected
        self._end_rect: Optional[QRect] = None
        # Keep a clean glass-like look consistent with app style.
        self.setStyleSheet(
            """
            QFileDialog {
                background: rgba(22, 30, 47, 245);
                border: 1px solid rgba(130, 175, 235, 165);
                border-radius: 12px;
            }
            QLabel, QLineEdit, QListView, QTreeView, QComboBox {
                color: #EAF2FF;
                background: rgba(20, 28, 43, 220);
                border: 1px solid rgba(100, 145, 210, 120);
                border-radius: 8px;
            }
            QPushButton {
                color: #FFFFFF;
                border: 1px solid rgba(165, 205, 255, 145);
                border-radius: 9px;
                padding: 6px 10px;
                background-color: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                                                  stop:0 rgba(112,188,255,248),
                                                  stop:1 rgba(22,106,198,240));
            }
            """
        )

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._animated_once:
            return
        self._animated_once = True

        # Target geometry centered in parent with responsive size.
        if self.parentWidget() is not None:
            pr = self.parentWidget().geometry()
            target_w = min(920, int(pr.width() * 0.74))
            target_h = min(640, int(pr.height() * 0.80))
            cx = pr.center().x()
            cy = pr.center().y()
            end_rect = QRect(cx - target_w // 2, cy - target_h // 2, target_w, target_h)
        else:
            sz = self.sizeHint()
            end_rect = QRect(140, 80, max(820, sz.width()), max(560, sz.height()))
        self._end_rect = end_rect

        start_w = int(end_rect.width() * 0.90)
        start_h = int(end_rect.height() * 0.90)
        start_rect = QRect(
            end_rect.center().x() - start_w // 2,
            end_rect.center().y() - start_h // 2,
            start_w,
            start_h,
        )

        self.setGeometry(start_rect)
        self.setWindowOpacity(0.0)

        geo_anim = QPropertyAnimation(self, b"geometry", self)
        geo_anim.setDuration(280)
        geo_anim.setStartValue(start_rect)
        geo_anim.setEndValue(end_rect)
        geo_anim.setEasingCurve(QEasingCurve.OutBack)

        op_anim = QPropertyAnimation(self, b"windowOpacity", self)
        op_anim.setDuration(220)
        op_anim.setStartValue(0.0)
        op_anim.setEndValue(1.0)
        op_anim.setEasingCurve(QEasingCurve.OutExpo)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(geo_anim)
        self._anim_group.addAnimation(op_anim)
        self._anim_group.start()

    def _start_exit_animation(self, result_code: int) -> None:
        if self._closing:
            return
        self._closing = True
        self._pending_result = result_code
        start_rect = self.geometry()
        end_w = int(start_rect.width() * 0.93)
        end_h = int(start_rect.height() * 0.93)
        end_rect = QRect(
            start_rect.center().x() - end_w // 2,
            start_rect.center().y() - end_h // 2,
            end_w,
            end_h,
        )

        geo_anim = QPropertyAnimation(self, b"geometry", self)
        geo_anim.setDuration(200)
        geo_anim.setStartValue(start_rect)
        geo_anim.setEndValue(end_rect)
        geo_anim.setEasingCurve(QEasingCurve.InCubic)

        op_anim = QPropertyAnimation(self, b"windowOpacity", self)
        op_anim.setDuration(170)
        op_anim.setStartValue(self.windowOpacity())
        op_anim.setEndValue(0.0)
        op_anim.setEasingCurve(QEasingCurve.InExpo)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(geo_anim)
        self._anim_group.addAnimation(op_anim)
        self._anim_group.finished.connect(lambda: self.done(self._pending_result))
        self._anim_group.start()

    def accept(self) -> None:  # noqa: N802
        self._start_exit_animation(QFileDialog.Accepted)

    def reject(self) -> None:  # noqa: N802
        self._start_exit_animation(QFileDialog.Rejected)


class ModalBackdrop(QWidget):
    """Dimmed backdrop for modal liquid-glass dialogs."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setGeometry(parent.rect())
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0.0)
        self._anim = QPropertyAnimation(self._opacity, b"opacity", self)
        self.setStyleSheet(
            """
            QWidget {
                background: qradialgradient(cx:0.5, cy:0.45, radius:0.9,
                                            stop:0 rgba(9, 14, 26, 48),
                                            stop:1 rgba(4, 8, 18, 156));
            }
            """
        )

    def show_animated(self) -> None:
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setDuration(140)
        self._anim.setStartValue(self._opacity.opacity())
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def hide_animated(self) -> None:
        self._anim.stop()
        self._anim.setDuration(120)
        self._anim.setStartValue(self._opacity.opacity())
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()


class GlassFrame(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setContentsMargins(0, 0, 0, 0)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(2, 2, -2, -2)
        rr = 20
        path = QPainterPath()
        path.addRoundedRect(QRectF(r), rr, rr)

        # dark translucent glass
        p.fillPath(path, QColor(30, 30, 30, 102))
        # subtle inner area
        inner = self.rect().adjusted(4, 4, -4, -4)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(QRectF(inner), rr - 2, rr - 2)
        p.fillPath(inner_path, QColor(44, 48, 58, 82))

        # bevel top / bottom
        p.setPen(QPen(QColor(255, 255, 255, 64), 1.5))
        p.drawLine(r.left() + rr, r.top() + 1, r.right() - rr, r.top() + 1)
        p.setPen(QPen(QColor(0, 0, 0, 50), 1.0))
        p.drawLine(r.left() + rr, r.bottom() - 1, r.right() - rr, r.bottom() - 1)

        # inner top glow
        glow = QRadialGradient(r.center().x(), r.top() + 4, max(80.0, r.width() * 0.4))
        glow.setColorAt(0.0, QColor(255, 255, 255, 34))
        glow.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(glow)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(r.center().x(), r.top() + 6), r.width() * 0.42, 42)


@dataclass
class BoardLayout:
    cell: int
    gap_h: int
    gap_v: int
    ox: int
    oy: int


@dataclass
class CellRipple:
    row: int
    col: int
    x: float
    y: float
    age: float
    duration: float


@dataclass
class ButtonRipple:
    x: float
    y: float
    age: float
    duration: float


class BoardWidget(QWidget):
    def __init__(self, owner: "FutoshikiQtWindow") -> None:
        super().__init__()
        self.owner = owner
        self.cell_boxes: Dict[Tuple[int, int], QRectF] = {}
        self.setMouseTracking(True)
        self._hover_cell: Optional[Tuple[int, int]] = None
        self._hover_scale = 1.0
        self._press_cell: Optional[Tuple[int, int]] = None
        self._press_scale = 1.0
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(140)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover_scale)
        self._press_anim = QVariantAnimation(self)
        self._press_anim.setDuration(120)
        self._press_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._press_anim.valueChanged.connect(self._on_press_scale)
        self._phase = 0.0
        self._last_tick = time.perf_counter()
        self._ripples: List[CellRipple] = []
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_anim)
        self._anim_timer.start(16)
        self.setMinimumSize(360, 360)

    def _tick_anim(self) -> None:
        now = time.perf_counter()
        dt = max(0.0, min(0.05, now - self._last_tick))
        self._last_tick = now
        # Time-based phase progression avoids visible cadence reset.
        self._phase += dt * 1.55
        keep: List[CellRipple] = []
        for rp in self._ripples:
            rp.age += dt
            if rp.age < rp.duration:
                keep.append(rp)
        self._ripples = keep
        # Crystal shimmer now runs continuously for all cells.
        self.update()

    def _calc_layout(self, n: int) -> BoardLayout:
        w = max(40, self.width())
        h = max(40, self.height())
        gap_h = max(18, min(30, w // max(8, n * 3)))
        gap_v = max(16, min(28, h // max(8, n * 3)))
        cell = max(28, min(64, min((w - (n - 1) * gap_h - 24) // n, (h - (n - 1) * gap_v - 24) // n)))
        row_w = n * cell + (n - 1) * gap_h
        col_h = n * cell + (n - 1) * gap_v
        return BoardLayout(cell, gap_h, gap_v, (w - row_w) // 2, (h - col_h) // 2)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(16, 20, 28, 70))
        self.cell_boxes.clear()
        if self.owner.puzzle is None or self.owner.display_grid is None:
            p.setPen(QColor("#9DB0CF"))
            p.setFont(QFont("Inter", 12))
            p.drawText(self.rect(), Qt.AlignCenter, "Load an input file to begin")
            return

        puzzle = self.owner.puzzle
        grid = self.owner.display_grid
        n = puzzle.n
        lay = self._calc_layout(n)

        for i in range(n):
            y0 = lay.oy + i * (lay.cell + lay.gap_v)
            x = lay.ox
            for j in range(n):
                if j > 0:
                    rel = puzzle.hcons[i][j - 1]
                    if rel != 0:
                        conf = self.owner.pair_conflict_h(i, j - 1)
                        self._draw_h_arrow(p, x + lay.gap_h // 2, y0 + lay.cell // 2, lay.gap_h, rel, conf, i, j - 1)
                    x += lay.gap_h

                val = grid[i][j]
                if val == 0:
                    fill = QColor("#2A3040")
                    rim = QColor("#3E4A65")
                    txt = QColor("#9CB0D0")
                    text = ""
                    state = "empty"
                elif puzzle.grid[i][j] != 0:
                    fill = QColor("#0A84FF")
                    rim = QColor("#68B8FF")
                    txt = QColor("#FFFFFF")
                    text = str(val)
                    state = "clue"
                elif self.owner.has_conflict(i, j, val):
                    fill = QColor("#FF453A")
                    rim = QColor("#FF7A73")
                    txt = QColor("#FFFFFF")
                    text = str(val)
                    state = "conflict"
                else:
                    fill = QColor("#25364F")
                    rim = QColor("#3D5A83")
                    txt = QColor("#5FB2FF")
                    text = str(val)
                    state = "solved"

                r = QRectF(x, y0, lay.cell, lay.cell)
                draw_r = r
                if self._hover_cell == (i, j):
                    draw_r = self._scaled_rect(draw_r, self._hover_scale)
                if self._press_cell == (i, j):
                    draw_r = self._scaled_rect(draw_r, self._press_scale)
                self._draw_cell(p, draw_r, fill, rim, state, i, j)
                if self.owner.selected_cell == (i, j):
                    pp = QPen(QColor("#FF9F0A"), 2.4)
                    p.setPen(pp)
                    p.setBrush(Qt.NoBrush)
                    p.drawRoundedRect(draw_r.adjusted(2, 2, -2, -2), 10, 10)
                if text:
                    p.setPen(txt)
                    p.setFont(QFont("Times New Roman", max(12, int(lay.cell * 0.40)), QFont.Bold))
                    p.drawText(draw_r, Qt.AlignCenter, text)
                self.cell_boxes[(i, j)] = r
                x += lay.cell

            if i < n - 1:
                ymid = y0 + lay.cell + lay.gap_v // 2
                for j in range(n):
                    rel = puzzle.vcons[i][j]
                    if rel == 0:
                        continue
                    conf = self.owner.pair_conflict_v(i, j)
                    xmid = lay.ox + j * (lay.cell + lay.gap_h) + lay.cell // 2
                    self._draw_v_arrow(p, xmid, ymid, lay.gap_v, rel, conf, i, j)

    def _draw_cell(self, p: QPainter, r: QRectF, fill: QColor, rim: QColor, state: str, row: int, col: int) -> None:
        rr = 10.0
        # Depth shadow
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRoundedRect(r.adjusted(2, 3, 2, 3), rr, rr)

        # Base glass body
        base = QLinearGradient(r.left(), r.top(), r.right(), r.bottom())
        base.setColorAt(0.0, fill.lighter(110))
        base.setColorAt(0.45, fill)
        base.setColorAt(1.0, fill.darker(120))
        p.setBrush(base)
        p.setPen(QPen(rim, 1.4))
        p.drawRoundedRect(r, rr, rr)

        # Clip inside for crystal/refraction overlays
        clip = QPainterPath()
        clip.addRoundedRect(r.adjusted(1, 1, -1, -1), rr - 1, rr - 1)
        p.save()
        p.setClipPath(clip)

        # Refraction diagonal band
        ref = QLinearGradient(r.left(), r.top(), r.right(), r.bottom())
        ref.setColorAt(0.0, QColor(255, 255, 255, 0))
        ref.setColorAt(0.38, QColor(255, 255, 255, 22))
        ref.setColorAt(0.56, QColor(255, 255, 255, 48 if state != "conflict" else 30))
        ref.setColorAt(0.72, QColor(255, 255, 255, 18))
        ref.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(r, ref)

        # Continuous crystal shimmer (hover no longer controls shimmer; only scale).
        phase_offset = (row * 0.73 + col * 0.41)
        sweep = (math.sin(self._phase * 1.55 + phase_offset) + 1.0) * 0.5
        x0 = r.left() - r.width() * 0.42 + sweep * r.width() * 1.45
        shimmer = QLinearGradient(x0, r.top(), x0 + r.width() * 0.42, r.bottom())
        shimmer_alpha = 30 if state != "conflict" else 20
        shimmer.setColorAt(0.0, QColor(255, 255, 255, 0))
        shimmer.setColorAt(0.5, QColor(255, 255, 255, shimmer_alpha))
        shimmer.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(r, shimmer)

        # Click ripple
        for rp in self._ripples:
            if rp.row != row or rp.col != col:
                continue
            t = max(0.0, min(1.0, rp.age / rp.duration))
            alpha = int((1.0 - t) * 72)
            rad = (0.18 + 0.86 * t) * max(r.width(), r.height())
            rg = QRadialGradient(QPointF(rp.x, rp.y), rad)
            rg.setColorAt(0.0, QColor(255, 255, 255, alpha))
            rg.setColorAt(0.5, QColor(180, 225, 255, int(alpha * 0.66)))
            rg.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(rg)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(rp.x, rp.y), rad, rad)

        p.restore()

        # Edge polish
        p.setPen(QPen(QColor(255, 255, 255, 76), 1.0))
        p.drawLine(r.left() + 10, r.top() + 2, r.right() - 10, r.top() + 2)
        p.setPen(QPen(QColor(0, 0, 0, 44), 1.0))
        p.drawLine(r.left() + 9, r.bottom() - 1, r.right() - 9, r.bottom() - 1)

    def _arrow_boost(self, cells: List[Tuple[int, int]]) -> float:
        boost = 0.0
        for rp in self._ripples:
            if (rp.row, rp.col) in cells:
                t = max(0.0, min(1.0, rp.age / rp.duration))
                boost = max(boost, 1.0 - t)
        return boost

    def _draw_h_arrow(self, p: QPainter, cx: int, cy: int, gap: int, rel: int, conflict: bool, i: int, j: int) -> None:
        boost = self._arrow_boost([(i, j), (i, j + 1)])
        col = QColor("#FF453A") if conflict else QColor("#8EA0C4")
        if boost > 0.0 and not conflict:
            col = col.lighter(int(100 + 40 * boost))
        sh = QColor(0, 0, 0, 90)
        w = max(7, int(gap * 0.30))
        h = max(9, int(gap * 0.42))
        sw = max(2, int(gap * 0.08))
        if rel == 1:  # <
            p1, p2, p3 = QPointF(cx + w / 2, cy - h / 2), QPointF(cx - w / 2, cy), QPointF(cx + w / 2, cy + h / 2)
        else:  # >
            p1, p2, p3 = QPointF(cx - w / 2, cy - h / 2), QPointF(cx + w / 2, cy), QPointF(cx - w / 2, cy + h / 2)
        sh_pen = QPen(sh, sw + 1)
        sh_pen.setCapStyle(Qt.RoundCap)
        sh_pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(sh_pen)
        p.drawLine(p1 + QPointF(1, 2), p2 + QPointF(1, 2))
        p.drawLine(p2 + QPointF(1, 2), p3 + QPointF(1, 2))
        fg_pen = QPen(col, sw)
        fg_pen.setCapStyle(Qt.RoundCap)
        fg_pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(fg_pen)
        p.drawLine(p1, p2)
        p.drawLine(p2, p3)
        if boost > 0.0:
            gl = QColor(180, 225, 255, int(80 * boost))
            p.setPen(QPen(gl, sw + 2))
            p.drawLine(p1, p2)
            p.drawLine(p2, p3)

    def _draw_v_arrow(self, p: QPainter, cx: int, cy: int, gap: int, rel: int, conflict: bool, i: int, j: int) -> None:
        boost = self._arrow_boost([(i, j), (i + 1, j)])
        col = QColor("#FF453A") if conflict else QColor("#8EA0C4")
        if boost > 0.0 and not conflict:
            col = col.lighter(int(100 + 40 * boost))
        sh = QColor(0, 0, 0, 90)
        w = max(9, int(gap * 0.42))
        h = max(7, int(gap * 0.30))
        sw = max(2, int(gap * 0.08))
        if rel == 1:  # v
            p1, p2, p3 = QPointF(cx - w / 2, cy - h / 2), QPointF(cx, cy + h / 2), QPointF(cx + w / 2, cy - h / 2)
        else:  # ^
            p1, p2, p3 = QPointF(cx - w / 2, cy + h / 2), QPointF(cx, cy - h / 2), QPointF(cx + w / 2, cy + h / 2)
        sh_pen = QPen(sh, sw + 1)
        sh_pen.setCapStyle(Qt.RoundCap)
        sh_pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(sh_pen)
        p.drawLine(p1 + QPointF(1, 2), p2 + QPointF(1, 2))
        p.drawLine(p2 + QPointF(1, 2), p3 + QPointF(1, 2))
        fg_pen = QPen(col, sw)
        fg_pen.setCapStyle(Qt.RoundCap)
        fg_pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(fg_pen)
        p.drawLine(p1, p2)
        p.drawLine(p2, p3)
        if boost > 0.0:
            gl = QColor(180, 225, 255, int(80 * boost))
            p.setPen(QPen(gl, sw + 2))
            p.drawLine(p1, p2)
            p.drawLine(p2, p3)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.owner.puzzle is None or self.owner.display_grid is None:
            return
        pos = event.position()
        for (i, j), r in self.cell_boxes.items():
            if r.contains(pos):
                self._press_cell = (i, j)
                self._press_anim.stop()
                self._press_anim.setStartValue(0.94)
                self._press_anim.setEndValue(1.0)
                self._press_anim.start()
                self._ripples.append(
                    CellRipple(
                        row=i,
                        col=j,
                        x=pos.x(),
                        y=pos.y(),
                        age=0.0,
                        duration=0.52,
                    )
                )
                self.owner.on_cell_clicked(i, j, event.globalPosition().toPoint())
                self.update()
                return

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        new_hover = None
        for cell, r in self.cell_boxes.items():
            if r.contains(pos):
                new_hover = cell
                break
        if new_hover != self._hover_cell:
            self._hover_cell = new_hover
            self._hover_anim.stop()
            self._hover_anim.setStartValue(self._hover_scale)
            self._hover_anim.setEndValue(1.05 if new_hover is not None else 1.0)
            self._hover_anim.start()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_cell = None
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_scale)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def _on_hover_scale(self, v: float) -> None:
        self._hover_scale = float(v)
        self.update()

    def _on_press_scale(self, v: float) -> None:
        self._press_scale = float(v)
        if abs(self._press_scale - 1.0) < 1e-3:
            self._press_cell = None
        self.update()

    def _scaled_rect(self, r: QRectF, scale: float) -> QRectF:
        cx, cy = r.center().x(), r.center().y()
        w = r.width() * scale
        h = r.height() * scale
        return QRectF(cx - w / 2, cy - h / 2, w, h)


class FutoshikiQtWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CSC14003 — Futoshiki Solver (PySide6)")
        self.resize(1340, 820)
        self.setMinimumSize(1100, 700)

        self.puzzle: Optional[Puzzle] = None
        self.last_grid: Optional[List[List[int]]] = None
        self.last_trace: List[Tuple[str, int, int, int]] = []
        self.display_grid: Optional[List[List[int]]] = None
        self.selected_cell: Optional[Tuple[int, int]] = None
        self.step_i = 0
        self.step_order: List[Tuple[int, int]] = []

        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._auto_tick)
        self.auto_interval_ms = 180
        self.auto_play = False

        self.metric_cells = QLabel("—")
        self.metric_steps = QLabel("—")
        self.metric_time = QLabel("—")
        self.metric_nodes = QLabel("—")
        self.metric_valid = QLabel("—")

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        bg = MeshBackground()
        self.setCentralWidget(bg)
        root = QVBoxLayout(bg)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(10)

        title = QLabel("Futoshiki  ·  Logic Solver  ·  CSC14003 AI Project")
        title.setObjectName("title")
        root.addWidget(title)

        body = QGridLayout()
        body.setHorizontalSpacing(12)
        body.setVerticalSpacing(0)
        root.addLayout(body, 1)

        self.left = GlassFrame()
        self.mid = GlassFrame()
        self.right = GlassFrame()
        body.addWidget(self.left, 0, 0, 1, 1)
        body.addWidget(self.mid, 0, 1, 1, 1)
        body.addWidget(self.right, 0, 2, 1, 1)
        body.setColumnStretch(0, 7)
        body.setColumnStretch(1, 4)
        body.setColumnStretch(2, 5)

        # Left panel
        lv = QVBoxLayout(self.left)
        lv.setContentsMargins(14, 14, 14, 12)
        self.board = BoardWidget(self)
        lv.addWidget(self.board, 1)
        leg = QLabel(
            '<span style="color:#5FB2FF;font-weight:600">●</span> Blue=clue&nbsp;&nbsp;'
            '<span style="color:#D7E6FF;font-weight:600">●</span> Light=solved&nbsp;&nbsp;'
            '<span style="color:#FF6E66;font-weight:600">●</span> Red=conflict'
        )
        leg.setObjectName("legend")
        lv.addWidget(leg)

        # Mid panel
        mv = QVBoxLayout(self.mid)
        mv.setContentsMargins(14, 14, 14, 14)
        self.size_label = QLabel("—")
        mv.addWidget(QLabel("Puzzle Size"))
        mv.addWidget(self.size_label)
        mv.addWidget(QLabel("Click Mode"))
        self.click_mode = QComboBox()
        self.click_mode.addItems(["cycle", "selector"])
        mv.addWidget(self.click_mode)
        mv.addWidget(QLabel("Solver Algorithm"))

        self.algo_group = QButtonGroup(self)
        for key, label in ALGOS:
            rb = QRadioButton(label)
            if key == "astar":
                rb.setChecked(True)
            rb.setProperty("algo_key", key)
            self.algo_group.addButton(rb)
            mv.addWidget(rb)
        mv.addStretch(1)

        self.btn_load = LiquidButton("Load Input File")
        self.btn_solve = LiquidButton("Solve Puzzle")
        self.btn_auto = LiquidButton("Auto Replay")
        self.btn_save = LiquidButton("Save Solution")
        for b in (self.btn_load, self.btn_solve, self.btn_auto, self.btn_save):
            mv.addWidget(b)
        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        mv.addWidget(self.path_label)

        self.btn_load.clicked.connect(self.load_file)
        self.btn_solve.clicked.connect(self.do_solve)
        self.btn_auto.clicked.connect(self.toggle_auto_play)
        self.btn_save.clicked.connect(self.do_save)

        # Right panel
        rv = QVBoxLayout(self.right)
        rv.setContentsMargins(14, 14, 14, 14)
        rv.addWidget(QLabel("Algorithm Details"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        rv.addWidget(self.log_box, 1)

        metrics = QWidget()
        mg = QGridLayout(metrics)
        mg.setContentsMargins(10, 10, 10, 10)
        rows = [
            ("Total Cells Assigned", self.metric_cells),
            ("Solution Steps", self.metric_steps),
            ("Execution Time", self.metric_time),
            ("Nodes Expanded", self.metric_nodes),
            ("Solution Valid", self.metric_valid),
        ]
        for i, (k, v) in enumerate(rows):
            mg.addWidget(QLabel(k), i, 0)
            mg.addWidget(v, i, 1, alignment=Qt.AlignRight)
        rv.addWidget(metrics)
        metrics.setObjectName("metricsCard")

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QLabel#title { color: #F2F6FF; font: 700 26px 'Inter'; }
            QLabel#legend { color: #9BB0D4; font: 12px 'Inter'; }
            QLabel { color: #C0CAE3; font: 13px 'Inter'; }
            QRadioButton { color: #D6E1FA; spacing: 8px; }
            QRadioButton::indicator { width: 12px; height: 12px; }
            QRadioButton::indicator:unchecked { border: 1px solid #7382A5; border-radius: 6px; background: #1D2230; }
            QRadioButton::indicator:checked { border: 1px solid #62B5FF; border-radius: 6px; background: #0A84FF; }
            QComboBox {
                background: rgba(36,40,51,180);
                color: #EAF2FF;
                border: 1px solid rgba(115,130,165,140);
                border-radius: 12px;
                padding: 6px 10px;
            }
            QTextEdit {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                                            stop:0 rgba(33,45,72,86),
                                            stop:1 rgba(21,30,50,78));
                color: #EAF2FF;
                border: 1px solid rgba(145,178,230,138);
                border-radius: 14px;
                selection-background-color: rgba(77,163,255,120);
            }
            QWidget#metricsCard {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                                            stop:0 rgba(40,52,78,88),
                                            stop:1 rgba(27,36,56,78));
                border: 1px solid rgba(145,178,230,128);
                border-radius: 14px;
            }
            QPushButton {
                color: #FFFFFF;
                border: 1px solid rgba(180,210,255,120);
                border-radius: 11px;
                padding: 8px 12px;
                background-color: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                                                  stop:0 rgba(130,204,255,248),
                                                  stop:0.45 rgba(88,164,238,244),
                                                  stop:1 rgba(14,84,162,242));
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                                                  stop:0 rgba(164,224,255,255),
                                                  stop:0.45 rgba(113,190,255,255),
                                                  stop:1 rgba(33,126,226,255));
                border-color: rgba(225,242,255,220);
            }
            QPushButton:pressed {
                padding-top: 8px;
                padding-bottom: 8px;
                background-color: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                                                  stop:0 rgba(102,169,230,255),
                                                  stop:1 rgba(10,70,136,255));
            }
            """
        )

    def selected_algo(self) -> str:
        btn = self.algo_group.checkedButton()
        if btn is None:
            return "astar"
        return btn.property("algo_key")

    def log(self, text: str) -> None:
        self.log_box.append(text)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def _set_metrics(self, steps: int, runtime: float, nodes: int, valid: str) -> None:
        self.metric_steps.setText(str(steps))
        self.metric_time.setText(f"{runtime:.4f}s")
        self.metric_nodes.setText(str(nodes))
        self.metric_valid.setText(valid)

    def _refresh_status(self) -> None:
        if self.puzzle is None or self.display_grid is None:
            return
        n = self.puzzle.n
        total = n * n
        filled = sum(1 for i in range(n) for j in range(n) if self.display_grid[i][j] != 0)
        self.metric_cells.setText(f"{filled}/{total}" + (" (Completed)" if filled == total else ""))
        if filled < total:
            self.metric_valid.setText("In progress")
        else:
            self.metric_valid.setText("✓ YES" if is_valid_solution(self.puzzle, self.display_grid) else "✗ NO")

    def has_conflict(self, i: int, j: int, v: int) -> bool:
        if v == 0 or self.puzzle is None or self.display_grid is None:
            return False
        p, g, n = self.puzzle, self.display_grid, self.puzzle.n
        for jj in range(n):
            if jj != j and g[i][jj] == v:
                return True
        for ii in range(n):
            if ii != i and g[ii][j] == v:
                return True
        if j < n - 1 and p.hcons[i][j] and g[i][j + 1] and not inequality_ok(v, g[i][j + 1], p.hcons[i][j]):
            return True
        if j > 0 and p.hcons[i][j - 1] and g[i][j - 1] and not inequality_ok(g[i][j - 1], v, p.hcons[i][j - 1]):
            return True
        if i < n - 1 and p.vcons[i][j] and g[i + 1][j] and not inequality_ok(v, g[i + 1][j], p.vcons[i][j]):
            return True
        if i > 0 and p.vcons[i - 1][j] and g[i - 1][j] and not inequality_ok(g[i - 1][j], v, p.vcons[i - 1][j]):
            return True
        return False

    def pair_conflict_h(self, i: int, j: int) -> bool:
        if self.puzzle is None or self.display_grid is None:
            return False
        rel = self.puzzle.hcons[i][j]
        if not rel:
            return False
        a, b = self.display_grid[i][j], self.display_grid[i][j + 1]
        if a != 0 and b != 0 and not inequality_ok(a, b, rel):
            return True
        if a != 0 and self.has_conflict(i, j, a):
            return True
        if b != 0 and self.has_conflict(i, j + 1, b):
            return True
        return False

    def pair_conflict_v(self, i: int, j: int) -> bool:
        if self.puzzle is None or self.display_grid is None:
            return False
        rel = self.puzzle.vcons[i][j]
        if not rel:
            return False
        a, b = self.display_grid[i][j], self.display_grid[i + 1][j]
        if a != 0 and b != 0 and not inequality_ok(a, b, rel):
            return True
        if a != 0 and self.has_conflict(i, j, a):
            return True
        if b != 0 and self.has_conflict(i + 1, j, b):
            return True
        return False

    def on_cell_clicked(self, i: int, j: int, global_pos) -> None:
        if self.puzzle is None or self.display_grid is None:
            return
        if self.puzzle.grid[i][j] != 0:
            self.selected_cell = None
            self.board.update()
            return
        self.selected_cell = (i, j)
        if self.click_mode.currentText() == "selector":
            menu = QMenu(self)
            for val in range(self.puzzle.n + 1):
                txt = "—" if val == 0 else str(val)
                act = QAction(txt, self)
                act.triggered.connect(lambda checked=False, v=val: self._set_cell_value(i, j, v))
                menu.addAction(act)
            menu.exec(global_pos)
        else:
            n = self.puzzle.n
            self.display_grid[i][j] = (self.display_grid[i][j] + 1) % (n + 1)
            self._refresh_status()
            self.board.update()

    def _set_cell_value(self, i: int, j: int, v: int) -> None:
        if self.display_grid is None:
            return
        self.display_grid[i][j] = v
        self._refresh_status()
        self.board.update()

    def load_file(self) -> None:
        source_dir = os.path.dirname(os.path.abspath(__file__))
        default_dir = os.path.normpath(os.path.join(source_dir, "..", "inputs"))
        if not os.path.isdir(default_dir):
            default_dir = source_dir
        backdrop = ModalBackdrop(self)
        backdrop.show_animated()
        dlg = AnimatedFileDialog(self, start_dir=default_dir)
        result = dlg.exec()
        backdrop.hide_animated()
        if result != QFileDialog.Accepted:
            return
        files = dlg.selectedFiles()
        path = files[0] if files else ""
        if not path:
            return
        try:
            self.puzzle = read_input(path)
            self.last_grid = None
            self.last_trace = []
            self.display_grid = [row[:] for row in self.puzzle.grid]
            self.step_i = 0
            self.step_order = []
            self.size_label.setText(f"{self.puzzle.n}×{self.puzzle.n}")
            self.path_label.setText(path.split("/")[-1].split("\\")[-1])
            self._set_metrics(0, 0.0, 0, "In progress")
            self.log_box.clear()
            self.log(f"✦ Loaded n={self.puzzle.n} ({path})")
            self._refresh_status()
            self.board.update()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Load error", str(exc))

    def do_solve(self) -> None:
        if self.puzzle is None:
            QMessageBox.warning(self, "Solve", "Load a puzzle first.")
            return
        self._stop_auto()
        algo = self.selected_algo()
        self.log(f"⚙ Running: {algo} ...")
        r = solve(self.puzzle, algo)
        for line in r.messages:
            self.log("  " + line)
        n, total = self.puzzle.n, self.puzzle.n * self.puzzle.n
        solve_steps = len(r.trace)
        if r.solved_grid is None or r.contradiction:
            self.last_grid = None
            self.last_trace = []
            self.display_grid = [row[:] for row in self.puzzle.grid]
            filled = sum(1 for i in range(n) for j in range(n) if self.display_grid[i][j] != 0)
            self.metric_cells.setText(f"{filled}/{total}")
            self._set_metrics(solve_steps, r.runtime_sec, r.nodes_expanded, "✗ NO")
            self.log("✗ No solution found.")
        else:
            self.last_grid = r.solved_grid
            self.last_trace = list(r.trace)
            self.display_grid = [row[:] for row in r.solved_grid]
            self.metric_cells.setText(f"{total}/{total} (Completed)")
            if solve_steps == 0:
                solve_steps = sum(1 for i in range(n) for j in range(n) if self.puzzle.grid[i][j] == 0)
            self._set_metrics(solve_steps, r.runtime_sec, r.nodes_expanded, "✓ YES")
            steps = len(self.last_trace) if self.last_trace else solve_steps
            self.auto_interval_ms = 16 if steps > 300 else 40 if steps > 100 else 160
            self.log(f"✓ Solved — replay {steps} steps @ {self.auto_interval_ms}ms/step")
        self.step_i = 0
        self.step_order = []
        self.board.update()

    def _step_trace(self) -> bool:
        if self.puzzle is None:
            return False
        if self.last_trace:
            total = len(self.last_trace)
            if self.step_i == 0:
                self.display_grid = [row[:] for row in self.puzzle.grid]
                self._refresh_status()
                self.log(f"▶ Replay started ({total} trace steps)")
            if self.step_i >= total:
                if self.last_grid is not None:
                    self.display_grid = [row[:] for row in self.last_grid]
                    self._refresh_status()
                self.log("■ Replay complete")
                self.board.update()
                return False
            action, i, j, v = self.last_trace[self.step_i]
            k = self.step_i + 1
            if self.display_grid is not None:
                if action in {"set", "propagate", "commit"}:
                    self.display_grid[i][j] = v
                elif action == "unset" and self.puzzle.grid[i][j] == 0:
                    self.display_grid[i][j] = 0
            if action == "set":
                self.log(f"[{k}/{total}] Try ({i + 1},{j + 1}) = {v}")
            elif action == "propagate":
                self.log(f"[{k}/{total}] Propagate ({i + 1},{j + 1}) = {v}")
            elif action == "commit":
                self.log(f"[{k}/{total}] Commit ({i + 1},{j + 1}) = {v}")
            elif action == "unset":
                self.log(f"[{k}/{total}] Backtrack ({i + 1},{j + 1})")
            elif action == "reject":
                self.log(f"[{k}/{total}] Reject ({i + 1},{j + 1}) = {v}")
            else:
                self.log(f"[{k}/{total}] {action} ({i + 1},{j + 1}) = {v}")
            self.step_i += 1
            self._refresh_status()
            self.board.update()
            return True
        return self._step_final_reveal()

    def _step_final_reveal(self) -> bool:
        if self.puzzle is None or self.last_grid is None:
            return False
        if not self.step_order:
            n = self.puzzle.n
            self.step_order = [(i, j) for i in range(n) for j in range(n) if self.puzzle.grid[i][j] == 0]
            self.step_i = 0
            self.display_grid = [row[:] for row in self.puzzle.grid]
            self._refresh_status()
            self.log(f"▶ Replay started ({len(self.step_order)} reveal steps)")
        if self.step_i >= len(self.step_order):
            self.log("■ Replay complete")
            self.board.update()
            return False
        i, j = self.step_order[self.step_i]
        if self.display_grid is not None:
            self.display_grid[i][j] = self.last_grid[i][j]
        self.log(f"[{self.step_i + 1}/{len(self.step_order)}] Reveal ({i + 1},{j + 1}) = {self.last_grid[i][j]}")
        self.step_i += 1
        self._refresh_status()
        self.board.update()
        return True

    def _auto_tick(self) -> None:
        if not self.auto_play:
            return
        if not self._step_trace():
            self._stop_auto()

    def _stop_auto(self) -> None:
        self.auto_play = False
        self.auto_timer.stop()
        self.btn_auto.setText("Auto Replay")

    def toggle_auto_play(self) -> None:
        if self.puzzle is None:
            QMessageBox.warning(self, "Auto", "Load a puzzle first.")
            return
        if self.last_grid is None and not self.last_trace:
            QMessageBox.information(self, "Auto", "Solve first, then replay.")
            return
        if self.auto_play:
            self._stop_auto()
            self.log("⏸ Replay paused")
        else:
            self.auto_play = True
            self.btn_auto.setText("Pause Auto")
            self.log("▶ Auto replay ON")
            self.auto_timer.start(self.auto_interval_ms)

    def do_save(self) -> None:
        if self.puzzle is None or self.last_grid is None:
            QMessageBox.warning(self, "Save", "Solve successfully first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Solution", "", "Text Files (*.txt);;All Files (*)")
        if path:
            write_output(path, self.puzzle, self.last_grid)
            QMessageBox.information(self, "Saved", path)


def main() -> None:
    app = QApplication.instance() or QApplication([])
    win = FutoshikiQtWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()

