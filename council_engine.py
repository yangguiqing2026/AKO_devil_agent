"""
AKO_devil_agent 内部三角圆桌 — 确定性裁判引擎 v1.2
FactCheckEngine: 事实核查裁判（非 LLM）
PriorityEngine: 攻击优先级裁判（非 LLM）

规则来源：AKO_devil_agent_patch_v1.2_council.md §3.2
"""
import re
from typing import List, Optional


class Evidence:
    """证据条目"""

    VALID_SOURCES = {"用户日志", "外部API", "公开数据", "历史记录", "推理"}

    def __init__(self, content: str, source: str, covers_assertion: Optional[str] = None):
        self.content = content
        self.source = source if source in self.VALID_SOURCES else "推理"
        self._covers = covers_assertion

    def covers(self, assertion: str) -> bool:
        """判断此证据是否覆盖给定断言"""
        if self._covers:
            return self._covers in assertion or assertion in self._covers
        return assertion.lower() in self.content.lower()

    def to_dict(self) -> dict:
        return {"content": self.content, "source": self.source}


class FactCheckEngine:
    """第一裁判：事实核查引擎
    输入：PROD 的质疑声明 + FACT 提供的证据列表
    输出：A / B / C
    - A: 证据充足，通过
    - B: 证据部分充足，需 PROD 补充
    - C: 证据不足 / 无证据，驳回
    """

    # 核心断言提取关键词
    ASSERTION_KEYWORDS = [
        "现金流", "亏损", "合规", "安全", "法律",
        "战略", "方向", "立项", "合作", "退出",
        "优化", "效率", "建议", "成本", "收入",
        "人员", "技术债", "延迟", "风险", "错误",
        "数据", "指标", "转化", "用户", "市场"
    ]

    def judge(self, prod_claim: str, evidence_list: List[Evidence]) -> str:
        """
        事实核查判决
        返回: "A" | "B" | "C"
        """
        # 规则0: 无证据直接驳回
        if not evidence_list:
            return "C"

        # 规则1: 证据必须包含至少一个可验证数据源
        verifiable_sources = {"用户日志", "外部API", "公开数据", "历史记录"}
        has_verifiable = any(e.source in verifiable_sources for e in evidence_list)
        if not has_verifiable:
            return "C"

        # 规则2: 证据链必须覆盖质疑的所有核心断言
        claim_assertions = self.extract_assertions(prod_claim)
        if not claim_assertions:
            return "B"

        covered = sum(
            1 for a in claim_assertions
            if any(e.covers(a) for e in evidence_list)
        )
        coverage_ratio = covered / len(claim_assertions)

        if coverage_ratio >= 0.8:
            return "A"
        elif coverage_ratio >= 0.5:
            return "B"
        else:
            return "C"

    def extract_assertions(self, text: str) -> List[str]:
        """
        从质疑文本中提取核心断言句
        按句号、问号、换行分割，过滤出含有关键词或数字的句子
        """
        # 分割为句子
        sentences = re.split(r'[。？！\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        assertions = []
        for s in sentences:
            # 含关键词或数字的句子视为断言
            has_keyword = any(k in s for k in self.ASSERTION_KEYWORDS)
            has_number = bool(re.search(r'\d+', s))
            has_question = "?" in s or "？" in s
            if has_keyword or has_number or has_question:
                assertions.append(s)

        return assertions


class PriorityEngine:
    """第二裁判：优先级引擎
    输入：通过事实核查的质疑 + 当前业务上下文
    输出：P1 / P2 / P3
    - P1: 立即输出（涉及现金流/安全/合规/法律）
    - P2: 正常输出（涉及战略/方向/重大决策）
    - P3: 暂缓（优化建议/效率提升）
    """

    P1_KEYWORDS = ["现金流", "亏损", "合规", "安全", "法律", "熔断", "危机", "破产"]
    P2_KEYWORDS = ["战略", "方向", "立项", "合作", "退出", "组织", "人员流失", "技术债"]
    P3_KEYWORDS = ["优化", "效率", "建议", "可以考虑", "改进", "调整", "微调"]

    # 阻尼席特殊规则：涉及特定人员的议题降级
    PROTECTED_PERSONS = ["周明静"]

    def judge(self, prod_claim: str, business_context: Optional[dict] = None) -> str:
        """
        优先级判决
        返回: "P1" | "P2" | "P3"
        """
        claim_lower = prod_claim.lower()

        # 规则0: 涉及受保护人员的议题降级为 P2
        if business_context and business_context.get("protect_relationship"):
            if any(p in prod_claim for p in self.PROTECTED_PERSONS):
                return "P2"

        # 规则1: 涉及现金流/安全的 = P1
        if any(k in prod_claim for k in self.P1_KEYWORDS):
            return "P1"

        # 规则2: 涉及战略方向/重大决策 = P2
        if any(k in prod_claim for k in self.P2_KEYWORDS):
            return "P2"

        # 规则3: 优化建议/效率提升 = P3（暂缓）
        if any(k in prod_claim for k in self.P3_KEYWORDS):
            return "P3"

        # 默认: P2
        return "P2"


class CouncilDebateRecord:
    """单次三角辩论记录（供史官使用）"""

    def __init__(self, prod_claim: str = ""):
        self.prod_claim = prod_claim
        self.fact_report = ""
        self.fact_judge = ""
        self.evidence_list: List[Evidence] = []
        self.damp_report = ""
        self.priority_judge = ""
        self.final_output = ""
        self.user_response = ""
        self.verification_result = ""  # "Devil对" / "用户对" / "双方都对" / "Devil错"

    def to_dict(self) -> dict:
        return {
            "prod_claim": self.prod_claim,
            "fact_report": self.fact_report,
            "fact_judge": self.fact_judge,
            "evidence_list": [e.to_dict() for e in self.evidence_list],
            "damp_report": self.damp_report,
            "priority_judge": self.priority_judge,
            "final_output": self.final_output,
            "user_response": self.user_response,
            "verification_result": self.verification_result,
        }