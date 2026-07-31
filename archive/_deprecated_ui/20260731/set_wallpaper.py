"""
AKO_devil_agent 壁纸设置工具
使用 SystemParametersInfo API 设置桌面壁纸
开机自运行：放置快捷方式到 shell:startup
"""
import ctypes
import sys
from pathlib import Path

# Windows API constants
SPI_SETDESKWALLPAPER = 0x0014
SPIF_UPDATEINIFILE = 0x0001
SPIF_SENDCHANGE = 0x0002

WALLPAPER_DIR = Path(__file__).parent / "assets" / "wallpaper"


def set_wallpaper(image_path: str) -> bool:
    """使用 SystemParametersInfoW 设置桌面壁纸"""
    result = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        image_path,
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )
    return result != 0


def find_best_wallpaper() -> Path:
    """查找最适合当前分辨率的壁纸"""
    # 检测屏幕分辨率
    try:
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
    except Exception:
        screen_w, screen_h = 1920, 1080

    # 按优先级匹配
    candidates = [
        f"devil_wallpaper_{screen_w}x{screen_h}.png",
        f"devil_wallpaper_{int(screen_h * 16 / 9)}x{screen_h}.png",  # 16:9 fallback
        "devil_wallpaper_2560x1440.png",
        "devil_wallpaper_1920x1080.png",
        "devil_wallpaper_default.png",
    ]

    for name in candidates:
        path = WALLPAPER_DIR / name
        if path.exists():
            return path

    return WALLPAPER_DIR / "devil_wallpaper_default.png"


def create_startup_shortcut():
    """创建开机自启动快捷方式"""
    import os
    from pathlib import Path

    startup_dir = Path(os.environ.get("APPDATA", "")) / \
        "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_path = startup_dir / "AKO_devil_wallpaper.bat"

    script_path = Path(__file__).resolve()

    bat_content = f'''@echo off
cd /d "{script_path.parent}"
python "{script_path}" --silent
'''

    startup_dir.mkdir(parents=True, exist_ok=True)
    shortcut_path.write_text(bat_content, encoding="utf-8")
    print(f"Startup shortcut created: {shortcut_path}")
    return shortcut_path


def remove_startup_shortcut():
    """移除开机自启动快捷方式"""
    import os
    startup_dir = Path(os.environ.get("APPDATA", "")) / \
        "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_path = startup_dir / "AKO_devil_wallpaper.bat"
    if shortcut_path.exists():
        shortcut_path.unlink()
        print(f"Startup shortcut removed: {shortcut_path}")


def main():
    silent = "--silent" in sys.argv

    wallpaper_path = find_best_wallpaper()
    if not wallpaper_path.exists():
        print(f"Wallpaper not found: {wallpaper_path}")
        return 1

    success = set_wallpaper(str(wallpaper_path))
    if success:
        if not silent:
            print(f"Wallpaper set: {wallpaper_path}")
        return 0
    else:
        if not silent:
            print("Failed to set wallpaper.")
        return 1


if __name__ == "__main__":
    # 处理命令行参数
    if "--install" in sys.argv:
        create_startup_shortcut()
    elif "--uninstall" in sys.argv:
        remove_startup_shortcut()
    else:
        sys.exit(main())