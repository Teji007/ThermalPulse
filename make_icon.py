import os
import struct
import sys

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

SIZES = [16, 24, 32, 48, 64, 128, 256]


def render_icon_png(size: int) -> bytes:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)
    m = s * 0.06

    bg_rect = QRectF(m, m, s - 2 * m, s - 2 * m)
    bg = QLinearGradient(0, 0, s, s)
    bg.setColorAt(0.0, QColor("#181d28"))
    bg.setColorAt(1.0, QColor("#090b10"))
    p.setBrush(bg)
    p.setPen(QPen(QColor("#ef4444"), max(1.2, s * 0.045)))
    p.drawRoundedRect(bg_rect, s * 0.22, s * 0.22)

    ring_m = s * 0.19
    ring_rect = QRectF(ring_m, ring_m, s - 2 * ring_m, s - 2 * ring_m)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor("#f97316"), max(1.2, s * 0.055), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawArc(ring_rect, 35 * 16, 125 * 16)
    p.drawArc(ring_rect, 215 * 16, 125 * 16)

    cx, cy = s / 2.0, s / 2.0
    bolt = QPainterPath()
    bolt.moveTo(cx + s * 0.05, cy - s * 0.24)
    bolt.lineTo(cx - s * 0.16, cy + s * 0.03)
    bolt.lineTo(cx - s * 0.02, cy + s * 0.03)
    bolt.lineTo(cx - s * 0.07, cy + s * 0.24)
    bolt.lineTo(cx + s * 0.16, cy - s * 0.03)
    bolt.lineTo(cx + s * 0.02, cy - s * 0.03)
    bolt.closeSubpath()

    grad = QLinearGradient(0, cy - s * 0.24, 0, cy + s * 0.24)
    grad.setColorAt(0.0, QColor("#fff7ed"))
    grad.setColorAt(0.5, QColor("#fb923c"))
    grad.setColorAt(1.0, QColor("#ef4444"))
    p.setBrush(grad)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPath(bolt)
    p.end()

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pix.save(buf, "PNG")
    return bytes(buf.data())


def build_ico(out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    images = [(sz, render_icon_png(sz)) for sz in SIZES]

    header = struct.pack("<HHH", 0, 1, len(images))
    entries = bytearray()
    offset = 6 + 16 * len(images)

    for sz, png in images:
        dim = 0 if sz >= 256 else sz
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        offset += len(png)

    with open(out_path, "wb") as f:
        f.write(header)
        f.write(entries)
        for _, png in images:
            f.write(png)
    print(f"Generated {out_path} ({len(images)} sizes)")


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    build_ico(os.path.join("assets", "app.ico"))