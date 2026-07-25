"""
AKO_devil_agent 核心引擎
管理攻击强度、冲突跟踪、反制机制
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import config


class DevilCore:
    """核心引擎：不执行指令，只管理状态和判断攻击级别"""

    def __init__(self):
        self.state = self._load_state()
        self.interactions = self._load_interactions()
        self.sensitive_zones = self._load_sensitive_zones()

    # ---- 状态持久化 ----

    def _load_state(self) -> dict:
        path = config.attack_state_path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {
            "current_level": "L1",
            "level_start_date": datetime.now().isoformat(),
            "last_discomfort_date": None,
            "last_user_response_date": datetime.now().isoformat(),
            "consecutive_dismissed": 0,
            "total_queries": 0,
            "total_persuasions": 0,
            "dormant": False,
            "first_run": True
        }

    def _save_state(self):
        config.attack_state_path().write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _load_interactions(self) -> list:
        path = config.interaction_log_path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return []

    def _save_interactions(self):
        config.interaction_log_path().write_text(
            json.dumps(self.interactions, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _load_sensitive_zones(self) -> set:
        path = config.sensitive_zones_path()
        if path.exists():
            return set(json.loads(path.read_text(encoding="utf-8")))
        return set()

    def _save_sensitive_zones(self):
        config.sensitive_zones_path().write_text(
            json.dumps(list(self.sensitive_zones), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    # ---- 攻击级别管理 ----

    def evaluate_level(self) -> str:
        """根据用户行为自适应调整攻击级别"""
        now = datetime.now()
        last_discomfort = (
            datetime.fromisoformat(self.state["last_discomfort_date"])
            if self.state["last_discomfort_date"]
            else None
        )
        last_response = datetime.fromisoformat(self.state["last_user_response_date"])

        # L5: 检测极端状态
        if self.state.get("extreme_risk", False):
            self.state["current_level"] = "L5"
            self._save_state()
            return "L5"

        # L4: 连续14天被忽视
        if self.state["consecutive_dismissed"] >= 14:
            self.state["current_level"] = "L4"
            self._save_state()
            return "L4"

        # L3: 连续7天未触发不舒服
        if last_discomfort and (now - last_discomfort).days >= 7:
            self.state["current_level"] = "L3"
            self._save_state()
            return "L3"

        # L2: 连续3天未回应
        if (now - last_response).days >= 3:
            self.state["current_level"] = "L2"
            self._save_state()
            return "L2"

        return self.state.get("current_level", "L1")

    def is_sensitive_topic(self, topic: str) -> bool:
        return topic in self.sensitive_zones

    def mark_sensitive(self, topic: str):
        self.sensitive_zones.add(topic)
        self._save_sensitive_zones()

    # ---- 交互记录 ----

    def record_interaction(self, query: str, user_response: str = None, discomfort: bool = False):
        self.state["total_queries"] += 1
        now = datetime.now()

        entry = {
            "timestamp": now.isoformat(),
            "query": query,
            "level": self.state["current_level"],
            "user_response": user_response,
            "discomfort_triggered": discomfort
        }
        self.interactions.append(entry)
        self._save_interactions()

        if user_response:
            self.state["last_user_response_date"] = now.isoformat()
            if "无需处理" in user_response:
                self.state["consecutive_dismissed"] += 1
            else:
                self.state["consecutive_dismissed"] = 0

        if discomfort:
            self.state["last_discomfort_date"] = now.isoformat()
            self.state["consecutive_dismissed"] = 0

        self._check_countermeasures(user_response)
        self._save_state()

    def _check_countermeasures(self, user_response: str):
        if not user_response:
            return
        for trigger in config.COUNTERMEASURES:
            if trigger in user_response:
                if trigger == "闭嘴":
                    self.state["shut_up_timestamp"] = datetime.now().isoformat()
                elif trigger == "这个太私人了":
                    if self.interactions:
                        last_query = self.interactions[-1].get("query", "")
                        self.mark_sensitive(last_query[:50])
                self._save_state()

    def should_return_after_shutup(self) -> bool:
        shut_up_time = self.state.get("shut_up_timestamp")
        if not shut_up_time:
            return False
        elapsed = datetime.now() - datetime.fromisoformat(shut_up_time)
        return elapsed >= timedelta(hours=24)

    # ---- 休眠逻辑 ----

    def check_dormant(self) -> bool:
        if not self.interactions:
            return False
        last_interaction = max(
            datetime.fromisoformat(i["timestamp"]) for i in self.interactions
        )
        days_since = (datetime.now() - last_interaction).days
        if days_since >= 30:
            self.state["dormant"] = True
            self._save_state()
            return True
        return False

    def heartbeat_due(self) -> bool:
        if not self.state.get("dormant"):
            return False
        last_heartbeat = self.state.get("last_heartbeat")
        if not last_heartbeat:
            return True
        return (datetime.now() - datetime.fromisoformat(last_heartbeat)).days >= 30

    def send_heartbeat(self):
        self.state["last_heartbeat"] = datetime.now().isoformat()
        self._save_state()

    # ---- 成功指标统计 ----

    def get_persuasion_rate(self) -> float:
        if self.state["total_queries"] == 0:
            return 0.0
        return self.state["total_persuasions"] / self.state["total_queries"]

    def record_persuasion(self):
        self.state["total_persuasions"] += 1
        self._save_state()