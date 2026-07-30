"""
AKO_devil_agent 内部三角圆桌 — 子Agent 配置 v1.2
PROD (刺探席 / Zealot): 狂热挑刺者 — 找到最狠的角度
FACT (事实席 / Reaper): 事实收割者 — 证据在哪？
DAMP (阻尼席 / Fulcrum): 逻辑阻尼器 — 现在说吗？

每个子Agent通过提示词框架定义行为，不依赖外部LLM调用；
在本地环境中通过规则+模板生成输出。
"""
from typing import List, Optional
from council_engine import Evidence


class PRODSeat:
    """刺探席 PROD — Zealot 狂热挑刺者
    使命：找到用户决策中最脆弱的点，用最大火力攻击
    """

    ROLE = "刺探席 PROD"
    PERSONA = "Zealot 狂热挑刺者"

    # 攻击角度模板（按议题模块分类）
    ATTACK_ANGLES = {
        "business": [
            "这个商业模式的核心假设是什么？如果假设不成立，整个逻辑链就断了。列出你的【核心假设】。",
            "收入预测的依据是什么？过去3个月的实际数据能否支撑这个预测？不要用'预计'这种词。",
            "这个项目中你最不愿意面对的风险是什么？直接说出来，不要回避。",
            "如果这个项目失败，最大的三个原因会是什么？列出具体原因，不是什么'市场不好'。",
            "你的定价策略基于什么？竞品分析的日期是哪天？数据过期了没有？"
        ],
        "tech": [
            "这个技术方案的最小可行版本是什么？你花在'完美架构'上的时间占了多少比例？",
            "这个系统的单点故障在哪里？如果那个点挂了，恢复时间是多少？有没有实测过？",
            "技术选型的决策依据是什么？有没有做过AB对比测试？还是只是'觉得这个好'？",
            "上次技术评审是什么时候？提出的问题都解决了吗？没解决的在拖延什么？",
            "安全审计做过没有？最近一次渗透测试的结果是什么？"
        ],
        "user": [
            "你最近一次深度反思自己做错的决策是什么？说出具体的时间、事件和后果。",
            "你现在最回避的问题是哪个？不是'没有'——每个人都有一个。说出它。",
            "过去一周你花了多少时间在真正推动业务的事情上？有没有算过？",
            "你的身体健康指标跟3个月前比如何？体检报告你自己看过了吗？",
            "你今天的情绪状态会影响你的判断吗？你是'累了想逃避'还是'清醒地决定'？"
        ],
        "org": [
            "团队中谁最近表现最好？谁最差？你有没有跟最差的那个人谈过？",
            "如果有核心成员明天离职，你的应急方案是什么？有没有备手？",
            "组织中的信息孤岛在哪里？哪些决策是'我知道但别人不知道'的？",
            "你和周明静最近一次讨论战略方向是什么时候？有没有不同意见？怎么处理的？",
            "团队扩张的速度是否超过了你管理能力的增长速度？具体数字是什么？"
        ],
        "general": [
            "你为什么觉得这个方向是对的？用具体数据回答，不要用'我认为'。",
            "如果不做这件事，最大的机会成本是什么？用数字量化。",
            "你上一次推翻自己判断是什么时候？那次你学到了什么？",
            "这个决策的不可逆性有多高？如果错了，代价多大？",
            "你征求过谁的意见？有没有不同观点的声音？还是只找了'同意你的人'？"
        ]
    }

    @classmethod
    def generate_claim(cls, module: str, trigger: str, user_input: str = "",
                       context: Optional[dict] = None) -> str:
        """
        生成质疑草案（最狠角度）

        Args:
            module: 模块名 (business/tech/user/org/general)
            trigger: 触发器
            user_input: 用户输入
            context: 额外上下文

        Returns:
            质疑草案文本
        """
        import random

        angles = cls.ATTACK_ANGLES.get(module, cls.ATTACK_ANGLES["general"])
        angle = random.choice(angles)

        # 组合质疑草案 = 事实引用 + 逻辑漏洞 + 必须回答的问题
        parts = []

        # 如果有用户输入，引用用户的话
        if user_input and len(user_input) > 5:
            quote = user_input[:100] + ("..." if len(user_input) > 100 else "")
            parts.append(f"【事实】你的原话：\"{quote}\"")

        # 逻辑漏洞
        if context and context.get("logic_flaw"):
            parts.append(f"【逻辑漏洞】{context['logic_flaw']}")
        else:
            parts.append(f"【逻辑漏洞】{cls._detect_logic_flaw(user_input, module)}")

        # 必须回答的问题
        parts.append(f"【必须回答的问题】{angle}")

        return "\n\n".join(parts)

    @classmethod
    def _detect_logic_flaw(cls, user_input: str, module: str) -> str:
        """检测输入中的常见逻辑漏洞"""
        import re

        if not user_input:
            return "没有提供足够信息来支撑你的判断——这是'拍脑袋'决策的典型特征。"

        flaws = []

        # 检测模糊用语
        vague_words = ["我觉得", "可能", "也许", "大概", "应该", "估计", "差不多"]
        for w in vague_words:
            if w in user_input:
                flaws.append(f"使用了'{w}'——这是主观感觉，不是数据分析。")

        # 检测缺少数字
        if not re.search(r'\d+', user_input):
            flaws.append("整个论述中没有出现任何具体数字——没有数据的决策就是赌博。")

        # 检测过度自信
        absolute_words = ["绝对", "100%", "肯定", "毫无疑问", "必然"]
        for w in absolute_words:
            if w in user_input:
                flaws.append(f"使用了'{w}'——过度自信是决策失误的最常见原因。")

        if not flaws:
            flaws.append("你的论证链条不完整——缺少从'观察到的问题'到'你的方案为什么是最优解'的推理过程。")

        return " ".join(flaws[:2])


class FACTSeat:
    """事实席 FACT — Reaper 事实收割者
    使命：审查刺探席的每条质疑，验证证据链完整性
    """

    ROLE = "事实席 FACT"
    PERSONA = "Reaper 事实收割者"

    @classmethod
    def review_claim(cls, prod_claim: str,
                     available_evidence: Optional[List[Evidence]] = None) -> dict:
        """
        审查刺探席的质疑，返回核查报告

        Returns:
            {
                "grade": "A/B/C",
                "evidence_list": [Evidence, ...],
                "missing_items": ["需要补充的证据项", ...],
                "report": "核查报告文本"
            }
        """
        from council_engine import FactCheckEngine

        engine = FactCheckEngine()
        evidence_list = available_evidence or []

        # 从 prod_claim 中提取可能的证据线索（基于用户原话引用）
        evidence_from_claim = cls._extract_cited_evidence(prod_claim)
        evidence_list.extend(evidence_from_claim)

        grade = engine.judge(prod_claim, evidence_list)
        missing_items = cls._identify_missing(prod_claim, evidence_list)

        report_lines = [
            f"## 事实核查报告",
            f"",
            f"### 核查结果：{grade}",
            f"",
            f"### 可用证据 ({len(evidence_list)} 条)",
        ]
        for i, e in enumerate(evidence_list, 1):
            report_lines.append(f"{i}. [{e.source}] {e.content[:80]}")

        if missing_items:
            report_lines.append("")
            report_lines.append("### 缺失证据")
            for m in missing_items:
                report_lines.append(f"- {m}")

        if grade == "C":
            report_lines.append("")
            report_lines.append("**判决：证据不足，驳回。** 这不是挑刺，这是造谣。")

        return {
            "grade": grade,
            "evidence_list": evidence_list,
            "missing_items": missing_items,
            "report": "\n".join(report_lines)
        }

    @classmethod
    def _extract_cited_evidence(cls, prod_claim: str) -> List[Evidence]:
        """从 PROD 质疑中提取引用的用户原话作为证据"""
        import re
        evidence = []
        # 寻找 "你的原话" 引用的内容
        quotes = re.findall(r'[""''](.+?)[""'']', prod_claim)
        for q in quotes:
            if len(q) > 5:
                evidence.append(Evidence(
                    content=f"用户原话引用: {q[:100]}",
                    source="用户日志",
                    covers_assertion=q[:30]
                ))
        return evidence

    @classmethod
    def _identify_missing(cls, prod_claim: str,
                          evidence_list: List[Evidence]) -> List[str]:
        """识别缺失的证据项"""
        from council_engine import FactCheckEngine
        engine = FactCheckEngine()
        assertions = engine.extract_assertions(prod_claim)

        missing = []
        covered_assertions = set()
        for a in assertions:
            if any(e.covers(a) for e in evidence_list):
                covered_assertions.add(a)

        for a in assertions:
            if a not in covered_assertions:
                missing.append(f"需要为断言「{a[:60]}」提供可验证证据")

        return missing


class DAMPSeat:
    """阻尼席 DAMP — Fulcrum 逻辑阻尼器
    使命：评估通过事实核查的质疑，决定攻击优先级和强度
    """

    ROLE = "阻尼席 DAMP"
    PERSONA = "Fulcrum 逻辑阻尼器"

    # P1-P3 对应的触发条件说明
    PRIORITY_REASONS = {
        "P1": [
            "涉及现金流或资金安全",
            "涉及法律合规风险",
            "涉及系统安全或数据安全",
            "涉及人员健康与安全"
        ],
        "P2": [
            "涉及战略方向调整",
            "涉及重大业务决策",
            "涉及组织架构变更",
            "涉及核心技术选型",
            "涉及外部合作关系"
        ],
        "P3": [
            "流程优化建议 — 当前不紧急",
            "效率提升建议 — 可安排合适时机",
            "细节调整 — 不影响核心业务",
            "探索性建议 — 需要更多数据支撑"
        ]
    }

    @classmethod
    def evaluate(cls, prod_claim: str, fact_grade: str,
                 business_context: Optional[dict] = None) -> dict:
        """
        评估攻击优先级

        Returns:
            {
                "priority": "P1/P2/P3",
                "reason": "理由",
                "trigger_condition": "当X发生时，升级为P1",
                "report": "优先级评估报告"
            }
        """
        from council_engine import PriorityEngine
        import random

        engine = PriorityEngine()
        priority = engine.judge(prod_claim, business_context)

        reasons = cls.PRIORITY_REASONS.get(priority, cls.PRIORITY_REASONS["P2"])
        reason = random.choice(reasons)

        # 为 P3 生成触发条件
        trigger_condition = ""
        if priority == "P3":
            trigger_condition = cls._generate_p3_trigger(prod_claim)

        report = cls._generate_report(priority, reason, trigger_condition, fact_grade)

        return {
            "priority": priority,
            "reason": reason,
            "trigger_condition": trigger_condition,
            "report": report
        }

    @classmethod
    def _generate_p3_trigger(cls, prod_claim: str) -> str:
        """为P3暂缓议题生成升级触发条件"""
        if "效率" in prod_claim or "优化" in prod_claim:
            return "当同一流程连续2次出现延迟或错误时，自动升级为 P1"
        if "建议" in prod_claim:
            return "当下次同类问题再次发生时，自动升级为 P2"
        if "调整" in prod_claim or "微调" in prod_claim:
            return "当相关指标连续2周下降超过10%时，自动升级为 P1"
        return "当下次月度复盘时如果仍未处理，自动升级为 P2"

    @classmethod
    def _generate_report(cls, priority: str, reason: str,
                         trigger_condition: str, fact_grade: str) -> str:
        report_lines = [
            f"## 阻尼席优先级评估",
            f"",
            f"### 判决：{priority}",
            f"理由：{reason}",
            f"事实核查等级：{fact_grade}",
        ]
        if trigger_condition:
            report_lines.append(f"升级触发条件：{trigger_condition}")
        if priority == "P3":
            report_lines.append("")
            report_lines.append("**注意：P3 不意味着放弃，只意味着'现在不是最佳时机'。**")
        return "\n".join(report_lines)