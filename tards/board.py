from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .player import Player
    from .cards import Minion, MinionCard
    from .game import Game


class Board:
    SIZE = 5
    COL_NAMES = ["高地", "山脊", "中路", "河岸", "水路"]

    def __init__(self):
        self.minion_place: Dict[Tuple[int, int], "Minion"] = {}
        self.cell_underlay: Dict[Tuple[int, int], "Minion"] = {}
        self.game_ref: Optional["Game"] = None

    def target_check(self, target) -> bool:
        if not isinstance(target, tuple) or len(target) != 2:
            return False
        r, c = target
        return 0 <= r < self.SIZE and 0 <= c < self.SIZE

    def _is_water_at(self, pos: Tuple[int, int]) -> bool:
        """判断指定位置是否为水路（支持全局地形覆盖）。"""
        from card_pools.effect_utils import get_terrain_at
        override = get_terrain_at(self.game_ref, pos) if self.game_ref else None
        if override == "水路":
            return True
        if override == "陆地":
            return False
        return pos[1] == 4

    def is_valid_deploy(self, pos: Tuple[int, int], player: "Player", card: "MinionCard") -> bool:
        r, c = pos
        if r not in player.get_friendly_rows():
            return False

        existing = self.minion_place.get(pos)

        # 藤蔓：只能部署在友方异象上
        if "藤蔓" in card.keywords:
            if not existing or existing.owner != player:
                return False
            if hasattr(existing, 'vine_overlay') and existing.vine_overlay:
                return False
            return True

        is_water = self._is_water_at(pos)
        aquatic = card.keywords.get("水生", False) or card.keywords.get("两栖", False)

        # 漂浮物：可以在其上部署异象，无视水路限制
        if existing and "漂浮物" in existing.keywords and existing.owner == player:
            return True

        if is_water and not aquatic:
            return False
        if not is_water and card.keywords.get("水生", False):
            return False
        if "高地" in card.keywords and c != 0:
            return False
        if "河岸" in card.keywords and c != 3:
            return False
        if "独行" in card.keywords:
            friendlies = self.get_minions_in_column(c, friendly_to=player)
            if friendlies:
                return False
        friendlies = self.get_minions_in_column(c, friendly_to=player)
        if friendlies:
            has_synergy = any("协同" in m.keywords for m in friendlies)
            if not has_synergy and "协同" not in card.keywords:
                return False
        return True

    def get_minion_at(self, target: Tuple[int, int]) -> Optional["Minion"]:
        return self.minion_place.get(target)

    def remove_minion(self, target: Tuple[int, int]) -> Optional["Minion"]:
        """将异象从战场移除。注意：移除不触发亡语（与消灭不同）。"""
        m = self.minion_place.get(target, None)
        if not m:
            return None

        # === BEFORE_REMOVE 事件 ===
        if self.game_ref:
            from tards.constants import EVENT_BEFORE_REMOVE
            event = self.game_ref.emit_event(
                EVENT_BEFORE_REMOVE,
                source=None,
                target=m,
                minion=m,
                player=m.owner,
                position=target,
            )
            if getattr(event, "cancelled", False):
                return None

        m = self.minion_place.pop(target, None)
        if m:
            # 清理部署钩子
            if self.game_ref:
                m.clear_deploy_hook(self.game_ref)
            # 清理本 minion 向其它异象提供的所有光环
            m.clear_all_provided_auras()
            # 如果移除的是藤蔓，释放宿主
            if hasattr(m, 'vine_host') and m.vine_host:
                host = m.vine_host
                host.vine_overlay = None
                host.position = target
                self.minion_place[target] = host
                m.vine_host = None
            # 如果移除的是漂浮物上的 occupant，漂浮物回归
            elif hasattr(m, 'float_host') and m.float_host:
                host = m.float_host
                host.float_occupant = None
                host.position = target
                self.minion_place[target] = host
                m.float_host = None
            elif target in self.cell_underlay:
                # 直接移除 underlay（宿主或漂浮物），连带移除 overlay
                under = self.cell_underlay.pop(target)
                under.position = None
            # === REMOVED 事件 ===
            if self.game_ref:
                from tards.constants import EVENT_REMOVED
                self.game_ref.emit_event(
                    EVENT_REMOVED,
                    source=None,
                    target=m,
                    minion=m,
                    player=m.owner,
                    position=target,
                )
            if self.game_ref and not self.game_ref.effect_queue.is_resolving():
                self.game_ref.refresh_all_auras()
        return m

    def replace_minion(self, target: Tuple[int, int], new_minion: "Minion") -> bool:
        """将指定位置上的异象替换为新异象，位置不变（不触发亡语）。"""
        if target not in self.minion_place:
            return False
        old = self.minion_place.pop(target)
        self.minion_place[target] = new_minion
        new_minion.position = target
        if self.game_ref and not self.game_ref.effect_queue.is_resolving():
            self.game_ref.refresh_all_auras()
        return True

    def place_minion(self, minion: "Minion", target: Tuple[int, int]) -> bool:
        existing = self.minion_place.get(target)

        # 藤蔓：覆盖友方异象
        if existing and "藤蔓" in getattr(minion, "keywords", {}):
            if existing.owner != minion.owner:
                return False
            self.cell_underlay[target] = existing
            existing.vine_overlay = minion
            existing.position = target
            self.minion_place[target] = minion
            minion.position = target
            minion.vine_host = existing
            if self.game_ref and not self.game_ref.effect_queue.is_resolving():
                self.game_ref.refresh_all_auras()
            return True

        # 漂浮物：允许在其上部署新异象
        if existing and "漂浮物" in existing.keywords and existing.owner == minion.owner:
            self.cell_underlay[target] = existing
            existing.float_occupant = minion
            existing.position = target
            self.minion_place[target] = minion
            minion.position = target
            minion.float_host = existing
            if self.game_ref and not self.game_ref.effect_queue.is_resolving():
                self.game_ref.refresh_all_auras()
            return True

        if target in self.minion_place:
            return False
        self.minion_place[target] = minion
        minion.position = target
        if self.game_ref and not self.game_ref.effect_queue.is_resolving():
            self.game_ref.refresh_all_auras()
        return True

    def move_minion(self, minion: "Minion", new_pos: Tuple[int, int], allow_cross_side: bool = False) -> bool:
        """将存活异象移动到新的空格子。不触发亡语。

        allow_cross_side: 为 True 时允许跨阵营移动（如劫持/位移效果）。
        移动前后会发射 before_move / moved 事件。
        """
        if not minion.is_alive():
            return False
        old_pos = minion.position
        if old_pos == new_pos:
            return True
        if not self.target_check(new_pos):
            return False
        if new_pos in self.minion_place:
            return False
        r, c = new_pos
        if not allow_cross_side and r not in minion.owner.get_friendly_rows():
            return False
        is_water = self._is_water_at(new_pos)
        aquatic = minion.keywords.get("水生", False) or minion.keywords.get("两栖", False)
        if is_water and not aquatic:
            return False
        if not is_water and minion.keywords.get("水生", False):
            return False

        # 发射 before_move 事件（可取消）
        if self.game_ref:
            from .constants import EVENT_BEFORE_MOVE
            evt = self.game_ref.emit_event(
                EVENT_BEFORE_MOVE, source=minion,
                old_pos=old_pos, new_pos=new_pos, minion=minion
            )
            if evt and evt.cancelled:
                return False

        # 处理 underlay 释放
        if old_pos in self.cell_underlay:
            under = self.cell_underlay.pop(old_pos)
            if hasattr(minion, 'vine_host') and minion.vine_host is under:
                under.vine_overlay = None
                minion.vine_host = None
                under.position = None
            elif hasattr(minion, 'float_host') and minion.float_host is under:
                under.float_occupant = None
                minion.float_host = None
                under.position = None

        self.minion_place.pop(old_pos, None)
        self.minion_place[new_pos] = minion
        minion.position = new_pos
        if self.game_ref and not self.game_ref.effect_queue.is_resolving():
            self.game_ref.refresh_all_auras()

        # 发射 moved 事件
        if self.game_ref:
            from .constants import EVENT_MOVED
            self.game_ref.emit_event(
                EVENT_MOVED, source=minion,
                old_pos=old_pos, new_pos=new_pos, minion=minion
            )
        return True

    def swap_minions(self, m1: "Minion", m2: "Minion") -> bool:
        """交换两个存活异象的位置。"""
        if not m1.is_alive() or not m2.is_alive():
            return False
        p1, p2 = m1.position, m2.position
        if p1 == p2:
            return True
        if self.minion_place.get(p1) is not m1 or self.minion_place.get(p2) is not m2:
            return False
        # 暂时不支持带 underlay 的交换，简化处理
        if p1 in self.cell_underlay or p2 in self.cell_underlay:
            return False
        self.minion_place[p1] = m2
        self.minion_place[p2] = m1
        m1.position = p2
        m2.position = p1
        if self.game_ref and not self.game_ref.effect_queue.is_resolving():
            self.game_ref.refresh_all_auras()
        return True

    def get_minions_of_player(self, player: "Player") -> List["Minion"]:
        result = [m for m in self.minion_place.values() if m.owner == player]
        for m in self.cell_underlay.values():
            if m.owner == player and m not in result:
                result.append(m)
        return result

    def get_minions_in_column(self, col: int, friendly_to: Optional["Player"] = None) -> List["Minion"]:
        result = []
        for r in range(self.SIZE):
            pos = (r, col)
            m = self.minion_place.get(pos)
            if m and (friendly_to is None or m.owner == friendly_to):
                result.append(m)
            u = self.cell_underlay.get(pos)
            if u and (friendly_to is None or u.owner == friendly_to) and u not in result:
                result.append(u)
        return result

    def get_enemy_minions_in_column(self, col: int, player: "Player") -> List["Minion"]:
        result = []
        for m in self.minion_place.values():
            if m.position[1] == col and m.owner != player:
                result.append(m)
        for m in self.cell_underlay.values():
            if m.position[1] == col and m.owner != player and m not in result:
                result.append(m)
        return result

    def get_front_minion(self, col: int, player: "Player", attacker: Optional["Minion"] = None) -> Optional["Minion"]:
        """获取指定列中对 player 而言的敌方前排异象。"""
        enemies = self.get_enemy_minions_in_column(col, player)
        if not enemies:
            return None

        # 潜水/潜行：结算阶段中无法被选中（视野也不能看穿）
        in_resolve = self.game_ref and self.game_ref.current_phase == getattr(self.game_ref, 'PHASE_RESOLVE', 'resolve')
        if attacker or in_resolve:
            enemies = [m for m in enemies if not m.keywords.get("潜水", False) and not m.keywords.get("潜行", False)]

        # 恐惧：无法被异象选中（仅对异象攻击生效）
        if attacker:
            enemies = [m for m in enemies if not getattr(m, '_fear_active', False)]

        # 通用攻击目标过滤（如活塞城槌跳过低攻异象）
        if attacker and hasattr(attacker, '_attack_target_filter'):
            enemies = [m for m in enemies if attacker._attack_target_filter(m)]

        # 空袭：优先攻击具有防空的异象，否则跳过所有异象直击英雄
        if attacker and attacker.keywords.get("空袭", False):
            anti_air = [m for m in enemies if m.keywords.get("防空", False)]
            if anti_air:
                anti_air.sort(key=lambda m: abs(m.position[0] - 2))
                return anti_air[0]
            return None

        if not enemies:
            return None
        # 前排：距离 row=2（中线）更近
        enemies.sort(key=lambda m: abs(m.position[0] - 2))
        return enemies[0]

    def __str__(self) -> str:
        lines = []
        header = "    " + "  ".join(f"{name:6}" for name in self.COL_NAMES)
        lines.append(header)
        for r in range(self.SIZE):
            cells = []
            for c in range(self.SIZE):
                m = self.minion_place.get((r, c))
                if m:
                    owner = "A" if m.owner.side == 0 else "B"
                    cells.append(f"{owner}{m.name}")
                else:
                    cells.append("")
            line = f"[{r}] " + " | ".join(f"{cell:6}" for cell in cells)
            lines.append(line)
        return "\n".join(lines)
