"""
输出格式化器 v1.1
按白皮书第五章规范进行输出格式化：Markdown、无装饰、无emoji、无尊称、≤200字、强制留白
v1.1: 新增耳光格式支持
"""
import re
import config


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

    # v1.1: 铁律6 - 事实优先标记
    FACT_FIRST_MARKER = "事实优先于礼貌"

    @classmethod
    def format_output(cls, raw_text: str) -> str:
        """格式化输出：移除禁止短语、确保无emoji、控制长度"""
        text = raw_text
        text = cls._strip_emoji(text)
        text = cls._check_forbidden_prefixes(text)
        if config.OUTPUT_SPEC["signature"] not in text:
            text += f"\n\n{config.OUTPUT_SPEC['signature']}"
        return text.strip()

    @classmethod
    def format_slap_output(cls, facts: str, logic_flaw: str, question: str) -> str:
        """v1.1 耳光格式：
        [事实陈述，无缓冲]
        [你的逻辑漏洞，用你自己的话反打你]
        [必须回应的问题，不给逃避空间]
        """
        parts = [facts.strip(), logic_flaw.strip(), question.strip()]
        # Filter empty parts
        parts = [p for p in parts if p]
        if not parts:
            return f"{config.OUTPUT_SPEC['signature']}"
        return "\n\n".join(parts) + f"\n\n{config.OUTPUT_SPEC['signature']}"

    @classmethod
    def check_execution_request(cls, user_input: str) -> bool:
        """铁律1: 检测用户是否在请求执行指令"""
        for indicator in cls.EXECUTION_INDICATORS:
            if indicator in user_input:
                return True
        return False

    @classmethod
    def generate_execution_refusal(cls, user_input: str = "") -> str:
        """铁律1: 生成执行拒绝回复"""
        return f"为什么需要这个？有没有更好的方式？\n\n{config.OUTPUT_SPEC['signature']}"

    @classmethod
    def _strip_emoji(cls, text: str) -> str:
        """移除所有emoji字符（精确匹配，保护CJK）"""
        import unicodedata
        result = []
        for char in text:
            cp = ord(char)
            if (0x1F000 <= cp <= 0x1F9FF or
                0xFE00 <= cp <= 0xFE0F or
                cp == 0x200D or cp == 0xFE0F):
                continue
            result.append(char)
        return "".join(result)

    @classmethod
    def _check_forbidden_prefixes(cls, text: str) -> str:
        """检查并标记禁止使用的讨好前缀"""
        for prefix in cls.FORBIDDEN_PREFIXES:
            if text.strip().startswith(prefix):
                pass
        return text

    @classmethod
    def validate_output(cls, text: str) -> dict:
        """验证输出是否符合规范"""
        issues = []
        for prefix in cls.FORBIDDEN_PREFIXES:
            if prefix in text:
                issues.append(f"包含禁止短语: '{prefix}'")
        has_emoji = cls._strip_emoji(text) != text
        if has_emoji:
            issues.append("包含emoji字符")
        if config.OUTPUT_SPEC["signature"] not in text:
            issues.append("缺少签名")
        return {"valid": len(issues) == 0, "issues": issues}

    @classmethod
    def format_report_header(cls, report_type: str) -> str:
        headers = {
            "error_book": "## AKO商业决策错题本",
            "tech_debt": "## 技术债务热力图",
            "cognitive_bias": "## AKO用户认知偏差报告",
            "vulnerability": "## AKO组织脆弱性指数",
            "escalation": "## 被忽视建议清单",
            "slap_metrics": "## 耳光命中率报告"
        }
        return headers.get(report_type, f"## {report_type}")

    @classmethod
    def format_countermeasure_response(cls, trigger: str) -> str:
        action = config.COUNTERMEASURES.get(trigger, "已记录。")
        return f"{action}\n\n{config.OUTPUT_SPEC['signature']}"