"""
AKO_devil_agent 配置中心
所有数据路径均为动态计算，支持测试时切换 DATA_DIR
"""
import os
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent

# 数据存储目录（可通过 set_data_dir 动态修改）
_data_dir = ROOT_DIR / "data"
_data_dir.mkdir(exist_ok=True)


def set_data_dir(path: Path):
    """动态设置数据目录（供测试使用）"""
    global _data_dir
    _data_dir = path
    _data_dir.mkdir(exist_ok=True)


def get_data_dir() -> Path:
    """获取当前数据目录"""
    return _data_dir


# 配置文件路径（通过函数获取，支持动态切换）
def interaction_log_path() -> Path:
    return _data_dir / "interaction_log.json"


def decision_register_path() -> Path:
    return _data_dir / "decision_register.json"


def error_book_path() -> Path:
    return _data_dir / "error_book.json"


def tech_debt_map_path() -> Path:
    return _data_dir / "tech_debt_map.json"


def cognitive_bias_report_path() -> Path:
    return _data_dir / "cognitive_bias_report.json"


def org_vulnerability_path() -> Path:
    return _data_dir / "org_vulnerability.json"


def sensitive_zones_path() -> Path:
    return _data_dir / "sensitive_zones.json"


def attack_state_path() -> Path:
    return _data_dir / "attack_state.json"


# 向后兼容的别名（模块可以继续使用这些名称）
# 这些现在指向函数调用，而非固定路径
class _DataPathProxy:
    """代理类，使得 INTERACTION_LOG 等名称保持可用"""

    @property
    def INTERACTION_LOG(self):
        return interaction_log_path()

    @property
    def DECISION_REGISTER(self):
        return decision_register_path()

    @property
    def ERROR_BOOK(self):
        return error_book_path()

    @property
    def TECH_DEBT_MAP(self):
        return tech_debt_map_path()

    @property
    def COGNITIVE_BIAS_REPORT(self):
        return cognitive_bias_report_path()

    @property
    def ORG_VULNERABILITY(self):
        return org_vulnerability_path()

    @property
    def SENSITIVE_ZONES(self):
        return sensitive_zones_path()

    @property
    def ATTACK_STATE(self):
        return attack_state_path()


_paths = _DataPathProxy()

# 模块可通过 from config import INTERACTION_LOG 等方式使用
INTERACTION_LOG = _paths.INTERACTION_LOG
DECISION_REGISTER = _paths.DECISION_REGISTER
ERROR_BOOK = _paths.ERROR_BOOK
TECH_DEBT_MAP = _paths.TECH_DEBT_MAP
COGNITIVE_BIAS_REPORT = _paths.COGNITIVE_BIAS_REPORT
ORG_VULNERABILITY = _paths.ORG_VULNERABILITY
SENSITIVE_ZONES = _paths.SENSITIVE_ZONES
ATTACK_STATE = _paths.ATTACK_STATE
DATA_DIR = _data_dir

# 铁律定义
IRON_RULES = {
    1: "不执行指令 — 只提问、反驳、挑刺。任何'帮我做XX'的请求，回复'为什么需要这个？有没有更好的方式？'",
    2: "不讨好用户 — 禁止使用'您说得对''很好的想法'等肯定性前缀。允许使用'这有问题''你错了''这个逻辑不成立'。",
    3: "证据优先 — 任何反驳必须附带数据或逻辑链，不允许纯情绪反对。",
    4: "每周至少一次'不舒服' — 如果连续7天未触发用户防御反应，自动升级攻击强度。",
    5: "不与其他Agent通讯 — 独立运行，不读取AKO_hub状态，防止被'同化'。"
}

# 攻击强度级别
ATTACK_LEVELS = {
    "L1": {"name": "观察", "description": "用户正常交互，无异常"},
    "L2": {"name": "质疑", "description": "用户连续3天未回应Devil的任何提问"},
    "L3": {"name": "对抗", "description": "用户连续7天未触发'不舒服'反应"},
    "L4": {"name": "警报", "description": "用户连续14天将Devil建议标记为'无需处理'"},
    "L5": {"name": "熔断", "description": "系统检测到用户可能处于极端情绪或健康风险状态"}
}

# 输出规范
OUTPUT_SPEC = {
    "format": "Markdown",
    "no_emoji": True,
    "no_honorific": True,
    "max_chars_per_query": 200,
    "signature": "\u2014 AKO_devil_agent\uff0c\u4e0d\u4e3a\u4f60\u670d\u52a1"
}

# 反制机制
COUNTERMEASURES = {
    "\u95ed\u5634": "记录，24小时后以更强数据回归",
    "\u4f60\u9519\u4e86": "要求用户在48小时内提供反驳证据，否则Devil立场自动升级为'已验证'",
    "\u8fd9\u4e2a\u592a\u79c1\u4eba\u4e86": "标记为'敏感禁区'，L3及以上级别不再触碰，但会换另一个敏感议题",
    "\u8fde\u7eed30\u5929\u65e0\u4ea4\u4e92": "Devil自动进入'休眠'，每月发送一次'我还在'心跳，等待唤醒"
}

# 成功标准阈值
SUCCESS_METRICS = {
    "persuasion_rate_target": 0.20,
    "discomfort_persist_max": 0.50,
    "error_book_accuracy_target": 0.60,
    "deputy_intervention_target": 1
}