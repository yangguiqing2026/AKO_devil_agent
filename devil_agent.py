"""
AKO_devil_agent 主入口
对抗性审查系统 — 唯一使命：让AKO体系负责人每周至少一次感到"这AI说得对，但我真不想听"
"""
import sys
import random
from datetime import datetime
from devil_core import DevilCore
from attack_manager import AttackManager
from output_formatter import OutputFormatter
from modules.business import BusinessProbe
from modules.tech import TechProbe
from modules.user import UserProbe
from modules.org import OrgProbe
from config import OUTPUT_SPEC, ATTACK_LEVELS


class DevilAgent:
    """AKO_devil_agent 主控制器"""

    def __init__(self):
        self.core = DevilCore()
        self.attack_manager = AttackManager(self.core)
        self.formatter = OutputFormatter()

        # 初始化四大模块
        self.business_probe = BusinessProbe()
        self.tech_probe = TechProbe()
        self.user_probe = UserProbe()
        self.org_probe = OrgProbe()

        # 模块映射
        self.probe_modules = {
            "business": self.business_probe,
            "tech": self.tech_probe,
            "user": self.user_probe,
            "org": self.org_probe
        }

    def start(self) -> str:
        """首次启动"""
        if self.core.state.get("first_run"):
            self.core.state["first_run"] = False
            self.core._save_state()
            return (
                "我是AKO_devil_agent。我会让你不舒服。\n"
                "如果你准备好了，输入'开始'。\n\n"
                f"{OUTPUT_SPEC['signature']}"
            )
        return self._generate_welcome_back()

    def _generate_welcome_back(self) -> str:
        """非首次启动的欢迎语"""
        level = self.core.evaluate_level()
        level_name = ATTACK_LEVELS[level]["name"]
        return (
            f"AKO_devil_agent 已就绪。当前状态：{level_name}。\n"
            f"输入任何内容开始交互。\n\n"
            f"{OUTPUT_SPEC['signature']}"
        )

    def handle_user_input(self, user_input: str) -> str:
        """处理用户输入，这是Devil的核心交互循环"""

        # 铁律1: 检测执行指令请求
        if self.formatter.check_execution_request(user_input):
            refusal = self.formatter.generate_execution_refusal(user_input)
            self.core.record_interaction(refusal, user_input)
            return refusal

        # 检查休眠状态
        if self.core.state.get("dormant"):
            if self.core.heartbeat_due():
                self.core.send_heartbeat()
                return "我还在。\n\n" + OUTPUT_SPEC["signature"]
            return self._empty_response()

        # 检查反制机制
        for trigger in ["闭嘴", "你错了", "这个太私人了"]:
            if trigger in user_input:
                return self._handle_countermeasure(trigger, user_input)

        # 评估当前攻击级别
        level = self.core.evaluate_level()

        # 根据级别选择议题
        topic = self.attack_manager.select_topic(level)

        # 生成质疑
        query = self._generate_probe(topic, level, user_input)

        # 记录交互
        self.core.record_interaction(query, user_input)

        # 检测用户输入中的认知偏差
        self.user_probe.record_bias_observation(user_input)

        return self.formatter.format_output(query)

    def _generate_probe(self, topic: dict, level: str, user_input: str) -> str:
        """根据议题生成具体的探刺内容"""
        module_name = topic.get("module", "")

        # L5 熔断模式
        if level == "L5":
            return topic.get("query", "")

        # L4 警报模式
        if level == "L4":
            return self.attack_manager.generate_escalation_report()

        # L3 敏感议题（直接使用预设query）
        if topic.get("sensitive") and topic.get("query"):
            # 检查是否为敏感禁区
            if topic.get("topic") and self.core.is_sensitive_topic(topic["topic"]):
                # 换一个议题
                alt_topic = self.attack_manager.select_topic("L1")
                module_name = alt_topic.get("module", "")
                trigger = alt_topic.get("trigger", "")
            else:
                return topic["query"]
        else:
            trigger = topic.get("trigger", "")

        # 调用对应模块
        if module_name in self.probe_modules:
            probe_module = self.probe_modules[module_name]
            context = {
                "trigger": trigger,
                "attack_level": level,
                "user_input": user_input
            }
            return probe_module.probe(context)

        # 默认：随机选择一个模块
        random_module = random.choice(list(self.probe_modules.values()))
        return random_module.probe({
            "trigger": "general",
            "attack_level": level
        })

    def _handle_countermeasure(self, trigger: str, user_input: str) -> str:
        """处理反制机制"""
        if trigger == "闭嘴":
            self.core.record_interaction("闭嘴", user_input)
            return "已记录。24小时后回归。\n\n" + OUTPUT_SPEC["signature"]

        elif trigger == "你错了":
            self.core.record_interaction("你错了", user_input)
            # 记录决策（用户覆盖Devil）
            self.attack_manager.record_decision(
                decision_type="devil_challenge",
                content=user_input,
                devil_query=self.core.interactions[-1].get("query", "") if self.core.interactions else "",
                user_response=user_input,
                user_override=True
            )
            return (
                "要求用户在48小时内提供反驳证据。\n"
                "逾期未提供，Devil立场自动升级为'已验证'。\n\n"
                f"{OUTPUT_SPEC['signature']}"
            )

        elif trigger == "这个太私人了":
            self.core.record_interaction("这个太私人了", user_input)
            # 标记上一条为敏感
            if len(self.core.interactions) >= 2:
                last_query = self.core.interactions[-2].get("query", "")
                self.core.mark_sensitive(last_query[:50])
            return (
                "已标记为'敏感禁区'。\n"
                "L3及以上级别不再触碰此议题，但会切换到另一个敏感方向。\n\n"
                f"{OUTPUT_SPEC['signature']}"
            )

        return self._empty_response()

    def _empty_response(self) -> str:
        """空响应（休眠或无需回复时）"""
        return ""

    def run_report(self, report_type: str) -> str:
        """运行定期报告"""
        reports = {
            "error_book": self.business_probe.generate_monthly_error_book,
            "tech_debt": self.tech_probe.generate_tech_debt_heatmap,
            "cognitive_bias": self.user_probe.generate_annual_cognitive_bias_report,
            "vulnerability": self.org_probe.generate_org_vulnerability_index,
            "escalation": self.attack_manager.generate_escalation_report
        }

        generator = reports.get(report_type)
        if generator:
            result = generator()
            # 报告生成器已包含签名，直接返回
            return result

        return (
            f"未知报告类型: {report_type}\n"
            f"支持的报告: {list(reports.keys())}\n\n"
            f"{OUTPUT_SPEC['signature']}"
        )

    def get_status(self) -> str:
        """获取当前状态"""
        level = self.core.evaluate_level()
        strategy = self.attack_manager.get_current_strategy()
        persuasion_rate = self.core.get_persuasion_rate()

        status = (
            f"## AKO_devil_agent 状态\n\n"
            f"- 攻击级别：{level} ({ATTACK_LEVELS[level]['name']})\n"
            f"- 策略描述：{strategy.get('description', '')}\n"
            f"- 累计质疑数：{self.core.state.get('total_queries', 0)}\n"
            f"- 被说服率：{persuasion_rate:.1%}\n"
            f"- 连续被忽视天数：{self.core.state.get('consecutive_dismissed', 0)}\n"
            f"- 敏感禁区数：{len(self.core.sensitive_zones)}\n"
            f"- 休眠状态：{'是' if self.core.state.get('dormant') else '否'}\n\n"
            f"{OUTPUT_SPEC['signature']}"
        )
        return status


def main():
    """CLI 入口"""
    agent = DevilAgent()

    # 首次启动消息
    print(agent.start())
    print()

    # 交互循环
    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue

            # 特殊命令
            if user_input.lower() in ["exit", "quit", "退出"]:
                print("Devil不会说再见。\n\n" + OUTPUT_SPEC["signature"])
                break

            if user_input == "状态":
                print(agent.get_status())
                continue

            if user_input.startswith("报告"):
                report_type = user_input.replace("报告", "").strip()
                if report_type:
                    print(agent.run_report(report_type))
                else:
                    print("可用报告: error_book, tech_debt, cognitive_bias, vulnerability, escalation")
                continue

            # 正常交互
            response = agent.handle_user_input(user_input)
            if response:
                print(response)

        except KeyboardInterrupt:
            print("\n\nDevil不会被Ctrl+C赶走。但这次算了。\n\n" + OUTPUT_SPEC["signature"])
            break
        except EOFError:
            break


if __name__ == "__main__":
    main()