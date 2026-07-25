"""
AKO_devil_agent 全系统测试
覆盖所有模块、铁律、攻击级别、反制机制和报告生成
每个类使用独立的临时数据目录
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
from devil_core import DevilCore
from attack_manager import AttackManager
from output_formatter import OutputFormatter
from modules.business import BusinessProbe
from modules.tech import TechProbe
from modules.user import UserProbe
from modules.org import OrgProbe
from devil_agent import DevilAgent


class TestConfig(unittest.TestCase):
    def test_iron_rules_defined(self):
        self.assertEqual(len(config.IRON_RULES), 5)

    def test_attack_levels_complete(self):
        for level in ["L1", "L2", "L3", "L4", "L5"]:
            self.assertIn(level, config.ATTACK_LEVELS)

    def test_output_spec(self):
        self.assertTrue(config.OUTPUT_SPEC["no_emoji"])
        self.assertIn("不为你服务", config.OUTPUT_SPEC["signature"])

    def test_countermeasures(self):
        for key in ["闭嘴", "你错了", "这个太私人了", "连续30天无交互"]:
            self.assertIn(key, config.COUNTERMEASURES)

    def test_success_metrics(self):
        self.assertGreaterEqual(config.SUCCESS_METRICS["persuasion_rate_target"], 0.20)


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
        # total_queries can accumulate from other tests in this class
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
        self.assertIn("攻击级别", status)

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

    def test_bias_detection_during_interaction(self):
        agent = DevilAgent()
        result = agent.handle_user_input("这个方案绝对100%没有问题")
        self.assertIn(config.OUTPUT_SPEC["signature"], result)
        observations = agent.user_probe._load_bias_data().get("observations", [])
        self.assertGreater(len(observations), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)