"""
语言模式检测器 - v1.1 熔断退出辅助
用于判断用户语言模式是否回归基线
"""
import re


class LanguageDetector:
    """检测用户输入的语言模式状态"""

    # 非基线标记：高情绪/高风险语言特征
    DISTRESS_MARKERS = {
        "exclamation_flood": {"pattern": r"！{2,}", "description": "连续感叹号"},
        "sarcastic_laugh": {"pattern": r"呵呵|哈哈[哈]{2,}", "description": "讽刺/苦笑笑声"},
        "all_caps": {"pattern": r"[\u4e00-\u9fff]*[A-Z]{4,}", "description": "中文夹杂全大写"},
        "repeated_question": {"pattern": r"[？？]{2,}", "description": "连续问号"},
        "negative_catastrophe": {
            "keywords": ["完了", "没救了", "一切都毁了", "不行了", "撑不住了", "活不下去了"],
            "description": "灾难化语言"
        },
        "self_blame": {
            "keywords": ["是我没用", "都是我的错", "我不配", "我太差了", "我对不起"],
            "description": "自我攻击语言"
        }
    }

    # 基线标记：理性陈述句特征
    BASELINE_MARKERS = {
        "declarative_sentence": {"pattern": r"。$", "description": "以句号结尾的陈述"},
        "specific_data": {"pattern": r"\d+[%％元万百千]", "description": "包含具体数据"},
        "action_plan": {
            "keywords": ["我决定", "我会", "下一步", "计划", "先做", "从...开始"],
            "description": "包含行动意图"
        },
        "calm_reflection": {
            "keywords": ["我想清楚了", "明白了", "理解了", "谢谢", "好的"],
            "description": "冷静反思"
        }
    }

    @classmethod
    def is_distressed_language(cls, text: str) -> bool:
        """判断是否处于高情绪/高风险语言模式"""
        score = 0
        for marker_key, marker in cls.DISTRESS_MARKERS.items():
            if "pattern" in marker:
                if re.search(marker["pattern"], text):
                    score += 1
            elif "keywords" in marker:
                for kw in marker["keywords"]:
                    if kw in text:
                        score += 1
                        break
        return score >= 2  # 两个或以上负面标记 → 非基线

    @classmethod
    def is_baseline_language(cls, text: str) -> bool:
        """判断是否回归基线（理性陈述句）"""
        # 基线条件：零 distress markers，且有 baseline 特征
        if cls.is_distressed_language(text):
            return False

        baseline_score = 0
        for marker_key, marker in cls.BASELINE_MARKERS.items():
            if "pattern" in marker:
                if re.search(marker["pattern"], text):
                    baseline_score += 1
            elif "keywords" in marker:
                for kw in marker["keywords"]:
                    if kw in text:
                        baseline_score += 1
                        break

        return baseline_score >= 1  # 至少一个基线特征

    @classmethod
    def analyze(cls, text: str) -> dict:
        """完整分析：返回模式评估"""
        return {
            "is_baseline": cls.is_baseline_language(text),
            "is_distressed": cls.is_distressed_language(text),
            "text_length": len(text),
            "has_exclamation": "!" in text or "！" in text
        }