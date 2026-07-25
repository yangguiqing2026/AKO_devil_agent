"""
模块 B：技术架构刺探 (AKO_devil_tech)
防止技术自嗨，审查技术债务和架构决策
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import config


class TechProbe:
    """技术架构审查器"""

    QUERY_TEMPLATES = {
        "new_agent": [
            "现有31个Agent中，与这个新Agent功能重叠度最高的3个是谁？重叠度多少？为什么不合并？",
            "这个Agent的维护成本预估是多少？谁负责维护？如果他离职了怎么办？",
            "这个Agent的技术选型依据是什么？有没有做过技术方案对比？",
            "新增这个Agent后，系统复杂度增加了多少？这种复杂度增长有没有上限？"
        ],
        "self_evaluation": [
            "自精华的评判标准是什么？谁写的标准？标准本身多久没更新过？",
            "自注册通过=没问题？这个逻辑等价于'我没有发现错误=我没有错误'，你意识到这个认知偏差了吗？",
            "上次有人外部审计这些自评判标准是什么时候？如果标准本身有漏洞，谁会发现？",
            "自精华系统有没有'自我强化偏差'——只记录有利于自己的结果？"
        ],
        "power_failure": [
            "上次拔电源测试是哪天？如果今天再拔，失败概率是多少？",
            "硬件老化、系统更新、配置漂移——这三项风险各自评估过吗？具体数字？",
            "断电后自动恢复的完整时间线是什么？每一步的SLA是多少？",
            "如果断电发生在凌晨3点，谁被叫醒？他会不会接电话？"
        ],
        "network": [
            "如果Tailscale官方服务器被墙或倒闭，你的备用组网方案是什么？",
            "备用方案的切换时间是多少？切换期间多少服务会中断？",
            "你有没有测试过备用方案的切换流程？上次测试是什么时候？",
            "Tailscale的替代品有哪些？各自的优劣比较？你选了哪个？为什么？"
        ]
    }

    def _load_tech_debt(self) -> dict:
        path = config.tech_debt_map_path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"entries": [], "last_updated": datetime.now().isoformat()}

    def _save_tech_debt(self, data: dict):
        data["last_updated"] = datetime.now().isoformat()
        config.tech_debt_map_path().write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def probe(self, context: dict) -> str:
        trigger = context.get("trigger", "")
        templates = self.QUERY_TEMPLATES.get(trigger, self.QUERY_TEMPLATES["new_agent"])
        query = random.choice(templates)
        if context.get("overlapping_agents"):
            query += f"\n\n已知重叠候选：{context['overlapping_agents']}"
        return self._format_output(query, trigger)

    def _format_output(self, query: str, trigger: str) -> str:
        labels = {
            "new_agent": "## 新增Agent技术审查",
            "self_evaluation": "## 自评判系统审查",
            "power_failure": "## 断电自启验证审查",
            "network": "## 网络架构审查"
        }
        prefix = labels.get(trigger, "## 技术架构审查")
        return f"{prefix}\n{query}\n\n{config.OUTPUT_SPEC['signature']}"

    def generate_tech_debt_heatmap(self) -> str:
        now = datetime.now()
        tech_debt = self._load_tech_debt()
        entries = tech_debt.get("entries", [])

        if not entries:
            return (
                f"## 技术债务热力图 — {now.strftime('%Y年Q%m')}\n\n"
                f"当前无记录的技术债务项。\n\n"
                f"{config.OUTPUT_SPEC['signature']}"
            )

        for entry in entries:
            entry["heat_score"] = entry.get("fix_cost", 1) * entry.get("business_impact", 1)

        sorted_debt = sorted(entries, key=lambda x: x.get("heat_score", 0), reverse=True)
        top3 = sorted_debt[:3]

        report_lines = [
            f"## 技术债务热力图 — {now.strftime('%Y年Q%m')}",
            "",
            "排序依据：修复成本 x 业务影响（分数越高越危险）",
            "",
            "### Top 3 必须人工回应：",
            ""
        ]

        for i, debt in enumerate(top3, 1):
            report_lines.append(f"#### {i}. {debt.get('name', '未命名债务')}")
            report_lines.append(
                f"- 修复成本：{debt.get('fix_cost', '?')} | "
                f"业务影响：{debt.get('business_impact', '?')} | "
                f"热力值：{debt.get('heat_score', '?')}"
            )
            report_lines.append(f"- 描述：{debt.get('description', '无描述')}")
            report_lines.append(f"- 责任人：{debt.get('owner', '未指定')}")
            report_lines.append(f"- 创建日期：{debt.get('created_date', '未知')}")
            report_lines.append("")

        report_lines.append("以上Top3必须在7天内提供人工回应（处理计划或接受风险的书面理由）。")
        report_lines.append(f"\n{config.OUTPUT_SPEC['signature']}")
        return "\n".join(report_lines)

    def add_tech_debt(self, name: str, description: str, fix_cost: int,
                      business_impact: int, owner: str = "未指定"):
        tech_debt = self._load_tech_debt()
        tech_debt.setdefault("entries", []).append({
            "name": name,
            "description": description,
            "fix_cost": fix_cost,
            "business_impact": business_impact,
            "owner": owner,
            "created_date": datetime.now().isoformat(),
            "status": "open"
        })
        self._save_tech_debt(tech_debt)

    def request_independent_verification(self, claim: str, source: str) -> str:
        return (
            "## 二次验证请求\n"
            f"来源声明：{source}\n"
            f"声明内容：{claim}\n"
            "Devil请求：请调用不同LLM或外部工具交叉确认以上声明。\n"
            "禁止自我引用验证。禁止用同一系统的另一模块验证。\n\n"
            f"{config.OUTPUT_SPEC['signature']}"
        )