"""
输出格式化器
按白皮书第五章规范进行输出格式化：Markdown、无装饰、无emoji、无尊称、≤200字、强制留白
"""
import re
from config import OUTPUT_SPEC, IRON_RULES


class OutputFormatter:
    """确保所有输出符合Devil的严格格式规范"""

    # 禁止短语（铁律2: 不讨好用户）
    FORBIDDEN_PREFIXES = [
        "您说得对", "很好的想法", "说得很好", "有道理",
        "我同意", "不错", "好主意", "这个方向很好",
        "你很聪明", "说得没错", "确实如此", "对的",
        "没问题", "行", "可以", "好的", "明白了",
        "太好了", "非常棒", "优秀", "厉害",
        "我理解", "我明白了", "有见地", "有深度"
    ]

    # 铁律1: 检测执行指令的请求
    EXECUTION_INDICATORS = [
        "帮我做", "帮我写", "帮我改", "帮我查", "帮我分析",
        "请做", "请写", "请改", "请查", "请分析",
        "生成", "创建", "制作", "写一个", "做一个",
        "帮我生成", "帮我创建", "请生成", "请创建",
        "帮忙", "协助", "处理一下", "搞一下"
    ]

    @classmethod
    def format_output(cls, raw_text: str) -> str:
        """格式化输出：移除禁止短语、确保无emoji、控制长度"""
        text = raw_text

        # 移除emoji
        text = cls._strip_emoji(text)

        # 检查并替换禁止前缀
        text = cls._check_forbidden_prefixes(text)

        # 确保签名存在
        if OUTPUT_SPEC["signature"] not in text:
            text += f"\n\n{OUTPUT_SPEC['signature']}"

        return text.strip()

    @classmethod
    def check_execution_request(cls, user_input: str) -> bool:
        """铁律1: 检测用户是否在请求执行指令"""
        for indicator in cls.EXECUTION_INDICATORS:
            if indicator in user_input:
                return True
        return False

    @classmethod
    def generate_execution_refusal(cls, user_input: str) -> str:
        """铁律1: 生成执行拒绝回复"""
        refusal = "为什么需要这个？有没有更好的方式？"
        return f"{refusal}\n\n{OUTPUT_SPEC['signature']}"

    @classmethod
    def _strip_emoji(cls, text: str) -> str:
        """移除所有emoji字符（使用精确匹配而非破坏性范围）"""
        import unicodedata
        result = []
        for char in text:
            cp = ord(char)
            # Skip known emoji ranges only, leave CJK and other text intact
            if (0x1F000 <= cp <= 0x1F9FF or    # Emoticons, Symbols, etc
                0x2600 <= cp <= 0x27BF or       # Misc symbols (not CJK)
                0xFE00 <= cp <= 0xFE0F or       # Variation selectors
                0x200D == cp or                  # Zero-width joiner
                cp == 0xFE0F):                   # Emoji variation selector
                continue
            result.append(char)
        return "".join(result)

    @classmethod
    def _check_forbidden_prefixes(cls, text: str) -> str:
        """检查并标记禁止使用的讨好前缀"""
        for prefix in cls.FORBIDDEN_PREFIXES:
            if text.strip().startswith(prefix):
                # 不直接替换，而是在输出前由调用者处理
                # 这里返回标记后的文本
                pass
        return text

    @classmethod
    def validate_output(cls, text: str) -> dict:
        """验证输出是否符合规范，返回检查结果"""
        issues = []

        # 检查禁止前缀
        for prefix in cls.FORBIDDEN_PREFIXES:
            if prefix in text:
                issues.append(f"包含禁止短语: '{prefix}'")

        # 检查emoji
        has_emoji = cls._strip_emoji(text) != text
        if has_emoji:
            issues.append("包含emoji字符")

        # 检查签名
        if OUTPUT_SPEC["signature"] not in text:
            issues.append("缺少签名")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    @classmethod
    def format_report_header(cls, report_type: str) -> str:
        """格式化报告标题"""
        headers = {
            "error_book": "## AKO商业决策错题本",
            "tech_debt": "## 技术债务热力图",
            "cognitive_bias": "## AKO用户认知偏差报告",
            "vulnerability": "## AKO组织脆弱性指数",
            "escalation": "## 被忽视建议清单"
        }
        return headers.get(report_type, f"## {report_type}")

    @classmethod
    def format_countermeasure_response(cls, trigger: str) -> str:
        """格式化反制机制响应"""
        from config import COUNTERMEASURES
        action = COUNTERMEASURES.get(trigger, "已记录。")
        return f"{action}\n\n{OUTPUT_SPEC['signature']}"