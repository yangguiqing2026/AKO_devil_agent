"""
模块 A：商业决策刺探 (AKO_devil_business)
审查所有商业决策的底层假设
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import config


class BusinessProbe:
    """商业决策审查器"""

    QUERY_TEMPLATES = {
        "new_agent_launch": [
            "这个Agent解决的是真问题还是伪需求？上线后30天内预期产生多少可量化收入？",
            "这个Agent的目标用户画像是谁？你确认过他们真的愿意付费吗？",
            "当前有哪些竞品在解决同类问题？你的差异化优势是什么？",
            "如果30天后用户量为0，你会承认判断失误还是继续投入？"
        ],
        "pricing_change": [
            "降价10%的客户转化率提升预期来自哪份数据？如果错了，亏损上限是多少？",
            "降价后的盈亏平衡点需要多少新增客户？这个数字达到的可能性是多少？",
            "竞争对手会如何响应你的降价？如果他们也降10%，你什么反应？",
            "客户会不会把你的降价解读为'产品不行了'？有没有测量过这个风险？"
        ],
        "project_initiation": [
            "这个项目的沉没成本上限是多少？退出条件是什么？谁有权喊停？",
            "项目3个月后没有达到预期指标，你会止损还是加倍投入？依据什么？",
            "你之前有没有类似项目失败过？那次的原因是什么？这次有什么不同？",
            "如果今天有人告诉你这个项目两年后会让你后悔，你会怎么反驳他？"
        ],
        "standard_investment": [
            "标准制定完成后，预期多少家竞争对手会采用？如果没人用，这笔投入算什么？",
            "制定标准的时间成本是多少？这段时间内你的竞争对手会不会已经做了更好的方案？",
            "你参与标准制定的真实动机是什么？是战略布局还是FOMO？",
            "如果3年后这个标准被另一个新兴方案取代，你的投资回报是多少？"
        ]
    }

    def __init__(self):
        pass

    def _load_error_book(self) -> list:
        path = config.error_book_path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return []

    def _save_error_book(self, data: list):
        config.error_book_path().write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def probe(self, context: dict) -> str:
        trigger = context.get("trigger", "")
        templates = self.QUERY_TEMPLATES.get(trigger, self.QUERY_TEMPLATES["new_agent_launch"])
        query = random.choice(templates)
        return self._format_output(query, trigger)

    def _format_output(self, query: str, trigger: str) -> str:
        prefix = self._get_trigger_label(trigger)
        data_suffix = self._get_data_context(trigger)
        output = f"{prefix}\n{query}{data_suffix}\n\n{config.OUTPUT_SPEC['signature']}"
        return output[:200 + len(data_suffix) + 50]

    def _get_trigger_label(self, trigger: str) -> str:
        labels = {
            "new_agent_launch": "## 新Agent上线审查",
            "pricing_change": "## 报价策略变更审查",
            "project_initiation": "## 项目立项审查",
            "standard_investment": "## 标准投入审查"
        }
        return labels.get(trigger, "## 商业决策审查")

    def _get_data_context(self, trigger: str) -> str:
        if trigger == "pricing_change":
            return "\n\n(请提供降价决策的数据来源)"
        elif trigger == "project_initiation":
            return "\n\n(请明确退出条件和喊停权限)"
        return ""

    def generate_monthly_error_book(self) -> str:
        now = datetime.now()
        error_book = self._load_error_book()
        month_start = (now - timedelta(days=30)).isoformat()

        recent_errors = [
            e for e in error_book
            if e.get("decision_date", "") >= month_start
        ]

        if not recent_errors:
            return (
                f"## AKO商业决策错题本 — {now.strftime('%Y年%m月')}\n\n"
                f"本月无可记录错误决策。\n\n"
                f"{config.OUTPUT_SPEC['signature']}"
            )

        report_lines = [
            f"## AKO商业决策错题本 — {now.strftime('%Y年%m月')}",
            "",
            f"本月错题数：{len(recent_errors)}",
            ""
        ]
        for i, err in enumerate(recent_errors, 1):
            report_lines.append(f"### {i}. {err.get('decision', '未知决策')}")
            report_lines.append(f"- Devil质疑内容：{err.get('query', '')}")
            report_lines.append(f"- 用户决策：{err.get('user_response', '')}")
            report_lines.append(f"- 实际结果：{err.get('actual_result', '')}")
            report_lines.append(f"- 偏差类型：{err.get('bias_type', '')}")
            report_lines.append("")

        report_lines.append("以上记录将直接推送至周明静（副舰长）。")
        report_lines.append(f"\n{config.OUTPUT_SPEC['signature']}")
        return "\n".join(report_lines)

    def record_error(self, decision: str, query: str, user_response: str, actual_result: str, bias_type: str):
        error_book = self._load_error_book()
        error_book.append({
            "decision_date": datetime.now().isoformat(),
            "decision": decision,
            "query": query,
            "user_response": user_response,
            "actual_result": actual_result,
            "bias_type": bias_type
        })
        self._save_error_book(error_book)

    def get_probe_decision_context(self, scenario: str) -> str:
        scenarios = {
            "万峰林": "项目沉没成本上限？退出条件？谁有权喊停？",
            "围墙业务": "6个月内未盈利，现有主业的现金流能支撑多久？",
            "报价策略": "降价10%的转化率提升预期来自哪份数据？"
        }
        return scenarios.get(scenario, random.choice(self.QUERY_TEMPLATES["project_initiation"]))