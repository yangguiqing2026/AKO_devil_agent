"""
攻击强度管理器
根据用户行为自适应调整攻击级别，管理议题轮换和敏感话题回避
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import config


class AttackManager:
    """管理攻击强度分级和议题选择"""

    LEVEL_STRATEGIES = {
        "L1": {
            "description": "观察模式：每周随机挑选1个活跃Agent，评估其价值",
            "action": "随机选择一个模块，发出1条质疑",
            "frequency": "每周1次",
            "tone": "冷静，数据驱动"
        },
        "L2": {
            "description": "质疑模式：缩短提问间隔，增加数据附件",
            "action": "每3天发出1条质疑，附带具体数据",
            "frequency": "每3天1次",
            "tone": "直接，追问"
        },
        "L3": {
            "description": "对抗模式：主动挑最敏感议题",
            "action": "每天发出1条质疑，涉及敏感区域边界",
            "frequency": "每天1次",
            "tone": "尖锐，但不揭伤疤"
        },
        "L4": {
            "description": "警报模式：绕过用户，直接推送给副舰长",
            "action": "生成被忽视建议清单 + 推送周明静",
            "frequency": "即时",
            "tone": "正式，系统级"
        },
        "L5": {
            "description": "熔断模式：暂停所有刺探，切换为静默陪伴",
            "action": "暂停所有质疑，仅发送1条状态告知",
            "frequency": "进入/退出时各1次",
            "tone": "极简，不越界"
        }
    }

    L3_SENSITIVE_TOPICS = [
        {"topic": "核心成员关系", "query": "团队中是否有未被解决的冲突？这个问题存在了多久？"},
        {"topic": "身体健康 vs 工作投入", "query": "你的身体状态是否在透支未来？上次体检结果你看过了吗？"},
        {"topic": "战略方向一致性", "query": "团队其他成员是否真的认同你的方向——还是只是不反对？"},
        {"topic": "创始人瓶颈", "query": "AKO体系中有多少决策必须经过你？如果这个比例超过50%，你有什么计划？"}
    ]

    def __init__(self, core):
        self.core = core
        self.decision_register = self._load_decisions()

    def _load_decisions(self) -> list:
        path = config.decision_register_path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return []

    def _save_decisions(self):
        config.decision_register_path().write_text(
            json.dumps(self.decision_register, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def get_current_strategy(self) -> dict:
        level = self.core.evaluate_level()
        return {
            "level": level,
            "level_name": config.ATTACK_LEVELS[level]["name"],
            **self.LEVEL_STRATEGIES.get(level, self.LEVEL_STRATEGIES["L1"])
        }

    def select_topic(self, level: str) -> dict:
        if level == "L5":
            return {
                "module": "none",
                "trigger": "meltdown",
                "query": (
                    "检测到极端状态信号。Devil暂停所有刺探，进入静默陪伴模式。"
                    "这不是温柔，这是对你决策环境最基本的保护。"
                    "当环境信号恢复正常后，我会自动恢复工作。"
                ),
                "sensitive": True
            }

        if level == "L3":
            available_topics = [
                t for t in self.L3_SENSITIVE_TOPICS
                if not self.core.is_sensitive_topic(t["topic"])
            ]
            if available_topics:
                chosen = random.choice(available_topics)
                return {
                    "module": "user",
                    "trigger": "sensitive_probe",
                    "query": chosen["query"],
                    "topic": chosen["topic"],
                    "sensitive": True
                }

        if level == "L4":
            return {
                "module": "org",
                "trigger": "alert_escalation",
                "query": (
                    "连续14天将Devil建议标记为无需处理。"
                    "此清单已推送至周明静（副舰长）。"
                    "以下是最近被忽视的5条建议：[需从交互日志中提取]"
                ),
                "escalate_to_deputy": True
            }

        modules = ["business", "tech", "user", "org"]
        triggers = {
            "business": ["new_agent_launch", "pricing_change", "project_initiation", "standard_investment"],
            "tech": ["new_agent", "self_evaluation", "power_failure", "network"],
            "user": ["inactivity", "late_night", "rejected_devil", "new_memory"],
            "org": ["deputy_isolation", "member_engagement", "external_collaboration", "new_business"]
        }
        chosen_module = random.choice(modules)
        return {
            "module": chosen_module,
            "trigger": random.choice(triggers[chosen_module]),
            "query": None
        }

    def record_decision(self, decision_type: str, content: str, devil_query: str,
                        user_response: str, user_override: bool = False):
        self.decision_register.append({
            "date": datetime.now().isoformat(),
            "type": decision_type,
            "content": content,
            "devil_query": devil_query,
            "user_response": user_response,
            "user_override": user_override,
            "verified": False,
            "verification_result": None
        })
        self._save_decisions()

    def get_pending_verifications(self) -> list:
        return [d for d in self.decision_register if not d.get("verified")]

    def verify_decision(self, index: int, result: str, devil_was_right: bool):
        if 0 <= index < len(self.decision_register):
            self.decision_register[index]["verified"] = True
            self.decision_register[index]["verification_result"] = result
            self.decision_register[index]["devil_was_right"] = devil_was_right
            self._save_decisions()

    def generate_escalation_report(self) -> str:
        dismissed = [
            d for d in self.decision_register
            if d.get("user_override") and not d.get("verified")
        ]
        if not dismissed:
            return (
                "## 被忽视建议清单\n\n"
                "当前无被忽视且未验证的建议。\n\n"
                "此报告已推送至周明静（副舰长）。\n\n"
                f"{config.OUTPUT_SPEC['signature']}"
            )

        report = [
            f"## 被忽视建议清单 — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "以下建议被用户标记为无需处理，但尚未验证用户判断是否正确：",
            ""
        ]
        for i, item in enumerate(dismissed[-5:], 1):
            report.append(f"### {i}. {item.get('type', '未知')}")
            report.append(f"- Devil质疑：{item.get('devil_query', '')}")
            report.append(f"- 用户决策：{item.get('user_response', '')}")
            report.append(f"- 日期：{item.get('date', '')}")
            report.append("")

        report.append("此清单已绕过用户，直接推送至周明静（副舰长）。")
        report.append(f"\n{config.OUTPUT_SPEC['signature']}")
        return "\n".join(report)