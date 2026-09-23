"""点线大作战技能系统预留接口。

Phase 1 不启用具体技能，但核心画线规则通过 DrawRules 读取，
后续角色技能可以修改转向次数、行动次数、速度和画线时限。
"""

from dataclasses import dataclass, replace
from typing import Any


@dataclass
class DrawRules:
    """单次行动的可修改规则。"""

    max_turns: int = 1
    max_actions: int = 1
    min_average_speed: float = 100.0
    max_draw_seconds: float = 1.0
    ignore_speed_check: bool = False


class BaseSkill:
    """所有技能继承的基础接口。"""

    name = "未命名技能"

    def on_turn_start(self, player: Any) -> None:
        pass

    def on_draw_start(self, player: Any) -> None:
        pass

    def modify_draw_rules(self, rules: DrawRules, player: Any) -> DrawRules:
        return rules

    def on_draw_end(self, player: Any, result: Any) -> Any:
        return result

    def on_turn_end(self, player: Any) -> None:
        pass


class SkillSet:
    """玩家技能组容器；当前为空，但保留组合多个技能的入口。"""

    def __init__(self, skills=None):
        self.skills = list(skills or [])

    def add(self, skill: BaseSkill) -> None:
        self.skills.append(skill)

    def on_turn_start(self, player: Any) -> None:
        for skill in self.skills:
            skill.on_turn_start(player)

    def on_draw_start(self, player: Any) -> None:
        for skill in self.skills:
            skill.on_draw_start(player)

    def draw_rules(self, player: Any) -> DrawRules:
        rules = DrawRules()
        for skill in self.skills:
            rules = skill.modify_draw_rules(replace(rules), player)
        return rules

    def on_draw_end(self, player: Any, result: Any) -> Any:
        for skill in self.skills:
            result = skill.on_draw_end(player, result)
        return result

    def on_turn_end(self, player: Any) -> None:
        for skill in self.skills:
            skill.on_turn_end(player)
