from typing import Any, Callable, Dict, List, Optional
from ..core.board import Board
from ..cards import MineralCard, Minion, MinionCard, Strategy, Conspiracy
from ..data.card_db import DEFAULT_REGISTRY, CardType, Pack
from ..constants import (
    EVENT_BELL,
    EVENT_BRAKE,
    EVENT_CARD_PLAYED,
    EVENT_CONSPIRACY_TRIGGERED,
    EVENT_DEATH,
    EVENT_DEPLOYED,
    EVENT_DRAW,
    EVENT_PHASE_END,
    EVENT_PHASE_START,
    EVENT_PLAYER_DAMAGE,
    EVENT_SACRIFICE,
    EVENT_TURN_END,
    EVENT_TURN_START,
    EVENT_MINERAL_EXCHANGED,
)
from ..effect_queue import EffectQueue
from ..events import EventBus, GameEvent
from ..core.fusion import FusionSystem
from ..core.game_history import GameHistory
from ..core.game_logger import GameLogger
from ..core.player import Player
from ..core.targeting import TargetingRequest, TargetingSystem

class PhaseMixin:

    def draw_phase(self, first: Player, second: Player):
        self.current_phase = self.PHASE_DRAW
        self.current_player = first
        self.emit_event(EVENT_PHASE_START, phase=self.PHASE_DRAW, first=first, second=second)
        print("[抽牌阶段]")
        for p in [second, first]:
            if self.current_turn == 1 and p == first:
                continue  # 第一回合先手不抽牌
            if p._skip_next_draw:
                p._skip_next_draw = False
                print(f"  {p.name} 跳过抽牌")
            else:
                # 冥刻1级：若开启了"抽松鼠"，从松鼠牌堆抽牌（替代本回合的普通抽牌）
                underworld_pts = p.immersion_points.get(Pack.UNDERWORLD, 0)
                if underworld_pts >= 1 and p.squirrel_draw_enabled and p.squirrel_deck:
                    card = p.squirrel_deck.pop()
                    p.add_card_to_hand(card, game=self, reason="冥刻沉浸度抽取松鼠")
                    p.squirrel_draw_enabled = False
                    print(f"  {p.name} 从松鼠牌堆抽取了松鼠")
                else:
                    p.draw_card(1, game=self)

        for p in [first, second]:
            # 血契1级：抽牌阶段-1HP，+1S（流失生命值，不触发'受到伤害时'效果）
            blood_pts = p.immersion_points.get(Pack.BLOOD, 0)
            if blood_pts >= 1:
                p.lose_hp(1)
                p.s_point += 1
                print(f"  {p.name} 血契沉浸度触发：失去1HP，获得1S")

            # T槽自然增长
            discrete_pts = p.immersion_points.get(Pack.DISCRETE, 0)
            max_t = (8 if discrete_pts >= 2 else 10) + getattr(p, "_natural_t_max_cap_modifier", 0)
            max_t = max(0, max_t)
            old_t_max = p.t_point_max

            # 判断本回合是否增加T槽（离散沉浸度≥2时，第5和第10回合为C回合，不加T）
            should_increase_t = True
            if discrete_pts >= 2 and self.current_turn in (5, 10):
                should_increase_t = False

            if should_increase_t and p.t_point_max < max_t:
                p.t_point_max += 1

            # C槽自然增长（离散沉浸度≥2：第5和第10回合各+2C，上限4）
            if discrete_pts >= 2:
                if self.current_turn == 5 or self.current_turn == 10:
                    p.c_point_max = min(p.c_point_max + 2, 4)

            # 每回合资源点数回满
            p.t_point = p.t_point_max
            print(f"  {p.name} T槽={p.t_point_max}，获得 {p.t_point} T点")
            if p.c_point_max > 0:
                p.c_point = p.c_point_max
                print(f"  {p.name} C槽={p.c_point_max}，获得 {p.c_point} C点")

            # 重置冥刻2级松鼠兑换标记
            p.squirrel_exchanged_this_turn = False

        self.emit_event(EVENT_PHASE_END, phase=self.PHASE_DRAW, first=first, second=second)

    def action_phase(self, first: Player, second: Player):
        self.current_phase = self.PHASE_ACTION
        self.emit_event(EVENT_PHASE_START, phase=self.PHASE_ACTION, first=first, second=second)
        print("[出牌阶段]")
        for p in self.players:
            p.reset_turn_flags()
            # 结算阶段结束清空鲜血
            p.b_point = 0
            for m in self.board.get_minions_of_player(p):
                m.clear_temp_effects()
                # 重置献祭次数
                sacrifice_kw = m.base_keywords.get("献祭", False)
                if sacrifice_kw is True:
                    m._sacrifice_remaining = 1
                elif isinstance(sacrifice_kw, int):
                    m._sacrifice_remaining = sacrifice_kw
                else:
                    m._sacrifice_remaining = 1

        active = first
        opponent = second
        turn_count = 0
        while not self.game_over:
            turn_count += 1
            if turn_count > 40:
                print("  出牌阶段回合数过多，强制结束")
                break

            # 双方都拉闸，出牌阶段结束
            if active.braked and opponent.braked:
                break

            # 当前玩家已拉闸，切换到对方
            if active.braked:
                active, opponent = opponent, active
                continue

            self.current_player = active
            print(f"\n  >>> {active.name} 的回合 (T点:{active.t_point}, HP:{active.health})")
            self.show_hand(active)
            active.bell = False
            active.t_changed_this_round = False

            if self.action_provider:
                action = self.action_provider(self, active, opponent)
            else:
                action = None

            if action is None:
                # 没有行动提供者或返回空，默认拉闸
                print(f"  {active.name} 没有可执行的行动，结束出牌阶段")
                active.braked = True
                active, opponent = opponent, active
                if active.braked:
                    break
                continue

            act_type = action.get("type")
            if act_type == "brake":
                active.braked = True
                print(f"  {active.name} 拉闸")
                self.emit_event(EVENT_BRAKE, player=active)
                active, opponent = opponent, active
                if active.braked:
                    print("  双方均已拉闸，出牌阶段结束")
                    break
                continue
            elif act_type == "bell":
                active.bell = True
                self.emit_event(EVENT_BELL, player=active)
                if not active.played_card_this_round:
                    print(f"  {active.name} 本回合未打出过手牌即拍铃，失去 1 T点")
                    active.t_point_change(-1)
                active, opponent = opponent, active
                active.played_card_this_round = False
                continue
            elif act_type == "exchange":
                discrete_pts = active.immersion_points.get(Pack.DISCRETE, 0)
                if discrete_pts < 1:
                    print(f"  {active.name} 没有离散沉浸度，无法兑换矿物")
                else:
                    card_name = action.get("card_name")
                    card_def = DEFAULT_REGISTRY.get(card_name)
                    if not card_def or card_def.card_type != CardType.MINERAL:
                        print(f"  非法兑换请求，跳过")
                    else:
                        mineral_card = card_def.to_game_card(active)
                        print(f"  {active.name} 尝试兑换 {card_name}")
                        ok = active.exchange_mineral(mineral_card, self)
                        if not ok:
                            print(f"  兑换失败")
            elif act_type == "exchange_squirrel":
                underworld_pts = active.immersion_points.get(Pack.UNDERWORLD, 0)
                if underworld_pts < 2:
                    print(f"  {active.name} 冥刻沉浸度不足，无法兑换松鼠")
                elif active.squirrel_exchanged_this_turn:
                    print(f"  {active.name} 本回合已兑换过松鼠")
                elif not active.squirrel_deck:
                    print(f"  {active.name} 松鼠牌堆已空")
                elif active.t_point < 1:
                    print(f"  {active.name} T点不足，无法兑换松鼠")
                else:
                    active.t_point_change(-1)
                    card = active.squirrel_deck.pop()
                    active.add_card_to_hand(card, game=self, reason="消耗1T兑换了")
                    active.squirrel_exchanged_this_turn = True
                    self.emit_event(EVENT_MINERAL_EXCHANGED, player=active, card=card)
            elif act_type == "play":
                serial = action.get("serial")
                target = action.get("target")
                bluff = action.get("bluff", False)
                sacrifices = action.get("sacrifices", [])
                # 过滤掉因不同步而丢失的牺牲目标（只剩 tuple 位置），以及献祭次数已耗尽的异象
                valid_sacs = [m for m in sacrifices if hasattr(m, "keywords") and getattr(m, "is_alive", lambda: True)() and getattr(m, '_sacrifice_remaining', 0) > 0]
                temp_b = 0
                if valid_sacs:
                    temp_b = sum(m.keywords.get("丰饶", 1) for m in valid_sacs)
                    # 双倍血契（含垢齿轮等效果）
                    if getattr(active, "_double_blood_gain", False):
                        temp_b *= 2
                        print(f"  {active.name} 双倍血契触发，获得 {temp_b}B")
                    active.b_point += temp_b
                try:
                    can_play, reason = active.card_can_play(serial, target)
                    if can_play:
                        card = active._get_hand_card(serial)
                        # 全局部署限制检查（仅异象卡）
                        if isinstance(card, MinionCard):
                            blocked = False
                            for restriction in self._global_deploy_restrictions:
                                if not restriction(active, card):
                                    print(f"  全局部署限制阻止了 {card.name} 的部署")
                                    blocked = True
                                    break
                            if blocked:
                                active.b_point -= temp_b
                                continue
                        # 将预选献祭目标暂存到卡牌上，供 effect() 异步读取
                        if valid_sacs and card is not None:
                            card._preselected_sacrifices = valid_sacs
                        print(f"  {active.name} 尝试打出 {card.name} (目标: {self._fmt_target(target)})")
                        ok = active.play_card(serial, target, self, bluff=bluff)
                        if not ok:
                            print(f"  出牌失败")
                            # 出牌失败时回滚预加的献祭 B 点
                            active.b_point -= temp_b
                    else:
                        print(f"  非法出牌请求：{reason}")
                        # 无法出牌时回滚预加的献祭 B 点
                        active.b_point -= temp_b
                finally:
                    # 清理暂存的预选献祭目标
                    card = active._get_hand_card(serial)
                    if card is not None and hasattr(card, '_preselected_sacrifices'):
                        delattr(card, '_preselected_sacrifices')
            elif act_type == "set_attack_targets":
                pos = action.get("pos")
                targets = action.get("targets", [])
                m = self.board.get_minion_at(pos)
                if m and m.owner == active:
                    m._pending_attack_targets = targets
                    print(f"  {active.name} 设置 {m.name} 的攻击目标")
                else:
                    print(f"  非法的攻击目标设置")
            elif act_type == "set_effect_target":
                pos = action.get("pos")
                target = action.get("target")
                m = self.board.get_minion_at(pos)
                if m and m.owner == active and m.is_alive():
                    m._pending_effect_target = target
                    print(f"  {active.name} 设置 {m.name} 的效果目标")
                else:
                    print(f"  非法的效果目标设置")
            else:
                print(f"  未知的行动类型: {act_type}")

            if self.check_game_over():
                break

        self.emit_event(EVENT_PHASE_END, phase=self.PHASE_ACTION, first=first, second=second)

    def resolve_phase(self, first: Player, second: Player):
        # 检查是否被跳过（钝锈指针等效果）
        if getattr(self, "_skip_resolve_phase", False):
            print("[结算阶段被跳过]")
            self._skip_resolve_phase = False
            return

        # 清空本回合状态追踪（"回合"等价于结算阶段）
        self.p1._cards_played_this_phase = 0
        self.p2._cards_played_this_phase = 0

        self.current_phase = self.PHASE_RESOLVE
        self.current_player = first
        self.emit_event(EVENT_PHASE_START, phase=self.PHASE_RESOLVE, first=first, second=second)
        print("[结算阶段]")
        print(self.board)

        # 高频攻击次数状态：按 Minion 对象引用存储，支持结算阶段中途加入的异象
        attacker_swings: dict[Minion, int] = {}
        # 记录因高频而临时改变的先攻值，结算阶段结束后恢复
        original_first_strike: dict[Minion, int] = {}

        # 对战顺序：水路(4) -> 河岸(3) -> 中路(2) -> 山脊(1) -> 高地(0)
        self._current_resolve_column = None
        for col in range(4, -1, -1):
            if self.game_over:
                break
            self._current_resolve_column = col
            col_name = self.board.COL_NAMES[col]

            # 找出以本列为 base_col 的攻击者（横扫异象只在 base_col 发起攻击）
            attackers = []
            for m in self.board.minion_place.values():
                if m.position[1] != col:
                    continue
                if not m.can_attack_this_turn(self.current_turn):
                    continue
                from card_pools.effect_utils import can_minion_attack
                if not can_minion_attack(m, self):
                    continue
                if getattr(m, "_skip_resolve_attack", False):
                    continue

                if m not in attacker_swings:
                    swings = m.keywords.get("高频", 1)
                    if swings is True:
                        swings = 1
                    elif not isinstance(swings, int) or swings <= 0:
                        swings = 1
                    attacker_swings[m] = swings

                if attacker_swings[m] > 0:
                    attackers.append(m)

            if not attackers:
                continue

            # 排序：先攻等级降序 -> 距离中线升序 -> side
            attackers.sort(key=lambda m: (
                -m.keywords.get("先攻", 0),
                abs(m.position[0] - 2),
                m.owner.side,
            ))

            print(f"  {col_name}列发生战斗")

            while True:
                if self.game_over:
                    break
                # 动态刷新：找出仍存活且还有攻击次数的 base_col == col 的异象
                active = [m for m in self.board.minion_place.values()
                          if m.position[1] == col and m.is_alive()
                          and m.can_attack_this_turn(self.current_turn)
                          and attacker_swings.get(m, 0) > 0]
                from card_pools.effect_utils import can_minion_attack
                active = [m for m in active if can_minion_attack(m, self)]
                if not active:
                    break

                active.sort(key=lambda m: (
                    -m.keywords.get("先攻", 0),
                    abs(m.position[0] - 2),
                    m.owner.side,
                ))

                # 只取当前先攻最高的一批异象作为本轮攻击者
                highest_fs = active[0].keywords.get("先攻", 0)
                group = [m for m in active if m.keywords.get("先攻", 0) == highest_fs]

                def do_round():
                    for m in group:
                        # 同先攻组内不检查 _pending_death，保证同先攻异象都能出手
                        if not m.is_alive() or attacker_swings.get(m, 0) <= 0:
                            continue

                        # 防空：本列敌方异象失去串击/穿刺
                        has_enemy_anti_air = any(
                            enemy.keywords.get("防空", False)
                            for enemy in self.board.get_enemy_minions_in_column(base_col, m.owner)
                        )
                        can_chain = not has_enemy_anti_air and m.keywords.get("串击", False)
                        has_pierce = not has_enemy_anti_air and m.keywords.get("穿刺", False)

                        sweep = m.keywords.get("横扫", 0)
                        if not isinstance(sweep, int):
                            sweep = 0

                        if sweep > 0:
                            # 横扫：按对战顺序依次对所有覆盖列造成伤害
                            affected_cols = {base_col}
                            for offset in range(1, sweep + 1):
                                if base_col - offset >= 0:
                                    affected_cols.add(base_col - offset)
                                if base_col + offset < 5:
                                    affected_cols.add(base_col + offset)

                            hero_hit = False
                            for scol in sorted(affected_cols, reverse=True):
                                target = self.board.get_front_minion(scol, m.owner, attacker=m)
                                if target and target.is_alive():
                                    pass
                                else:
                                    target = self.p2 if m.owner == self.p1 else self.p1

                                is_sweep_col = (scol != base_col)
                                if is_sweep_col and isinstance(target, Player) and hero_hit:
                                    continue

                                if is_sweep_col:
                                    print(f"  {m.name} 横扫 {self.board.COL_NAMES[scol]}列")
                                    if isinstance(target, Minion):
                                        target.take_damage(m.attack)
                                        if target.is_alive():
                                            spike = target.keywords.get("尖刺", 0)
                                            if spike > 0:
                                                print(f"  {target.name} 的尖刺反弹 {spike} 点伤害")
                                                m.take_damage(spike)
                                    else:
                                        print(f"  {m.name} 横扫直接攻击 {target.name}，造成 {m.attack} 点伤害")
                                        target.health_change(-m.attack, source=m)
                                        hero_hit = True
                                else:
                                    # 本列正常攻击
                                    if target and target.is_alive():
                                        from card_pools.effect_utils import is_untargetable_by_minions
                                        if is_untargetable_by_minions(target):
                                            print(f"  {m.name} 攻击 {target.name}，但目标无法被异象选中，攻击落空")
                                            enemy = self.p2 if m.owner == self.p1 else self.p1
                                            m.attack_target(enemy)
                                        else:
                                            m.attack_target(target)
                                    else:
                                        enemy = self.p2 if m.owner == self.p1 else self.p1
                                        m.attack_target(enemy)
                        # 预设攻击目标（视野+高频等异象在行动阶段选择的直接目标）
                        pending = getattr(m, "_pending_attack_targets", None)
                        if pending and isinstance(pending, list) and len(pending) > 0:
                            # 按顺序消耗预设目标：第1次攻击取第0个，第2次取第1个...
                            total_swings = m.keywords.get("高频", 1)
                            if total_swings is True:
                                total_swings = 1
                            remaining = attacker_swings.get(m, total_swings)
                            target_idx = total_swings - remaining
                            if 0 <= target_idx < len(pending):
                                target = pending[target_idx]
                                # 结算阶段：潜水/潜行异象无法被选中，攻击落空
                                if hasattr(target, "keywords") and (target.keywords.get("潜水", False) or target.keywords.get("潜行", False)):
                                    print(f"  {m.name} 攻击 {target.name}，但目标处于潜水/潜行状态，攻击落空")
                                elif target and hasattr(target, "is_alive") and target.is_alive():
                                    m.attack_target(target)
                                elif hasattr(target, "health_change"):
                                    # 目标是玩家
                                    print(f"  {m.name} 直接攻击 {target.name}")
                                    target.health_change(-m.current_attack, source=m)
                                else:
                                    print(f"  {m.name} 的攻击目标已消失，攻击落空")
                            else:
                                # 预设目标耗尽，攻击英雄
                                enemy = self.p2 if m.owner == self.p1 else self.p1
                                m.attack_target(enemy)
                        elif can_chain:
                            # 串击：攻击同列所有敌方异象
                            enemies = [e for e in self.board.get_enemy_minions_in_column(base_col, m.owner) if e.is_alive()]
                            # 潜水/潜行始终不可见
                            enemies = [e for e in enemies if not e.keywords.get("潜水", False) and not e.keywords.get("潜行", False)]
                            if enemies:
                                print(f"  {m.name} 串击 {self.board.COL_NAMES[base_col]}列所有敌方异象")
                                # 只调用一次 attack_target，由其内部统一处理同列所有敌方异象
                                m.attack_target(enemies[0])
                            else:
                                enemy = self.p2 if m.owner == self.p1 else self.p1
                                m.attack_target(enemy)
                        else:
                            # 普通攻击（含视野偏移、穿刺）
                            target = self.board.get_front_minion(base_col, m.owner, attacker=m)
                            if target and target.is_alive():
                                m.attack_target(target)
                            else:
                                enemy = self.p2 if m.owner == self.p1 else self.p1
                                m.attack_target(enemy)

                        attacker_swings[m] -= 1
                        if m.keywords.get("兴奋", False) and getattr(m, "_excitement_triggered", False):
                            attacker_swings[m] += 1
                            m._excitement_triggered = False
                            print(f"  {m.name} 兴奋：消灭异象后再攻击一次")
                        if self.resolve_step_callback:
                            self.resolve_step_callback()
                        if m.keywords.get("高频", 0) > 0:
                            if m not in original_first_strike:
                                original_first_strike[m] = m.keywords.get("先攻", 0)
                            current = m.keywords.get("先攻", 0)
                            if isinstance(current, int) and current > 0:
                                m.keywords["先攻"] = current - 1

                        if self.check_game_over():
                            return

                base_col = col
                self.effect_queue.resolve(f"{col_name}列发生战斗", do_round)

                # 每列结算完后按配置停顿，便于 GUI 观察战斗过程
                if self.resolve_column_delay > 0:
                    import time
                    time.sleep(self.resolve_column_delay)

        self._current_resolve_column = None
        # 结算阶段结束：恢复因高频临时降低的先攻等级
        for m, original in original_first_strike.items():
            if m.is_alive():
                m.keywords["先攻"] = original

        # 结算阶段结束：清理全场异象的临时攻击/生命 buff，并递减状态层数
        # temp_keywords 保留到 action phase start 的 clear_temp_effects() 再清理
        for m in list(self.board.minion_place.values()):
            if not m.is_alive():
                continue
            m.temp_attack_bonus = 0
            m.temp_health_bonus = 0
            m.temp_max_health_bonus = 0
            # 清理行动阶段预设的攻击目标
            if hasattr(m, "_pending_attack_targets"):
                m._pending_attack_targets = None
            # 随时间削减层数的状态关键词（修改源头以确保 recalculate 不会还原）
            for kw in ["冰冻", "眩晕", "休眠"]:
                for source in (m.base_keywords, m.perm_keywords, m.temp_keywords):
                    val = source.get(kw)
                    if isinstance(val, int) and val > 0:
                        val -= 1
                        if val <= 0:
                            source.pop(kw, None)
                        else:
                            source[kw] = val
            m.recalculate()

        # 结算阶段结束：处理成长
        for m in list(self.board.minion_place.values()):
            if not m.is_alive():
                continue
            grow = m.keywords.get("成长")
            if isinstance(grow, int) and grow > 0:
                # 通用成长前回调：返回 True 表示取消本次成长（重置计时等）
                cancel = False
                for cb in list(getattr(m, '_on_grow_callbacks', [])):
                    if cb(m, m.owner, self):
                        cancel = True
                if cancel:
                    continue
                grow -= 1
                if grow <= 0:
                    m.keywords.pop("成长", None)
                    m.evolve(self)
                else:
                    m.keywords["成长"] = grow
            elif grow == 0:
                m.keywords.pop("成长", None)
                m.evolve(self)

        self.emit_event(EVENT_PHASE_END, phase=self.PHASE_RESOLVE, first=first, second=second)

