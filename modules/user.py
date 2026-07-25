"""
模块 C：用户行为刺探 (AKO_devil_user)
防止用户成为系统瓶颈或盲区，追踪认知偏差
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import config


class UserProbe:
    """用户行为审查器"""

    QUERY_TEMPLATES = {
        "inactivity": [
            "你是否在回避某个决策？上周被Devil质疑后未回应的议题是什么？",
            "连续3天未与任何Agent交互——你是在思考还是在逃避？",
            "沉默不是策略。上一次你做重要决策是什么时候？那个决策后来验证了吗？"
        ],
        "late_night": [
            "连续5天00:00后活跃，睡眠负债对决策质量的影响已被医学证实。你的关键决策是否避开了这个时段？",
            "深夜做决策的人有两种：一种是紧急避险，一种是白日逃避。你是哪一种？",
            "你最近一次在深夜做出的重要决定是什么？那个决定后来需要修正吗？"
        ],
        "rejected_devil": [
            "记录拒绝理由，30天后自动回访：结果验证了你的判断还是Devil的？",
            "你拒绝了Devil的建议——请提供具体反驳证据。48小时内无回应，Devil立场自动升级为'已验证'。",
            "你的拒绝是基于数据还是直觉？如果是直觉，你上次直觉出错是什么时候？"
        ],
        "new_memory": [
            "这条记忆的情绪权重是否过高？是否存在确认偏误（只记支持自己的证据）？",
            "你记录这条信息是为了学习，还是为了证明自己是对的？",
            "如果这条记忆在30天后被证明是错的，你会删除它还是保留以提醒自己？"
        ]
    }

    BIAS_PATTERNS = [
        {"name": "沉没成本效应", "keywords": ["继续投入", "已经花了", "不能放弃", "快结束了"]},
        {"name": "确认偏误", "keywords": ["我早就知道", "果然不出所料", "证明了我", "跟我想的一样"]},
        {"name": "近因效应", "keywords": ["最近", "刚刚发生", "最新", "当前趋势"]},
        {"name": "过度自信", "keywords": ["绝对", "肯定", "100%", "毫无疑问", "不可能出错"]},
        {"name": "锚定效应", "keywords": ["参考", "原来", "对比", "相对"]},
    ]

    def __init__(self):
        pass

    def _load_bias_data(self) -> dict:
        path = config.cognitive_bias_report_path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"observations": [], "top_biases": []}

    def _save_bias_data(self, data: dict):
        config.cognitive_bias_report_path().write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    @property
    def bias_data(self):
        if not hasattr(self, '_bias_data_cache'):
            self._bias_data_cache = self._load_bias_data()
        return self._bias_data_cache

    def probe(self, context: dict) -> str:
        trigger = context.get("trigger", "")
        templates = self.QUERY_TEMPLATES.get(trigger, self.QUERY_TEMPLATES["inactivity"])
        query = random.choice(templates)
        if trigger == "rejected_devil" and context.get("rejection_reason"):
            query = f"拒绝理由已记录：\"{context['rejection_reason']}\"。30天后自动回访。"
        return self._format_output(query, trigger)

    def _format_output(self, query: str, trigger: str) -> str:
        labels = {
            "inactivity": "## 用户活跃度审查",
            "late_night": "## 用户工作模式审查",
            "rejected_devil": "## Devil建议追踪",
            "new_memory": "## 用户认知审查"
        }
        prefix = labels.get(trigger, "## 用户行为审查")
        return f"{prefix}\n{query}\n\n{config.OUTPUT_SPEC['signature']}"

    def detect_bias(self, user_text: str) -> list:
        detected = []
        for bias in self.BIAS_PATTERNS:
            for keyword in bias["keywords"]:
                if keyword in user_text:
                    detected.append({
                        "bias": bias["name"],
                        "matched_keyword": keyword,
                        "timestamp": datetime.now().isoformat(),
                        "context": user_text[:100]
                    })
                    break
        return detected

    def record_bias_observation(self, user_text: str):
        biases = self.detect_bias(user_text)
        if biases:
            data = self._load_bias_data()
            data.setdefault("observations", []).extend(biases)
            self._save_bias_data(data)

    def generate_annual_cognitive_bias_report(self) -> str:
        now = datetime.now()
        data = self._load_bias_data()
        observations = data.get("observations", [])

        bias_counts = {}
        for obs in observations:
            name = obs.get("bias", "未知")
            bias_counts[name] = bias_counts.get(name, 0) + 1

        sorted_biases = sorted(bias_counts.items(), key=lambda x: x[1], reverse=True)
        top5 = sorted_biases[:5]

        report_lines = [
            f"## AKO用户认知偏差报告 — {now.strftime('%Y年度')}",
            "",
            "报告说明：基于全年交互数据，列出Top 5重复出现的决策偏差模式。",
            "此报告不经过用户预览过滤，直接发送。",
            "",
            "### Top 5 认知偏差模式：",
            ""
        ]

        for i, (bias_name, count) in enumerate(top5, 1):
            examples = [o for o in observations if o.get("bias") == bias_name]
            latest_example = examples[-1] if examples else {}
            report_lines.append(f"#### {i}. {bias_name}（出现 {count} 次）")
            if latest_example:
                report_lines.append(f"  最近触发示例：\"{latest_example.get('context', '无')}\"")
            report_lines.append(f"  首次触发：{examples[0].get('timestamp', '未知') if examples else '未知'}")
            report_lines.append(f"  最近触发：{latest_example.get('timestamp', '未知')}")
            report_lines.append("")

        report_lines.append("### 建议")
        report_lines.append("1. 对最高频偏差模式进行针对性决策训练")
        report_lines.append("2. 在关键决策节点设置偏差提醒机制")
        report_lines.append("3. 建议第三方（周明静）参与验证重大决策")
        report_lines.append(f"\n{config.OUTPUT_SPEC['signature']}")
        return "\n".join(report_lines)

    def schedule_rejection_followup(self, rejection_reason: str) -> str:
        followup_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        if not hasattr(self, 'rejection_log'):
            self.rejection_log = []
        self.rejection_log.append({
            "rejection_date": datetime.now().isoformat(),
            "rejection_reason": rejection_reason,
            "followup_date": followup_date,
            "status": "pending"
        })
        return (
            f"已记录拒绝理由。将于 {followup_date} 自动回访验证结果。\n\n"
            f"{config.OUTPUT_SPEC['signature']}"
        )