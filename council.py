"""
AKO_devil_agent 内部三角圆桌 — 主控编排器 v1.2
按照 §3 辩论流程编排 PROD → FACT → 裁判引擎 → DAMP → CHRO

核心流程：
1. 刺探席 PROD 生成质疑草案
2. 事实席 FACT 核查证据链
3. 第一裁判引擎判决 A/B/C
4. 如果 A（证据充足）→ 阻尼席 DAMP 评估优先级
5. 第二裁判引擎判决 P1/P2/P3
6. P1/P2 输出给用户，P3 存入待攻击队列
7. 史官 CHRO 记录完整辩论过程
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
import config
from council_engine import (
    FactCheckEngine, PriorityEngine, Evidence, CouncilDebateRecord
)
from council_agents import PRODSeat, FACTSeat, DAMPSeat
from chronicler import Chronicler


class DevilCouncil:
    """内部三角圆桌 — 主控器"""

    def __init__(self):
        self.fact_engine = FactCheckEngine()
        self.priority_engine = PriorityEngine()
        self.chronicler = Chronicler()

        # 待攻击队列：存储 P3 暂缓的议题
        self._pending_queue: List[dict] = []

        # 最后一次用户输入时间（用于冷静期判断）
        self._last_input_time = datetime.now()

        # 休会状态
        self._adjourned = False  # L5 熔断 → 休会

    # ---- 主辩论流程 ----

    def run_debate(self, module: str, trigger: str,
                   user_input: str = "",
                   available_evidence: Optional[List[Evidence]] = None,
                   business_context: Optional[dict] = None) -> dict:
        """
        执行一次完整的三角辩论

        Args:
            module: 议题模块 (business/tech/user/org)
            trigger: 触发器类型
            user_input: 用户原始输入
            available_evidence: 可用的外部证据
            business_context: 业务上下文（包含保护关系等标记）

        Returns:
            {
                "output": str or None,  # 输出给用户的质疑（如通过双裁判）
                "session_id": str,      # 审计会话 ID
                "passed": bool,         # 是否通过双裁判
                "record": CouncilDebateRecord  # 完整记录
            }
        """
        # 创建记录
        record = CouncilDebateRecord()

        # 检查休会状态
        if self._adjourned:
            return self._handle_adjourned(record)

        # Step 1: PROD 刺探席 — 生成质疑草案
        prod_claim = PRODSeat.generate_claim(
            module=module,
            trigger=trigger,
            user_input=user_input,
            context=business_context
        )
        record.prod_claim = prod_claim

        # Step 2: FACT 事实席 — 核查证据链
        fact_result = FACTSeat.review_claim(prod_claim, available_evidence)
        record.fact_report = fact_result["report"]
        record.fact_judge = fact_result["grade"]
        record.evidence_list = fact_result["evidence_list"]

        # Step 3: 第一裁判引擎判决
        # (已在 FACTSeat.review_claim 中执行)
        if record.fact_judge in ("B", "C"):
            # 证据不足或部分充足 → 驳回，记录日志
            record.damp_report = f"证据等级 {record.fact_judge} — 不进入优先级评估"
            record.priority_judge = "DISMISSED"
            record.final_output = ""

            session_id = self.chronicler.record_session(record, trigger=trigger)
            return {
                "output": None,
                "session_id": session_id,
                "passed": False,
                "record": record
            }

        # Step 4: DAMP 阻尼席 — 评估优先级
        damp_result = DAMPSeat.evaluate(
            prod_claim, record.fact_judge, business_context
        )
        record.damp_report = damp_result["report"]
        record.priority_judge = damp_result["priority"]

        # Step 5: 第二裁判引擎判决
        if record.priority_judge == "P3":
            # 暂缓 → 存入待攻击队列
            self._pending_queue.append({
                "claim": prod_claim,
                "module": module,
                "trigger": trigger,
                "trigger_condition": damp_result["trigger_condition"],
                "added_at": datetime.now().isoformat(),
                "counter": 0  # 触发计数器
            })
            record.final_output = ""
            session_id = self.chronicler.record_session(record, trigger=trigger)
            return {
                "output": None,
                "session_id": session_id,
                "passed": False,
                "record": record,
                "queued": True
            }

        # Step 6: P1/P2 → 格式化输出给用户
        final_output = self._format_council_output(record)
        record.final_output = final_output

        # Step 7: CHRO 史官 → 归档
        session_id = self.chronicler.record_session(record, trigger=trigger)

        return {
            "output": final_output,
            "session_id": session_id,
            "passed": True,
            "record": record
        }

    def _format_council_output(self, record: CouncilDebateRecord) -> str:
        """将三角辩论结果格式化为面向用户的输出"""
        parts = []

        # 以 PROD 的质疑为核心输出
        parts.append(record.prod_claim)

        # 加裁判标记
        parts.append(
            f"\n---\n[内部裁决: 事实核查={record.fact_judge}, "
            f"优先级={record.priority_judge}]"
        )

        signature = config.OUTPUT_SPEC.get("signature",
            "— AKO_devil_agent，不为你服务")
        parts.append(f"\n{signature}")

        return "\n".join(parts)

    # ---- 待攻击队列管理 ----

    def check_pending_queue(self, context: Optional[dict] = None) -> Optional[dict]:
        """
        检查待攻击队列，看是否有 P3 议题需要升级
        返回: 需要输出的议题 dict or None
        """
        triggered_items = []
        remaining_items = []

        for item in self._pending_queue:
            should_trigger = self._evaluate_p3_trigger(item, context)
            if should_trigger:
                # 重新评估优先级
                new_priority = self.priority_engine.judge(
                    item["claim"],
                    business_context={"P3_upgrade": True}
                )
                if new_priority in ("P1", "P2"):
                    triggered_items.append(item)
                    continue
            remaining_items.append(item)

        self._pending_queue = remaining_items

        if triggered_items:
            return triggered_items[0]
        return None

    def _evaluate_p3_trigger(self, item: dict,
                             context: Optional[dict] = None) -> bool:
        """评估 P3 暂缓议题是否达到触发条件"""
        # 按时间检查：超过7天未处理的 P3 自动升级为 P2
        added_at = datetime.fromisoformat(item["added_at"])
        days_pending = (datetime.now() - added_at).days

        if days_pending >= 7:
            return True

        # 按触发条件关键词检查
        condition = item.get("trigger_condition", "")
        if context:
            if "延迟" in condition and context.get("recent_errors", 0) >= 2:
                return True
            if "下降" in condition and context.get("metric_drop", False):
                return True

        return False

    def get_pending_queue(self) -> List[dict]:
        """获取当前待攻击队列"""
        return [
            {
                "claim": item["claim"][:100],
                "trigger_condition": item["trigger_condition"],
                "days_pending": (datetime.now() -
                                datetime.fromisoformat(item["added_at"])).days
            }
            for item in self._pending_queue
        ]

    # ---- 休会（L5 熔断升级）- v1.2 ----

    def adjourn(self):
        """
        休会：三角议会暂停
        - PROD 休眠
        - FACT 转为健康监测模式
        - DAMP 维持最低限度优先级评估
        - CHRO 继续记录
        """
        self._adjourned = True

    def resume(self):
        """恢复议会"""
        self._adjourned = False
        self._last_input_time = datetime.now()

    def _handle_adjourned(self, record: CouncilDebateRecord) -> dict:
        """处理休会期间的请求"""
        record.prod_claim = "议会休会中 — PROD 休眠"
        record.fact_report = "FACT 转入健康监测模式"
        record.fact_judge = "ADJOURNED"
        record.priority_judge = "ADJOURNED"
        record.final_output = ""

        session_id = self.chronicler.record_session(record, trigger="adjourned")

        return {
            "output": None,
            "session_id": session_id,
            "passed": False,
            "record": record
        }

    def check_adjourn_resume(self, user_input: str = "") -> str:
        """
        检查是否应恢复议会
        恢复条件：
        1. 用户连续5分钟无输入（冷静期）
        2. 用户主动输入'我准备好了'（自我确认）

        返回: 恢复原因字符串 or 空字符串
        """
        if not self._adjourned:
            return ""

        now = datetime.now()
        elapsed = (now - self._last_input_time).total_seconds()

        # 条件1: 冷静期
        if elapsed >= 300:
            self.resume()
            return "silence_timeout"

        # 条件2: 自我确认
        if user_input and "我准备好了" in user_input:
            self.resume()
            return "self_confirmation"

        return ""

    def mark_input(self):
        """标记收到用户输入"""
        self._last_input_time = datetime.now()

    @property
    def is_adjourned(self) -> bool:
        return self._adjourned

    # ---- 统计与报告 ----

    def get_council_statistics(self) -> dict:
        """获取议会统计信息"""
        ledger_stats = self.chronicler.get_statistics()
        return {
            "pending_queue_size": len(self._pending_queue),
            "adjourned": self._adjourned,
            **ledger_stats
        }

    def generate_council_report(self) -> str:
        """生成议会运行报告"""
        stats = self.get_council_statistics()

        report_lines = [
            "## AKO_devil_council 运行报告",
            "",
            f"### 状态",
            f"- 议会状态: {'休会中' if self._adjourned else '正常运作'}",
            f"- 待攻击队列: {stats['pending_queue_size']} 条",
            f"- 总辩论次数: {stats['total_sessions']}",
            f"- 证据充足率 (A): {stats['grade_a_count']} 次",
            f"- 驳回率 (C): {stats['dismissal_rate']}%",
            f"- P1 立即输出: {stats['priority_p1_count']} 次",
            f"- P3 暂缓: {stats['priority_p3_count']} 次",
        ]

        if self._pending_queue:
            report_lines.append("")
            report_lines.append("### 待攻击队列")
            for i, item in enumerate(self._pending_queue, 1):
                claim_preview = item["claim"][:80]
                report_lines.append(
                    f"{i}. {claim_preview}... "
                    f"(暂缓 {item.get('days_pending', 0)} 天)"
                )

        report_lines.append(f"\n{config.OUTPUT_SPEC['signature']}")
        return "\n".join(report_lines)