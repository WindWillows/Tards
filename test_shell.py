#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式本地测试模块 (TardsShell)

用法:
    python test_shell.py

命令:
    hand / h          查看当前玩家手牌
    board / bd        查看场上异象
    res               查看双方资源
    status / st       查看当前回合/阶段
    play <idx> / p <idx>   打出指定手牌（自动提示目标）
    brake / b         拉闸，结束出牌阶段
    bell              拍铃，切换当前行动玩家
    draw              执行抽牌阶段
    action / a        进入出牌阶段（交互循环）
    resolve / r       执行结算阶段
    turn              执行完整一回合
    search <kw>       搜索卡牌
    give <name> [A|B] 将卡牌加入手牌（默认当前玩家）
    setres <p> <r> <v>  修改资源 (t/b/s/c)
    setmax <p> <r> <v>  修改资源上限 (t/c)
    help / ?          打印帮助
    exit / quit       退出
"""

import sys
import os

# 修复 Windows PowerShell / CMD 中文输出乱码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        import io
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    # 同时尝试设置控制台代码页
    os.system("chcp 65001 >nul 2>&1")

from typing import Any, Dict, List, Optional, Tuple

from tards import Game, Player
from tards.board import Board
from tards.card_db import DEFAULT_REGISTRY, CardType
from tards.cards import MinionCard, Strategy, Conspiracy, MineralCard
from tards.targets import target_friendly_positions

# 强制导入三个卡包，填充 DEFAULT_REGISTRY
import card_pools.discrete
import card_pools.underworld
import card_pools.blood


# =============================================================================
# 初始化
# =============================================================================

def setup_quick_battle() -> Tuple[Game, Player, Player]:
    """初始化一个快速测试对战，跳过自动循环。"""
    p1 = Player(0, "玩家A", "测试", [])
    p2 = Player(1, "玩家B", "测试", [])
    game = Game(p1, p2, action_provider=None)

    for p in [p1, p2]:
        p.board_ref = game.board
        p.health = 30
        p.health_max = 30
        p.t_point = 10
        p.t_point_max = 10
        p.b_point = 0
        p.s_point = 0
        p.c_point = 0
        p.c_point_max = 0
        p.card_hand_max = 10

    game.current_turn = 1
    game.current_player = p1
    return game, p1, p2


# =============================================================================
# 辅助函数
# =============================================================================

def _find_player(game: Game, name_or_side: str) -> Optional[Player]:
    """根据名称或 side 查找玩家。A=玩家A(p1), B=玩家B(p2)。"""
    name_or_side = name_or_side.strip().upper()
    if name_or_side in ("A", "0"):
        return game.p1
    if name_or_side in ("B", "1"):
        return game.p2
    for p in game.players:
        if p.name == name_or_side:
            return p
    return None


def _fmt_target(t: Any) -> str:
    """格式化目标对象。"""
    if t is None:
        return "无"
    if isinstance(t, tuple) and len(t) == 2:
        return f"({t[0]},{t[1]})"
    if hasattr(t, "name"):
        return getattr(t, "name", str(t))
    return str(t)


def _search_cards(keyword: str) -> List[Any]:
    """在注册表中模糊搜索卡牌。"""
    keyword = keyword.strip().lower()
    results = []
    for card in DEFAULT_REGISTRY.all_cards():
        if keyword in card.name.lower():
            results.append(card)
    return results


# =============================================================================
# TardsShell
# =============================================================================

class TardsShell:
    def __init__(self, game: Game):
        self.game = game
        self.game.action_provider = self._action_provider
        self._in_action_phase = False
        self._last_cmd = ""
        self._pending_action = None  # 用于将主循环的命令传递给 action_phase

    # ------------------------------------------------------------------
    # 信息打印
    # ------------------------------------------------------------------

    def _print_hand(self, player: Player):
        print(f"  [{player.name}] 手牌 ({len(player.card_hand)}/{player.card_hand_max}):")
        for i, card in enumerate(player.card_hand, 1):
            cost_str = str(card.cost) if hasattr(card, "cost") else "?"
            ctype = ""
            if isinstance(card, MinionCard):
                ctype = f" 异象 {card.attack}/{card.health}"
            elif isinstance(card, Strategy):
                ctype = " 策略"
            elif isinstance(card, Conspiracy):
                ctype = " 阴谋"
            elif isinstance(card, MineralCard):
                ctype = f" 矿物[{getattr(card, 'mineral_type', '?')}]"
            print(f"    [{i}] {card.name} ({cost_str}){ctype}")
        if not player.card_hand:
            print("    (空)")

    def _print_board(self):
        print(self.game.board)

    def _print_resources(self):
        for p in self.game.players:
            print(f"  [{p.name}] HP={p.health}/{p.health_max}  "
                  f"T={p.t_point}/{p.t_point_max}  "
                  f"B={p.b_point}  S={p.s_point}  "
                  f"C={p.c_point}/{p.c_point_max}")

    def _print_status(self):
        p = self.game.current_player
        print(f"  回合 {self.game.current_turn} | 当前玩家: {p.name if p else '无'}")

    # ------------------------------------------------------------------
    # action_provider（出牌阶段的核心交互钩子）
    # ------------------------------------------------------------------

    def _action_provider(self, game: Game, active: Player, opponent: Player) -> Optional[Dict[str, Any]]:
        self._in_action_phase = True
        # 如果有从主循环传递过来的待执行命令，直接消费它
        if self._pending_action is not None:
            action = self._pending_action
            self._pending_action = None
            return action
        while True:
            prompt = f"\n[{active.name}]> "
            try:
                raw = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  退出游戏")
                game.game_over = True
                return None
            if not raw:
                continue
            action = self._parse_command(raw, active, opponent)
            if action is not None:
                return action
            # action is None 表示命令已处理，继续等待下一条命令

    # ------------------------------------------------------------------
    # 命令解析
    # ------------------------------------------------------------------

    def _parse_command(self, cmd: str, active: Player, opponent: Player) -> Optional[Dict[str, Any]]:
        parts = cmd.split()
        if not parts:
            return None
        head = parts[0].lower()
        args = parts[1:]

        # 信息查看
        if head in ("hand", "h"):
            self._print_hand(active)
            return None
        if head in ("board", "bd"):
            self._print_board()
            return None
        if head == "res":
            self._print_resources()
            return None
        if head in ("status", "st"):
            self._print_status()
            return None

        # 阶段控制
        if head in ("brake", "b"):
            return {"type": "brake"}
        if head == "bell":
            return {"type": "bell"}

        # 出牌
        if head in ("play", "p"):
            return self._cmd_play(args, active)

        # 资源调整
        if head == "setres":
            self._cmd_setres(args)
            return None
        if head == "setmax":
            self._cmd_setmax(args)
            return None

        # 卡牌搜索/给予
        if head == "search":
            self._cmd_search(args)
            return None
        if head == "give":
            self._cmd_give(args, active)
            return None

        # 帮助
        if head in ("help", "?"):
            self._print_help()
            return None

        # 退出
        if head in ("exit", "quit"):
            self.game.game_over = True
            if self._in_action_phase:
                return {"type": "brake"}
            return None

        print(f"  未知命令: {head}，输入 help 查看帮助")
        return None

    # ------------------------------------------------------------------
    # 打出卡牌
    # ------------------------------------------------------------------

    def _cmd_play(self, args: List[str], active: Player) -> Optional[Dict[str, Any]]:
        if not args:
            print("  用法: play <手牌序号>")
            return None
        try:
            idx = int(args[0])
        except ValueError:
            print("  手牌序号必须是数字")
            return None
        if idx < 1 or idx > len(active.card_hand):
            print(f"  手牌序号超出范围 (1~{len(active.card_hand)})")
            return None

        card = active.card_hand[idx - 1]
        serial = idx

        # 献祭处理 (cost.b > 0 的异象卡)
        sacrifices = []
        if isinstance(card, MinionCard) and card.cost.b > 0:
            sacs = self._prompt_sacrifices(active, card.cost.b)
            if sacs is None:
                print("  取消出牌")
                return None
            sacrifices = sacs

        # 主目标选择
        target = self._prompt_target(card, active)
        if target is None and not self._can_target_none(card):
            print("  取消出牌")
            return None

        # 额外目标（多阶段指向）
        extra_targets = None
        stages = getattr(card, "extra_targeting_stages", None)
        if isinstance(card, MinionCard) and stages:
            all_extra = []
            for stage_def in stages:
                if isinstance(stage_def, (list, tuple)):
                    fn, count, repeat = stage_def[0], stage_def[1], stage_def[2]
                else:
                    fn = stage_def.get("fn")
                    count = stage_def.get("count", 1)
                    repeat = stage_def.get("repeat", False)
                et = self._prompt_extra_target(fn, count, repeat, active, "部署额外目标")
                if et:
                    all_extra.extend(et)
            if all_extra:
                extra_targets = all_extra
        elif isinstance(card, (Strategy, Conspiracy, MineralCard)) and stages:
            all_extra = []
            for stage_def in card.extra_targeting_stages:
                if isinstance(stage_def, (list, tuple)):
                    fn, count, repeat = stage_def[0], stage_def[1], stage_def[2]
                else:
                    fn = stage_def.get("fn")
                    count = stage_def.get("count", 1)
                    repeat = stage_def.get("repeat", False)
                et = self._prompt_extra_target(fn, count, repeat, active, "额外目标")
                if et:
                    all_extra.extend(et)
            if all_extra:
                extra_targets = all_extra

        return {
            "type": "play",
            "serial": serial,
            "target": target,
            "sacrifices": sacrifices,
            "extra_targets": extra_targets or None,
        }

    def _can_target_none(self, card: Any) -> bool:
        """判断卡牌是否允许无目标打出。"""
        if isinstance(card, MinionCard):
            return False
        return True

    def _prompt_target(self, card: Any, active: Player) -> Any:
        """通用目标选择提示。"""
        from tards.targets import target_none
        targets_fn = getattr(card, "targets", None) or target_none
        valid = list(targets_fn(active, active.board_ref))
        if not valid or (len(valid) == 1 and valid[0] is None):
            return None

        print(f"  请选择 [{card.name}] 的目标:")
        for i, t in enumerate(valid, 1):
            print(f"    [{i}] {_fmt_target(t)}")
        print("    [0] 取消")
        try:
            choice = int(input("  目标编号> "))
        except ValueError:
            print("  输入无效")
            return None
        if choice == 0:
            return None
        if choice < 1 or choice > len(valid):
            print("  编号超出范围")
            return None
        return valid[choice - 1]

    def _prompt_extra_target(self, targets_fn, count: int, repeat: bool, active: Player, prompt_name: str) -> Optional[List[Any]]:
        """提示选择额外目标。"""
        if targets_fn is None:
            return None
        valid = list(targets_fn(active, active.board_ref))
        if not valid:
            return None
        print(f"  请选择 [{prompt_name}]:")
        for i, t in enumerate(valid, 1):
            print(f"    [{i}] {_fmt_target(t)}")
        print("    [0] 跳过")
        selected = []
        while len(selected) < count:
            try:
                choice = int(input(f"  目标编号 ({len(selected) + 1}/{count})> "))
            except ValueError:
                print("  输入无效")
                continue
            if choice == 0:
                break
            if choice < 1 or choice > len(valid):
                print("  编号超出范围")
                continue
            t = valid[choice - 1]
            if not repeat and t in selected:
                print("  不能重复选择同一目标")
                continue
            selected.append(t)
        return selected if selected else None

    def _prompt_sacrifices(self, active: Player, required: int) -> Optional[List[Any]]:
        """提示选择献祭异象。"""
        minions = list(active.board_ref.get_minions_of_player(active))
        if not minions:
            print("  场上没有可献祭的友方异象")
            return None
        print(f"  需要献祭 {required} B点，请选择献祭异象（丰饶值之和需≥{required}）:")
        for i, m in enumerate(minions, 1):
            fertile = m.keywords.get("丰饶", 1)
            print(f"    [{i}] {m.name} ({m.current_attack}/{m.current_health}) 丰饶={fertile}")
        print("    [0] 取消")
        selected = []
        total = 0
        while True:
            try:
                choice = int(input(f"  献祭编号 (当前{total}/{required})> "))
            except ValueError:
                print("  输入无效")
                continue
            if choice == 0:
                return None
            if choice < 1 or choice > len(minions):
                print("  编号超出范围")
                continue
            m = minions[choice - 1]
            if m in selected:
                print("  已选择该异象")
                continue
            selected.append(m)
            total += m.keywords.get("丰饶", 1)
            if total >= required:
                break
        return selected

    # ------------------------------------------------------------------
    # 资源调整
    # ------------------------------------------------------------------

    def _cmd_setres(self, args: List[str]):
        if len(args) < 3:
            print("  用法: setres <A|B> <t|b|s|c> <数值>")
            return
        p = _find_player(self.game, args[0])
        if p is None:
            print(f"  找不到玩家: {args[0]}")
            return
        r = args[1].lower()
        try:
            val = int(args[2])
        except ValueError:
            print("  数值必须是整数")
            return
        if r == "t":
            p.t_point = max(0, val)
        elif r == "b":
            p.b_point = max(0, val)
        elif r == "s":
            p.s_point = max(0, val)
        elif r == "c":
            p.c_point = max(0, val)
        else:
            print(f"  未知资源类型: {r} (支持 t/b/s/c)")
            return
        print(f"  [{p.name}] {r.upper()}点已设为 {val}")

    def _cmd_setmax(self, args: List[str]):
        if len(args) < 3:
            print("  用法: setmax <A|B> <t|c> <数值>")
            return
        p = _find_player(self.game, args[0])
        if p is None:
            print(f"  找不到玩家: {args[0]}")
            return
        r = args[1].lower()
        try:
            val = int(args[2])
        except ValueError:
            print("  数值必须是整数")
            return
        if r == "t":
            p.t_point_max = max(0, val)
        elif r == "c":
            p.c_point_max = max(0, val)
        else:
            print(f"  未知上限类型: {r} (支持 t/c)")
            return
        print(f"  [{p.name}] {r.upper()}上限已设为 {val}")

    # ------------------------------------------------------------------
    # 卡牌搜索/给予
    # ------------------------------------------------------------------

    def _cmd_search(self, args: List[str]):
        if not args:
            print("  用法: search <关键字>")
            return
        kw = " ".join(args)
        results = _search_cards(kw)
        if not results:
            print(f"  未找到包含 '{kw}' 的卡牌")
            return
        print(f"  找到 {len(results)} 张卡牌:")
        for i, card in enumerate(results[:20], 1):
            print(f"    [{i}] {card.name} ({card.cost_str}) [{card.pack.value}] {card.card_type.value}")
        if len(results) > 20:
            print(f"    ... 还有 {len(results) - 20} 张")

    def _cmd_give(self, args: List[str], active: Player):
        if not args:
            print("  用法: give <卡名> [A|B]")
            return
        # 最后一段如果是 A/B，则作为玩家指定
        target_player = active
        name = " ".join(args)
        if args[-1].upper() in ("A", "B"):
            target_player = _find_player(self.game, args[-1])
            name = " ".join(args[:-1])

        card_def = DEFAULT_REGISTRY.get(name)
        if card_def is None:
            # 模糊搜索
            results = _search_cards(name)
            if len(results) == 1:
                card_def = results[0]
                print(f"  模糊匹配到: {card_def.name}")
            elif len(results) > 1:
                print(f"  找到多张匹配卡牌，请输入完整名称:")
                for c in results[:10]:
                    print(f"    - {c.name}")
                return
            else:
                print(f"  注册表中找不到卡牌: {name}")
                return

        card = card_def.to_game_card(target_player)
        if len(target_player.card_hand) < target_player.card_hand_max:
            target_player.card_hand.append(card)
            print(f"  [{target_player.name}] 获得 [{card.name}]")
        else:
            target_player.card_dis.append(card)
            print(f"  [{target_player.name}] 手牌已满，[{card.name}] 被弃置")

    # ------------------------------------------------------------------
    # 帮助
    # ------------------------------------------------------------------

    def _print_help(self):
        print("""
命令列表:
  --- 信息查看 ---
  hand / h              查看当前玩家手牌
  board / bd            查看场上异象
  res                   查看双方资源
  status / st           查看当前回合/阶段

  --- 出牌阶段操作 (随时可用，会自动进入 action phase) ---
  play <idx> / p <idx>  打出指定手牌（自动提示目标）
  brake / b             拉闸，结束出牌阶段
  bell                  拍铃，切换当前行动玩家

  --- 阶段控制 ---
  draw                  执行抽牌阶段
  action / a            进入出牌阶段（交互循环）
  resolve / r           执行结算阶段
  turn                  执行完整一回合

  --- 调试/作弊 ---
  search <kw>           搜索卡牌
  give <name> [A|B]     将卡牌加入手牌
  setres <p> <r> <v>    修改资源 (t/b/s/c)
  setmax <p> <r> <v>    修改资源上限 (t/c)

  --- 其他 ---
  help / ?              打印帮助
  exit / quit           退出游戏
""")

    # ------------------------------------------------------------------
    # 外部阶段控制（在 action_phase 之外使用）
    # ------------------------------------------------------------------

    def run_draw_phase(self):
        first = self.game.current_player
        second = self.game.p2 if first is self.game.p1 else self.game.p1
        self.game.draw_phase(first, second)

    def run_action_phase(self):
        first = self.game.current_player
        second = self.game.p2 if first is self.game.p1 else self.game.p1
        self._in_action_phase = True
        try:
            self.game.action_phase(first, second)
        finally:
            self._in_action_phase = False

    def run_resolve_phase(self):
        first = self.game.current_player
        second = self.game.p2 if first is self.game.p1 else self.game.p1
        self.game.resolve_phase(first, second)

    def run_turn(self):
        self.run_draw_phase()
        self.run_action_phase()
        self.run_resolve_phase()
        # 切换玩家
        self.game.current_player = self.game.p2 if self.game.current_player is self.game.p1 else self.game.p1
        self.game.current_turn += 1

    def run_shell(self):
        """主循环：接受命令并执行阶段控制。"""
        print("=" * 50)
        print("Tards 交互式测试终端")
        print("=" * 50)
        self._print_help()
        while not self.game.game_over:
            try:
                raw = input("\n[TEST]> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  再见")
                break
            if not raw:
                continue
            parts = raw.split()
            head = parts[0].lower()
            args = parts[1:]

            if head in ("draw",):
                self.run_draw_phase()
            elif head in ("action", "a"):
                self.run_action_phase()
            elif head in ("resolve", "r"):
                self.run_resolve_phase()
            elif head == "turn":
                self.run_turn()
            elif head in ("exit", "quit"):
                break
            elif head in ("help", "?"):
                self._print_help()
            elif head in ("hand", "h", "board", "bd", "res", "status", "st",
                          "search", "give", "setres", "setmax"):
                # 这些命令需要 active player；默认当前玩家
                active = self.game.current_player or self.game.p1
                opponent = self.game.p2 if active is self.game.p1 else self.game.p1
                self._parse_command(raw, active, opponent)
            elif head in ("play", "p", "brake", "b", "bell"):
                # play/brake/bell 是 action phase 命令
                # 如果已经在 action phase 中，理论上不会走到这里（会被 action_phase 吞掉）
                # 如果不在，自动进入 action phase 并传递这条命令
                if self._in_action_phase:
                    print(f"  内部错误：在 action phase 中收到 {head} 但未被处理")
                else:
                    active = self.game.current_player or self.game.p1
                    opponent = self.game.p2 if active is self.game.p1 else self.game.p1
                    action = self._parse_command(raw, active, opponent)
                    if action is not None:
                        self._pending_action = action
                        self.run_action_phase()
            else:
                print(f"  未知命令: {head}，输入 help 查看帮助")


# =============================================================================
# 入口
# =============================================================================

if __name__ == "__main__":
    game, p1, p2 = setup_quick_battle()
    shell = TardsShell(game)
    shell.run_shell()
