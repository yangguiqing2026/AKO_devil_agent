"""
AKO_devil_agent 任务栏图标
Windows 任务栏常驻，非系统托盘
技术：PyQt6 无边框置顶窗口 + Windows API 定位
"""
import sys
import subprocess
import ctypes
from ctypes import wintypes
from pathlib import Path
import config

from PyQt6.QtCore import Qt, QTimer, QPoint, QSize, QPointF
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QAction,
    QPen, QBrush, QPainterPath, QPolygonF
)
from PyQt6.QtWidgets import QApplication, QWidget, QMenu, QLabel

# ====== Windows API 常量 ======
NULL = 0
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
LWA_ALPHA = 0x00000002
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

ABM_GETTASKBARPOS = 0x00000005
ABE_BOTTOM = 3

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

# ====== Windows API 封装 ======

class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", wintypes.RECT),
        ("lParam", wintypes.LPARAM),
    ]

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]

def get_taskbar_info() -> dict:
    abd = APPBARDATA()
    abd.cbSize = ctypes.sizeof(APPBARDATA)
    abd.hWnd = user32.FindWindowW("Shell_TrayWnd", None)
    result = shell32.SHAppBarMessage(ABM_GETTASKBARPOS, ctypes.byref(abd))
    if result:
        return {
            "left": abd.rc.left, "top": abd.rc.top,
            "right": abd.rc.right, "bottom": abd.rc.bottom,
            "width": abd.rc.right - abd.rc.left,
            "height": abd.rc.bottom - abd.rc.top,
            "edge": abd.uEdge,
        }
    return {"left": 0, "top": 1000, "right": 1920, "bottom": 1080,
            "width": 1920, "height": 80, "edge": ABE_BOTTOM}

def set_window_ex_style(hwnd: int, style: int) -> int:
    return user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

def get_window_ex_style(hwnd: int) -> int:
    return user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

def set_window_pos_topmost(hwnd: int):
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                       SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


# ====== 图标生成器 ======
def generate_icon_pixmap(size: int = 48) -> QPixmap:
    """在内存中绘制 devil_eye 图标（等腰三角形版），不依赖 SVG"""

    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#0a0a0f"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gold = QColor("#c4a35a")

    # Scale to fit
    sx = size / 512.0
    sy = size / 520.0
    s = min(sx, sy)

    def tx(x):
        return x * s

    def ty(y):
        return y * s

    def pt(x, y):
        return QPointF(tx(x), ty(y))

    # 外三角
    tri = QPolygonF([pt(256, 8), pt(500, 504), pt(12, 504)])
    painter.setBrush(QBrush(QColor("#0a0a0f")))
    painter.setPen(QPen(gold, max(1.0, 8 * s)))
    painter.drawPolygon(tri)

    # 内层三角
    tri2 = QPolygonF([pt(256, 38), pt(476, 498), pt(36, 498)])
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(gold, max(0.5, 2 * s)))
    painter.setOpacity(0.4)
    painter.drawPolygon(tri2)

    painter.setPen(QPen(gold, max(0.3, 0.5 * s)))
    painter.setOpacity(0.2)
    tri3 = QPolygonF([pt(256, 52), pt(464, 492), pt(48, 492)])
    painter.drawPolygon(tri3)
    painter.setOpacity(1.0)

    # 眼：两段弧线
    painter.setPen(QPen(gold, max(0.5, 5 * s)))
    path_up = QPainterPath()
    path_up.moveTo(pt(130, 320))
    path_up.quadTo(pt(160, 180), pt(256, 140))
    path_up.quadTo(pt(370, 180), pt(382, 320))
    painter.drawPath(path_up)

    path_lo = QPainterPath()
    path_lo.moveTo(pt(130, 320))
    path_lo.quadTo(pt(160, 390), pt(256, 420))
    path_lo.quadTo(pt(370, 390), pt(382, 320))
    painter.drawPath(path_lo)

    # 瞳孔（偏右）
    center = pt(278, 305)
    r_outer = 44 * s
    r_inner = 26 * s
    r_glint = 8 * s

    painter.setBrush(QBrush(gold))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(center, r_outer, r_outer)
    painter.setBrush(QBrush(QColor("#0a0a0f")))
    painter.drawEllipse(center, r_inner, r_inner)
    painter.setBrush(QBrush(gold))
    painter.setOpacity(0.6)
    painter.drawEllipse(pt(283, 300), r_glint, r_glint)
    painter.setOpacity(1.0)

    # 裂纹
    painter.setPen(QPen(gold, max(0.5, 4 * s), Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin))
    crack = [pt(380, 380), pt(350, 355), pt(370, 330),
             pt(340, 305), pt(360, 275)]
    for i in range(len(crack) - 1):
        painter.drawLine(crack[i], crack[i + 1])

    painter.setPen(QPen(gold, max(0.3, 2 * s), Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
    painter.drawLine(pt(370, 330), pt(395, 312))

    # 裂纹三角碎片
    frag = QPainterPath()
    frag.moveTo(pt(348, 352))
    frag.lineTo(pt(356, 346))
    frag.lineTo(pt(352, 358))
    frag.closeSubpath()
    painter.setBrush(QBrush(gold))
    painter.setOpacity(0.3)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPath(frag)
    painter.setOpacity(1.0)

    # 底部金色标记
    painter.setBrush(QBrush(gold))
    painter.setOpacity(0.4)
    painter.drawRect(int(tx(236)), int(ty(468)), int(40 * s), int(10 * s))
    painter.setOpacity(1.0)

    # 三角顶点强调线
    painter.setPen(QPen(gold, max(0.3, 1.5 * s)))
    painter.setOpacity(0.3)
    painter.drawLine(pt(256, 22), pt(256, 36))
    painter.drawLine(pt(82, 486), pt(96, 478))
    painter.drawLine(pt(430, 486), pt(416, 478))
    painter.setOpacity(1.0)

    painter.end()
    return pixmap


# ====== 任务栏图标窗口 ======
class TaskbarIcon(QWidget):
    """无边框置顶窗口，模拟任务栏图标"""

    DOUBLE_CLICK_MS = 300

    def __init__(self):
        super().__init__()

        self.dpi_scale = self._get_dpi_scale()
        self.icon_size = int(48 * self.dpi_scale)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(self.icon_size, self.icon_size)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(self.icon_size, self.icon_size)
        pixmap = generate_icon_pixmap(self.icon_size)
        self.icon_label.setPixmap(pixmap)

        self._click_count = 0
        self._first_click_time = 0
        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.timeout.connect(self._on_single_click_timeout)

        self._build_context_menu()
        self._position_to_taskbar()
        self._make_click_through()
        self.show()

    def _get_dpi_scale(self) -> float:
        try:
            screen = QApplication.primaryScreen()
            if screen:
                return screen.devicePixelRatio()
        except Exception:
            pass
        return 1.0

    def _build_context_menu(self):
        self.menu = QMenu(self)
        self.menu.setStyleSheet("""
            QMenu { background-color: #0a0a0f; color: #c4a35a;
                    border: 1px solid #c4a35a; font-family: 'Courier New'; font-size: 12px; }
            QMenu::item:selected { background-color: rgba(196,163,90,0.2); }
        """)
        a1 = QAction("唤醒 Devil", self)
        a1.triggered.connect(self._on_wake)
        self.menu.addAction(a1)
        self.menu.addSeparator()
        a2 = QAction("状态", self)
        a2.triggered.connect(self._on_status)
        self.menu.addAction(a2)
        a3 = QAction("退出", self)
        a3.triggered.connect(self._on_exit)
        self.menu.addAction(a3)

    def _make_click_through(self):
        hwnd = int(self.winId())
        ex = get_window_ex_style(hwnd)
        set_window_ex_style(hwnd, ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)

    def _remove_click_through(self):
        hwnd = int(self.winId())
        ex = get_window_ex_style(hwnd)
        set_window_ex_style(hwnd, ex & ~WS_EX_TRANSPARENT)

    def _position_to_taskbar(self):
        tb = get_taskbar_info()
        margin = 8
        if tb.get("edge", ABE_BOTTOM) == ABE_BOTTOM:
            x = tb["right"] - self.icon_size - margin
            y = tb["top"] - self.icon_size - margin
        else:
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                x = geo.right() - self.icon_size - margin
                y = geo.bottom() - self.icon_size - margin
            else:
                x, y = 1850, 950
        self.move(int(x), int(y))
        set_window_pos_topmost(int(self.winId()))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._remove_click_through()
            self._handle_left_click()
        elif event.button() == Qt.MouseButton.RightButton:
            self._remove_click_through()
            self.menu.exec(self.mapToGlobal(event.pos()))
            QTimer.singleShot(200, self._make_click_through)

    def _handle_left_click(self):
        import time
        now = time.time() * 1000
        self._click_count += 1
        if self._click_count == 1:
            self._first_click_time = now
            self._single_click_timer.start(self.DOUBLE_CLICK_MS + 50)
        elif self._click_count == 2:
            elapsed = now - self._first_click_time
            if elapsed <= self.DOUBLE_CLICK_MS:
                self._single_click_timer.stop()
                self._click_count = 0
                self._on_double_click()
            else:
                self._click_count = 1
                self._first_click_time = now

    def _on_single_click_timeout(self):
        self._click_count = 0
        self._make_click_through()

    def _on_double_click(self):
        self._make_click_through()
        self._flash()
        self._launch_or_focus_devil()

    def _launch_or_focus_devil(self):
        """启动或聚焦 devil_agent.py 终端窗口"""
        from pathlib import Path
        agent_path = Path(__file__).parent / "devil_agent.py"
        if not agent_path.exists():
            print("找不到 devil_agent.py")
            return

        try:
            # 使用 start 新建终端窗口运行 devil_agent.py
            subprocess.Popen(
                ["cmd", "/c", "start", "AKO_devil_agent", "python", str(agent_path)],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=str(agent_path.parent)
            )
        except Exception:
            # Fallback: 直接在当前目录打开
            try:
                subprocess.Popen(["python", str(agent_path)])
            except Exception:
                pass

    def _flash(self):
        self.setWindowOpacity(0.3)
        QTimer.singleShot(100, lambda: self.setWindowOpacity(1.0))

    def contextMenuEvent(self, event):
        self.menu.exec(event.globalPos())

    def _on_wake(self):
        self._on_double_click()

    def _on_status(self):
        try:
            from devil_agent import DevilAgent
            agent = DevilAgent()
            print(agent.get_status())
        except Exception as e:
            print(f"无法获取状态: {e}")

    def _on_exit(self):
        QApplication.quit()

    @staticmethod
    def get_resource_usage() -> dict:
        import psutil, os
        proc = psutil.Process(os.getpid())
        mem_info = proc.memory_info()
        return {
            "memory_mb": round(mem_info.rss / (1024 * 1024), 2),
            "cpu_percent": round(proc.cpu_percent(interval=0.1) / (os.cpu_count() or 1), 2)
        }


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AKO_devil_agent_taskbar")
    app.setQuitOnLastWindowClosed(False)

    icon = TaskbarIcon()

    # 定时器：保持置顶与位置
    position_timer = QTimer()
    position_timer.timeout.connect(icon._position_to_taskbar)
    position_timer.start(5000)

    print("AKO_devil_agent 任务栏图标已启动。")
    print("双击图标唤醒 Devil。")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()