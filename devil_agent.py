"""
AKO_devil_agent 主入口 v1.2
对抗性审查系统 — 唯一使命：让AKO体系负责人每周至少一次感到"这AI说得对，但我真不想听"
v1.1: 新增耳光触发器、第6条铁律、耳光命中率报告
v1.2: 内部三角圆桌辩论系统（PROD/FACT/DAMP + 确定性双裁判 + CHRO审计账本）
"""
import sys
import random
import webbrowser
from datetime import datetime
from devil_core import DevilCore
from attack_manager import AttackManager
from output_formatter import OutputFormatter
from icon_loader import IconLoader
from modules.business import BusinessProbe
from modules.tech import TechProbe
from modules.user import UserProbe
from modules.org import OrgProbe
from modules.slap import SlapProbe
from council import DevilCouncil
import config


class DevilAgent:
    """AKO_devil_agent 主控制器 v1.2"""

    def __init__(self):
        self.core = DevilCore()
        self.attack_manager = AttackManager(self.core)
        self.formatter = OutputFormatter()

        # 五大模块
        self.business_probe = BusinessProbe()
        self.tech_probe = TechProbe()
        self.user_probe = UserProbe()
        self.org_probe = OrgProbe()
        self.slap_probe = SlapProbe()  # v1.1 新增

        # v1.2: 内部三角圆桌
        self.council = DevilCouncil()

        self.probe_modules = {
            "business": self.business_probe,
            "tech": self.tech_probe,
            "user": self.user_probe,
            "org": self.org_probe,
            "slap": self.slap_probe
        }

    def start(self) -> str:
        """首次启动"""
        if self.core.state.get("first_run"):
            self.core.state["first_run"] = False
            self.core._save_state()
            return (
                "我是AKO_devil_agent。我会让你不舒服。\n"
                "如果你准备好了，输入'开始'。\n\n"
                f"{config.OUTPUT_SPEC['signature']}"
            )
        return self._generate_welcome_back()

    def _generate_welcome_back(self) -> str:
        """非首次启动的欢迎语"""
        level = self.core.evaluate_level()
        level_name = config.ATTACK_LEVELS[level]["name"]
        dominant = self.slap_probe.get_dominant_pattern()
        status = (
            f"AKO_devil_agent 已就绪。当前状态：{level_name}。\n"
            f"输入任何内容开始交互。\n"
        )
        if dominant != "尚未积累足够数据":
            status += f"你最主要的回避模式：{dominant}。\n"
        return f"{status}\n{config.OUTPUT_SPEC['signature']}"

    def handle_user_input(self, user_input: str) -> str:
        """处理用户输入，这是Devil的核心交互循环 - v1.2增强版"""

        self.core.mark_input_received()
        self.council.mark_input()

        # 铁律1: 检测执行指令请求
        if self.formatter.check_execution_request(user_input):
            refusal = self.formatter.generate_execution_refusal(user_input)
            self.core.record_interaction(refusal, user_input)
            return refusal

        # 检查休眠状态
        if self.core.state.get("dormant"):
            if self.core.heartbeat_due():
                self.core.send_heartbeat()
                return "我还在。\n\n" + config.OUTPUT_SPEC["signature"]
            return ""

        # 检查反制机制
        for trigger in ["闭嘴", "你错了", "这个太私人了"]:
            if trigger in user_input:
                return self._handle_countermeasure(trigger, user_input)

        # 评估当前攻击级别（优先于其他逻辑）
        level = self.core.evaluate_level()

        # v1.2: L5强制冷却 → 三角议会休会
        if level == "L5":
            # 检查休会退出条件
            adjourn_exit = self.council.check_adjourn_resume(user_input)
            if not self.council.is_adjourned:
                self.council.adjourn()
            if adjourn_exit:
                self.core.exit_meltdown()
                self.council.resume()
                return (
                    "强制冷却解除。议会恢复运作。\n"
                    f"退出原因：{'冷静期超时' if adjourn_exit == 'silence_timeout' else '自我确认'}。\n"
                    "Devil恢复工作。\n\n"
                    f"{config.OUTPUT_SPEC['signature']}"
                )
            # 仍在休会：停止输出
            return ""

        # v1.1: 优先检查耳光触发器
        slap_trigger = self.slap_probe.detect_slap_trigger(user_input)
        if slap_trigger:
            slap_response = self.slap_probe.generate_slap(slap_trigger)
            self.core.record_interaction(slap_response, user_input, discomfort=True)
            if slap_trigger["trigger_name"] == "procrastination":
                self.slap_probe.schedule_procrastination_followup(user_input)
            return slap_response

        # 根据级别选择议题
        topic = self.attack_manager.select_topic(level)

        # v1.2: 通过三角圆桌生成质疑
        query = self._generate_probe_with_council(topic, level, user_input)

        # 如果 council 驳回了（返回空），尝试原模块直出（降级兼容）
        if not query:
            query = self._generate_probe(topic, level, user_input)

        # 记录交互
        discomfort = level in ["L3", "L4"]
        self.core.record_interaction(query, user_input, discomfort=discomfort)

        # 检测用户输入中的认知偏差
        self.user_probe.record_bias_observation(user_input)

        return self.formatter.format_output(query)

    def _generate_probe(self, topic: dict, level: str, user_input: str) -> str:
        """根据议题生成具体的探刺内容（v1.1 原版，作为 council 降级兼容）"""
        module_name = topic.get("module", "")

        if level == "L5":
            return topic.get("query", "")

        if level == "L4":
            return self.attack_manager.generate_escalation_report()

        # L3 敏感议题
        if topic.get("sensitive") and topic.get("query"):
            if topic.get("topic") and self.core.is_sensitive_topic(topic["topic"]):
                alt_topic = self.attack_manager.select_topic("L1")
                module_name = alt_topic.get("module", "")
                trigger = alt_topic.get("trigger", "")
            else:
                return topic["query"]
        else:
            trigger = topic.get("trigger", "")

        if module_name in self.probe_modules:
            probe_module = self.probe_modules[module_name]
            context = {"trigger": trigger, "attack_level": level, "user_input": user_input}
            return probe_module.probe(context)

        random_module = random.choice(
            [m for m in self.probe_modules.values() if not isinstance(m, SlapProbe)]
        )
        return random_module.probe({"trigger": "general", "attack_level": level})

    def _generate_probe_with_council(self, topic: dict, level: str,
                                      user_input: str) -> str:
        """
        v1.2: 通过三角圆桌生成质疑
        流程：PROD → FACT → 裁判引擎1 → DAMP → 裁判引擎2 → 输出
        只输出通过双裁判的质疑
        """
        module_name = topic.get("module", "general")

        # L4/L5 不经过 council，直接输出
        if level in ("L4", "L5"):
            if level == "L4":
                return self.attack_manager.generate_escalation_report()
            return topic.get("query", "")

        # 构建业务上下文
        business_context = {}

        # 涉及周明静的议题，标记关系保护
        if "明静" in user_input or "周明静" in user_input:
            business_context["protect_relationship"] = True

        # 按模块添加特定上下文
        if module_name == "user":
            business_context["logic_flaw"] = (
                self.slap_probe.get_dominant_pattern()
                if self.slap_probe.get_dominant_pattern() != "尚未积累足够数据"
                else ""
            )

        # 运行辩论
        result = self.council.run_debate(
            module=module_name,
            trigger=topic.get("trigger", "general"),
            user_input=user_input,
            business_context=business_context
        )

        return result.get("output", "")

    def _handle_countermeasure(self, trigger: str, user_input: str) -> str:
        """处理反制机制"""
        if trigger == "闭嘴":
            self.core.record_interaction("闭嘴", user_input)
            return "已记录。24小时后回归。\n\n" + config.OUTPUT_SPEC["signature"]

        elif trigger == "你错了":
            self.core.record_interaction("你错了", user_input)
            self.attack_manager.record_decision(
                decision_type="devil_challenge",
                content=user_input,
                devil_query=(
                    self.core.interactions[-1].get("query", "")
                    if self.core.interactions else ""
                ),
                user_response=user_input,
                user_override=True
            )
            return (
                "要求用户在48小时内提供反驳证据。\n"
                "逾期未提供，Devil立场自动升级为'已验证'。\n\n"
                f"{config.OUTPUT_SPEC['signature']}"
            )

        elif trigger == "这个太私人了":
            self.core.record_interaction("这个太私人了", user_input)
            if len(self.core.interactions) >= 2:
                last_query = self.core.interactions[-2].get("query", "")
                self.core.mark_sensitive(last_query[:50])
            return (
                "已标记为'敏感禁区'。\n"
                "L3及以上级别不再触碰此议题，但会切换到另一个敏感方向。\n\n"
                f"{config.OUTPUT_SPEC['signature']}"
            )

        return ""

    def run_report(self, report_type: str) -> str:
        """运行定期报告 - v1.2 新增议会报告"""
        reports = {
            "error_book": self.business_probe.generate_monthly_error_book,
            "tech_debt": self.tech_probe.generate_tech_debt_heatmap,
            "cognitive_bias": self.user_probe.generate_annual_cognitive_bias_report,
            "vulnerability": self.org_probe.generate_org_vulnerability_index,
            "escalation": self.attack_manager.generate_escalation_report,
            "slap_metrics": self._generate_slap_report,
            "council": self.council.generate_council_report
        }

        generator = reports.get(report_type)
        if generator:
            return generator()

        return (
            f"未知报告类型: {report_type}\n"
            f"支持的报告: {list(reports.keys())}\n\n"
            f"{config.OUTPUT_SPEC['signature']}"
        )

    def _generate_slap_report(self) -> str:
        """v1.1: 生成耳光命中率报告"""
        metrics = self.slap_probe.get_slap_metrics()
        dominant = self.slap_probe.get_dominant_pattern()
        targets = config.SLAP_METRICS

        report = [
            "## 耳光命中率报告",
            "",
            f"### 累计数据",
            f"- 总耳光数：{metrics['total_slaps']}",
            f"- 主观感觉替代数据：{metrics['vague_reasoning_count']} 次",
            f"- 回避关键数字：{metrics['avoiding_numbers_count']} 次",
            f"- 重复失败模式：{metrics['repeating_failure_count']} 次",
            f"- 情绪/身体挡箭牌：{metrics['emotional_defense_count']} 次",
            f"- 拖延决策：{metrics['procrastination_count']} 次",
            "",
            f"### 最主要回避模式",
            f"**{dominant}**",
            "",
            f"### 月度目标",
            f"- 沉默超10秒：≥{targets['monthly_silence_over_10s']}次",
            f"- 想反驳但找不到数据：≥{targets['monthly_cant_refute']}次",
            f"- 当天睡不着：≥{targets['monthly_sleepless_night']}次",
            f"(Devil不为此道歉)",
            "",
            f"{config.OUTPUT_SPEC['signature']}"
        ]
        return "\n".join(report)

    def get_status(self) -> str:
        """获取当前状态 v1.2"""
        level = self.core.evaluate_level()
        strategy = self.attack_manager.get_current_strategy()
        persuasion_rate = self.core.get_persuasion_rate()
        slap_metrics = self.slap_probe.get_slap_metrics()
        council_stats = self.council.get_council_statistics()

        status = (
            f"## AKO_devil_agent 状态 (v1.2)\n\n"
            f"### 攻击系统\n"
            f"- 攻击级别：{level} ({config.ATTACK_LEVELS[level]['name']})\n"
            f"- 策略描述：{strategy.get('description', '')}\n"
            f"- 累计质疑数：{self.core.state.get('total_queries', 0)}\n"
            f"- 被说服率：{persuasion_rate:.1%}\n"
            f"- 连续被忽视天数：{self.core.state.get('consecutive_dismissed', 0)}\n"
            f"- 敏感禁区数：{len(self.core.sensitive_zones)}\n"
            f"- 总耳光数：{slap_metrics['total_slaps']}\n"
            f"- 休眠状态：{'是' if self.core.state.get('dormant') else '否'}\n"
            f"\n### 内部议会\n"
            f"- 议会状态：{'休会中' if council_stats['adjourned'] else '正常运作'}\n"
            f"- 辩论次数：{council_stats['total_sessions']}\n"
            f"- 证据充足率(A)：{council_stats['grade_a_count']} 次\n"
            f"- 驳回率(C)：{council_stats['dismissal_rate']}%\n"
            f"- P1 立即输出：{council_stats['priority_p1_count']} 次\n"
            f"- P3 暂缓：{council_stats['priority_p3_count']} 次\n"
            f"- 待攻击队列：{council_stats['pending_queue_size']} 条\n\n"
            f"{config.OUTPUT_SPEC['signature']}"
        )
        return status


def _open_dashboard():
    """生成并打开仪表盘 HTML，内嵌 devil_eye 图标"""
    from pathlib import Path
    dashboard_html = IconLoader.get_dashboard_html()
    dashboard_path = Path(__file__).parent / "assets" / "dashboard.html"
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(dashboard_html, encoding="utf-8")
    # [CLEANED_GUI] webbrowser.open(f"file:///{dashboard_path.as_posix()}")

def main():
    """CLI 入口"""
    agent = DevilAgent()

    # 启动时打开可视化仪表盘
    try:
        _open_dashboard()
    except Exception:
        pass  # 图标加载失败不影响核心功能

    print(agent.start())
    print()

    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "退出"]:
                print("Devil不会说再见。\n\n" + config.OUTPUT_SPEC["signature"])
                break

            if user_input == "状态":
                print(agent.get_status())
                continue

            if user_input.startswith("报告"):
                report_type = user_input.replace("报告", "").strip()
                if report_type:
                    print(agent.run_report(report_type))
                else:
                    print("可用报告: error_book, tech_debt, cognitive_bias, vulnerability, escalation, slap_metrics, council")
                continue

            response = agent.handle_user_input(user_input)
            if response:
                print(response)

        except KeyboardInterrupt:
            print("\n\nDevil不会被Ctrl+C赶走。但这次算了。\n\n" + config.OUTPUT_SPEC["signature"])
            break
        except EOFError:
            break


if __name__ == "__main__":
    main()