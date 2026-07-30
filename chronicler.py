"""
AKO_devil_agent 内部三角圆桌 — 史官模块 v1.2
CHRO (Chronicler): 纯记录者 — 只记录、不评判、不参与辩论
所有三角辩论的原始记录写入不可变审计账本 (SQLite)

路径：E:\AKO_devil_agent\audit_ledger\
格式：SQLite，单表 council_sessions
"""
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import config
from council_engine import CouncilDebateRecord


class Chronicler:
    """史官 CHRO — 审计账本管理者"""

    DB_FILENAME = "council_ledger.db"

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent / "audit_ledger"
        db_path.mkdir(parents=True, exist_ok=True)
        self.db_file = db_path / self.DB_FILENAME
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(str(self.db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS council_sessions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                trigger TEXT,
                prod_claim TEXT,
                fact_report TEXT,
                fact_judge TEXT,
                evidence_list TEXT,
                damp_report TEXT,
                priority_judge TEXT,
                final_output TEXT,
                user_response TEXT,
                verification_result TEXT,
                immutable INTEGER DEFAULT 1
            )
        """)
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON council_sessions(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fact_judge
            ON council_sessions(fact_judge)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_verification
            ON council_sessions(verification_result)
        """)
        conn.commit()
        conn.close()

    def record_session(self, record: CouncilDebateRecord,
                       trigger: str = "",
                       user_response: str = "") -> str:
        """
        记录一次完整的三角辩论会话
        返回: session_id
        """
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn = sqlite3.connect(str(self.db_file))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO council_sessions (
                id, session_id, timestamp, trigger,
                prod_claim, fact_report, fact_judge, evidence_list,
                damp_report, priority_judge,
                final_output, user_response, verification_result, immutable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            session_id,  # id 也使用 session_id
            session_id,
            now,
            trigger,
            record.prod_claim,
            record.fact_report,
            record.fact_judge,
            json.dumps([e.to_dict() for e in record.evidence_list], ensure_ascii=False),
            record.damp_report,
            record.priority_judge,
            record.final_output,
            user_response or record.user_response,
            record.verification_result
        ))
        conn.commit()
        conn.close()
        return session_id

    def update_verification(self, session_id: str, result: str):
        """事后验证：更新裁决结果"""
        conn = sqlite3.connect(str(self.db_file))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE council_sessions SET verification_result = ? WHERE session_id = ?",
            (result, session_id)
        )
        conn.commit()
        conn.close()

    def update_user_response(self, session_id: str, response: str):
        """记录用户回应"""
        conn = sqlite3.connect(str(self.db_file))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE council_sessions SET user_response = ? WHERE session_id = ?",
            (response, session_id)
        )
        conn.commit()
        conn.close()

    # ---- 查询接口 (供周明静使用) ----

    def query_monthly_hit_rate(self, year: Optional[int] = None, month: Optional[int] = None) -> dict:
        """
        本月 Devil 质疑命中率
        SELECT COUNT(*) as total,
               SUM(CASE WHEN verification_result = 'Devil对' THEN 1 ELSE 0 END) as devil_wins
        """
        if year is None or month is None:
            now = datetime.now()
            year, month = now.year, now.month

        start_date = f"{year}-{month:02d}-01"
        conn = sqlite3.connect(str(self.db_file))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_claims,
                SUM(CASE WHEN verification_result = 'Devil对' THEN 1 ELSE 0 END) as devil_wins
            FROM council_sessions
            WHERE timestamp >= ?
        """, (start_date,))
        row = cursor.fetchone()
        conn.close()

        total = row[0] or 0
        wins = row[1] or 0
        hit_rate = round(wins * 100.0 / total, 2) if total > 0 else 0.0

        return {
            "month": f"{year}-{month:02d}",
            "total_claims": total,
            "devil_wins": wins,
            "hit_rate": hit_rate
        }

    def query_rejected_claims(self, limit: int = 10) -> List[dict]:
        """
        被驳回的质疑（PROD 过度攻击的证据）
        WHERE fact_judge = 'C'
        """
        conn = sqlite3.connect(str(self.db_file))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, prod_claim, fact_report
            FROM council_sessions
            WHERE fact_judge = 'C'
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "timestamp": r[0],
                "prod_claim": r[1],
                "fact_report": r[2]
            }
            for r in rows
        ]

    def query_user_avoidance(self, days: int = 14) -> List[dict]:
        """
        用户连续拒绝 Devil 的议题（L4警报数据源）
        WHERE user_response IN ('无需处理', '以后再说', '闭嘴')
        """
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        conn = sqlite3.connect(str(self.db_file))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, trigger, final_output, user_response
            FROM council_sessions
            WHERE user_response IN ('无需处理', '以后再说', '闭嘴')
              AND timestamp >= ?
            ORDER BY timestamp DESC
        """, (start_date,))
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "timestamp": r[0],
                "trigger": r[1],
                "final_output": r[2],
                "user_response": r[3]
            }
            for r in rows
        ]

    def query_recent_sessions(self, limit: int = 20) -> List[dict]:
        """查询最近会话"""
        conn = sqlite3.connect(str(self.db_file))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, timestamp, trigger, prod_claim,
                   fact_judge, priority_judge, verification_result
            FROM council_sessions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "session_id": r[0],
                "timestamp": r[1],
                "trigger": r[2],
                "prod_claim": r[3][:100] if r[3] else "",
                "fact_judge": r[4],
                "priority_judge": r[5],
                "verification_result": r[6]
            }
            for r in rows
        ]

    def get_statistics(self) -> dict:
        """获取审计账本统计摘要"""
        conn = sqlite3.connect(str(self.db_file))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM council_sessions")
        total = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM council_sessions WHERE fact_judge = 'A'"
        )
        grade_a = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM council_sessions WHERE fact_judge = 'C'"
        )
        grade_c = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM council_sessions WHERE priority_judge = 'P1'"
        )
        priority_p1 = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM council_sessions WHERE priority_judge = 'P3'"
        )
        priority_p3 = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "total_sessions": total,
            "grade_a_count": grade_a,
            "grade_c_count": grade_c,
            "priority_p1_count": priority_p1,
            "priority_p3_count": priority_p3,
            "dismissal_rate": round(grade_c * 100.0 / total, 2) if total > 0 else 0.0
        }