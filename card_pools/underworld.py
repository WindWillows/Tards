# 自动生成的卡包定义文件
# 由 translate_packs.py 翻译生成

from tards import register_card, CardType, Pack, Rarity, DEFAULT_REGISTRY
from tards.targets import target_friendly_positions, target_none, target_any_minion, target_enemy_minions, target_enemy_player, target_self, target_friendly_minions, target_hand_minions
from tards.auto_effects import move_enemy_to_friendly, swap_units, return_to_hand
from tards.constants import (
    EVENT_DEPLOYED, EVENT_CARD_PLAYED, EVENT_BELL, EVENT_BEFORE_STACK_RESOLVE,
    EVENT_DRAW, EVENT_BEFORE_POINT, EVENT_TURN_START, EVENT_DEATH, EVENT_BEFORE_ATTACK,
)
from tards.cards import Strategy, MinionCard, Minion
from .underworld_effects import *

# =============================================================================
# 冥刻阴谋手动实现
# =============================================================================

# ---------- 剪刀 ----------
def _jiandao_condition(game, event_data, player):
    """对方部署异象后触发。"""
    if event_data.get("event_type") != EVENT_DEPLOYED:
        return False
    deploy_player = event_data.get("player")
    if not deploy_player or deploy_player == player:
        return False
    return True

def _jiandao_effect(game, event_data, player):
    """对方失去4T。"""
    deploy_player = event_data.get("player")
    if deploy_player:
        print(f"  阴谋 [剪刀] 触发：{deploy_player.name} 失去 4T")
        deploy_player.t_point_change(-4)


# ---------- 反戈 ----------
def _fange_condition(game, event_data, player):
    """对方打出异象时触发。"""
    if event_data.get("event_type") != EVENT_CARD_PLAYED:
        return False
    card = event_data.get("card")
    card_player = event_data.get("player")
    if not card or not isinstance(card, MinionCard):
        return False
    if card_player == player:
        return False
    return True

def _fange_effect(game, event_data, player):
    """对打出异象的玩家造成等同于其T花费的伤害。"""
    card = event_data.get("card")
    if isinstance(card, MinionCard):
        damage = card.cost.t if card.cost else 0
        target = card.owner
        if target and damage > 0:
            print(f"  阴谋 [反戈] 触发：{card.name} 的反噬对 {target.name} 造成 {damage} 点伤害")
            target.health_change(-damage)


# ---------- 蓄锐 ----------
def _xurui_condition(game, event_data, player):
    """对方拍铃且本阶段未出牌时触发。"""
    if event_data.get("event_type") != EVENT_BELL:
        return False
    bell_player = event_data.get("player")
    if bell_player == player:
        return False
    if getattr(bell_player, "_cards_played_this_phase", 0) > 0:
        return False
    return True

def _xurui_effect(game, event_data, player):
    """阴谋拥有者获得4T。"""
    print(f"  阴谋 [蓄锐] 触发：{player.name} 获得 4T")
    player.t_point_change(4)


# ---------- 墨水（堆栈反制检测） ----------
def _moshui_condition(game, event_data, player):
    """对方打出花费<=4T的策略时，通过堆栈响应窗口反制。

    检测机制：监听 before_stack_resolve 事件，查看即将结算的堆栈帧。
    若该帧对应敌方的一张<=4T策略卡，则推入反制效果到堆栈顶部（LIFO），
    使反制效果先于原效果执行，从而取消原效果并将其洗入卡组。
    """
    if event_data.get("event_type") != EVENT_BEFORE_STACK_RESOLVE:
        return False
    frame = event_data.get("frame")
    if not frame:
        return False
    source = getattr(frame, "source", None)
    if not source or not isinstance(source, Strategy):
        return False
    if source.owner == player:
        return False
    if source.cost.t > 4:
        return False

    # 推入反制效果到堆栈顶部，确保它在原效果之前结算
    def _moshui_counter():
        frame.cancelled = True
        opponent = source.owner
        # 策略卡仍在手牌中（play_fn 尚未执行），将其移除并洗入卡组
        if source in opponent.card_hand:
            opponent.card_hand.remove(source)
        opponent.card_deck.append(source)
        import random
        random.shuffle(opponent.card_deck)
        print(f"  阴谋 [墨水] 反制：{source.name} 被洗入 {opponent.name} 的卡组")

    game.effect_queue.push_stack("阴谋 [墨水] 反制", _moshui_counter)
    return True

def _moshui_effect(game, event_data, player):
    """反制的主要工作已在 condition_fn 的堆栈推入中完成，
    此处仅打印确认信息。阴谋卡本身由 register_conspiracy 自动弃置。
    """
    print(f"  阴谋 [墨水] 结算完毕")


# ---------- 劲风 ----------
def _jinfeng_condition(game, event_data, player):
    """对方在额外抽牌阶段（非系统抽牌阶段）抽牌时触发。"""
    if event_data.get("event_type") != EVENT_DRAW:
        return False
    draw_player = event_data.get("player")
    if not draw_player or draw_player == player:
        return False
    if game.current_phase == game.PHASE_DRAW:
        return False
    return True

def _jinfeng_effect(game, event_data, player):
    """弃掉对方抽到的牌，并随机使其一张手牌花费+1T。"""
    draw_player = event_data.get("player")
    card = event_data.get("card")
    if card and card in draw_player.card_hand:
        draw_player.card_hand.remove(card)
        draw_player.card_dis.append(card)
        print(f"  阴谋 [劲风] 弃掉了 {draw_player.name} 抽到的 [{card.name}]")
    if draw_player.card_hand:
        import random
        target_card = random.choice(draw_player.card_hand)
        target_card.cost.t += 1
        print(f"  阴谋 [劲风] 使 {draw_player.name} 的 [{target_card.name}] 花费 +1T")


# ---------- 离群 ----------
def _liqun_condition(game, event_data, player):
    """敌方异象部署后，若其所在列进入协同状态（该列有≥2个敌方异象），触发。"""
    if event_data.get("event_type") != EVENT_DEPLOYED:
        return False
    minion = event_data.get("minion")
    if not minion or minion.owner == player:
        return False
    pos = minion.position
    c = pos[1]
    enemy_count = 0
    for r in range(game.board.SIZE):
        m = game.board.minion_place.get((r, c))
        if m and m.owner == minion.owner:
            enemy_count += 1
    # 部署后 enemy_count >= 2 且部署前 enemy_count - 1 <= 1
    if enemy_count >= 2 and (enemy_count - 1) <= 1:
        return True
    return False

def _liqun_effect(game, event_data, player):
    """消灭该列所有进入协同状态的敌方异象。"""
    minion = event_data.get("minion")
    c = minion.position[1]
    from card_pools.effect_utils import destroy_minion
    to_destroy = []
    for r in range(game.board.SIZE):
        m = game.board.minion_place.get((r, c))
        if m and m.owner == minion.owner:
            to_destroy.append(m)
    for m in to_destroy:
        destroy_minion(m, game)
    print(f"  阴谋 [离群] 消灭了 {len(to_destroy)} 个进入协同状态的异象")


# ---------- 入河 ----------
_RUHE_LISTENER_ID = 987654321

def _ruhe_condition(game, event_data, player):
    """对方部署异象前（堆栈响应窗口），将其移除并延迟至下回合加入原位。"""
    if event_data.get("event_type") != EVENT_BEFORE_STACK_RESOLVE:
        return False
    frame = event_data.get("frame")
    if not frame:
        return False
    source = getattr(frame, "source", None)
    if not source or not isinstance(source, MinionCard):
        return False
    if source.owner == player:
        return False
    target = getattr(source, "_deploy_target", None)
    if not target:
        return False

    def _counter():
        frame.cancelled = True
        deploy_player = source.owner
        if source in deploy_player.card_hand:
            deploy_player.card_hand.remove(source)
        pending = getattr(game, "_ruhe_pending", [])
        pending.append({
            "card": source,
            "player": deploy_player,
            "pos": target,
            "trigger_turn": game.current_turn + 1,
        })
        game._ruhe_pending = pending
        print(f"  阴谋 [入河] 反制了 [{source.name}] 的部署，下回合将其加入原位 {target}")

    game.effect_queue.push_stack("阴谋 [入河] 反制", _counter)
    return True

def _ruhe_effect(game, event_data, player):
    """注册回合开始监听器，延迟部署被反制的异象。"""
    listener_id = id(event_data)

    def _redeploy_listener(event):
        pending = getattr(game, "_ruhe_pending", [])
        to_remove = []
        for item in pending:
            if game.current_turn >= item["trigger_turn"]:
                card = item["card"]
                deploy_player = item["player"]
                pos = item["pos"]
                minion = Minion(
                    name=card.name,
                    owner=deploy_player,
                    position=pos,
                    attack=card.attack,
                    health=card.health,
                    source_card=card,
                    board=game.board,
                    keywords=dict(card.keywords) if card.keywords else {},
                    on_turn_start=card.on_turn_start,
                    on_turn_end=card.on_turn_end,
                    on_phase_start=card.on_phase_start,
                    on_phase_end=card.on_phase_end,
                    tags=list(card.tags) if card.tags else [],
                    hidden_keywords=dict(card.hidden_keywords) if card.hidden_keywords else {},
                )
                minion.summon_turn = game.current_turn
                game.board.place_minion(minion, pos)
                print(f"  阴谋 [入河] 将 [{card.name}] 加入战场 {pos}")
                to_remove.append(item)
        for item in to_remove:
            pending.remove(item)
        game._ruhe_pending = pending
        if not pending:
            game.unregister_listeners_by_owner(listener_id)

    game.register_listener(EVENT_TURN_START, _redeploy_listener, priority=50, owner_id=listener_id)
    print(f"  阴谋 [入河] 效果触发：等待下回合将异象加入原位")


# ---------- 怪石 ----------
def _guaishi_condition(game, event_data, player):
    """对方拉闸且剩余T点为0时触发。"""
    if event_data.get("event_type") != EVENT_BELL:
        return False
    bell_player = event_data.get("player")
    if not bell_player or bell_player == player:
        return False
    if bell_player.t_point != 0:
        return False
    return True

def _guaishi_effect(game, event_data, player):
    """对方永久失去一个T槽。"""
    bell_player = event_data.get("player")
    if bell_player:
        bell_player.t_point_max_change(-1)
        print(f"  阴谋 [怪石] 触发：{bell_player.name} 失去一个T槽（当前上限 {bell_player.t_point_max}）")


# ---------- 海市蜃楼 ----------
def _haishi_condition(game, event_data, player):
    """1个异象被指向前，改为其随机敌方异象成为指向目标。"""
    if event_data.get("event_type") != EVENT_BEFORE_POINT:
        return False
    event = event_data.get("_event_ref")
    if not event:
        return False
    target = event.data.get("target")
    if not isinstance(target, Minion):
        return False
    source_player = event.data.get("player")
    if source_player == player:
        return False
    # 改为被指向异象的随机敌方异象
    enemy_minions = [m for m in game.board.minion_place.values()
                     if m.owner != target.owner and m.is_alive()]
    if not enemy_minions:
        return False
    import random
    new_target = random.choice(enemy_minions)
    event.data["target"] = new_target
    print(f"  阴谋 [海市蜃楼] 将指向目标从 [{target.name}] 改为 [{new_target.name}]")
    return True

def _haishi_effect(game, event_data, player):
    """重定向已在 condition_fn 中同步完成。"""
    print(f"  阴谋 [海市蜃楼] 结算完毕")


# ---------- 掩星 ----------
def _yanxing_condition(game, event_data, player):
    """场上敌方异象数量成为唯一最多时触发。"""
    event_type = event_data.get("event_type")
    if event_type == EVENT_DEPLOYED:
        minion = event_data.get("minion")
        if not minion or minion.owner == player:
            return False
        enemy_count = sum(1 for m in game.board.minion_place.values()
                          if m.owner != player and m.is_alive())
        friendly_count = sum(1 for m in game.board.minion_place.values()
                             if m.owner == player and m.is_alive())
        if enemy_count > friendly_count and (enemy_count - 1) <= friendly_count:
            return True
        return False
    elif event_type == EVENT_DEATH:
        minion = event_data.get("minion")
        if not minion or minion.owner != player:
            return False
        enemy_count = sum(1 for m in game.board.minion_place.values()
                          if m.owner != player and m.is_alive())
        friendly_count = sum(1 for m in game.board.minion_place.values()
                             if m.owner == player and m.is_alive())
        if enemy_count > friendly_count and enemy_count <= (friendly_count + 1):
            return True
        return False
    return False

def _yanxing_effect(game, event_data, player):
    """阴谋拥有者抽2张牌。"""
    print(f"  阴谋 [掩星] 触发：{player.name} 抽2张牌")
    player.draw_card(2, game=game)


# ---------- 夜袭 ----------
def _yexi_condition(game, event_data, player):
    """敌方异象对阴谋拥有者造成伤害前触发。"""
    if event_data.get("event_type") != EVENT_BEFORE_ATTACK:
        return False
    attacker = event_data.get("attacker")
    defender = event_data.get("defender")
    if not isinstance(attacker, Minion):
        return False
    if attacker.owner == player:
        return False
    if defender != player:
        return False
    return True

def _yexi_effect(game, event_data, player):
    """使其先获得-2攻击力。若具有迅捷，将其消灭。"""
    attacker = event_data.get("attacker")
    from card_pools.effect_utils import destroy_minion
    if attacker.keywords.get("迅捷", False):
        destroy_minion(attacker, game)
        print(f"  阴谋 [夜袭] 消灭了具有迅捷的 [{attacker.name}]")
    else:
        attacker.base_attack -= 2
        attacker.recalculate()
        print(f"  阴谋 [夜袭] 使 [{attacker.name}] 获得-2攻击力（当前 {attacker.current_attack}）")


# Pack: UNDERWORLD

register_card(
    name="松鼠球",
    cost_str="5T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=9,
    keywords={"协同": True, "献祭": 2, "亡语": True},
    evolve_to="松鼠",
    # 效果描述：受到伤害后，向相邻陆地移动一格，在原地留下一只“松鼠”。 亡语：在原地留下一只“松鼠”。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="松鼠",
    cost_str="1T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=2,
    tags=['生物', '陆生'],
    is_token=True,
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="松鼠罐",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"协同": True, "丰饶": 2},
    # 效果描述：回合结束：消灭友方场上的“松鼠”。每消灭一只，献祭等级+1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="猫",
    cost_str="1T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=1,
    # 效果描述：不会因献祭而被消灭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="黑山羊",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=4,
    keywords={"协同": True, "绝缘": True, "丰饶": 3, "亡语": True},
    # 效果描述：亡语：若献祭点数溢出，抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="13号孩子",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=1,
    keywords={"绝缘": True, "献祭": 13},
    evolve_to="13号",
    # 效果描述：无法被异象选中。献祭后，变为“13号”。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="13号",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"空袭": True, "亡语": True},
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：献祭后，转换为“13号孩子”。亡语：消灭伤害来源。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="烛烟",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=2,
    keywords={"协同": True, "亡语": True},
    tags=['生物', '陆生'],
    # 效果描述：亡语：抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=_zhuyan_special,
)

register_card(
    name="大团烛烟",
    cost_str="1T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"协同": True, "丰饶": 2, "迅捷": True, "亡语": True},
    tags=['生物', '陆生'],
    # 效果描述：亡语：抽2张牌。
    targets_fn=target_friendly_positions,
    special_fn=_datuanzhuyan_special,
)

register_card(
    name="白鼬",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=6,
    keywords={"协同": True, "迅捷": True},
    # 效果描述：受到战斗伤害后，将其消灭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="臭虫",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=6,
    keywords={"协同": True, "尖刺": 1},
    # 效果描述：与其同列的敌方异象具有-1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=_chouchong_special,
)

register_card(
    name="弱狼",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"协同": True, "亡语": True},
    # 效果描述：亡语：造成3点伤害，随机分配至敌方主角与伤害来源。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="林鼠",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=3,
    keywords={"丰饶": 2},
    # 效果描述：部署：抽一张指令，或将1只0T的松鼠加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=_linshu_special,
)

register_card(
    name="狼",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    # 效果描述：无法选中HP不大于2的异象。回合开始：对一个本列异象造成2点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="灰熊",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=6,
    keywords={"坚韧": 1},
    # 效果描述：对方部署异象时，失去1T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="棕熊",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=4,
    health=5,
    keywords={"先攻": 1},
    # 效果描述：兴奋 对攻击力≤3的异象伤害+2。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="陆龟",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=8,
    keywords={"协同": True, "坚韧": 2},
    # 效果描述：处于协同时，受到的战斗伤害翻倍。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="翠鸟",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=1,
    keywords={"两栖": True, "先攻": 1},
    tags=['两栖'],
    # 效果描述：部署：若在水路，获得潜水和空袭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="雕",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=5,
    health=4,
    keywords={"两栖": True, "迅捷": True, "先攻": 3},
    tags=['两栖'],
    # 效果描述：首次攻击后，失去先攻Ⅲ，获得-3攻击力和空袭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鹰",
    cost_str="2T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=3,
    keywords={"视野": 2, "高频": 3},
    # 效果描述：受到其伤害的目标此前每被本异象指向一次，受到的伤害+1.
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="雀",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=1,
    health=2,
    keywords={"协同": True, "两栖": True},
    tags=['两栖'],
    # 效果描述：部署时：将其复制加入战场。回合结束：将其复制加入战场。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鹞",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=5,
    health=3,
    keywords={"两栖": True, "迅捷": True},
    tags=['两栖'],
    # 效果描述：受到伤害时，改为失去1点HP。无法获得HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鸥",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=2,
    health=4,
    keywords={"水生": True, "潜水": True, "高频": 2, "亡语": True},
    tags=['水生'],
    # 效果描述：免疫非战斗伤害。亡语：抽1张异象，使其具有两栖。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="雄鹿",
    cost_str="4T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=3,
    keywords={"丰饶": 2},
    # 效果描述：无法攻击对手。回合结束：若本回合未受到伤害，获得+1/1并对对手造成等同 于其攻击力的伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="雌鹿",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=6,
    keywords={"协同": True, "丰饶": 2},
    # 效果描述：攻击力最高的敌方异象无法攻击。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="豪猪",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=6,
    keywords={"协同": True, "坚韧": 1},
    # 效果描述：受到伤害后，对伤害来源造成等量伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="牛蛙",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=2,
    health=2,
    keywords={"协同": True, "水生": True, "防空": True},
    tags=['水生'],
    # 效果描述：部署：将其复制加入同一列，使其具有迅捷。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="林蛙",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=2,
    keywords={"两栖": True, "防空": True},
    tags=['两栖'],
    # 效果描述：部署：消灭场上攻击力最低的异象，获得被消灭异象的攻击力与防御力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="河狸",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    keywords={"两栖": True, "潜水": True},
    tags=['两栖'],
    evolve_to="河坝",
    # 效果描述：回合开始：将一张“河坝”加入对方手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="河坝",
    cost_str="1T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=1,
    keywords={"水生": True},
    tags=['水生', '两栖', '生物'],
    is_token=True,
    # 效果描述：回合开始：将其消灭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="地鼠",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=6,
    keywords={"协同": True, "尖刺": 1, "坚韧": 1},
    # 效果描述：如可能，移动以承担指向友方目标的伤害。回合结束：将HP改为6。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蛇",
    cost_str="1T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    keywords={"高频": 2, "亡语": True},
    # 效果描述：对HP不小于本异象的目标，伤害+1。亡语：对全体敌方目标造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="兀鹫",
    cost_str="0T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"空袭": True, "高地": True},
    # 效果描述：友方异象攻击后，若攻击目标 HP不小于2，令攻击目标失去1点HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="箭毒蛙",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=1,
    keywords={"迅捷": True, "两栖": True, "亡语": True},
    tags=['两栖'],
    # 效果描述：对对手造成的伤害翻倍。亡语：对方所有手牌花费+1T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="松毛虫",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=2,
    keywords={"协同": True, "亡语": True},
    # 效果描述：对对手造成的伤害翻倍。亡语：对方所有手牌获得：打出时，受到1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="“猹”",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=3,
    keywords={"潜水": True, "两栖": True, "亡语": True},
    tags=['两栖'],
    evolve_to="西瓜",
    # 效果描述：回合结束：场上异象更少的一方抽一张牌。亡语：将一张“西瓜”加入原位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="西瓜",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"协同": True, "亡语": True},
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：亡语：双方各抽2张牌。
    targets_fn=target_friendly_positions,
    special_fn=_xigua_special,
)

register_card(
    name="螳螂",
    cost_str="1T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=5,
    keywords={"协同": True},
    # 效果描述：受伤时，友方陆地异象具有+1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="象群",
    cost_str="6T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=8,
    keywords={"坚韧": 1, "先攻": -1},
    # 效果描述：部署：对所有异象造成1点伤害。回合开始时，随机眩晕一个敌方异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="信鸽",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    keywords={"两栖": True, "迅捷": True},
    tags=['两栖'],
    # 效果描述：回合结束：返回手牌，抽一张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="隼",
    cost_str="5T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=3,
    health=1,
    keywords={"先攻": 3, "迅捷": True},
    # 效果描述：攻击后，返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鸠",
    cost_str="4T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=2,
    health=2,
    keywords={"协同": True, "两栖": True, "穿透": True},
    tags=['两栖'],
    # 效果描述：友方异象被消灭后，加入其位置并攻击。友方异象部署时，本异象返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="节肢座首",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"脆弱": True, "亡语": True},
    tags=['生物', '陆生', '昆虫'],
    statue_top=True,
    statue_bottom=False,
    statue_pair="arthropod",
    on_statue_activate=_arthropod_top_effect,
    # 效果描述：（雕像激活后将在回合结束时移除 保留增益） 激活时：所有友方昆虫异象具有亡语；对对手造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="多足底座",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=4,
    tags=['生物', '陆生', '昆虫'],
    statue_top=False,
    statue_bottom=True,
    statue_pair="arthropod",
    on_statue_fuse=_arthropod_bottom_effect,
    # 效果描述：（只有“上下匹配”的雕像可以在一回合内拼装 否则需要两回合） 融合：激活座首，所有友方昆虫异象进入战场时+1/1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="水肺座首",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"脆弱": True},
    tags=['生物', '陆生', '水生', '两栖'],
    statue_top=True,
    statue_bottom=False,
    statue_pair="aquatic",
    on_statue_activate=_aquatic_top_effect,
    # 效果描述：激活时：所有友方两栖/水生异象部署花费-1T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鳍尾底座",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"两栖": True},
    tags=['两栖', '生物', '水生'],
    statue_top=False,
    statue_bottom=True,
    statue_pair="aquatic",
    on_statue_fuse=_aquatic_bottom_effect,
    # 效果描述：融合：激活座首，所有友方两栖/水生异象具有先攻1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="尖牙座首",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"脆弱": True},
    tags=['生物', '陆生', '肉食动物'],
    statue_top=True,
    statue_bottom=False,
    statue_pair="predator",
    on_statue_activate=_predator_top_effect,
    # 效果描述：激活时：所有友方的陆生肉食动物进入战场时+2/1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="利爪底座",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"高地": True},
    tags=['生物', '陆生', '肉食动物'],
    statue_top=False,
    statue_bottom=True,
    statue_pair="predator",
    on_statue_fuse=_predator_bottom_effect,
    # 效果描述：融合：激活座首，所有友方陆生肉食动物部署花费-1B。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="丰饶座首",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"脆弱": True},
    tags=['生物', '陆生'],
    statue_top=True,
    statue_bottom=False,
    statue_pair="sacrifice",
    on_statue_activate=_sacrifice_top_effect,
    # 效果描述：激活时：每回合首个友方B=0异象入场时献祭等级+1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="牢牲底座",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=4,
    tags=['生物', '陆生'],
    statue_top=False,
    statue_bottom=True,
    statue_pair="sacrifice",
    on_statue_fuse=_sacrifice_bottom_effect,
    # 效果描述：中路 融合：激活座首，所有B=0异象丰饶等级+1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="长翅座首",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"脆弱": True},
    tags=['生物', '陆生', '飞禽'],
    statue_top=True,
    statue_bottom=False,
    statue_pair="avian",
    on_statue_activate=_avian_top_effect,
    # 效果描述：激活时：所有友方飞禽类异象具有迅捷。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="破风底座",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"高地": True},
    tags=['生物', '陆生', '飞禽'],
    statue_top=False,
    statue_bottom=True,
    statue_pair="avian",
    on_statue_fuse=_avian_bottom_effect,
    # 效果描述：融合：激活座首，所有友方飞禽类异象首次攻击力+2。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="幼狼",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=2,
    keywords={"成长": 1},
    evolve_to="成狼",
    # 效果描述：组队 成长时，若不是组队状态，重置计时。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="成狼",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"协同": True, "高频": 2, "成长": 2},
    tags=['友好', '生物', '肉食动物', '陆生'],
    is_token=True,
    evolve_to="狼王",
    # 效果描述：成长前，若未消灭过异象，失去成长2。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="狼王",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    keywords={"协同": True, "高频": 2},
    tags=['友好', '生物', '肉食动物', '陆生'],
    is_token=True,
    # 效果描述：所有友方异象具有坚韧1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="幼鸟",
    cost_str="1T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=1,
    keywords={"成长": 2},
    evolve_to="成鸟",
    # 效果描述：部署：指向一个友方飞禽异象，使其获得+3防御力和“友方幼鸟无法选中”。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="成鸟",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=2,
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：若指向异象存活，将本异象转换为指向异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="奇怪的蛹",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=4,
    keywords={"协同": True},
    evolve_to="巨蛾",
    # 效果描述：出牌阶段结束：弃掉此牌，将一张“巨蛾”洗入卡组。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="巨蛾",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"迅捷": True},
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：友方迅捷异象具有+1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="群猿",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    # 效果描述：组队 每有一个其它异象被献祭，+1/1，丰饶等级+1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="狐",
    cost_str="0T4B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=0,
    health=4,
    keywords={"迅捷": True, "三重打击": True},
    # 效果描述：攻击后，获得+1攻击力。免疫偶数伤害。
    targets_fn=target_friendly_positions,
    special_fn=_hu_special,
)

register_card(
    name="鹤",
    cost_str="5T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=6,
    keywords={"两栖": True},
    tags=['两栖'],
    # 效果描述：组队 回合开始：重置一个异象的攻击力与防御力，你获得+1HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="夜枭",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    # 效果描述：敌方异象部署、加入和被消灭时，对对手造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鮟鱇",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=4,
    keywords={"重甲": 1, "水生": True},
    tags=['水生'],
    # 效果描述：回合结束：指向一个异象。回合开始：消灭指向异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鹏",
    cost_str="5T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=2,
    health=6,
    keywords={"横扫": 1, "迅捷": True},
    # 效果描述：所有花费≤5的非飞禽异象部署时具有休眠I。 部署：使敌方花费不大于4的异象返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=lambda p, t, g, extras=None: return_to_hand(t, g, p),
)

register_card(
    name="鲲",
    cost_str="5T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=2,
    health=6,
    keywords={"水生": True, "坚韧": 1, "横扫": 1},
    tags=['水生'],
    # 效果描述：平地均算作是水路。 部署：使全体友方非两栖异象获得“水生”。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="食蚁兽",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"迅捷": True},
    # 效果描述：被弃掉或被从卡组中移除时：改为加入战场。部署：双方随机弃一张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="头鹿",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=4,
    keywords={"协同": True, "坚韧": 1, "成长": 2},
    evolve_to="老鹿",
    # 效果描述：你的手牌花费-1T。成长时，若场上有B=0异象，改为重置计时。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="老鹿",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=1,
    keywords={"协同": True},
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：你的手牌花费+1T。无法选中。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="信天翁",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=3,
    keywords={"迅捷": True, "空袭": True},
    # 效果描述：部署：使异象更多一方的一个异象返回其所有者手中。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鼯鼱",
    cost_str="1T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=1,
    keywords={"迅捷": True},
    # 效果描述：必须是本轮部署的第一个异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="豺",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=4,
    health=4,
    keywords={"亡语": True},
    # 效果描述：部署：失去1个T槽。亡语：所有手牌花费-1T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="负鼠",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"坚韧": 1},
    # 效果描述：场上有不少于3个友方异象时，花费-2B。部署：开发一张卡组中的牌。
    targets_fn=target_friendly_positions,
    special_fn=lambda p, t, g, extras=None: g.develop_card(p, p.original_deck_defs),
)

register_card(
    name="追猎者",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=1,
    keywords={"亡语": True},
    # 效果描述：部署：指向一个不处于本列的异象。亡语：将其消灭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="嘲鸫",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    keywords={"两栖": True, "潜水": True},
    tags=['两栖'],
    # 效果描述：友方异象在受到致命伤害前，先获得+1HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="木鹊",
    cost_str="5T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=3,
    # 效果描述：你的手牌花费-1B。 回合结束：若本回合对手受到的伤害累计不小于3，你获得1B。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="牛虻",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=3,
    keywords={"协同": True},
    # 效果描述：敌方目标被指向后，也算作是被本异象指向。 回合开始：使所有被本异象指向的目标失去1点HP。 部署：指向一个目标。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="野牛",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=5,
    health=6,
    keywords={"坚韧": 1},
    # 效果描述：攻击目标的HP不大于3时，具有穿透。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="跳蛛",
    cost_str="1T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"防空": True},
    # 效果描述：若这是你本回合部署的最后一个异象，获得迅捷。 你部署献祭点数大于0的异象时，对对手造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鹳",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    keywords={"视野": 2, "两栖": True},
    tags=['两栖'],
    # 效果描述：将其消灭的异象的回响加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="燕",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=3,
    keywords={"迅捷": True, "穿刺": True, "两栖": True},
    tags=['两栖'],
    # 效果描述：部署：失去一个T槽。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="天牛",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=4,
    keywords={"协同": True, "穿透": True},
    # 效果描述：回合结束：使同列敌方前排异象移动至后排，后排异象返回对方手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="射水鱼",
    cost_str="4T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"水生": True, "防空": True, "视野": 2},
    tags=['水生'],
    # 效果描述：对空袭与昆虫异象伤害翻倍。受到本异象伤害的异象本回合改为在回合结束时 攻击。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鸮",
    cost_str="4T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=5,
    keywords={"视野": 1, "先攻": 1},
    # 效果描述：攻击时，改为与目标对战。消灭一个异象后，获得等同于其攻击力的HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鬣狗",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=2,
    health=1,
    keywords={"迅捷": True, "先攻": 1, "协同": True},
    # 效果描述：将其消灭的异象的回响加入手牌。你打出或弃掉回响时，本异象返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="寄居蟹",
    cost_str="4T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    keywords={"坚韧": 1, "两栖": True, "协同": True},
    tags=['两栖'],
    # 效果描述：回合结束：向相邻方向移动一格。 将受到其伤害的异象的回响加入手牌，回合开始时弃掉。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="猞猁",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=5,
    keywords={"协同": True, "坚韧": 1},
    # 效果描述：相邻异象受到伤害时，改为由本异象承受。 回合结束：若本异象本回合未受到伤害，对对手造成2点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蟒",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=3,
    keywords={"迅捷": True, "亡语": True},
    # 效果描述：必须是本回合双方部署的第2个异象。 亡语：若消灭过异象，随机消灭一个敌方异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="避役",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=2,
    # 效果描述：受到不小于4的单次伤害时，改为失去1点HP。 部署：开发1张冥刻阴谋。
    targets_fn=target_friendly_positions,
    special_fn=lambda p, t, g, extras=None: g.develop_card(p, [c for c in DEFAULT_REGISTRY.all_cards() if c.pack == Pack.UNDERWORLD and c.card_type == CardType.CONSPIRACY]),
)

register_card(
    name="雪豹",
    cost_str="3T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=5,
    health=5,
    keywords={"先攻": 1, "高地": True},
    # 效果描述：部署：将1个花费不大于2T的异象移动至友方区域。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="水螅岩",
    cost_str="5T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=5,
    health=3,
    keywords={"水生": True, "成长": True, "亡语": True},
    tags=['水生'],
    evolve_to="水螅群",
    # 效果描述：亡语：若是由于异象效果被消灭，改为在回合结束时成长。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="水螅群",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    keywords={"水生": True},
    tags=['水生', '两栖', '生物'],
    is_token=True,
    # 效果描述：抽牌阶段：对方失去3T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蚜虫",
    cost_str="4T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"亡语": True},
    # 效果描述：亡语：T槽更少的一方失去1个T槽。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蚊",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=4,
    keywords={"协同": True},
    # 效果描述：对方所有异象花费+2T。对方异象部署前，本异象返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鸬鹚",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=4,
    keywords={"协同": True},
    # 效果描述：友方异象更少时，使所有敌方异象具有-1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="虎",
    cost_str="4T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=6,
    health=6,
    keywords={"坚韧": 2, "绝缘": True},
    # 效果描述：对方无法使用策略指向友方异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="环形虫",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=2,
    keywords={"亡语": True},
    # 效果描述：部署：指向一个异象。亡语：使伤害来源与一个随机敌方异象对战。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="石钱子",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=4,
    keywords={"协同": True, "迅捷": True, "亡语": True},
    evolve_to="断尾",
    # 效果描述：亡语：将一张“断尾”加入原位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="断尾",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=1,
    keywords={"协同": True},
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：回合结束：转换为“石钱子”。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蚁穴",
    cost_str="5T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=6,
    keywords={"坚韧": 1},
    # 效果描述：场上有昆虫类异象时，HP无法降至1以下。 回合开始：将1张“兵蚁”加入战场。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="兵蚁",
    cost_str="1T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    keywords={"协同": True, "迅捷": True},
    tags=['生物', '陆生'],
    # 效果描述：场上每有一个友方昆虫异象，+1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

def _songshuping_effect(player, target, game, extras=None):
    """松鼠瓶：将2张"松鼠"加入手牌，此前你每使用过一次"松鼠瓶"，额外加入一只"松鼠"。

    松鼠直接从卡池定义创建新 token（不消耗 squirrel_deck）。
    若手牌已满，超出部分弃置。
    """
    squirrel_def = DEFAULT_REGISTRY.get("松鼠")
    if not squirrel_def:
        print(f"  [警告] 找不到松鼠定义，松鼠瓶效果失败")
        return False

    used_count = getattr(player, "_squirrel_bottle_used", 0)
    count = 2 + used_count

    added = 0
    discarded = 0
    for _ in range(count):
        card = squirrel_def.to_game_card(player)
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(card)
            added += 1
        else:
            player.card_dis.append(card)
            discarded += 1

    player._squirrel_bottle_used = used_count + 1

    print(
        f"  {player.name} 使用松鼠瓶，将 {added} 张松鼠加入手牌"
        f"{'（' + str(discarded) + ' 张因手牌满被弃置）' if discarded else ''}"
    )
    return True


register_card(
    name="松鼠瓶",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：将2张“松鼠”加入手牌，此前你每使用过一次“松鼠瓶”，额外加入一只“松鼠”。
    targets_fn=target_none,
    effect_fn=_songshuping_effect,
)

def _shudong_targets(player, board):
    from card_pools.effect_utils import empty_positions
    return empty_positions(player, board)


def _shudong_effect(player, target, game, extras=None):
    from card_pools.effect_utils import all_friendly_minions, deploy_card_copy
    from tards.card_db import Pack

    # 1. 部署松鼠
    squirrel_def = DEFAULT_REGISTRY.get("松鼠")
    if not squirrel_def:
        return False
    card = squirrel_def.to_game_card(player)
    ok = deploy_card_copy(player, game, card, target)
    if not ok:
        return False

    # 2. 给友方 B=0 冥刻异象添加"无法被选中"
    affected = []
    for m in all_friendly_minions(game, player):
        source = getattr(m, "source_card", None)
        if source and getattr(source, "pack", None) == Pack.UNDERWORLD and source.cost.b == 0:
            m.temp_keywords["无法被选中"] = True
            affected.append(m.name)
    if affected:
        print(f"  树洞：本回合 {', '.join(affected)} 无法被选中")

    return True


register_card(
    name="树洞",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：将一只"松鼠"加入战场，本回合所有B=0友方异象无法选中。
    targets_fn=_shudong_targets,
    effect_fn=_shudong_effect,
)

def _xueping_effect(player, target, game, extras=None):
    if target not in player.card_hand:
        return False
    from tards.cards import MinionCard
    if not isinstance(target, MinionCard):
        return False
    # 弃掉目标异象
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  {player.name} 弃掉了 [{target.name}]")
    # 获得3B
    player.b_point_change(3)
    # 若非松鼠，抽一张牌
    if target.name != "松鼠":
        player.draw_card(1, game=game)
    return True


register_card(
    name="血瓶",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：选择并弃一张异象，获得3B。若非松鼠，抽一张牌。
    targets_fn=target_hand_minions,
    effect_fn=_xueping_effect,
)

register_card(
    name="金牙齿",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    asset_id="jin_yachi",
    # 效果描述：对一个目标造成1点伤害。若将其消灭，获得1T，抽一张牌。
    targets_fn=target_any_minion_or_enemy_player,
    effect_fn=_jin_yachi_strategy,
)

def _qianzi_effect(player, target, game, extras=None):
    """钳子：对你造成2点伤害，然后对一个异象造成4点伤害。抽一张牌。"""
    from card_pools.effect_utils import deal_damage_to_player, deal_damage_to_minion
    from tards.cards import Minion

    # 对自己造成2点伤害
    deal_damage_to_player(player, 2, game=game)
    print(f"  钳子：{player.name} 受到2点伤害")

    # 对目标异象造成4点伤害
    if isinstance(target, Minion) and target.is_alive():
        deal_damage_to_minion(target, 4, game=game)
        print(f"  钳子：{target.name} 受到4点伤害")

    # 抽一张牌
    player.draw_card(1, game=game)
    print(f"  钳子：{player.name} 抽1张牌")
    return True


register_card(
    name="钳子",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对你造成2点伤害，然后对一个异象造成4点伤害。抽一张牌。
    targets_fn=target_any_minion,
    effect_fn=_qianzi_effect,
)

def _linshu_daobing_effect(player, target, game, extras=None):
    import random
    from card_pools.effect_utils import (
        deal_damage_to_player, deal_damage_to_minion, all_enemy_minions,
    )
    from tards.cards import Minion

    # 1. 对你造成4点伤害
    deal_damage_to_player(player, 4, source=None, game=game)

    # 2. 8点伤害随机分配至所有敌方目标
    opponent = game.p2 if player == game.p1 else game.p1
    for _ in range(8):
        enemy_minions = [m for m in all_enemy_minions(game, player) if m.is_alive()]
        candidates = enemy_minions + [opponent]
        if not candidates:
            break
        chosen = random.choice(candidates)
        if isinstance(chosen, Minion):
            deal_damage_to_minion(chosen, 1, source=None, game=game)
        else:
            deal_damage_to_player(chosen, 1, source=None, game=game)

    return True


register_card(
    name="林鼠匕首",
    cost_str="5T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：对你造成4点伤害，然后造成8点伤害，随机分配至所有敌方目标。
    targets_fn=target_none,
    effect_fn=_linshu_daobing_effect,
)

def _guwang_effect(player, target, game, extras=None):
    from tards.cards import MinionCard
    if not isinstance(target, MinionCard) or target not in player.card_hand:
        return False

    # 弃掉目标异象
    player.card_hand.remove(target)
    player.card_dis.append(target)

    # 计算献祭等级与丰饶等级
    sac_level = target.keywords.get("献祭", 0)
    if sac_level is True:
        sac_level = 1
    elif not isinstance(sac_level, int):
        sac_level = 0

    fer_level = target.keywords.get("丰饶", 0)
    if fer_level is True:
        fer_level = 1
    elif not isinstance(fer_level, int):
        fer_level = 0

    product = sac_level * fer_level
    card_name = "骨王之赏" if product >= 2 else "骨王之惠"

    card_def = DEFAULT_REGISTRY.get(card_name)
    if card_def:
        card = card_def.to_game_card(player)
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(card)
        else:
            player.card_dis.append(card)
        print(f"  骨王：弃掉 [{target.name}]（献祭{sac_level}×丰饶{fer_level}={product}），获得 [{card_name}]")
    else:
        print(f"  骨王：找不到 {card_name} 的定义")

    return True


register_card(
    name="骨王",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：选择并弃一张异象，若其献祭等级与丰饶等级之积不小于2，将一张"骨王之 赏"加入手牌；否则将一张"骨王之惠"加入手牌。
    targets_fn=target_hand_minions,
    effect_fn=_guwang_effect,
)

def _guwangzhi_hui_effect(player, target, game, extras=None):
    """骨王之惠：抽一张牌，使其-2T1B。"""
    if not player.card_deck:
        print("  骨王之惠：牌库为空")
        return True
    card = player.card_deck.pop()
    card.cost.t = max(0, card.cost.t - 2)
    card.cost.b += 1
    if len(player.card_hand) < player.card_hand_max:
        player.card_hand.append(card)
        print(f"  骨王之惠：抽出 [{card.name}]，费用变为 {card.cost}")
    else:
        player.card_dis.append(card)
        print(f"  骨王之惠：手牌已满，[{card.name}] 被弃置")
    return True


def _guwangzhi_shang_effect(player, target, game, extras=None):
    """骨王之赏：抽2张牌，免除其献祭点数。"""
    drawn = []
    for _ in range(2):
        if not player.card_deck:
            break
        card = player.card_deck.pop()
        drawn.append(card)

    for card in drawn:
        # 免除献祭点数：将鲜血费用设为0
        card.cost.b = 0
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(card)
            print(f"  骨王之赏：抽出 [{card.name}]，献祭点数已免除")
        else:
            player.card_dis.append(card)
            print(f"  骨王之赏：手牌已满，[{card.name}] 被弃置")
    return True


register_card(
    name="骨王之惠",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    is_token=True,
    # 效果描述：抽一张牌，使其-2T1B。
    targets_fn=target_none,
    effect_fn=_guwangzhi_hui_effect,
)

register_card(
    name="骨王之赏",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    is_token=True,
    # 效果描述：抽2张牌，免除其献祭点数。
    targets_fn=target_none,
    effect_fn=_guwangzhi_shang_effect,
)

def _lazhu_effect(player, target, game, extras=None):
    # 获得+6HP（上限+当前）
    player.health_max_change(6)
    player.health_change(6)
    # 抽2张牌
    player.draw_card(2, game=game)
    return True


register_card(
    name="蜡烛",
    cost_str="6T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：你获得+6HP，抽2张牌。此前你每使用过一次"烛烟"，花费-2T。
    targets_fn=target_none,
    effect_fn=_lazhu_effect,
)

def _zhiwuxuejia_effect(player, target, game, extras=None):
    from tards.cards import MinionCard
    if not isinstance(target, MinionCard) or target not in player.card_hand:
        return False

    # 弃掉目标异象
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  植物学家：弃掉 [{target.name}]")

    # 在手牌中查找另一张同名异象
    same_name = [c for c in player.card_hand
                 if isinstance(c, MinionCard) and c.name == target.name]
    if not same_name:
        print(f"  植物学家：手牌中没有另一张 [{target.name}]")
        return True

    buff_card = same_name[0]
    buff_card.attack *= 2
    buff_card.health *= 2
    buff_card.cost.t += 1
    print(f"  植物学家：[{buff_card.name}] 攻防翻倍（{buff_card.attack}/{buff_card.health}），花费+1T")
    return True


register_card(
    name="植物学家",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：选择并弃一张异象，使你手牌中另一张同名异象攻防翻倍且花费+1T。
    targets_fn=target_hand_minions,
    effect_fn=_zhiwuxuejia_effect,
)

def _pimaoshang_choice(player, board):
    return ["抽2张异象", "获得4T"]


def _pimaoshang_effect(player, target, game, extras=None):
    import random
    from tards.cards import MinionCard

    # 阶段1：随机将一张手牌（非自身）洗入卡组
    remaining = [c for c in player.card_hand if c.name != "皮毛商"]
    if remaining:
        chosen = random.choice(remaining)
        player.card_hand.remove(chosen)
        player.card_deck.append(chosen)
        random.shuffle(player.card_deck)
        print(f"  皮毛商：将 [{chosen.name}] 洗入卡组")

    # 阶段2：抉择
    choice = (extras or [None])[0]
    if choice == "抽2张异象":
        minion_cards = [c for c in player.card_deck if isinstance(c, MinionCard)]
        drawn = 0
        for card in minion_cards[:2]:
            player.card_deck.remove(card)
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(card)
            else:
                player.card_dis.append(card)
                print(f"  皮毛商：手牌已满，{card.name} 被弃置")
            drawn += 1
        print(f"  皮毛商：从卡组中抽出 {drawn} 张异象")
    elif choice == "获得4T":
        player.t_point_change(4)
        print(f"  皮毛商：{player.name} 获得 4T")

    return True


register_card(
    name="皮毛商",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：随机将一张手牌洗入卡组。抉择：抽2张异象或获得4T。
    targets_fn=target_none,
    extra_targeting_stages=[(_pimaoshang_choice, 1, False)],
    effect_fn=_pimaoshang_effect,
)

def _lieren_targets(player, board):
    return player.card_hand[:]


def _lieren_effect(player, target, game, extras=None):
    import copy
    import random
    if target not in player.card_hand:
        return False

    # 弃掉目标
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  猎人：弃掉 [{target.name}]")

    # 复制2张洗入牌库
    for _ in range(2):
        cloned = copy.copy(target)
        player.card_deck.append(cloned)
    random.shuffle(player.card_deck)
    print(f"  猎人：将2张 [{target.name}] 的复制洗入牌库")
    return True


register_card(
    name="猎人",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：选择并弃一张牌，将其2张复制进入牌库。
    targets_fn=_lieren_targets,
    effect_fn=_lieren_effect,
)

def _yugou_effect(player, target, game, extras=None):
    from tards.cards import Minion
    from card_pools.effect_utils import convert_cost_to_t

    if not isinstance(target, Minion):
        return False

    # 检查费用折算不大于3T
    source_card = getattr(target, "source_card", None)
    if source_card and hasattr(source_card, "cost"):
        cost_t = convert_cost_to_t(source_card.cost)
    else:
        cost_t = 999
    if cost_t > 3:
        print(f"  鱼钩：{target.name} 折算费用 {cost_t}T > 3，无法移动")
        return False

    # 找到友方同一列最靠近前排的空位
    col = target.position[1]
    rows = sorted(player.get_friendly_rows(), key=lambda r: abs(r - 2))
    new_pos = None
    for r in rows:
        pos = (r, col)
        if pos not in game.board.minion_place:
            new_pos = pos
            break

    if new_pos is None:
        print(f"  鱼钩：友方第{col}列没有空位，移动失败")
        return False

    # 转移所有权并跨阵营移动
    target.owner = player
    ok = game.board.move_minion(target, new_pos, allow_cross_side=True)
    if ok:
        print(f"  鱼钩：将 [{target.name}] 转移至 {new_pos}")
    else:
        # 所有权回滚
        opponent = game.p2 if player == game.p1 else game.p1
        target.owner = opponent
        print(f"  鱼钩：移动 [{target.name}] 失败")
    return ok


register_card(
    name="鱼钩",
    cost_str="5T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：将一个花费不大于3T的异象移动至友方同一列。
    targets_fn=target_enemy_minions,
    effect_fn=_yugou_effect,
)

register_card(
    name="扇子",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使一个异象具有空袭直到回合结束。抽1张牌。
    targets_fn=target_any_minion,
    effect_fn=_shanzi_strategy,
)

def _bopidao_effect(player, target, game, extras=None):
    from tards.cards import Minion
    from card_pools.effect_utils import (
        destroy_minion, give_temp_keyword_until_turn_end,
    )
    if not isinstance(target, Minion) or not target.is_alive():
        return False

    if target.keywords.get("迅捷", False):
        destroy_minion(target, game)
        print(f"  剥皮刀：{target.name} 具有迅捷，被消灭")
    else:
        give_temp_keyword_until_turn_end(target, "眩晕", 1)
        print(f"  剥皮刀：{target.name} 被眩晕")
    return True


register_card(
    name="剥皮刀",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：眩晕一个异象。若是迅捷异象，改为消灭。
    targets_fn=target_any_minion,
    effect_fn=_bopidao_effect,
)

def _yanping_targets(player, board):
    return list(range(board.SIZE))


def _yanping_effect(player, target, game, extras=None):
    from tards.cards import MinionCard
    if not isinstance(target, int) or not (0 <= target < 5):
        return False

    col = target
    # 永久覆盖该列为高地
    if not hasattr(game, "_terrain_overrides"):
        game._terrain_overrides = {}
    for r in range(5):
        game._terrain_overrides[(r, col)] = "高地"
    print(f"  岩瓶：第 {col} 列（{game.board.COL_NAMES[col]}）永久视为高地")

    # 抽一张高地异象
    for i, card in enumerate(player.card_deck):
        if isinstance(card, MinionCard) and card.keywords.get("高地", False):
            player.card_deck.pop(i)
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(card)
            else:
                player.card_dis.append(card)
                print(f"  岩瓶：手牌已满，{card.name} 被弃置")
            print(f"  岩瓶：抽出高地异象 [{card.name}]")
            return True

    print("  岩瓶：卡组中没有高地异象")
    return True


register_card(
    name="岩瓶",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：使一列陆地也算作是高地。抽一张高地异象。
    targets_fn=_yanping_targets,
    effect_fn=_yanping_effect,
)

def _lanyue_effect(player, target, game, extras=None):
    from card_pools.effect_utils import on
    from tards.constants import EVENT_PHASE_START, EVENT_PHASE_END

    player._lan_yue_pending = True

    def on_action_start(event_data):
        if event_data.get("phase") != getattr(game, "PHASE_ACTION", "action"):
            return
        if not getattr(player, "_lan_yue_pending", False):
            return
        player._lan_yue_pending = False

        affected = 0
        for m in game.board.minion_place.values():
            if m.owner == player and m.is_alive():
                m._sacrifice_remaining += 1
                m.gain_keyword("献祭", 1, permanent=False)
                m._lan_yue_affected = True
                affected += 1
        if affected:
            print(f"  蓝月：{affected} 个友方异象献祭等级+1")

    def on_resolve_end(event_data):
        if event_data.get("phase") != getattr(game, "PHASE_RESOLVE", "resolve"):
            return
        cleaned = 0
        for m in list(game.board.minion_place.values()):
            if getattr(m, "_lan_yue_affected", False):
                m._lan_yue_affected = False

                base = m.base_keywords.get("献祭", 0)
                if base is True:
                    base = 1
                elif not isinstance(base, int):
                    base = 0

                if m._sacrifice_remaining > base:
                    m._sacrifice_remaining -= 1
                    if base >= 1 and m._sacrifice_remaining < 1:
                        m._sacrifice_remaining = 1
                cleaned += 1
        if cleaned:
            print(f"  蓝月效果结束（{cleaned} 个异象）")

    on(EVENT_PHASE_START, on_action_start, game)
    on(EVENT_PHASE_END, on_resolve_end, game)
    return True


register_card(
    name="蓝月",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：下个出牌阶段，你的所有异象献祭等级+1。
    targets_fn=target_none,
    effect_fn=_lanyue_effect,
)

def _zhadan_yao_effect(player, target, game, extras=None):
    """炸弹夫人的遥控器：使友方异象获得传染亡语。"""
    from tards.cards import Minion
    from card_pools.effect_utils import add_deathrattle, deal_damage_to_minion
    import random

    if not isinstance(target, Minion) or not target.is_alive():
        print("  炸弹夫人：目标不合法")
        return False

    def _make_deathrattle():
        def _deathrattle(minion, owner, board):
            g = getattr(board, "game_ref", None)
            friends = [m for m in board.minion_place.values() if m.owner == owner and m.is_alive() and m != minion]
            if not friends:
                return
            victim = random.choice(friends)
            deal_damage_to_minion(victim, 2, game=g)
            print(f"  炸弹夫人亡语：{victim.name} 受到2点伤害")
            if victim.is_alive():
                add_deathrattle(victim, _deathrattle)
                print(f"  炸弹夫人亡语：{victim.name} 获得传染亡语")
        return _deathrattle

    add_deathrattle(target, _make_deathrattle())
    print(f"  炸弹夫人：{target.name} 获得传染亡语")
    return True


register_card(
    name="炸弹夫人的遥控器",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：使一个异象获得亡语：随机对一个友方异象造成2点伤害，使其获得此亡语。
    targets_fn=target_friendly_minions,
    effect_fn=_zhadan_yao_effect,
)

def _xiangji_effect(player, target, game, extras=None):
    from tards.cards import Minion, MinionCard
    if not isinstance(target, Minion) or not target.is_alive():
        return False

    # 移除场上异象（不触发亡语）
    game.board.remove_minion(target.position)

    # 复制 source_card，所有权转移
    sc = target.source_card
    new_card = MinionCard(
        name=sc.name,
        owner=player,
        cost=sc.cost.copy() if hasattr(sc.cost, "copy") else sc.cost,
        targets=sc.targets,
        attack=sc.attack,
        health=sc.health,
        special=getattr(sc, "special", None),
        keywords=dict(sc.keywords) if hasattr(sc, "keywords") else {},
    )
    # 复制额外属性
    for attr in ("pack", "asset_id", "asset_back_id", "evolve_to",
                 "statue_top", "statue_bottom", "statue_pair",
                 "targets_count", "targets_repeat"):
        if hasattr(sc, attr):
            setattr(new_card, attr, getattr(sc, attr))
    if hasattr(sc, "tags"):
        new_card.tags = list(sc.tags)
    if hasattr(sc, "hidden_keywords"):
        new_card.hidden_keywords = dict(sc.hidden_keywords)
    if hasattr(sc, "extra_targeting_stages"):
        new_card.extra_targeting_stages = list(sc.extra_targeting_stages)

    if len(player.card_hand) < player.card_hand_max:
        player.card_hand.append(new_card)
        print(f"  相机：将 [{target.name}] 移入 {player.name} 手牌")
    else:
        player.card_dis.append(new_card)
        print(f"  相机：手牌已满，{target.name} 被弃置")
    return True


register_card(
    name="相机",
    cost_str="7T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：将场上的一个异象移动至你的手牌中。
    targets_fn=target_any_minion,
    effect_fn=_xiangji_effect,
)

def _shalou_cost_modifier(card, cost):
    owner = getattr(card, "owner", None)
    if owner and len(owner.card_hand) <= 3:
        cost.t = max(0, cost.t - 2)


def _shalou_effect(player, target, game, extras=None):
    import random
    opponent = game.p2 if player == game.p1 else game.p2

    # 随机将对方一张手牌放置至其卡组顶
    if opponent.card_hand:
        chosen = random.choice(opponent.card_hand)
        opponent.card_hand.remove(chosen)
        opponent.card_deck.insert(0, chosen)
        print(f"  沙漏：将 {opponent.name} 的 [{chosen.name}] 放置至其卡组顶")
    else:
        print(f"  沙漏：{opponent.name} 手牌为空")

    # 自己抽1张牌
    player.draw_card(1, game=game)
    return True


register_card(
    name="沙漏",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：手牌数不大于3时，花费-2T。随机将对方一张手牌放置至其卡组顶，你抽1张牌。
    targets_fn=target_none,
    cost_modifier=_shalou_cost_modifier,
    effect_fn=_shalou_effect,
)

def _xueyue_effect(player, target, game, extras=None):
    affected = 0
    for m in game.board.minion_place.values():
        if m.owner == player and m.is_alive():
            m.temp_attack_bonus += 1
            m.temp_keywords["坚韧"] = m.temp_keywords.get("坚韧", 0) + 1
            m.recalculate()
            affected += 1
    if affected:
        print(f"  血月：{affected} 个友方异象+1攻击力，获得坚韧1")
    return True


register_card(
    name="血月",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：你的所有异象具有+1攻击力和坚韧1，直到回合结束。
    targets_fn=target_none,
    effect_fn=_xueyue_effect,
)

def _jiaoshui_effect(player, target, game, extras=None):
    from tards.cards import Minion
    from card_pools.effect_utils import on
    from tards.constants import EVENT_BEFORE_DAMAGE, EVENT_AFTER_DAMAGE

    if not isinstance(target, Minion) or not target.is_alive():
        return False

    def protect(event_data):
        if event_data.get("target") is not target:
            return
        damage = event_data.get("damage", 0)
        if damage <= 0:
            return

        # 预判是否致命（考虑坚韧）
        tough = target.keywords.get("坚韧", 0)
        if target.keywords.get("脆弱", False) and tough == 0:
            tough = -1
        actual = max(0, damage - tough) if isinstance(tough, int) else damage
        if target.current_health > actual:
            return

        # +0/1：获得1HP（上限+当前）
        target.gain_health_bonus(1, permanent=True)
        target.current_health += 1
        target._jiaoshui_protected = True
        print(f"  胶水：{target.name} 受到致命伤害，+0/1")

    def check_survival(event_data):
        if event_data.get("target") is not target:
            return
        if not getattr(target, "_jiaoshui_protected", False):
            return
        target._jiaoshui_protected = False
        if target.is_alive():
            target.gain_attack(1, permanent=True)
            target.gain_health_bonus(1, permanent=True)
            target.current_health += 1
            print(f"  胶水：{target.name} 因此存活，+1/1")

    on(EVENT_BEFORE_DAMAGE, protect, game, minion=target)
    on(EVENT_AFTER_DAMAGE, check_survival, game, minion=target)
    print(f"  胶水：{target.name} 获得致命伤害保护")
    return True


register_card(
    name="胶水",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使一个异象获得：在受到致命伤害前，+0/1。若因此存活，+1/1。
    targets_fn=target_any_minion,
    effect_fn=_jiaoshui_effect,
)

def _shizhong_targets(player, board):
    from tards.cards import MinionCard
    from card_pools.effect_utils import convert_cost_to_t
    return [c for c in player.card_hand
            if isinstance(c, MinionCard) and convert_cost_to_t(c.cost) <= 7]


def _shizhong_effect(player, target, game, extras=None):
    from tards.cards import MinionCard, Minion
    from card_pools.effect_utils import on, empty_positions
    from tards.constants import EVENT_PHASE_START
    import random

    if not isinstance(target, MinionCard) or target not in player.card_hand:
        return False

    # 弃掉目标
    player.card_hand.remove(target)
    player.card_dis.append(target)

    target_turn = game.current_turn + 3
    if not hasattr(player, "_shizhong_delayed"):
        player._shizhong_delayed = []
    player._shizhong_delayed.append({"turn": target_turn, "card": target})
    print(f"  时钟：弃掉 [{target.name}]，将在第 {target_turn} 回合抽牌阶段加入战场")

    def on_draw_phase(event_data):
        if event_data.get("phase") != getattr(game, "PHASE_DRAW", "draw"):
            return
        delayed = getattr(player, "_shizhong_delayed", [])
        to_deploy = [d for d in delayed if d["turn"] == game.current_turn]
        if not to_deploy:
            return

        for entry in to_deploy:
            card = entry["card"]
            empties = empty_positions(player, game.board)
            valid = [pos for pos in empties if game.board.is_valid_deploy(pos, player, card)]
            if not valid:
                print(f"  时钟：无合法空位部署 {card.name}")
                continue

            pos = random.choice(valid)
            minion = Minion(
                name=card.name,
                owner=player,
                position=pos,
                attack=card.attack,
                health=card.health,
                source_card=card,
                board=game.board,
                keywords=dict(card.keywords) if hasattr(card, "keywords") else {},
                on_turn_start=getattr(card, "on_turn_start", None),
                on_turn_end=getattr(card, "on_turn_end", None),
                on_phase_start=getattr(card, "on_phase_start", None),
                on_phase_end=getattr(card, "on_phase_end", None),
            )
            game.board.place_minion(minion, pos)
            print(f"  时钟：{card.name} 加入战场 {pos}")

        player._shizhong_delayed = [d for d in delayed if d["turn"] != game.current_turn]

    if not getattr(player, "_shizhong_listener_registered", False):
        on(EVENT_PHASE_START, on_draw_phase, game)
        player._shizhong_listener_registered = True

    return True


register_card(
    name="时钟",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：弃掉一个花费不大于7T的异象，在3回合后的抽牌阶段将其加入战场。
    targets_fn=_shizhong_targets,
    effect_fn=_shizhong_effect,
)

def _yinghuo_effect(player, target, game, extras=None):
    from tards.cards import MinionCard
    if not isinstance(target, MinionCard) or target not in player.card_hand:
        return False

    # +2/3（永久修改卡牌面板）
    target.attack += 2
    target.health += 3

    # 添加亡语：对方抽一张牌
    def deathrattle(minion, owner, board):
        opponent = game.p1 if owner == game.p2 else game.p2
        opponent.draw_card(1, game=game)
        print(f"  {minion.name} 亡语：{opponent.name} 抽1张牌")

    target.keywords["亡语"] = deathrattle
    print(f"  营火：{target.name} 获得+2/3和亡语（对方抽牌）")
    return True


register_card(
    name="营火",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：使手牌中一个异象获得 +2/3 和亡语：对方抽一张牌。
    targets_fn=target_hand_minions,
    effect_fn=_yinghuo_effect,
)

def _bingkuai_effect(player, target, game, extras=None):
    from tards.cards import Minion
    from card_pools.effect_utils import on
    from tards.constants import EVENT_PHASE_END

    if not isinstance(target, Minion) or not target.is_alive() or target.owner != player:
        return False

    # +0/4 永久
    target.base_max_health_bonus += 4
    target.current_health += 4
    target.recalculate()

    # 冰冻2回合
    target.base_keywords["冰冻"] = 2

    # 坚韧I（冰冻期间生效）
    target.base_keywords["坚韧"] = 1
    target.recalculate()

    def on_resolve_end(event_data):
        if event_data.get("phase") != getattr(game, "PHASE_RESOLVE", "resolve"):
            return
        frozen = target.keywords.get("冰冻", 0)
        if not isinstance(frozen, int) or frozen <= 0:
            # 冰冻已解除，移除坚韧
            target.base_keywords.pop("坚韧", None)
            target.perm_keywords.pop("坚韧", None)
            target.temp_keywords.pop("坚韧", None)
            target.recalculate()
            print(f"  冰块：{target.name} 冰冻解除，坚韧消失")

    on(EVENT_PHASE_END, on_resolve_end, game, minion=target)
    print(f"  冰块：{target.name} +0/4，冰冻2回合，坚韧I")
    return True


register_card(
    name="冰块",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使一个友方异象获得 +0/4 并冰冻2回合，期间其拥有坚韧I。
    targets_fn=target_friendly_minions,
    effect_fn=_bingkuai_effect,
)

def _mudiaoshi_effect(player, target, game, extras=None):
    # 开发一张座首
    top_defs = [c for c in DEFAULT_REGISTRY.all_cards() if getattr(c, "statue_top", False)]
    if top_defs:
        game.develop_card(player, top_defs, count=min(3, len(top_defs)))
        print("  木雕师：开发一张座首")
    else:
        print("  木雕师：无可用座首")

    # 开发一张底座
    bottom_defs = [c for c in DEFAULT_REGISTRY.all_cards() if getattr(c, "statue_bottom", False)]
    if bottom_defs:
        game.develop_card(player, bottom_defs, count=min(3, len(bottom_defs)))
        print("  木雕师：开发一张底座")
    else:
        print("  木雕师：无可用底座")

    return True


register_card(
    name="木雕师",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：开发一张座首和一张底座。
    targets_fn=target_none,
    effect_fn=_mudiaoshi_effect,
)

def _muqi_targets(player, board):
    return [m for m in board.minion_place.values()
            if m.owner == player and m.is_alive()
            and (getattr(m, "statue_top", False) or getattr(m, "statue_bottom", False))]


def _muqi_effect(player, target, game, extras=None):
    if not target.is_alive() or target.owner != player:
        return False
    if not (getattr(target, "statue_top", False) or getattr(target, "statue_bottom", False)):
        return False

    target.gain_health_bonus(6, permanent=True)
    target.current_health += 6
    target.base_keywords["绝缘"] = True
    target.recalculate()
    print(f"  木漆：{target.name} +6HP，获得绝缘")
    return True


register_card(
    name="木漆",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：使一个木雕组件获得+6HP和绝缘。
    targets_fn=_muqi_targets,
    effect_fn=_muqi_effect,
)

def _make_targets(player, board):
    from tards.cards import Minion
    minions = [m for m in board.minion_place.values() if isinstance(m, Minion)]
    opponent = None
    if board.game_ref:
        opponent = board.game_ref.p2 if player == board.game_ref.p1 else board.game_ref.p1
    return minions + ([opponent] if opponent else [])


def _make_effect(player, target, game, extras=None):
    def filter_fn(t, damage, source):
        return t is target

    def replace_fn(damage):
        return 0

    game.add_damage_replacement(filter_fn, replace_fn, once=True, reason="玛珂")

    if isinstance(target, Minion):
        player.draw_card(1, game=game)
        print(f"  玛珂：{target.name} 免疫下次伤害，{player.name} 抽1张牌")
    else:
        print(f"  玛珂：{getattr(target, 'name', str(target))} 免疫下次伤害")
    return True


register_card(
    name="玛珂",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：使一个目标免疫下次伤害。若指向异象，抽1张牌。
    targets_fn=_make_targets,
    effect_fn=_make_effect,
)

def _hanji_effect(player, target, game, extras=None):
    """旱季：对所有陆地异象造成3点伤害，然后使所有陆地异象+1/+2。失去1个T槽。"""
    board = game.board
    from card_pools.effect_utils import deal_damage_to_minion

    def _get_land_minions():
        seen = set()
        result = []
        for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
            if m.is_alive() and m.position[1] != 4 and id(m) not in seen:
                result.append(m)
                seen.add(id(m))
        return result

    land_minions = _get_land_minions()
    for m in land_minions:
        deal_damage_to_minion(m, 3, game=game)
        print(f"  旱季：对 {m.name} 造成3点伤害")

    for m in _get_land_minions():
        m.gain_attack(1, permanent=True)
        m.gain_health_bonus(2, permanent=True)
        print(f"  旱季：{m.name} +1/+2")

    player.t_point_max_change(-1)
    print(f"  旱季：{player.name} 失去1个T槽")
    return True


def _shanhong_targets(player, board):
    """山洪：选择一列陆地（0-3）。"""
    return [0, 1, 2, 3]


def _shanhong_effect(player, target, game, extras=None):
    """山洪：使一列陆地算作水路直到下回合结束。失去1个T槽。"""
    if not isinstance(target, int) or not (0 <= target <= 3):
        print("  山洪：目标列不合法")
        return False

    col = target
    from card_pools.effect_utils import register_terrain_enforcement
    register_terrain_enforcement(game, col, "水路", game.current_turn + 1)
    print(f"  山洪：第 {col} 列（{game.board.COL_NAMES[col]}）被视为水路，直到下回合结束")

    player.t_point_max_change(-1)
    print(f"  山洪：{player.name} 失去1个T槽")
    return True


def _shuiyi_effect(player, target, game, extras=None):
    """水疫：若水路（列4）有敌方异象，对所有敌方异象造成1点伤害；若有异象被消灭，重复。"""
    opponent = game.p2 if player == game.p1 else game.p1
    board = game.board
    from card_pools.effect_utils import deal_damage_to_minion

    iteration = 0
    while True:
        iteration += 1
        # 检查水路是否有敌方异象
        water_enemies = board.get_enemy_minions_in_column(4, player)
        if not water_enemies:
            print(f"  水疫（第{iteration}轮）：水路无敌方异象，效果结束")
            break

        # 收集所有当前敌方异象（包含新召唤的）
        all_enemies = []
        seen = set()
        for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
            if m.is_alive() and m.owner == opponent and id(m) not in seen:
                all_enemies.append(m)
                seen.add(id(m))

        if not all_enemies:
            print(f"  水疫（第{iteration}轮）：无敌方异象可伤害")
            break

        any_killed = False
        for m in all_enemies:
            before_alive = m.is_alive()
            deal_damage_to_minion(m, 1, game=game)
            if before_alive and not m.is_alive():
                any_killed = True

        print(f"  水疫（第{iteration}轮）：对 {len(all_enemies)} 个敌方异象造成1点伤害")

        if not any_killed:
            print(f"  水疫（第{iteration}轮）：无异象被消灭，效果结束")
            break

    return True


def _shachen_effect(player, target, game, extras=None):
    """沙尘：眩晕一个敌方异象。若本回合对方先手，结束双方出牌阶段。"""
    from card_pools.effect_utils import give_temp_keyword_until_turn_end
    from tards.cards import Minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  沙尘：目标不合法")
        return False

    give_temp_keyword_until_turn_end(target, "眩晕", 1)
    print(f"  沙尘：{target.name} 被眩晕")

    # 判断本回合对方是否先手
    first = game.p1 if game.current_turn % 2 == 1 else game.p2
    if first != player:
        # 对方先手，结束双方出牌阶段
        game.p1.braked = True
        game.p2.braked = True
        print(f"  沙尘：本回合对方先手，双方出牌阶段结束")

    return True


def _kuangfeng_effect(player, target, game, extras=None):
    """狂风：对方无法部署异象，直到下一个出牌阶段结束。"""
    opponent = game.p2 if player == game.p1 else game.p1

    def _restriction_fn(p, card):
        if p == opponent:
            return False
        return True

    game._global_deploy_restrictions.append(_restriction_fn)
    print(f"  狂风：{opponent.name} 无法部署异象，直到下回合结束")

    # 下回合结束时移除限制
    def _cleanup():
        if _restriction_fn in game._global_deploy_restrictions:
            game._global_deploy_restrictions.remove(_restriction_fn)
            print(f"  狂风：{opponent.name} 的部署限制已解除")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": game.current_turn + 1,
        "fn": _cleanup,
    })
    return True


def _gaozhi_cost_modifier(card, cost):
    player = getattr(card, "owner", None)
    if not player:
        return
    game = getattr(getattr(player, "board_ref", None), "game_ref", None)
    if not game:
        return
    deployed = getattr(game, "_deployed_this_turn", {})
    count = len(deployed.get(player, []))
    if count > 0:
        cost.t = max(0, cost.t - count)
        print(f"  稿纸费用：本回合部署 {count} 个异象，费用-{count}T")


def _gaozhi_effect(player, target, game, extras=None):
    opponent = game.p2 if player == game.p1 else game.p1
    player.t_point_max += 1
    opponent.t_point_max_change(-1)
    print(f"  稿纸：{player.name} 获得1T槽，{opponent.name} 失去1T槽")
    return True


def _zhouyu_effect(player, target, game, extras=None):
    """骤雨：将1个异象返回其所有者手牌。对手下回合无法抽牌。"""
    from tards.cards import Minion
    from card_pools.effect_utils import return_minion_to_hand

    if not isinstance(target, Minion) or not target.is_alive():
        print("  骤雨：目标不合法")
        return False

    return_minion_to_hand(target, game)
    print(f"  骤雨：{target.name} 返回其所有者手牌")

    opponent = game.p2 if player == game.p1 else game.p1
    opponent._skip_next_draw = True
    print(f"  骤雨：{opponent.name} 下回合无法抽牌")
    return True


register_card(
    name="稿纸",
    cost_str="5T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：本回合你每部署1个异象，花费-1T。你获得1个T槽，对方失去1个T槽。
    targets_fn=target_none,
    cost_modifier=_gaozhi_cost_modifier,
    effect_fn=_gaozhi_effect,
)

register_card(
    name="金羊皮",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：开发一张冥刻金卡异象。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: g.develop_card(p, [c for c in DEFAULT_REGISTRY.all_cards() if c.pack == Pack.UNDERWORLD and c.rarity == Rarity.GOLD and c.card_type == CardType.MINION]),
)

def _fansheng_effect(player, target, game, extras=None):
    """繁盛：弃掉所有手牌，获得'抽牌阶段多抽1张'。"""
    from card_pools.effect_utils import on
    from tards.constants import EVENT_PHASE_START

    # 弃掉所有手牌
    discarded = list(player.card_hand)
    player.card_hand.clear()
    player.card_dis.extend(discarded)
    if discarded:
        names = ", ".join([c.name for c in discarded])
        print(f"  繁盛：{player.name} 弃掉 {len(discarded)} 张手牌（{names}）")
    else:
        print(f"  繁盛：{player.name} 手牌为空")

    # 注册抽牌阶段监听器
    def _extra_draw(event_data):
        if event_data.get("phase") != game.PHASE_DRAW:
            return
        # 只在玩家正常的抽牌时额外抽
        draw_player = event_data.get("player")
        if draw_player and draw_player != player:
            return
        player.draw_card(1, game=game)
        print(f"  繁盛：{player.name} 额外抽1张牌")

    on(EVENT_PHASE_START, _extra_draw, game)
    print(f"  繁盛：{player.name} 获得'抽牌阶段多抽1张'")
    return True


register_card(
    name="繁盛",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=2,
    # 效果描述：弃掉所有手牌，你获得：“抽牌阶段：你多抽1张牌。”
    targets_fn=target_none,
    effect_fn=_fansheng_effect,
)

register_card(
    name="旱季",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对所有陆地异象造成3点伤害，然后使所有陆地异象+1/2。你失去1个T槽。
    targets_fn=target_none,
    effect_fn=_hanji_effect,
)

register_card(
    name="山洪",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：回合结束时，使一列陆地算作水路直到下回合结束。你失去1个T槽。
    targets_fn=_shanhong_targets,
    effect_fn=_shanhong_effect,
)

register_card(
    name="水疫",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：若水路有敌方异象，对所有敌方异象造成1点伤害，若有异象被消灭，重复此 流程。
    targets_fn=target_none,
    effect_fn=_shuiyi_effect,
)

register_card(
    name="沙尘",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：眩晕一个敌方异象。若本回合对方先手，结束双方出牌阶段。
    targets_fn=target_enemy_minions,
    effect_fn=_shachen_effect,
)

register_card(
    name="狂风",
    cost_str="6T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：对方无法部署异象，直到下一个出牌阶段结束。
    targets_fn=target_none,
    effect_fn=_kuangfeng_effect,
)

register_card(
    name="骤雨",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：将1个异象返回其所有者手牌。对手下回合无法抽牌。
    targets_fn=target_any_minion,
    effect_fn=_zhouyu_effect,
)

register_card(
    name="屠刀",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：将2张“松鼠”加入手牌。本回合，你每献祭一个异象，抽一张牌。
    targets_fn=target_none,
    effect_fn=_tudao_effect,
)

def _tudao_effect(player, target, game, extras=None):
    """屠刀：将2张'松鼠'加入手牌。本回合，你每献祭一个异象，抽一张牌。"""
    from tards.constants import EVENT_SACRIFICE

    # 加入2张松鼠
    squirrel_count = 0
    for _ in range(2):
        if player.squirrel_deck:
            card = player.squirrel_deck.pop()
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(card)
                squirrel_count += 1
            else:
                player.card_dis.append(card)
                print(f"  屠刀：手牌已满，松鼠被弃置")
        else:
            # squirrel_deck 空了，从 registry 创建
            squirrel_def = DEFAULT_REGISTRY.get("松鼠")
            if squirrel_def:
                card = squirrel_def.to_game_card(player)
                if len(player.card_hand) < player.card_hand_max:
                    player.card_hand.append(card)
                    squirrel_count += 1
                else:
                    player.card_dis.append(card)
                    print(f"  屠刀：手牌已满，松鼠被弃置")
    print(f"  屠刀：{player.name} 将 {squirrel_count} 张松鼠加入手牌")

    # 注册献祭监听器
    def on_sacrifice(event_data):
        if event_data.get("player") == player:
            player.draw_card(1, game=game)
            print(f"  屠刀：{player.name} 献祭抽1张牌")

    owner_id = game.event_bus.register(EVENT_SACRIFICE, on_sacrifice)

    # 本回合结束时注销
    def cleanup():
        game.event_bus.unregister_by_owner(owner_id)
        print(f"  屠刀：献祭抽牌效果结束")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": game.current_turn,
        "fn": cleanup,
    })

    return True


def _zhenban_targets(player, board):
    """砧板：选择手牌中的一张牌。"""
    return player.card_hand


def _zhenban_effect(player, target, game, extras=None):
    """砧板：弃一张牌，抽一张花费更高的牌。若弃牌献祭等级×丰饶等级≥2，获得2B。"""
    if target not in player.card_hand:
        print("  砧板：目标不在手牌中")
        return False

    # 弃掉选中的牌
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  砧板：{player.name} 弃掉 [{target.name}]")

    # 计算弃牌总费用
    def _cost_total(cost):
        return cost.t + cost.c + cost.b + cost.s + cost.ct + sum(cost.minerals.values())

    discarded_cost = _cost_total(target.cost)

    # 从牌库顶找第一张费用更高的牌
    drawn = None
    for i, card in enumerate(player.card_deck):
        if _cost_total(card.cost) > discarded_cost:
            drawn = player.card_deck.pop(i)
            break

    if drawn:
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(drawn)
            print(f"  砧板：抽出更高费牌 [{drawn.name}]")
        else:
            player.card_dis.append(drawn)
            print(f"  砧板：手牌已满，[{drawn.name}] 被弃置")
    else:
        print("  砧板：牌库中没有更高费的牌")

    # 计算献祭等级 × 丰饶等级
    sacrifice_kw = getattr(target, "keywords", {}).get("献祭", False)
    if sacrifice_kw is True:
        sacrifice_level = 1
    elif isinstance(sacrifice_kw, int):
        sacrifice_level = sacrifice_kw
    else:
        sacrifice_level = 0

    feng_rang_kw = getattr(target, "keywords", {}).get("丰饶", False)
    if feng_rang_kw is True:
        feng_rang_level = 1
    elif isinstance(feng_rang_kw, int):
        feng_rang_level = feng_rang_kw
    else:
        feng_rang_level = 0

    if sacrifice_level * feng_rang_level >= 2:
        player.b_point += 2
        print(f"  砧板：{player.name} 获得 2B（献祭{sacrifice_level}×丰饶{feng_rang_level}={sacrifice_level * feng_rang_level}）")

    return True


register_card(
    name="砧板",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择并弃一张牌，抽一张花费更高的牌。若弃掉的牌献祭等级与丰饶等级之积 不小于2，你获得2B。
    targets_fn=_zhenban_targets,
    effect_fn=_zhenban_effect,
)

def _haichen_targets(player, board):
    """还尘：选择任意一个受伤异象。"""
    result = []
    seen = set()
    for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
        if m.is_alive() and m.current_health < m.max_health and id(m) not in seen:
            result.append(m)
            seen.add(id(m))
    return result


def _haichen_effect(player, target, game, extras=None):
    """还尘：消灭一个受伤异象。若是友方异象，抽三张牌。"""
    from tards.cards import Minion
    from card_pools.effect_utils import destroy_minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  还尘：目标不合法")
        return False

    if target.current_health >= target.max_health:
        print("  还尘：目标未受伤")
        return False

    destroy_minion(target, game)
    print(f"  还尘：消灭受伤异象 {target.name}")

    if target.owner == player:
        player.draw_card(3, game=game)
        print(f"  还尘：{player.name} 抽3张牌（友方异象）")

    return True


register_card(
    name="还尘",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：消灭一个受伤异象。若是友方异象，抽三张牌。
    targets_fn=_haichen_targets,
    effect_fn=_haichen_effect,
)

def _jidai_effect(player, target, game, extras=None):
    """继代：使一个异象获得亡语，将其-1/1的复制加入你的手牌。"""
    from tards.cards import Minion
    from card_pools.effect_utils import add_deathrattle

    if not isinstance(target, Minion) or not target.is_alive():
        print("  继代：目标不合法")
        return False

    def _deathrattle(minion, owner, board):
        from tards.cards import MinionCard
        sc = minion.source_card
        new_card = MinionCard(
            name=sc.name,
            owner=owner,
            cost=sc.cost.copy(),
            targets=sc.targets,
            attack=max(0, sc.attack - 1),
            health=max(1, sc.health - 1),
            special=getattr(sc, "special", None),
            keywords=dict(sc.keywords) if hasattr(sc, "keywords") else {},
        )
        if len(owner.card_hand) < owner.card_hand_max:
            owner.card_hand.append(new_card)
            print(f"  继代亡语：{new_card.name}({new_card.attack}/{new_card.health}) 加入 {owner.name} 手牌")
        else:
            owner.card_dis.append(new_card)
            print(f"  继代亡语：手牌已满，{new_card.name} 被弃置")

    add_deathrattle(target, _deathrattle)
    print(f"  继代：{target.name} 获得亡语")
    return True


register_card(
    name="继代",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使一个异象获得亡语：将其-1/1的复制加入你的手牌。
    targets_fn=target_any_minion,
    effect_fn=_jidai_effect,
)

def _yehuo_targets(player, board):
    """野火：选择手牌中的一张牌弃掉。"""
    return player.card_hand


def _yehuo_minion_choice(player, board):
    """野火：选择场上一个异象返回其所有者牌库顶。"""
    result = []
    seen = set()
    for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
        if m.is_alive() and id(m) not in seen:
            result.append(m)
            seen.add(id(m))
    return result


def _yehuo_effect(player, target, game, extras=None):
    """野火：弃1张牌，将1个异象返回其所有者牌库顶，眩晕周围异象。"""
    from card_pools.effect_utils import get_adjacent_positions, give_temp_keyword_until_turn_end
    from card_pools.effect_utils import place_at_deck_top
    from tards.cards import Minion

    # 阶段1：弃牌
    if target not in player.card_hand:
        print("  野火：弃牌目标不在手牌中")
        return False
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  野火：{player.name} 弃掉 [{target.name}]")

    # 阶段2：选异象
    minion_target = (extras or [None])[0]
    if not isinstance(minion_target, Minion) or not minion_target.is_alive():
        print("  野火：异象目标不合法")
        return False

    owner = minion_target.owner
    pos = minion_target.position
    sc = minion_target.source_card

    # 从场上移除
    game.board.remove_minion(pos)
    print(f"  野火：{minion_target.name} 从场上移除")

    # 将 source_card 放入所有者牌库顶
    place_at_deck_top(owner, [sc])
    print(f"  野火：{sc.name} 返回 {owner.name} 牌库顶")

    # 眩晕周围异象
    adj_positions = get_adjacent_positions(pos, game.board)
    for adj_pos in adj_positions:
        m = game.board.get_minion_at(adj_pos)
        if m and m.is_alive():
            give_temp_keyword_until_turn_end(m, "眩晕", 1)
            print(f"  野火：{m.name} 被眩晕")

    return True


register_card(
    name="野火",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择并弃1张牌，将一个异象返回其所有者牌堆顶。眩晕周围异象。
    targets_fn=_yehuo_targets,
    extra_targeting_stages=[(_yehuo_minion_choice, 1, False)],
    effect_fn=_yehuo_effect,
)

def _lunhui_targets(player, board):
    """轮回：选择手牌中的一张牌弃掉。"""
    return player.card_hand


def _lunhui_target_choice(player, board):
    """轮回：若弃掉回响，选择一个目标（敌方异象或敌方玩家）造成4点伤害。"""
    opponent = player.board_ref.game_ref.p2 if player == player.board_ref.game_ref.p1 else player.board_ref.game_ref.p1
    targets = []
    for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
        if m.is_alive() and m.owner == opponent:
            targets.append(m)
    targets.append(opponent)
    return targets


def _lunhui_effect(player, target, game, extras=None):
    """轮回：弃1张牌，抽1张。若弃掉回响，对目标造成4点伤害。"""
    from card_pools.effect_utils import deal_damage_to_minion, deal_damage_to_player
    from tards.cards import Minion

    if target not in player.card_hand:
        print("  轮回：目标不在手牌中")
        return False

    # 弃牌
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  轮回：{player.name} 弃掉 [{target.name}]")

    # 抽1张
    player.draw_card(1, game=game)
    print(f"  轮回：{player.name} 抽1张牌")

    # 若弃掉回响，造成4点伤害
    if target.keywords.get("回响", False):
        dmg_target = (extras or [None])[0]
        if isinstance(dmg_target, Minion) and dmg_target.is_alive():
            deal_damage_to_minion(dmg_target, 4, game=game)
            print(f"  轮回：{dmg_target.name} 受到4点伤害")
        elif dmg_target is player or dmg_target is (game.p2 if player == game.p1 else game.p1):
            deal_damage_to_player(dmg_target, 4, game=game)
            print(f"  轮回：{dmg_target.name} 受到4点伤害")
        else:
            print("  轮回：伤害目标不合法")

    return True


register_card(
    name="轮回",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择并弃1张牌，抽1张牌。若弃掉回响，对一个目标造成4点伤害。
    targets_fn=_lunhui_targets,
    extra_targeting_stages=[(_lunhui_target_choice, 1, False)],
    effect_fn=_lunhui_effect,
)

def _gengti_targets(player, board):
    """更替：选择手牌中的一个回响异象。"""
    from tards.cards import MinionCard
    result = []
    for card in player.card_hand:
        if isinstance(card, MinionCard) and (card.keywords.get("回响", False) or getattr(card, "echo_level", 0) > 0):
            result.append(card)
    return result


def _gengti_effect(player, target, game, extras=None):
    """更替：使手牌中的1个回响异象回响等级+1。"""
    from tards.cards import MinionCard

    if not isinstance(target, MinionCard) or target not in player.card_hand:
        print("  更替：目标不合法")
        return False

    if not (target.keywords.get("回响", False) or getattr(target, "echo_level", 0) > 0):
        print("  更替：目标不是回响异象")
        return False

    # 增加回响等级
    target.echo_level = getattr(target, "echo_level", 0) + 1
    # 同步更新关键词
    if "回响" in target.keywords:
        current = target.keywords["回响"]
        if isinstance(current, int):
            target.keywords["回响"] = current + 1
        elif current is True:
            target.keywords["回响"] = 2
    else:
        target.keywords["回响"] = target.echo_level

    print(f"  更替：{target.name} 回响等级+1（当前 {target.echo_level}）")
    return True


register_card(
    name="更替",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使手牌中的1个回响异象回响等级+1。
    targets_fn=_gengti_targets,
    effect_fn=_gengti_effect,
)

def _poxiao_effect(player, target, game, extras=None):
    """破晓：抽2张牌。若剩余T点≤1，获得两倍于本对局失去T槽数的T点。"""
    player.draw_card(2, game=game)
    print(f"  破晓：{player.name} 抽2张牌")

    if player.t_point <= 1:
        total_lost = sum(
            entry.get("amount", 0)
            for entry in getattr(game, "_state_log", [])
            if entry.get("event") == "t_max_lost" and entry.get("player") == player
        )
        gain = total_lost * 2
        if gain > 0:
            player.t_point_change(gain)
            print(f"  破晓：{player.name} 剩余T点≤1，获得 {gain}T（失去过{total_lost}个T槽）")
        else:
            print(f"  破晓：{player.name} 剩余T点≤1，但未失去过T槽")

    return True


register_card(
    name="破晓",
    cost_str="5T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：抽2张牌。然后若你剩余T点不大于1，获得两倍于你本对局失去过T槽数目的T点。
    targets_fn=target_none,
    effect_fn=_poxiao_effect,
)

def _liulinfengsheng_targets(player, board):
    """柳林风声：选择手牌中的一个异象弃掉。"""
    from tards.cards import MinionCard
    return [c for c in player.card_hand if isinstance(c, MinionCard)]


def _liulinfengsheng_effect(player, target, game, extras=None):
    """柳林风声：弃1异象，将5T复制加入对方手牌。对方部署其它异象时，复制卡加入友方区域。"""
    from tards.cards import MinionCard, Minion
    from tards.cost import Cost
    from card_pools.effect_utils import empty_positions
    import random

    if not isinstance(target, MinionCard) or target not in player.card_hand:
        print("  柳林风声：目标不在手牌中")
        return False

    # 弃掉
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  柳林风声：{player.name} 弃掉 [{target.name}]")

    opponent = game.p2 if player == game.p1 else game.p1

    # 创建5T复制卡
    shadow_card = MinionCard(
        name=target.name,
        owner=opponent,
        cost=Cost(t=5),
        targets=target.targets,
        attack=target.attack,
        health=target.health,
        special=target.special,
        keywords=dict(target.keywords) if target.keywords else {},
    )
    shadow_card.pack = getattr(target, "pack", None)
    shadow_card._liulin_shadow = True

    if len(opponent.card_hand) < opponent.card_hand_max:
        opponent.card_hand.append(shadow_card)
        print(f"  柳林风声：{shadow_card.name}(5T) 加入 {opponent.name} 手牌")
    else:
        opponent.card_dis.append(shadow_card)
        print(f"  柳林风声：{opponent.name} 手牌已满，复制卡被弃置")
        return True

    # deploy_hook：对方部署异象时触发
    def deploy_hook(minion):
        sc = getattr(minion, "source_card", None)
        # 检查是否是复制卡本身被部署
        if sc is shadow_card or getattr(sc, "_liulin_shadow", False):
            if deploy_hook in game.deploy_hooks:
                game.deploy_hooks.remove(deploy_hook)
            print(f"  柳林风声：{opponent.name} 手动部署了复制卡，效果不触发")
            return

        # 对方部署了其它异象，将复制卡加入友方区域
        if shadow_card in opponent.card_hand:
            opponent.card_hand.remove(shadow_card)
            valid_positions = empty_positions(player, game.board)
            if valid_positions:
                deploy_pos = random.choice(valid_positions)
                shadow_minion = Minion(
                    name=shadow_card.name,
                    owner=player,
                    position=deploy_pos,
                    attack=shadow_card.attack,
                    health=shadow_card.health,
                    source_card=shadow_card,
                    board=game.board,
                    keywords=dict(shadow_card.keywords) if shadow_card.keywords else {},
                )
                game.board.place_minion(shadow_minion, deploy_pos)
                shadow_minion.summon_turn = game.current_turn
                print(f"  柳林风声：{shadow_card.name} 加入 {player.name} 友方区域 {deploy_pos}")
            else:
                print(f"  柳林风声：{player.name} 友方区域无空位，复制卡被弃置")
        else:
            print(f"  柳林风声：复制卡已不在 {opponent.name} 手牌中")

        # 只触发一次，移除钩子
        if deploy_hook in game.deploy_hooks:
            game.deploy_hooks.remove(deploy_hook)

    game.deploy_hooks.append(deploy_hook)
    print(f"  柳林风声：已注册部署钩子")
    return True


register_card(
    name="柳林风声",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择并弃1张异象，将其花费为5T的复制加入对方手牌。对方部署其它异象时，将此异象加入友方区域。
    targets_fn=_liulinfengsheng_targets,
    effect_fn=_liulinfengsheng_effect,
)

def _hesheng_effect(player, target, game, extras=None):
    """贺胜：展示牌库顶4张，抽取最高费的一张，使其花费为0T。"""
    from card_pools.effect_utils import peek_deck_top, place_at_deck_bottom
    from tards.cost import Cost

    candidates = peek_deck_top(player, 4)
    if not candidates:
        print("  贺胜：牌库为空")
        return True

    # 展示
    names = ", ".join([f"[{c.name}]" for c in candidates])
    print(f"  贺胜：{player.name} 牌库顶展示 {len(candidates)} 张：{names}")

    # 找最高费
    def _cost_total(card):
        c = card.cost
        return c.t + c.c + c.b + c.s + c.ct + sum(c.minerals.values())

    best = max(candidates, key=_cost_total)
    print(f"  贺胜：最高费为 [{best.name}]")

    # 费用设为0T
    best.cost = Cost(t=0)
    print(f"  贺胜：[{best.name}] 花费设为 0T")

    # 从牌库移除并加入手牌
    player.card_deck.remove(best)
    if len(player.card_hand) < player.card_hand_max:
        player.card_hand.append(best)
        print(f"  贺胜：[{best.name}] 加入手牌")
    else:
        player.card_dis.append(best)
        print(f"  贺胜：手牌已满，[{best.name}] 被弃置")

    # 其余置底
    remaining = [c for c in candidates if c is not best]
    if remaining:
        place_at_deck_bottom(player, remaining)

    return True


register_card(
    name="贺胜",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：展示卡组顶的4张牌，抽取其中花费最高的一张，使其花费为0T。
    targets_fn=target_none,
    effect_fn=_hesheng_effect,
)

def _shanqian_effect(player, target, game, extras=None):
    """善潜：使一个异象立刻成长，然后+1/+1。"""
    from tards.cards import Minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  善潜：目标不合法")
        return False

    pos = target.position
    success = target.evolve(game)
    if success:
        new_minion = game.board.get_minion_at(pos)
        if new_minion and new_minion.is_alive():
            new_minion.gain_attack(1, permanent=True)
            new_minion.gain_health_bonus(1, permanent=True)
            print(f"  善潜：{new_minion.name} +1/+1")
    else:
        print(f"  善潜：{target.name} 无法成长")

    return True


register_card(
    name="善潜",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使一个异象立刻成长，然后使其获得+1/1。
    targets_fn=target_any_minion,
    effect_fn=_shanqian_effect,
)

def _culi_effect(player, target, game, extras=None):
    """粗粝：使1个异象获得：成长时，+2/2。"""
    from tards.cards import Minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  粗粝：目标不合法")
        return False

    target._on_evolve_buff = (2, 2)
    print(f"  粗粝：{target.name} 获得成长时+2/+2")
    return True


register_card(
    name="粗粝",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使1个异象获得：成长时，+2/2。
    targets_fn=target_any_minion,
    effect_fn=_culi_effect,
)

register_card(
    name="肉蛋糕",
    cost_str="6T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=3,
    # 效果描述：移除卡组顶的6张牌。将你的HP设为20。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="新月",
    cost_str="7T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="剪刀",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方部署异象后，失去4T。
    targets_fn=target_none,
    condition_fn=_jiandao_condition,
    effect_fn=_jiandao_effect,
)

register_card(
    name="墨水",
    cost_str="2T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方使用花费不大于4T的策略时，改为将其洗入对方卡组。
    targets_fn=target_none,
    condition_fn=_moshui_condition,
    effect_fn=_moshui_effect,
)

register_card(
    name="劲风",
    cost_str="2T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方额外抽1张牌后，将其弃掉，随机使对方1张手牌花费+1T。
    targets_fn=target_none,
    condition_fn=_jinfeng_condition,
    effect_fn=_jinfeng_effect,
)

register_card(
    name="离群",
    cost_str="3T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：消灭接下来首列进入协同状态的异象。
    targets_fn=target_none,
    condition_fn=_liqun_condition,
    effect_fn=_liqun_effect,
)

register_card(
    name="入河",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方部署异象前，将其移除，在下回合开始后将其加入原位。
    targets_fn=target_none,
    condition_fn=_ruhe_condition,
    effect_fn=_ruhe_effect,
)

register_card(
    name="怪石",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方拉闸时，若其剩余T点等于0，对方失去一个T槽。
    targets_fn=target_none,
    condition_fn=_guaishi_condition,
    effect_fn=_guaishi_effect,
)

register_card(
    name="海市蜃楼",
    cost_str="3T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：1个异象被指向前，改为其随机敌方异象成为指向目标。
    targets_fn=target_none,
    condition_fn=_haishi_condition,
    effect_fn=_haishi_effect,
)

register_card(
    name="掩星",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：场上敌方异象数量成为唯一最多时，抽2张牌。
    targets_fn=target_none,
    condition_fn=_yanxing_condition,
    effect_fn=_yanxing_effect,
)

register_card(
    name="反戈",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方打出下一张牌时，若是异象，对对手造成等同于其花费的伤害。
    targets_fn=target_enemy_player,
    condition_fn=_fange_condition,
    effect_fn=_fange_effect,
)

register_card(
    name="夜袭",
    cost_str="2T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：敌方异象对你造成伤害前，使其先获得-2攻击力。若具有迅捷，将其消灭。
    targets_fn=target_none,
    condition_fn=_yexi_condition,
    effect_fn=_yexi_effect,
)

register_card(
    name="蓄锐",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方下次拍铃时，若此轮次未出牌，你获得4T。
    targets_fn=target_none,
    condition_fn=_xurui_condition,
    effect_fn=_xurui_effect,
)
