"""
模块 D：组织健康刺探 (AKO_devil_org)
防止AKO变成"一个人的公司"，监控组织脆弱性
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import config


class OrgProbe:
    """组织健康审查器"""

    QUERY_TEMPLATES = {
        "deputy_isolation": [
            "副舰长的隔离是主动选择还是被动边缘化？AKO的知识传承是否依赖单一节点？",
            "周明静7天未参与任何Agent相关交互。如果核心成员明天离开，你有多少知识是只存在你脑中的？",
            "副舰长不参与可能是因为太忙、没有权限、或觉得没用——你确认过是哪个原因吗？"
        ],
        "member_engagement": [
            "是工具不好用，还是他们找到了绕过系统的方式？或者，他们还在吗？",
            "使用频率下降如果没有对应的工作产出增加，说明他们找到了替代方案——你了解那个方案吗？",
            "Pi Agent的日活波动超过30%时你收到过警报吗？如果没有，为什么？"
        ],
        "external_collaboration": [
            "这个合作的退出成本是多少？对方有没有替代方案？AKO是不是可替换的？",
            "中科院/中黔顺安/协会——如果明天对方单方面终止合作，你失去了什么？",
            "你在这个合作中的不可替代性是什么？如果对方内部换人对接，关系能延续吗？"
        ],
        "new_business": [
            "如果这两个新业务6个月内未盈利，现有主业的现金流能支撑多久？精确到月。",
            "围墙业务和箱体房租赁——你同时做两个新业务而不是一个，是分散风险还是稀释精力？",
            "新业务的客户获取成本是多少？你有没有算过，或者你在回避这个数字？"
        ]
    }

    VULNERABILITY_DIMENSIONS = [
        {"name": "人员", "indicators": ["关键人员流失风险", "知识集中度", "招聘/留人能力", "替补计划完善度"]},
        {"name": "资金", "indicators": ["现金流储备(月)", "收入多元化", "应收账款风险", "固定成本占比"]},
        {"name": "技术", "indicators": ["系统单点故障", "核心代码所有权", "外部依赖度", "安全合规"]},
        {"name": "合规", "indicators": ["牌照/许可证有效期", "合同风险", "知识产权归属", "数据合规"]}
    ]

    def _load_vulnerability_data(self) -> dict:
        path = config.org_vulnerability_path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"assessments": [], "last_report_date": None, "current_scores": {}}

    def _save_vulnerability_data(self, data: dict):
        config.org_vulnerability_path().write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def probe(self, context: dict) -> str:
        trigger = context.get("trigger", "")
        templates = self.QUERY_TEMPLATES.get(trigger, self.QUERY_TEMPLATES["deputy_isolation"])
        query = random.choice(templates)

        if trigger == "new_business" and context.get("project_name"):
            query = (
                f"{context['project_name']}——如果6个月内未盈利，现有主业的现金流能支撑多久？"
                "给出精确到月的数字，不是'应该没问题'。"
            )

        return self._format_output(query, trigger)

    def _format_output(self, query: str, trigger: str) -> str:
        labels = {
            "deputy_isolation": "## 副舰长参与度审查",
            "member_engagement": "## 成员活跃度审查",
            "external_collaboration": "## 外部合作审查",
            "new_business": "## 新业务风险评估"
        }
        prefix = labels.get(trigger, "## 组织健康审查")
        return f"{prefix}\n{query}\n\n{config.OUTPUT_SPEC['signature']}"

    def generate_org_vulnerability_index(self) -> str:
        now = datetime.now()
        data = self._load_vulnerability_data()
        scores = data.get("current_scores", {})

        dimension_scores = {}
        for dim in self.VULNERABILITY_DIMENSIONS:
            dim_name = dim["name"]
            dim_score = scores.get(dim_name, 5)
            dimension_scores[dim_name] = dim_score

        total = sum(dimension_scores.values()) / len(dimension_scores) if dimension_scores else 5
        threshold = 7.0
        alert = total >= threshold

        report = [
            f"## AKO组织脆弱性指数 — {now.strftime('%Y年%m月')}",
            "",
            f"综合脆弱指数：{total:.1f} / 10.0",
            f"阈值：{threshold} | 状态：{'**红色预警**' if alert else '正常'}",
            "",
            "### 四维度评分：",
            ""
        ]

        for dim in self.VULNERABILITY_DIMENSIONS:
            dim_name = dim["name"]
            dim_score = dimension_scores.get(dim_name, 5)
            bar = "\u2588" * int(dim_score) + "\u2591" * max(0, 10 - int(dim_score))
            report.append(f"- **{dim_name}**：{dim_score:.1f}/10  [{bar}]")
            report.append(f"  指标：{' | '.join(dim['indicators'])}")
            report.append("")

        if alert:
            report.append("### 红色预警")
            report.append("脆弱性指数超过阈值，建议立即采取以下行动：")
            report.append("1. 评估最高风险维度并制定缓解计划")
            report.append("2. 召集团队讨论（包括周明静）")
            report.append("3. 30天内复核风险缓解进展")
            report.append("")

        report.append("此报告已推送至周明静（副舰长）。")
        report.append(f"\n{config.OUTPUT_SPEC['signature']}")

        data["last_report_date"] = now.isoformat()
        data["current_scores"] = dimension_scores
        data.setdefault("assessments", []).append({
            "date": now.isoformat(),
            "total_score": round(total, 1),
            "dimension_scores": dimension_scores,
            "alert_triggered": alert
        })
        self._save_vulnerability_data(data)

        return "\n".join(report)

    def update_vulnerability_score(self, dimension: str, score: float):
        if 0 <= score <= 10:
            data = self._load_vulnerability_data()
            data.setdefault("current_scores", {})[dimension] = score
            self._save_vulnerability_data(data)

    def get_red_alert_targets(self) -> list:
        data = self._load_vulnerability_data()
        scores = data.get("current_scores", {})
        alerts = []
        for dim in self.VULNERABILITY_DIMENSIONS:
            dim_name = dim["name"]
            if scores.get(dim_name, 5) >= 7:
                alerts.append({"dimension": dim_name, "score": scores[dim_name], "indicators": dim["indicators"]})
        return alerts