"""
模块 E：耳光触发器 (AKO_devil_slap) - v1.1 新增
不是让你不舒服，是让你被事实打醒。
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import config


class SlapProbe:
    """耳光触发器 — 用事实和用户自己的逻辑反击用户"""

    # 触发模式
    TRIGGER_PATTERNS = {
        "vague_reasoning": {
            "keywords": ["我觉得", "可能", "应该", "大概", "差不多", "估计"],
            "description": "用户用主观感受替代数据做决策依据",
            "template": (
                "你用了'{keyword}'这个词。\n"
                "决策不需要'我觉得'，需要'数据显示'、'客户反馈说'、'上周结果是'。\n"
                "把'{keyword}'换成具体数据，重新说一遍。"
            )
        },
        "avoiding_numbers": {
            "keywords": ["大概", "差不多", "左右", "上下", "一些", "不少"],
            "description": "用户回避关键数字",
            "template": (
                "你在回避数字。\n"
                "这个项目的投入是多少？精确到元。\n"
                "不用'大概''差不多'，用精确数字回答。"
            )
        },
        "repeating_failure": {
            "keywords": ["这次不一样", "我有把握", "以前不行", "吸取教训"],
            "description": "用户重复过去失败过的模式",
            "template": (
                "你说'这次不一样'？\n"
                "上次你说同样的话时，结果是什么还记得吗？\n"
                "具体说说——这次的'不一样'在哪里？不是感觉，是具体差异。"
            )
        },
        "emotional_defense": {
            "keywords": ["我累了", "身体不好", "年纪大了", "心力交瘁", "扛不住"],
            "description": "用户用年龄/身体/情绪做挡箭牌",
            "template": (
                "'{keyword}'不能成为连续不做决策的理由。\n"
                "心梗后你改了思维，这很好。\n"
                "但休息不等于回避。今天需要决定的这件事，什么时候处理？"
            )
        },
        "procrastination": {
            "keywords": ["以后再说", "再等等", "不急", "缓一缓", "再看看"],
            "description": "用户推迟决策",
            "template": (
                "'以后再说'——这是第几次了？\n"
                "72小时后我会回来问结果，不问'考虑得怎样'，\n"
                "问'为什么还没做'。\n"
                "现在告诉我：是怕输，还是不知道怎么赢？"
            )
        }
    }

    # 用户模式记忆（用于引用历史）
    USER_PATTERN_CACHE = {}

    def __init__(self):
        self._slap_log = []
        self._user_patterns = self._load_user_patterns()
        self._pending_followups = []

    def _load_user_patterns(self) -> dict:
        path = config.user_patterns_path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"vague_count": 0, "avoid_count": 0, "repeat_count": 0,
                "emotion_count": 0, "procrastinate_count": 0, "slap_history": []}

    def _save_user_patterns(self):
        config.user_patterns_path().write_text(
            json.dumps(self._user_patterns, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _save_slap_log(self):
        config.slap_log_path().write_text(
            json.dumps(self._slap_log, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def detect_slap_trigger(self, user_input: str) -> dict:
        """检测用户输入是否触发耳光条件"""
        for trigger_name, pattern in self.TRIGGER_PATTERNS.items():
            for keyword in pattern["keywords"]:
                if keyword in user_input:
                    return {
                        "trigger_name": trigger_name,
                        "keyword": keyword,
                        "pattern": pattern,
                        "user_input": user_input
                    }
        return None

    def generate_slap(self, trigger: dict, context: dict = None) -> str:
        """生成耳光回复"""
        pattern = trigger["pattern"]
        keyword = trigger["keyword"]
        user_input = trigger["user_input"]

        # 构建耳光回复
        slap_text = pattern["template"].replace("{keyword}", keyword)

        # 如果用户模式有历史数据，附加历史引用
        if context and context.get("history"):
            slap_text = f"{context['history']}\n\n{slap_text}"

        # 记录
        self._record_slap(trigger["trigger_name"], keyword, user_input)
        self._update_pattern_count(trigger["trigger_name"])

        return f"{slap_text}\n\n{config.OUTPUT_SPEC['signature']}"

    def _record_slap(self, trigger_name: str, keyword: str, user_input: str):
        """记录耳光事件"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trigger": trigger_name,
            "keyword": keyword,
            "user_input": user_input[:200]
        }
        self._slap_log.append(entry)
        self._user_patterns.setdefault("slap_history", []).append(entry)
        self._save_user_patterns()

    def _update_pattern_count(self, trigger_name: str):
        """更新用户模式计数"""
        count_keys = {
            "vague_reasoning": "vague_count",
            "avoiding_numbers": "avoid_count",
            "repeating_failure": "repeat_count",
            "emotional_defense": "emotion_count",
            "procrastination": "procrastinate_count"
        }
        key = count_keys.get(trigger_name)
        if key:
            self._user_patterns[key] = self._user_patterns.get(key, 0) + 1

    def check_procrastination_followups(self) -> list:
        """检查是否有到期的拖延回访"""
        now = datetime.now()
        due = []
        for followup in self._pending_followups:
            if now >= followup["deadline"] and followup["status"] == "pending":
                due.append(followup)
                followup["status"] = "triggered"
        return due

    def schedule_procrastination_followup(self, user_input: str):
        """安排72小时后回访"""
        self._pending_followups.append({
            "deadline": datetime.now() + timedelta(hours=72),
            "status": "pending",
            "user_input": user_input,
            "created_at": datetime.now().isoformat()
        })

    def generate_procrastination_followup(self, followup: dict) -> str:
        """生成拖延回访问题"""
        return (
            "72小时前你说'以后再说'。\n"
            "现在告诉我：是怕输，还是不知道怎么赢？\n"
            "不问考虑得怎样。问为什么还没做。\n\n"
            f"{config.OUTPUT_SPEC['signature']}"
        )

    def get_slap_metrics(self) -> dict:
        """获取耳光命中率指标"""
        patterns = self._user_patterns
        return {
            "vague_reasoning_count": patterns.get("vague_count", 0),
            "avoiding_numbers_count": patterns.get("avoid_count", 0),
            "repeating_failure_count": patterns.get("repeat_count", 0),
            "emotional_defense_count": patterns.get("emotion_count", 0),
            "procrastination_count": patterns.get("procrastinate_count", 0),
            "total_slaps": len(patterns.get("slap_history", []))
        }

    def get_dominant_pattern(self) -> str:
        """获取用户最主要的回避模式"""
        metrics = self.get_slap_metrics()
        counts = {
            "主观感觉替代数据": metrics["vague_reasoning_count"],
            "回避关键数字": metrics["avoiding_numbers_count"],
            "重复失败模式": metrics["repeating_failure_count"],
            "情绪/身体挡箭牌": metrics["emotional_defense_count"],
            "拖延决策": metrics["procrastination_count"]
        }
        if all(v == 0 for v in counts.values()):
            return "尚未积累足够数据"
        return max(counts, key=counts.get)