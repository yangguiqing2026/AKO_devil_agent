"""
AKO_devil_agent 图标加载器
支持 SVG 和 base64 嵌入，不依赖网络
"""
import base64
from pathlib import Path


class IconLoader:
    """加载 devil_eye 图标资源"""

    ASSETS_DIR = Path(__file__).parent / "assets"

    @classmethod
    def load_svg(cls) -> str:
        """加载 SVG 源码"""
        svg_path = cls.ASSETS_DIR / "devil_eye.svg"
        if svg_path.exists():
            return svg_path.read_text(encoding="utf-8")
        return ""

    @classmethod
    def load_svg_base64(cls) -> str:
        """返回 SVG 的 base64 data URI，可直接嵌入 HTML/Markdown"""
        svg_content = cls.load_svg()
        if not svg_content:
            return ""
        b64 = base64.b64encode(svg_content.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{b64}"

    @classmethod
    def get_icon_markdown(cls, size: str = "64") -> str:
        """返回可内嵌进 Markdown 的图标 base64"""
        uri = cls.load_svg_base64()
        if not uri:
            return "(icon not found)"
        return f"![devil_eye]({uri})"

    @classmethod
    def get_icon_html(cls, width: int = 64, height: int = 64) -> str:
        """返回 HTML img 标签"""
        uri = cls.load_svg_base64()
        if not uri:
            return ""
        return f'<img src="{uri}" width="{width}" height="{height}" alt="AKO_devil_agent"/>'

    @classmethod
    def list_assets(cls) -> list:
        """列出所有可用资源"""
        if cls.ASSETS_DIR.exists():
            return [p.name for p in cls.ASSETS_DIR.iterdir()]
        return []

    @classmethod
    def verify_assets(cls) -> dict:
        """验证资源完整性"""
        required = ["devil_eye.svg"]
        status = {}
        for name in required:
            path = cls.ASSETS_DIR / name
            status[name] = {
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0
            }
        return status

    @classmethod
    def get_dashboard_html(cls) -> str:
        """返回完整的仪表盘 HTML，包含内嵌 SVG 图标"""
        html_path = cls.ASSETS_DIR / "dashboard.html"
        if html_path.exists():
            return html_path.read_text(encoding="utf-8")
        return ""
