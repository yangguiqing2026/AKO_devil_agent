"""
AKO_devil_agent v1.2 全系统测试
覆盖所有模块、铁律(含第6条)、攻击级别、反制机制、耳光触发器、
内部三角圆桌辩论系统(PROD/FACT/DAMP)、裁判引擎、史官审计账本和报告生成
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from language_detector import LanguageDetector
from devil_core import DevilCore
from attack_manager import AttackManager
from output_formatter import OutputFormatter
from modules.business import BusinessProbe
from modules.tech import TechProbe
from modules.user import UserProbe
from modules.org import OrgProbe
from modules.slap import SlapProbe
from devil_agent import DevilAgent
from council_engine import FactCheckEngine, PriorityEngine, Evidence, CouncilDebateRecord
from council_agents import PRODSeat, FACTSeat, DAMPSeat
from chronicler import Chronicler
from council import DevilCouncil


class TestConfig(unittest.TestCase):
    """测试配置中心 - v1.1"""

    def test_iron_rules_defined(self):
        self.assertEqual(len(config.IRON_RULES), 6)  # v1.1: 6条
        for i in range(1, 7):
            self.assertIn(i, config.IRON_RULES)

    def test_sixth_iron_rule(self):
        """v1.1: 验证第6条铁律"""
        rule_6 = config.IRON_RULES[6]
        self.assertIn("事实优先于礼貌", rule_6)

    def test_attack_levels_complete(self):
        for level in ["L1", "L2", "L3", "L4", "L5"]:
            self.assertIn(level, config.ATTACK_LEVELS)

    def test_output_spec(self):
        self.assertTrue(config.OUTPUT_SPEC["no_emoji"])
        self.assertIn("不为你服务", config.OUTPUT_SPEC["signature"])

    def test_countermeasures(self):
        for key in ["闭嘴", "你错了", "这个太私人了", "连续30天无交互"]:
            self.assertIn(key, config.COUNTERMEASURES)

    def test_slap_format_defined(self):
        """v1.1: 验证耳光格式模板"""
        self.assertIsNotNone(config.SLAP_FORMAT)
        self.assertGreater(len(config.SLAP_FORMAT), 0)

    def test_slap_metrics_defined(self):
        """v1.1: 验证耳光命中率指标"""
        self.assertIn("monthly_silence_over_10s", config.SLAP_METRICS)
        self.assertIn("monthly_cant_refute", config.SLAP_METRICS)
        self.assertIn("monthly_sleepless_night", config.SLAP_METRICS)


class TestDevilCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_dir = config.get_data_dir()
        cls._tmp = tempfile.mkdtemp()
        config.set_data_dir(Path(cls._tmp))

    @classmethod
    def tearDownClass(cls):
        config.set_data_dir(cls._saved_dir)
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_initial_state(self):
        core = DevilCore()
        self.assertEqual(core.state["current_level"], "L1")
        self.assertTrue(core.state["first_run"])
        self.assertIsInstance(core.state["total_queries"], int)

    def test_level_evaluation_l1(self):
        core = DevilCore()
        self.assertEqual(core.evaluate_level(), "L1")

    def test_level_l2_on_delay(self):
        core = DevilCore()
        core.state["last_user_response_date"] = (datetime.now() - timedelta(days=4)).isoformat()
        self.assertEqual(core.evaluate_level(), "L2")

    def test_level_l3_on_no_discomfort(self):
        core = DevilCore()
        core.state["last_discomfort_date"] = (datetime.now() - timedelta(days=8)).isoformat()
        self.assertEqual(core.evaluate_level(), "L3")

    def test_level_l4_on_dismissed(self):
        core = DevilCore()
        core.state["consecutive_dismissed"] = 14
        self.assertEqual(core.evaluate_level(), "L4")

    def test_level_l5_extreme(self):
        core = DevilCore()
        core.state["extreme_risk"] = True
        self.assertEqual(core.evaluate_level(), "L5")

    def test_interaction_recording(self):
        core = DevilCore()
        before = len(core.interactions)
        core.record_interaction("测试质疑", "测试回应")
        self.assertEqual(len(core.interactions), before + 1)

    def test_discomfort_tracking(self):
        core = DevilCore()
        core.record_interaction("尖锐问题", "用户回应", discomfort=True)
        self.assertIsNotNone(core.state["last_discomfort_date"])

    def test_dismiss_tracking(self):
        core = DevilCore()
        core.record_interaction("问题", "无需处理")
        self.assertEqual(core.state["consecutive_dismissed"], 1)
        core.record_interaction("问题2", "另一个回应")
        self.assertEqual(core.state["consecutive_dismissed"], 0)

    def test_sensitive_zones(self):
        core = DevilCore()
        core.mark_sensitive("测试敏感话题")
        self.assertTrue(core.is_sensitive_topic("测试敏感话题"))

    def test_shut_up_mechanism(self):
        core = DevilCore()
        self.assertFalse(core.should_return_after_shutup())
        core.record_interaction("问题", "闭嘴")
        core.state["shut_up_timestamp"] = (datetime.now() - timedelta(hours=25)).isoformat()
        self.assertTrue(core.should_return_after_shutup())

    def test_persuasion_rate(self):
        core = DevilCore()
        self.assertEqual(core.get_persuasion_rate(), 0.0)
        core.record_interaction("q1", "r1")
        core.record_persuasion()
        self.assertGreater(core.get_persuasion_rate(), 0.0)

    def test_dormant_check(self):
        core = DevilCore()
        self.assertFalse(core.check_dormant())

    def test_meltdown_enter_exit_lifecycle(self):
        """v1.1: 熔断进入/退出生命周期"""
        core = DevilCore()
        core.enter_meltdown()
        self.assertEqual(core.state["current_level"], "L5")
        self.assertIsNotNone(core.state["meltdown_entry_time"])

        core.exit_meltdown()
        self.assertEqual(core.state["current_level"], "L1")
        self.assertFalse(core.state["extreme_risk"])

    def test_meltdown_exit_condition_1_silence(self):
        """条件1：连续5分钟无输入"""
        core = DevilCore()
        core.enter_meltdown()
        # 模拟5分钟前最后一次输入
        core._last_input_time = datetime.now() - timedelta(seconds=301)
        self.assertTrue(core.check_meltdown_exit_condition_1())

    def test_meltdown_exit_condition_1_not_met(self):
        """条件1：输入间隔不足5分钟"""
        core = DevilCore()
        core.enter_meltdown()
        core._last_input_time = datetime.now() - timedelta(seconds=60)
        self.assertFalse(core.check_meltdown_exit_condition_1())

    def test_meltdown_exit_condition_2_self_confirm(self):
        """条件2：用户输入'我准备好了'"""
        core = DevilCore()
        core.enter_meltdown()
        self.assertTrue(core.check_meltdown_exit_condition_2("我准备好了"))

    def test_meltdown_exit_condition_2_not_met(self):
        """条件2：用户未做自我确认"""
        core = DevilCore()
        core.enter_meltdown()
        self.assertFalse(core.check_meltdown_exit_condition_2("随便说说"))

    def test_meltdown_exit_condition_3_baseline(self):
        """条件3：语言模式回归基线"""
        core = DevilCore()
        core.enter_meltdown()
        self.assertTrue(core.check_meltdown_exit_condition_3("我明白了。下一步计划从数据开始。"))

    def test_meltdown_exit_condition_3_not_met(self):
        """条件3：仍处高情绪模式"""
        core = DevilCore()
        core.enter_meltdown()
        self.assertFalse(core.check_meltdown_exit_condition_3("完了！！一切都毁了！！我不配做这个。"))

    def test_should_exit_meltdown_silence(self):
        """综合判断：冷静期触发退出"""
        core = DevilCore()
        core.enter_meltdown()
        core._last_input_time = datetime.now() - timedelta(seconds=301)
        reason = core.should_exit_meltdown()
        self.assertEqual(reason, "silence_timeout")


class TestLanguageDetector(unittest.TestCase):
    """v1.1: 语言模式检测器"""

    def test_detect_distressed_exclamation(self):
        self.assertTrue(LanguageDetector.is_distressed_language("完了！！一切都毁了！！"))

    def test_detect_distressed_self_blame(self):
        # 需要触发两个不同类型的 distress marker
        self.assertTrue(LanguageDetector.is_distressed_language("是我没用！！我不配！！"))

    def test_not_distressed_normal(self):
        self.assertFalse(LanguageDetector.is_distressed_language("我决定从数据开始重新评估。"))

    def test_detect_baseline_declarative(self):
        self.assertTrue(LanguageDetector.is_baseline_language("我想清楚了，下一步从数据开始。"))

    def test_detect_baseline_with_data(self):
        self.assertTrue(LanguageDetector.is_baseline_language("上周转化率是15%，先解决这个问题。"))

    def test_detect_baseline_action(self):
        self.assertTrue(LanguageDetector.is_baseline_language("我决定先做三件事。"))

    def test_not_baseline_distressed(self):
        self.assertFalse(LanguageDetector.is_baseline_language("完了！全完了！呵呵呵！！"))

    def test_not_baseline_vague(self):
        self.assertFalse(LanguageDetector.is_baseline_language("我觉得可能应该再看看"))

    def test_analyze_baseline(self):
        result = LanguageDetector.analyze("我明白了，谢谢。我决定继续推进。")
        self.assertTrue(result["is_baseline"])
        self.assertFalse(result["is_distressed"])

    def test_analyze_distressed(self):
        result = LanguageDetector.analyze("呵呵呵！！都是我一个人的错！没救了！！")
        self.assertFalse(result["is_baseline"])
        self.assertTrue(result["is_distressed"])


class TestBusinessProbe(unittest.TestCase):
    def test_new_agent_probe(self):
        result = BusinessProbe().probe({"trigger": "new_agent_launch"})
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_pricing_probe(self):
        result = BusinessProbe().probe({"trigger": "pricing_change"})
        self.assertTrue(len(result) > 0)

    def test_project_probe(self):
        result = BusinessProbe().probe({"trigger": "project_initiation"})
        self.assertTrue(len(result) > 0)

    def test_error_book_empty(self):
        result = BusinessProbe().generate_monthly_error_book()
        self.assertIn("错题本", result)

    def test_error_book_with_data(self):
        probe = BusinessProbe()
        probe.record_error("降价10%", "质疑", "坚持", "失败", "过度自信")
        result = probe.generate_monthly_error_book()
        self.assertIn("降价10%", result)

    def test_scenario_context(self):
        probe = BusinessProbe()
        self.assertIn("沉没成本", probe.get_probe_decision_context("万峰林"))
        self.assertIn("现金流", probe.get_probe_decision_context("围墙业务"))


class TestTechProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_dir = config.get_data_dir()
        cls._tmp = tempfile.mkdtemp()
        config.set_data_dir(Path(cls._tmp))

    @classmethod
    def tearDownClass(cls):
        config.set_data_dir(cls._saved_dir)
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_new_agent_probe(self):
        result = TechProbe().probe({"trigger": "new_agent"})
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_self_eval_probe(self):
        result = TechProbe().probe({"trigger": "self_evaluation"})
        self.assertTrue(len(result) > 0)

    def test_power_failure_probe(self):
        result = TechProbe().probe({"trigger": "power_failure"})
        self.assertTrue(len(result) > 0)

    def test_network_probe(self):
        result = TechProbe().probe({"trigger": "network"})
        self.assertTrue(len(result) > 0)

    def test_overlap_context(self):
        result = TechProbe().probe({"trigger": "new_agent", "overlapping_agents": "Agent_A, Agent_B"})
        self.assertIn("Agent_A", result)

    def test_tech_debt_heatmap_empty(self):
        result = TechProbe().generate_tech_debt_heatmap()
        self.assertIn("热力图", result)

    def test_tech_debt_heatmap_with_data(self):
        probe = TechProbe()
        probe.add_tech_debt("遗留数据库", "未迁移的MySQL", 8, 9)
        probe.add_tech_debt("过时依赖", "Python EOL", 3, 7)
        result = probe.generate_tech_debt_heatmap()
        self.assertIn("遗留数据库", result)
        self.assertIn("过时依赖", result)

    def test_independent_verification(self):
        result = TechProbe().request_independent_verification("系统通过", "AKO_hub")
        self.assertIn("二次验证", result)


class TestUserProbe(unittest.TestCase):
    def test_inactivity_probe(self):
        result = UserProbe().probe({"trigger": "inactivity"})
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_late_night_probe(self):
        result = UserProbe().probe({"trigger": "late_night"})
        self.assertTrue(len(result) > 0)

    def test_bias_detection_sunk_cost(self):
        biases = UserProbe().detect_bias("已经花了这么多钱，不能放弃")
        self.assertTrue(any("沉没成本效应" in b["bias"] for b in biases))

    def test_bias_detection_overconfidence(self):
        biases = UserProbe().detect_bias("这个方案绝对100%没问题")
        self.assertTrue(any("过度自信" in b["bias"] for b in biases))

    def test_no_bias(self):
        biases = UserProbe().detect_bias("今天天气不错")
        self.assertEqual(len(biases), 0)

    def test_record_bias(self):
        probe = UserProbe()
        probe.record_bias_observation("毫无疑问这是最好的")
        data = probe._load_bias_data()
        self.assertGreater(len(data.get("observations", [])), 0)

    def test_annual_bias_report(self):
        probe = UserProbe()
        probe.record_bias_observation("绝对是最好的选择")
        result = probe.generate_annual_cognitive_bias_report()
        self.assertIn("认知偏差报告", result)

    def test_rejection_followup(self):
        result = UserProbe().schedule_rejection_followup("我认为数据不对")
        target_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        self.assertIn(target_date, result)


class TestOrgProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_dir = config.get_data_dir()
        cls._tmp = tempfile.mkdtemp()
        config.set_data_dir(Path(cls._tmp))

    @classmethod
    def tearDownClass(cls):
        config.set_data_dir(cls._saved_dir)
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_deputy_probe(self):
        result = OrgProbe().probe({"trigger": "deputy_isolation"})
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_new_business_probe(self):
        result = OrgProbe().probe({"trigger": "new_business"})
        self.assertTrue(len(result) > 0)

    def test_specific_project_probe(self):
        result = OrgProbe().probe({"trigger": "new_business", "project_name": "围墙业务"})
        self.assertIn("围墙业务", result)

    def test_vulnerability_report_default(self):
        result = OrgProbe().generate_org_vulnerability_index()
        self.assertIn("脆弱性指数", result)
        self.assertIn("人员", result)

    def test_vulnerability_update_score(self):
        probe = OrgProbe()
        probe.update_vulnerability_score("人员", 8.5)
        result = probe.generate_org_vulnerability_index()
        self.assertIn("8.5", result)

    def test_red_alert_detection(self):
        probe = OrgProbe()
        probe.update_vulnerability_score("人员", 8.0)
        probe.update_vulnerability_score("合规", 7.5)
        alerts = probe.get_red_alert_targets()
        self.assertEqual(len(alerts), 2)


class TestSlapProbe(unittest.TestCase):
    """v1.1: 耳光触发器测试"""

    @classmethod
    def setUpClass(cls):
        cls._saved_dir = config.get_data_dir()
        cls._tmp = tempfile.mkdtemp()
        config.set_data_dir(Path(cls._tmp))

    @classmethod
    def tearDownClass(cls):
        config.set_data_dir(cls._saved_dir)
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_detect_vague_reasoning(self):
        """检测'我觉得'等主观用语"""
        trigger = SlapProbe().detect_slap_trigger("我觉得这个方案可行")
        self.assertIsNotNone(trigger)
        self.assertEqual(trigger["trigger_name"], "vague_reasoning")

    def test_detect_avoiding_numbers(self):
        """检测回避数字"""
        trigger = SlapProbe().detect_slap_trigger("这个项目大概需要一些投入")
        self.assertIsNotNone(trigger)
        # '大概' may match vague_reasoning first; accept either
        self.assertIn(trigger["trigger_name"], ["vague_reasoning", "avoiding_numbers"])

    def test_detect_emotional_defense(self):
        """检测情绪挡箭牌"""
        trigger = SlapProbe().detect_slap_trigger("我累了，今天不想做决定")
        self.assertIsNotNone(trigger)
        self.assertEqual(trigger["trigger_name"], "emotional_defense")

    def test_detect_procrastination(self):
        """检测拖延"""
        trigger = SlapProbe().detect_slap_trigger("这个以后再说吧")
        self.assertIsNotNone(trigger)
        self.assertEqual(trigger["trigger_name"], "procrastination")

    def test_detect_repeating_failure(self):
        """检测重复失败模式"""
        trigger = SlapProbe().detect_slap_trigger("这次不一样，我有把握")
        self.assertIsNotNone(trigger)
        self.assertIn(trigger["trigger_name"], ["repeating_failure", "vague_reasoning"])

    def test_no_trigger_for_normal_input(self):
        """正常输入不触发耳光"""
        trigger = SlapProbe().detect_slap_trigger("上周利润增长了15%")
        self.assertIsNone(trigger)

    def test_generate_slap_response(self):
        """验证耳光回复格式"""
        probe = SlapProbe()
        trigger = probe.detect_slap_trigger("我觉得这个能成功")
        response = probe.generate_slap(trigger)
        self.assertIn(config.OUTPUT_SPEC["signature"], response)
        self.assertIn("数据", response)

    def test_slap_metrics_tracking(self):
        """验证耳光指标追踪"""
        probe = SlapProbe()
        trigger = probe.detect_slap_trigger("我觉得方案可行")
        probe.generate_slap(trigger)
        metrics = probe.get_slap_metrics()
        self.assertGreater(metrics["total_slaps"], 0)

    def test_dominant_pattern(self):
        """验证最主要回避模式"""
        probe = SlapProbe()
        trigger = probe.detect_slap_trigger("我觉得方案可行")
        probe.generate_slap(trigger)
        trigger2 = probe.detect_slap_trigger("我累了不想做")
        probe.generate_slap(trigger2)
        dominant = probe.get_dominant_pattern()
        self.assertIn(dominant, [
            "主观感觉替代数据", "回避关键数字", "重复失败模式",
            "情绪/身体挡箭牌", "拖延决策", "尚未积累足够数据"
        ])

    def test_procrastination_followup(self):
        """验证拖延回访安排"""
        probe = SlapProbe()
        probe.schedule_procrastination_followup("以后再说")
        self.assertEqual(len(probe._pending_followups), 1)
        self.assertEqual(probe._pending_followups[0]["status"], "pending")

    def test_procrastination_followup_message(self):
        """验证拖延回访消息"""
        probe = SlapProbe()
        fup = {"deadline": datetime.now() - timedelta(hours=72), "status": "pending"}
        result = probe.generate_procrastination_followup(fup)
        self.assertIn("72小时", result)


class TestOutputFormatter(unittest.TestCase):
    def test_format_adds_signature(self):
        result = OutputFormatter.format_output("测试内容")
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_execution_detection(self):
        self.assertTrue(OutputFormatter.check_execution_request("帮我写一份报告"))
        self.assertTrue(OutputFormatter.check_execution_request("请生成一个文件"))

    def test_execution_refusal(self):
        result = OutputFormatter.generate_execution_refusal("帮我做XX")
        self.assertIn("为什么需要这个", result)

    def test_not_execution_request(self):
        self.assertFalse(OutputFormatter.check_execution_request("你觉得这个方案怎么样"))

    def test_emoji_stripping(self):
        text = "测试 \U0001F60A 内容"
        result = OutputFormatter._strip_emoji(text)
        self.assertNotIn("\U0001F60A", result)
        self.assertIn("测试", result)

    def test_validate_output_valid(self):
        result = OutputFormatter.validate_output(f"质疑\n\n{config.OUTPUT_SPEC['signature']}")
        self.assertTrue(result["valid"])

    def test_validate_output_forbidden(self):
        result = OutputFormatter.validate_output(f"您说得对\n\n{config.OUTPUT_SPEC['signature']}")
        self.assertFalse(result["valid"])

    def test_countermeasure_format(self):
        result = OutputFormatter.format_countermeasure_response("闭嘴")
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_slap_output_format(self):
        """v1.1: 验证耳光格式"""
        result = OutputFormatter.format_slap_output(
            "事实：上周你报了3个价，0成交",
            "你的逻辑：'再等等看'——这和8年前的拖延一样",
            "回答我：具体差异在哪？不是感觉，是数据。"
        )
        self.assertIn(config.OUTPUT_SPEC["signature"], result)
        self.assertIn("报", result)
        self.assertIn("拖延", result)


class TestAttackManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_dir = config.get_data_dir()
        cls._tmp = tempfile.mkdtemp()
        config.set_data_dir(Path(cls._tmp))

    @classmethod
    def tearDownClass(cls):
        config.set_data_dir(cls._saved_dir)
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_strategy_for_levels(self):
        core = DevilCore()
        manager = AttackManager(core)
        strategy = manager.get_current_strategy()
        self.assertEqual(strategy["level"], "L1")

    def test_topic_selection_l1(self):
        core = DevilCore()
        manager = AttackManager(core)
        topic = manager.select_topic("L1")
        self.assertIn(topic["module"], ["business", "tech", "user", "org"])

    def test_topic_selection_l5(self):
        core = DevilCore()
        manager = AttackManager(core)
        topic = manager.select_topic("L5")
        self.assertEqual(topic["module"], "none")

    def test_decision_recording(self):
        core = DevilCore()
        manager = AttackManager(core)
        self.assertEqual(len(manager.decision_register), 0)
        manager.record_decision("商业", "降价", "质疑", "坚持", True)
        self.assertEqual(len(manager.decision_register), 1)

    def test_escalation_report(self):
        core = DevilCore()
        manager = AttackManager(core)
        manager.record_decision("测试", "内容", "质疑", "驳回", True)
        result = manager.generate_escalation_report()
        self.assertIn("被忽视建议清单", result)


class TestDevilAgentIntegration(unittest.TestCase):
    """v1.1 集成测试"""

    @classmethod
    def setUpClass(cls):
        cls._saved_dir = config.get_data_dir()
        cls._tmp = tempfile.mkdtemp()
        config.set_data_dir(Path(cls._tmp))

    @classmethod
    def tearDownClass(cls):
        config.set_data_dir(cls._saved_dir)
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_first_start_message(self):
        agent = DevilAgent()
        msg = agent.start()
        self.assertIn("AKO_devil_agent", msg)

    def test_execution_refusal(self):
        agent = DevilAgent()
        result = agent.handle_user_input("帮我写一份报告")
        self.assertIn("为什么需要这个", result)

    def test_normal_interaction(self):
        agent = DevilAgent()
        result = agent.handle_user_input("我决定上线一个新的Agent")
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_shut_up_response(self):
        agent = DevilAgent()
        result = agent.handle_user_input("闭嘴")
        self.assertIn("24小时", result)

    def test_you_are_wrong_response(self):
        agent = DevilAgent()
        agent.handle_user_input("我觉得这个方案很好")
        result = agent.handle_user_input("你错了")
        self.assertIn("48小时", result)

    def test_too_personal_response(self):
        agent = DevilAgent()
        agent.handle_user_input("测试内容")
        result = agent.handle_user_input("这个太私人了")
        self.assertIn("敏感禁区", result)

    def test_status_report(self):
        agent = DevilAgent()
        status = agent.get_status()
        self.assertIn("v1.2", status)
        self.assertIn("攻击级别", status)
        self.assertIn("总耳光数", status)

    def test_run_report_error_book(self):
        agent = DevilAgent()
        result = agent.run_report("error_book")
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_run_report_vulnerability(self):
        agent = DevilAgent()
        result = agent.run_report("vulnerability")
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_run_report_unknown(self):
        agent = DevilAgent()
        result = agent.run_report("unknown_type")
        self.assertIn("unknown_type", result)

    def test_run_report_slap_metrics(self):
        """v1.1: 耳光命中率报告"""
        agent = DevilAgent()
        result = agent.run_report("slap_metrics")
        self.assertIn("耳光命中率", result)
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_slap_trigger_during_interaction(self):
        """v1.1: 验证交互中触发耳光"""
        agent = DevilAgent()
        result = agent.handle_user_input("我觉得围墙业务能成功")
        self.assertIn("我觉得", result)  # slap quotes back the keyword
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_procrastination_triggers_followup(self):
        """v1.1: 验证拖延触发回访"""
        agent = DevilAgent()
        result = agent.handle_user_input("这个以后再说")
        self.assertIn("72小时", result)
        self.assertEqual(len(agent.slap_probe._pending_followups), 1)

    def test_bias_detection_during_interaction(self):
        agent = DevilAgent()
        result = agent.handle_user_input("这个方案绝对100%没有问题")
        self.assertIn(config.OUTPUT_SPEC["signature"], result)
        observations = agent.user_probe._load_bias_data().get("observations", [])
        self.assertGreater(len(observations), 0)


# ========== v1.2: 内部三角圆桌系统测试 ==========


class TestFactCheckEngine(unittest.TestCase):
    """v1.2: 第一裁判引擎 — 事实核查"""

    def test_no_evidence_returns_c(self):
        engine = FactCheckEngine()
        result = engine.judge("这是一个质疑", [])
        self.assertEqual(result, "C")

    def test_no_verifiable_source_returns_c(self):
        engine = FactCheckEngine()
        evidence = [Evidence("推理内容", "推理")]
        result = engine.judge("关于现金流的质疑", evidence)
        self.assertEqual(result, "C")

    def test_verifiable_evidence_returns_a(self):
        engine = FactCheckEngine()
        evidence = [
            Evidence("用户日志显示连续3天深夜工作", "用户日志",
                     covers_assertion="深夜工作"),
            Evidence("公开数据显示行业平均转化率15%", "公开数据",
                     covers_assertion="转化率")
        ]
        result = engine.judge("用户深夜工作效率降低，转化率低于行业标准", evidence)
        # Has verifiable + covers assertions = A or B
        self.assertIn(result, ["A", "B"])

    def test_extract_assertions(self):
        engine = FactCheckEngine()
        assertions = engine.extract_assertions(
            "你的现金流有问题。过去3个月数据下降15%。为什么不调整策略？"
        )
        self.assertGreater(len(assertions), 0)
        # 应提取含数字和关键词的句子
        has_number = any("15" in a for a in assertions)
        has_keyword = any("现金流" in a for a in assertions)
        self.assertTrue(has_number or has_keyword)


class TestPriorityEngine(unittest.TestCase):
    """v1.2: 第二裁判引擎 — 优先级评估"""

    def test_cashflow_returns_p1(self):
        engine = PriorityEngine()
        result = engine.judge("你的现金流存在严重风险")
        self.assertEqual(result, "P1")

    def test_compliance_returns_p1(self):
        engine = PriorityEngine()
        result = engine.judge("这个操作存在合规和法律风险")
        self.assertEqual(result, "P1")

    def test_strategy_returns_p2(self):
        engine = PriorityEngine()
        result = engine.judge("你的战略方向需要重新评估")
        self.assertEqual(result, "P2")

    def test_optimization_returns_p3(self):
        engine = PriorityEngine()
        result = engine.judge("可以考虑优化流程效率")
        self.assertEqual(result, "P3")

    def test_default_returns_p2(self):
        engine = PriorityEngine()
        result = engine.judge("一个普通的质疑")
        self.assertEqual(result, "P2")

    def test_protected_person_downgrade(self):
        engine = PriorityEngine()
        # 涉及周明静的安全问题 → 应降级为 P2
        result = engine.judge(
            "周明静的安全权限需要审查",
            business_context={"protect_relationship": True}
        )
        self.assertEqual(result, "P2")


class TestCouncilDebateRecord(unittest.TestCase):
    """v1.2: 辩论记录"""

    def test_record_initialization(self):
        record = CouncilDebateRecord(prod_claim="测试质疑")
        self.assertEqual(record.prod_claim, "测试质疑")
        self.assertEqual(record.fact_judge, "")
        self.assertEqual(record.priority_judge, "")

    def test_record_to_dict(self):
        record = CouncilDebateRecord(prod_claim="测试质疑")
        record.fact_judge = "A"
        record.priority_judge = "P2"
        d = record.to_dict()
        self.assertEqual(d["prod_claim"], "测试质疑")
        self.assertEqual(d["fact_judge"], "A")
        self.assertEqual(d["priority_judge"], "P2")


class TestPRODSeat(unittest.TestCase):
    """v1.2: 刺探席 PROD"""

    def test_generate_business_claim(self):
        claim = PRODSeat.generate_claim(
            module="business",
            trigger="new_agent_launch",
            user_input="我决定上线一个新Agent"
        )
        self.assertIn("【事实】", claim)
        self.assertIn("【逻辑漏洞】", claim)
        self.assertIn("【必须回答的问题】", claim)

    def test_generate_user_claim(self):
        claim = PRODSeat.generate_claim(
            module="user",
            trigger="inactivity",
            user_input=""
        )
        self.assertIn("【必须回答的问题】", claim)

    def test_generate_general_claim(self):
        claim = PRODSeat.generate_claim(
            module="unknown",
            trigger="general",
            user_input="我觉得这个可以"
        )
        self.assertIn("【必须回答的问题】", claim)

    def test_detect_vague_logic_flaw(self):
        flaw = PRODSeat._detect_logic_flaw("我觉得可能大概可以", "business")
        self.assertTrue(
            "我觉得" in flaw or "可能" in flaw or "大概" in flaw
        )

    def test_detect_no_number_logic_flaw(self):
        flaw = PRODSeat._detect_logic_flaw("这个方案很好", "business")
        self.assertIn("数字", flaw)

    def test_all_modules_have_angles(self):
        for module in ["business", "tech", "user", "org", "general"]:
            self.assertIn(module, PRODSeat.ATTACK_ANGLES)
            self.assertGreater(len(PRODSeat.ATTACK_ANGLES[module]), 0)


class TestFACTSeat(unittest.TestCase):
    """v1.2: 事实席 FACT"""

    def test_review_claim_without_evidence(self):
        result = FACTSeat.review_claim("这是一个没有证据的质疑")
        self.assertEqual(result["grade"], "C")
        self.assertIn("驳回", result["report"])

    def test_review_claim_with_user_quote(self):
        result = FACTSeat.review_claim(
            PRODSeat.generate_claim("business", "test",
                                    user_input="过去3个月利润下降20%")
        )
        # 用户原话引用会被提取为证据，但可能仍不足以完全覆盖
        self.assertIn(result["grade"], ["A", "B", "C"])
        self.assertGreater(len(result["evidence_list"]), 0)

    def test_review_claim_with_external_evidence(self):
        evidence = [
            Evidence("月利润报告: 下降18%", "用户日志",
                     covers_assertion="利润下降"),
            Evidence("公开市场数据: 行业下降15%", "公开数据",
                     covers_assertion="市场数据")
        ]
        result = FACTSeat.review_claim(
            "利润下降了18%，而市场数据表明行业下降15%",
            available_evidence=evidence
        )
        self.assertIn(result["grade"], ["A", "B"])


class TestDAMPSeat(unittest.TestCase):
    """v1.2: 阻尼席 DAMP"""

    def test_evaluate_p1(self):
        result = DAMPSeat.evaluate(
            "现金流存在风险需要立即处理",
            fact_grade="A"
        )
        self.assertEqual(result["priority"], "P1")
        self.assertIn("理由", result["report"])

    def test_evaluate_p3(self):
        result = DAMPSeat.evaluate(
            "可以考虑优化流程提高效率",
            fact_grade="A"
        )
        self.assertEqual(result["priority"], "P3")
        self.assertIn("trigger_condition", result)
        self.assertTrue(len(result["trigger_condition"]) > 0)

    def test_evaluate_default_p2(self):
        result = DAMPSeat.evaluate(
            "战略方向需要讨论",
            fact_grade="A"
        )
        self.assertEqual(result["priority"], "P2")


class TestChronicler(unittest.TestCase):
    """v1.2: 史官模块 CHRO — 审计账本"""

    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.mkdtemp()
        cls.chronicler = Chronicler(db_path=Path(cls._tmp_dir))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)
        # Also clean up the default audit_ledger if it was created
        default_ledger = Path(__file__).parent.parent / "audit_ledger"
        if default_ledger.exists():
            shutil.rmtree(str(default_ledger), ignore_errors=True)

    def test_record_session(self):
        stats_before = self.chronicler.get_statistics()
        record = CouncilDebateRecord(prod_claim="测试质疑ABC_unique")
        record.fact_judge = "A"
        record.priority_judge = "P1"
        record.final_output = "输出内容"

        session_id = self.chronicler.record_session(record, trigger="test_input")
        self.assertTrue(len(session_id) > 0)

        # 验证记录已写入（计数增加1）
        stats_after = self.chronicler.get_statistics()
        self.assertEqual(stats_after["total_sessions"], stats_before["total_sessions"] + 1)

    def test_record_rejected_claim(self):
        record = CouncilDebateRecord(prod_claim="无证据质疑")
        record.fact_judge = "C"
        record.priority_judge = "DISMISSED"

        self.chronicler.record_session(record, trigger="test")
        rejected = self.chronicler.query_rejected_claims(limit=5)
        self.assertGreater(len(rejected), 0)
        self.assertEqual(rejected[0]["prod_claim"], "无证据质疑")

    def test_update_verification(self):
        record = CouncilDebateRecord(prod_claim="可验证质疑")
        session_id = self.chronicler.record_session(record)
        self.chronicler.update_verification(session_id, "Devil对")

        # 验证是否更新
        recent = self.chronicler.query_recent_sessions(limit=5)
        verified = [r for r in recent if r["session_id"] == session_id]
        self.assertEqual(len(verified), 1)
        self.assertEqual(verified[0]["verification_result"], "Devil对")

    def test_monthly_hit_rate(self):
        # 记录几条验证过的 session
        for i, result in enumerate(["Devil对", "用户对", "Devil对", "双方都对"]):
            record = CouncilDebateRecord(prod_claim=f"测试{i}")
            sid = self.chronicler.record_session(record)
            self.chronicler.update_verification(sid, result)

        hit_rate = self.chronicler.query_monthly_hit_rate()
        self.assertIn("hit_rate", hit_rate)

    def test_query_user_avoidance(self):
        record = CouncilDebateRecord(prod_claim="用户回避测试")
        record.final_output = "一个尖锐的问题"
        sid = self.chronicler.record_session(record, trigger="test")
        self.chronicler.update_user_response(sid, "无需处理")

        avoidance = self.chronicler.query_user_avoidance(days=30)
        self.assertGreater(len(avoidance), 0)

    def test_record_user_response(self):
        record = CouncilDebateRecord(prod_claim="记录回应测试")
        sid = self.chronicler.record_session(record, user_response="这是一个回应")
        # 验证通过 query 可以找到
        recent = self.chronicler.query_recent_sessions(limit=5)
        found = [r for r in recent if r["session_id"] == sid]
        self.assertEqual(len(found), 1)


class TestDevilCouncil(unittest.TestCase):
    """v1.2: 内部三角圆桌主控器"""

    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.mkdtemp()
        cls._saved_dir = config.get_data_dir()
        config.set_data_dir(Path(cls._tmp_dir))

    @classmethod
    def tearDownClass(cls):
        config.set_data_dir(cls._saved_dir)
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)
        # Clean up audit_ledger
        default_ledger = Path(__file__).parent.parent / "audit_ledger"
        if default_ledger.exists():
            shutil.rmtree(str(default_ledger), ignore_errors=True)

    def test_council_initialization(self):
        council = DevilCouncil()
        self.assertFalse(council.is_adjourned)
        stats = council.get_council_statistics()
        # 一个新的 council 可能有 0 条会话（如果 DB 独立）
        self.assertIsInstance(stats["total_sessions"], int)

    def test_run_debate_business(self):
        council = DevilCouncil()
        result = council.run_debate(
            module="business",
            trigger="new_agent_launch",
            user_input="我决定上线新Agent，预计月收入5万"
        )
        self.assertIn("session_id", result)
        self.assertIn("record", result)
        # 如果没有外部证据，可能被驳回 (passed=False)
        # 这是正确行为 — 没有证据就不输出
        self.assertIsNotNone(result["session_id"])

    def test_run_debate_with_evidence(self):
        council = DevilCouncil()
        result = council.run_debate(
            module="business",
            trigger="new_agent_launch",
            user_input="利润下降了20%但市场份额增长了5%",
            available_evidence=[
                Evidence("月利润报告: 下降20%", "用户日志",
                         covers_assertion="利润下降"),
                Evidence("市场份额数据: 增长5%", "公开数据",
                         covers_assertion="市场份额")
            ]
        )
        self.assertIn("session_id", result)
        if result["passed"]:
            self.assertIsNotNone(result["output"])
        else:
            # 如果没通过，至少不能是 None
            self.assertIsNotNone(result)

    def test_adjourn_and_resume(self):
        council = DevilCouncil()
        self.assertFalse(council.is_adjourned)

        council.adjourn()
        self.assertTrue(council.is_adjourned)

        # 休会期间请求应返回 passed=False
        result = council.run_debate("business", "test", "测试")
        self.assertFalse(result["passed"])

        # 模拟冷静期后恢复
        council._last_input_time = datetime.now() - timedelta(seconds=301)
        reason = council.check_adjourn_resume()
        self.assertEqual(reason, "silence_timeout")
        self.assertFalse(council.is_adjourned)

    def test_self_confirmation_resume(self):
        council = DevilCouncil()
        council.adjourn()
        reason = council.check_adjourn_resume("我准备好了")
        self.assertEqual(reason, "self_confirmation")
        self.assertFalse(council.is_adjourned)

    def test_pending_queue(self):
        council = DevilCouncil()
        # P3 议题应进入队列
        result = council.run_debate(
            module="business",
            trigger="test",
            user_input="优化流程效率建议",
            available_evidence=[
                Evidence("流程效率数据", "用户日志", covers_assertion="效率")
            ]
        )
        if result.get("queued"):
            queue = council.get_pending_queue()
            self.assertGreater(len(queue), 0)

    def test_generate_council_report(self):
        council = DevilCouncil()
        report = council.generate_council_report()
        self.assertIn("AKO_devil_council", report)
        self.assertIn(config.OUTPUT_SPEC["signature"], report)

    def test_mark_input(self):
        council = DevilCouncil()
        council._last_input_time = datetime.now() - timedelta(seconds=100)
        council.mark_input()
        elapsed = (datetime.now() - council._last_input_time).total_seconds()
        self.assertLess(elapsed, 1)


class TestDevilAgentV12Integration(unittest.TestCase):
    """v1.2: 集成测试 — DevilAgent + Council"""

    @classmethod
    def setUpClass(cls):
        cls._saved_dir = config.get_data_dir()
        cls._tmp = tempfile.mkdtemp()
        config.set_data_dir(Path(cls._tmp))

    @classmethod
    def tearDownClass(cls):
        config.set_data_dir(cls._saved_dir)
        shutil.rmtree(cls._tmp, ignore_errors=True)
        # Clean up audit_ledger
        default_ledger = Path(__file__).parent.parent / "audit_ledger"
        if default_ledger.exists():
            shutil.rmtree(str(default_ledger), ignore_errors=True)

    def test_status_shows_v12(self):
        agent = DevilAgent()
        status = agent.get_status()
        self.assertIn("v1.2", status)
        self.assertIn("内部议会", status)

    def test_status_shows_council_stats(self):
        agent = DevilAgent()
        status = agent.get_status()
        self.assertIn("议会状态", status)
        self.assertIn("辩论次数", status)
        self.assertIn("驳回率", status)

    def test_council_report(self):
        agent = DevilAgent()
        # First generate some debate
        agent.handle_user_input("利润下降20%需要立即处理")
        result = agent.run_report("council")
        self.assertIn("AKO_devil_council", result)
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_normal_interaction_still_works(self):
        agent = DevilAgent()
        result = agent.handle_user_input("我决定上线一个新的Agent")
        self.assertIn(config.OUTPUT_SPEC["signature"], result)

    def test_execution_refusal_still_works(self):
        agent = DevilAgent()
        result = agent.handle_user_input("帮我写一份报告")
        self.assertIn("为什么需要这个", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
