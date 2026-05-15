from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "shop" / "items"
SIZE = 1024
CANVAS = 512
SCALE = SIZE / CANVAS


def draw_background(painter, top, bottom):
    return


def draw_shadow(painter, x, y, w, h, alpha=70):
    painter.setPen(Qt.NoPen)
    for index in range(6, 0, -1):
        pad = index * 8
        painter.setBrush(QColor(0, 0, 0, max(8, alpha // (index + 1))))
        painter.drawEllipse(QRectF(x - pad, y - pad * 0.25, w + pad * 2, h + pad * 0.5))


def draw_fish(painter):
    draw_background(painter, "#0e3344", "#12221f")
    draw_shadow(painter, 128, 356, 260, 42)

    body = QPainterPath()
    body.moveTo(112, 256)
    body.cubicTo(160, 154, 314, 148, 392, 244)
    body.cubicTo(312, 344, 164, 354, 112, 256)
    painter.translate(12, 16)
    painter.setBrush(QColor("#234a53"))
    painter.setPen(Qt.NoPen)
    painter.drawPath(body)
    painter.translate(-12, -16)
    fish_gradient = QLinearGradient(120, 164, 390, 336)
    fish_gradient.setColorAt(0.0, QColor("#f3f8f6"))
    fish_gradient.setColorAt(0.55, QColor("#a9d8e1"))
    fish_gradient.setColorAt(1.0, QColor("#456d7f"))
    painter.setBrush(fish_gradient)
    painter.setPen(QPen(QColor("#d8f2f4"), 5))
    painter.drawPath(body)

    tail = QPainterPath()
    tail.moveTo(118, 256)
    tail.lineTo(54, 194)
    tail.cubicTo(78, 246, 78, 270, 54, 322)
    tail.closeSubpath()
    painter.translate(12, 16)
    painter.setBrush(QColor("#234a53"))
    painter.setPen(Qt.NoPen)
    painter.drawPath(tail)
    painter.translate(-12, -16)
    painter.setBrush(QColor("#79b8c7"))
    painter.setPen(QPen(QColor("#d8f2f4"), 4))
    painter.drawPath(tail)

    painter.setBrush(QColor("#0a1518"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QRectF(330, 222, 26, 26))
    painter.setBrush(QColor("#ffffff"))
    painter.drawEllipse(QRectF(337, 226, 8, 8))

    painter.setPen(QPen(QColor(255, 255, 255, 120), 3))
    for x in (188, 226, 264):
        painter.drawArc(QRectF(x, 212, 32, 74), 80 * 16, 170 * 16)
    painter.setPen(QPen(QColor("#ffffff"), 8))
    painter.drawArc(QRectF(182, 178, 166, 96), 42 * 16, 104 * 16)


def draw_milk(painter):
    draw_background(painter, "#173041", "#101a1b")
    draw_shadow(painter, 142, 374, 228, 38)

    side = QPainterPath()
    side.addRoundedRect(QRectF(244, 154, 112, 236), 28, 28)
    painter.setBrush(QColor("#b8d9dc"))
    painter.setPen(Qt.NoPen)
    painter.drawPath(side)

    bottle = QPainterPath()
    bottle.addRoundedRect(QRectF(164, 144, 184, 246), 32, 32)
    painter.setBrush(QColor("#eef8f4"))
    painter.setPen(QPen(QColor("#c7e3e5"), 5))
    painter.drawPath(bottle)

    neck = QPainterPath()
    neck.addRoundedRect(QRectF(206, 88, 100, 86), 18, 18)
    painter.setBrush(QColor("#f7fffb"))
    painter.drawPath(neck)

    cap = QPainterPath()
    cap.addRoundedRect(QRectF(196, 76, 120, 28), 10, 10)
    painter.setBrush(QColor("#d8b45c"))
    painter.setPen(QPen(QColor("#ffe8a6"), 3))
    painter.drawPath(cap)

    label = QPainterPath()
    label.addRoundedRect(QRectF(184, 226, 144, 92), 22, 22)
    painter.setBrush(QColor("#16313a"))
    painter.setPen(QPen(QColor("#8bdcca"), 4))
    painter.drawPath(label)
    painter.setPen(QColor("#f4d57f"))
    painter.setFont(QFont("Arial", 34, QFont.Black))
    painter.drawText(QRectF(184, 236, 144, 58), Qt.AlignCenter, "MILK")
    painter.setPen(QPen(QColor(255, 255, 255, 110), 8))
    painter.drawLine(202, 162, 202, 352)
    painter.setPen(QPen(QColor("#9abcc1"), 4))
    painter.drawLine(314, 174, 314, 374)


def draw_cake(painter):
    draw_background(painter, "#2f1d2e", "#171316")
    draw_shadow(painter, 116, 366, 284, 44)

    side = QPainterPath()
    side.addRoundedRect(QRectF(138, 270, 276, 116), 26, 26)
    painter.setBrush(QColor("#7b503b"))
    painter.setPen(Qt.NoPen)
    painter.drawPath(side)

    base = QPainterPath()
    base.addRoundedRect(QRectF(118, 224, 276, 140), 30, 30)
    cake_gradient = QLinearGradient(118, 224, 394, 364)
    cake_gradient.setColorAt(0.0, QColor("#f1d1a9"))
    cake_gradient.setColorAt(1.0, QColor("#a36f4c"))
    painter.setBrush(cake_gradient)
    painter.setPen(QPen(QColor("#ffe1b8"), 4))
    painter.drawPath(base)

    cream = QPainterPath()
    cream.moveTo(128, 226)
    cream.cubicTo(168, 184, 228, 196, 256, 166)
    cream.cubicTo(292, 198, 352, 184, 386, 226)
    cream.lineTo(128, 226)
    cream.closeSubpath()
    painter.setBrush(QColor("#fff5dc"))
    painter.setPen(QPen(QColor("#ffffff"), 4))
    painter.drawPath(cream)

    painter.setBrush(QColor("#3752a5"))
    painter.setPen(QPen(QColor("#bdccff"), 3))
    for x, y, s in [(176, 196, 28), (236, 174, 34), (312, 196, 30), (274, 216, 22)]:
        painter.drawEllipse(QRectF(x, y, s, s))

    painter.setPen(QPen(QColor("#653823"), 7))
    painter.drawLine(142, 286, 380, 286)
    painter.setPen(QPen(QColor(255, 255, 255, 88), 5))
    painter.drawLine(150, 244, 352, 244)
    painter.setPen(QPen(QColor("#7a422a"), 4))
    for x in (192, 244, 306, 352):
        painter.drawLine(x, 296, x - 16, 350)


def draw_snowball(painter):
    draw_background(painter, "#173747", "#0e181a")
    draw_shadow(painter, 132, 360, 248, 46)

    for i, (x, y, s, a) in enumerate([(140, 160, 226, 255), (105, 236, 150, 230), (276, 250, 128, 220)]):
        gradient = QRadialGradient(QPointF(x + s * 0.32, y + s * 0.28), s * 0.68)
        gradient.setColorAt(0.0, QColor(255, 255, 255, a))
        gradient.setColorAt(1.0, QColor(124, 188, 204, 220))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#eaffff"), 4))
        painter.drawEllipse(QRectF(x, y, s, s))

    painter.setPen(QPen(QColor(255, 255, 255, 126), 5))
    painter.drawArc(QRectF(178, 198, 132, 92), 38 * 16, 118 * 16)
    painter.setPen(QPen(QColor("#78b6c4"), 3))
    painter.drawArc(QRectF(316, 286, 74, 52), 40 * 16, 110 * 16)


def draw_scarf(painter):
    draw_background(painter, "#2d2430", "#11191b")
    draw_shadow(painter, 118, 362, 276, 42)

    back = QPainterPath()
    back.addRoundedRect(QRectF(102, 208, 328, 86), 36, 36)
    painter.setBrush(QColor("#81232c"))
    painter.setPen(Qt.NoPen)
    painter.drawPath(back)

    scarf = QPainterPath()
    scarf.addRoundedRect(QRectF(92, 190, 328, 86), 36, 36)
    painter.setBrush(QColor("#d34840"))
    painter.setPen(QPen(QColor("#ffb0a6"), 5))
    painter.drawPath(scarf)

    fold = QPainterPath()
    fold.addRoundedRect(QRectF(236, 164, 78, 210), 32, 32)
    painter.setBrush(QColor("#b63234"))
    painter.setPen(QPen(QColor("#ffb0a6"), 4))
    painter.drawPath(fold)

    painter.setPen(QPen(QColor("#f4d57f"), 8))
    for x in (136, 198, 342):
        painter.drawLine(x, 198, x + 42, 266)
    painter.setPen(QPen(QColor("#7e1f28"), 5))
    for y in (208, 252, 330):
        painter.drawLine(252, y, 300, y + 10)

    painter.setPen(QPen(QColor("#d34840"), 8))
    for x in (250, 270, 290):
        painter.drawLine(x, 374, x - 10, 410)
    painter.setPen(QPen(QColor(255, 255, 255, 70), 5))
    painter.drawLine(128, 210, 368, 232)


def draw_ice(painter):
    draw_background(painter, "#123342", "#10171a")
    draw_shadow(painter, 128, 372, 256, 40)

    cube = QPainterPath()
    cube.moveTo(150, 178)
    cube.lineTo(286, 128)
    cube.lineTo(392, 224)
    cube.lineTo(354, 360)
    cube.lineTo(196, 384)
    cube.lineTo(116, 270)
    cube.closeSubpath()
    gradient = QLinearGradient(116, 128, 392, 384)
    gradient.setColorAt(0.0, QColor("#f1ffff"))
    gradient.setColorAt(0.45, QColor("#95d7e9"))
    gradient.setColorAt(1.0, QColor("#316b82"))
    painter.setBrush(gradient)
    painter.setPen(QPen(QColor("#eaffff"), 5))
    painter.drawPath(cube)

    painter.setPen(QPen(QColor(255, 255, 255, 96), 4))
    painter.drawLine(150, 178, 236, 294)
    painter.drawLine(286, 128, 236, 294)
    painter.drawLine(392, 224, 236, 294)
    painter.drawLine(196, 384, 236, 294)

    painter.setPen(QPen(QColor("#ffffff"), 8))
    painter.drawLine(202, 196, 268, 172)
    painter.drawLine(152, 266, 184, 314)
    painter.setBrush(QColor(255, 255, 255, 46))
    painter.setPen(Qt.NoPen)
    painter.drawPolygon([QPointF(236, 294), QPointF(392, 224), QPointF(354, 360), QPointF(196, 384)])


DRAWERS = {
    "fish": draw_fish,
    "milk": draw_milk,
    "berry_cake": draw_cake,
    "snowball": draw_snowball,
    "scarf": draw_scarf,
    "ice": draw_ice,
}


def save_icon(name, drawer):
    image = QImage(SIZE, SIZE, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.scale(SCALE, SCALE)
    drawer(painter)
    painter.end()
    image.save(str(OUT_DIR / f"{name}.png"))


def main():
    app = QApplication.instance() or QApplication([])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, drawer in DRAWERS.items():
        save_icon(name, drawer)
    print(f"generated {len(DRAWERS)} shop item assets in {OUT_DIR}")
    app.quit()


if __name__ == "__main__":
    main()
