"""输入/事件控制器。

将 BattleFrame 中的键盘、鼠标、拖拽、指向、献祭、出牌等交互逻辑集中管理，
使 BattleFrame 仅保留 UI 组装与状态协调。
"""

from typing import Any, Callable, List, Optional

import random
import tkinter as tk
from tkinter import messagebox

from tards import Conspiracy, Minion, MinionCard, Player

from tards.core.targeting import TargetingRequest, get_attack_target_candidates
from gui.theme import UI_THEME


class InputController:
    """处理所有用户输入事件，并调用 frame 的方法更新 UI。"""

    def __init__(self, frame: Any):
        self.frame = frame

    # ------------------------------------------------------------------
    # 快捷键
    # ------------------------------------------------------------------
    def on_key_press(self, event) -> None:
        """处理键盘快捷键。"""
        frame = self.frame
        key = event.keysym
        if key == "Escape":
            self.on_cancel()
            return
        if key.lower() == "b":
            self.on_brake()
            return
        if key == "space":
            if frame.mulligan_controller.is_active() and not frame.state._mulligan_waiting_remote:
                frame.mulligan_controller.confirm()
            else:
                self.on_bell()
            return
        if key == "Return":
            if frame.state._in_sacrifice_mode:
                self.confirm_sacrifice()
                return
            if frame.state._in_targeting_mode and len(frame.state._targeting_valid_targets) == 1:
                target = frame.state._targeting_valid_targets[0]
                frame.state._in_targeting_mode = False
                on_confirm = frame.state._targeting_on_confirm
                frame.state._targeting_on_confirm = None
                frame.state._targeting_on_cancel = None
                frame.state._targeting_valid_targets = []
                frame.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
                if on_confirm:
                    on_confirm(target)
            return
        if key.lower() == "a":
            self.auto_fill_attack_targets()
            return
        if key.lower() == "e":
            self.auto_fill_effect_targets()
            return
        if key.lower() == "s":
            frame.action_controller.on_exchange_squirrel()
            return
        mineral_keys = {"i": "I", "g": "G", "d": "D", "m": "M"}
        if key.lower() in mineral_keys:
            frame.action_controller.on_exchange_mineral(mineral_keys[key.lower()])
            return
        key_map = {
            "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
            "6": 6, "7": 7, "8": 8, "9": 9, "0": 10,
            "KP_1": 1, "KP_2": 2, "KP_3": 3, "KP_4": 4, "KP_5": 5,
            "KP_6": 6, "KP_7": 7, "KP_8": 8, "KP_9": 9, "KP_0": 10,
        }
        if key in key_map:
            serial = key_map[key]
            idx = serial - 1
            self.on_hand_card_click(idx)

    def auto_fill_attack_targets(self) -> None:
        """一键自动为所有能攻击的异象填充默认攻击目标。"""
        frame = self.frame
        if not frame.duel.game or frame.duel.game.current_phase != "action":
            return
        active = frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        filled = 0
        for (r, c), m in frame.duel.game.board.minion_place.items():
            if m.owner != active:
                continue
            if not m.can_attack_this_turn(frame.duel.game.current_turn):
                continue
            vision = m.keywords.get("视野", 0)
            multi = m.keywords.get("高频", 0)
            count = multi if isinstance(multi, int) and multi > 0 else 1
            if vision <= 0 and (not isinstance(multi, int) or multi <= 0):
                continue
            existing = getattr(m, "_pending_attack_targets", None)
            if existing and isinstance(existing, list) and len(existing) >= count:
                continue
            candidates = get_attack_target_candidates(m, frame.duel.game)
            if not candidates:
                continue
            need = count - (len(existing) if existing else 0)
            selected = (existing or []) + candidates[:need]
            frame.duel.submit_local_action({
                "type": "set_attack_targets",
                "pos": m.position,
                "targets": selected,
            })
            filled += 1
        if filled > 0:
            frame.hint_label.config(text=f"已为 {filled} 个异象自动填充攻击目标")
            frame.after(1500, self.reset_guide_hint)
        else:
            frame.hint_label.config(text="没有需要填充的攻击目标")
            frame.after(1000, self.reset_guide_hint)

    def auto_fill_effect_targets(self) -> None:
        """一键自动为所有有效果预设能力的异象填充默认效果目标。"""
        frame = self.frame
        if not frame.duel.game or frame.duel.game.current_phase != "action":
            return
        active = frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        filled = 0
        for (r, c), m in frame.duel.game.board.minion_place.items():
            if m.owner != active:
                continue
            scope_fn = getattr(m, '_effect_target_scope_fn', None)
            if not scope_fn:
                continue
            if getattr(m, '_pending_effect_target', None) is not None:
                continue
            candidates = scope_fn(active, frame.duel.game.board)
            if not candidates:
                continue
            selected = random.choice(candidates)
            frame.duel.submit_local_action({
                "type": "set_effect_target",
                "pos": m.position,
                "target": selected,
            })
            filled += 1
        if filled > 0:
            frame.hint_label.config(text=f"已为 {filled} 个异象自动填充效果目标")
            frame.after(1500, self.reset_guide_hint)
        else:
            frame.hint_label.config(text="没有需要填充的效果目标")
            frame.after(1000, self.reset_guide_hint)

    # ------------------------------------------------------------------
    # 拖拽出牌
    # ------------------------------------------------------------------
    def on_drag_start(self, event, card, serial) -> None:
        """记录拖拽起始状态。"""
        frame = self.frame
        frame.state._dragging_card = card
        frame.state._dragging_serial = serial
        frame.state._drag_start_x = event.x_root
        frame.state._drag_start_y = event.y_root

    def on_drag_motion(self, event) -> None:
        """拖拽中显示跟随标签或卡牌缩略图。"""
        frame = self.frame
        if not frame.state._dragging_card:
            return
        if frame.state._drag_label:
            frame.state._drag_label.destroy()
        from tards.assets import get_asset_manager
        am = get_asset_manager()
        img = None
        asset_id = getattr(frame.state._dragging_card, "asset_id", None)
        if asset_id:
            img = am.get_thumbnail(asset_id, 80, 110)
        if img:
            frame.state._drag_label = tk.Label(frame, image=img, bg=UI_THEME["bg_panel"], relief=tk.RIDGE, bd=1)
            frame.state._drag_label.image = img
        else:
            name = getattr(frame.state._dragging_card, "name", "未知")
            frame.state._drag_label = tk.Label(
                frame, text=name, bg=UI_THEME["btn_warning_bg"], fg=UI_THEME["btn_warning_fg"],
                font=("Microsoft YaHei", 10, "bold"),
                relief=tk.RIDGE, bd=1
            )
        frame.state._drag_label.place(
            x=event.x_root - frame.winfo_rootx(),
            y=event.y_root - frame.winfo_rooty()
        )

    def on_drag_release(self, event) -> None:
        """释放时判断是否在棋盘内，尝试直接出牌。"""
        frame = self.frame
        if frame.state._drag_label:
            frame.state._drag_label.destroy()
            frame.state._drag_label = None
        if not frame.state._dragging_card:
            return
        dist = ((event.x_root - frame.state._drag_start_x) ** 2 +
                (event.y_root - frame.state._drag_start_y) ** 2) ** 0.5
        if dist < 20:
            serial = frame.state._dragging_serial
            frame.state._dragging_card = None
            frame.state._dragging_serial = None
            if serial is not None:
                self.on_hand_card_click(serial - 1)
            return
        canvas_x = event.x_root - frame.canvas.winfo_rootx() - frame.state.board_offset_x
        canvas_y = event.y_root - frame.canvas.winfo_rooty() - frame.state.board_offset_y
        board_w = frame.BOARD_COLS * frame.state.cell_size
        board_h = frame.BOARD_ROWS * frame.state.cell_size
        if 0 <= canvas_x < board_w and 0 <= canvas_y < board_h:
            c = int(canvas_x // frame.state.cell_size)
            display_r = int(canvas_y // frame.state.cell_size)
            logic_r = frame._logic_row(display_r)
            self.try_play_at_position(frame.state._dragging_serial, (logic_r, c))
        frame.state._dragging_card = None
        frame.state._dragging_serial = None

    def try_play_at_position(self, serial, target) -> None:
        """尝试在指定格子直接部署卡牌（仅支持无需献祭/指向的异象卡）。"""
        frame = self.frame
        if not frame.duel.game:
            return
        active = frame.duel.game.current_player
        card = active._get_hand_card(serial) if active else None
        if card is None:
            return
        if not isinstance(card, MinionCard):
            frame.hint_label.config(text="只能拖拽部署异象卡")
            frame.after(800, self.reset_guide_hint)
            return
        if card.cost.b > 0:
            frame.hint_label.config(text="需要献祭的卡牌无法拖拽部署")
            frame.after(800, self.reset_guide_hint)
            return
        stages = list(getattr(card, "extra_targeting_stages", []))
        if stages:
            frame.hint_label.config(text="需要指向的卡牌无法拖拽部署")
            frame.after(800, self.reset_guide_hint)
            return
        if not frame.duel.game.board.is_valid_deploy(target, active, card):
            self.flash_invalid_at(target)
            return
        existing = frame.duel.game.board.get_minion_at(target)
        if existing and not (
            ("漂浮物" in existing.keywords and existing.owner == active) or
            ("藤蔓" in card.keywords and existing.owner == active)
        ):
            self.flash_invalid_at(target)
            return
        self.submit_play(serial, target)

    # ------------------------------------------------------------------
    # 异象与玩家点击
    # ------------------------------------------------------------------
    def on_minion_click(self, minion: Minion) -> Optional[str]:
        """处理点击场上异象。"""
        frame = self.frame
        # 1. 献祭选择模式
        if frame.state._in_sacrifice_mode:
            if minion in frame.state._sacrifice_candidates:
                if minion in frame.state._selected_sacrifices:
                    frame.state._selected_sacrifices.remove(minion)
                else:
                    frame.state._selected_sacrifices.append(minion)
                frame._render_board()
                frame._render_info()
                total = sum(m.keywords.get("丰饶", 1) for m in frame.state._selected_sacrifices)
                if total >= frame.state._sacrifice_required:
                    self.confirm_sacrifice()
                return "break"
            return

        # 2. 指向模式
        if frame.state._in_targeting_mode:
            if minion in frame.state._targeting_valid_targets:
                frame.state._in_targeting_mode = False
                on_confirm = frame.state._targeting_on_confirm
                frame.state._targeting_on_confirm = None
                frame.state._targeting_on_cancel = None
                frame.state._targeting_valid_targets = []
                frame.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
                frame._render_board()
                frame._render_info()
                if on_confirm:
                    on_confirm(minion)
                return "break"
            return

        # 3. 非指向模式：进入预设
        if not frame.duel.game:
            return
        if frame.duel.game.current_phase != "action":
            return
        active = frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and minion.owner != frame.local_player:
            return
        if minion.owner != active:
            return
        if frame.state.selected_card is not None:
            return

        has_attack = minion.keywords.get("视野", 0) > 0
        has_effect = getattr(minion, '_effect_target_scope_fn', None) is not None
        entered = False
        if has_attack:
            self.handle_board_unit_click(minion.position, mode="attack")
            entered = True
        elif has_effect:
            self.handle_board_unit_click(minion.position, mode="effect")
            entered = True
        if entered:
            return "break"

    def on_minion_double_click(self, minion: Minion) -> str:
        """处理双击场上异象。"""
        frame = self.frame
        if not frame.duel.game:
            return "break"
        active = frame.duel.game.current_player
        if not active:
            return "break"
        if frame.duel.is_remote and minion.owner != frame.local_player:
            return "break"
        if minion.owner != active:
            return "break"
        if frame.duel.game.current_phase != "action":
            return "break"

        if (frame.state._in_targeting_mode
                and frame.state._current_targeting_mode == "attack"
                and frame.state._targeting_source_minion is minion):
            has_effect = getattr(minion, '_effect_target_scope_fn', None) is not None
            if has_effect:
                self.exit_targeting_mode()
                self.handle_board_unit_click(minion.position, mode="effect")
            return "break"

        if frame.state._in_targeting_mode:
            return "break"

        self.on_minion_click(minion)
        return "break"

    def on_player_label_click(self, player: Optional[Player]) -> None:
        """处理点击玩家信息标签（作为指向目标）。"""
        frame = self.frame
        if not frame.state._in_targeting_mode or not player:
            return
        if player in frame.state._targeting_valid_targets:
            frame.state._in_targeting_mode = False
            on_confirm = frame.state._targeting_on_confirm
            frame.state._targeting_on_confirm = None
            frame.state._targeting_on_cancel = None
            frame.state._targeting_valid_targets = []
            frame.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
            frame._render_board()
            frame._render_info()
            if on_confirm:
                on_confirm(player)

    # ------------------------------------------------------------------
    # 指向 / 献祭 模式控制
    # ------------------------------------------------------------------
    def enter_local_targeting(self, valid_targets: List[Any], on_confirm: Callable[[Any], None],
                              on_cancel: Optional[Callable[[], None]] = None, prompt: str = "请选择目标") -> None:
        """进入本地指向模式。"""
        frame = self.frame
        frame.state._in_targeting_mode = True
        frame.state._targeting_valid_targets = valid_targets
        frame.state._targeting_on_confirm = on_confirm
        frame.state._targeting_on_cancel = on_cancel
        frame.state.valid_targets = valid_targets
        frame.hint_label.config(text=prompt, font=("Microsoft YaHei", 12, "bold"), fg=UI_THEME["danger"])
        frame._render_board()
        frame._render_info()
        frame._render_hand()

    def show_targeting(self, request: TargetingRequest, valid_targets: List[Any]) -> None:
        """响应 targeting_request 事件，渲染指向选项。"""
        frame = self.frame
        if not valid_targets:
            if request.on_cancel:
                request.on_cancel()
            if hasattr(frame.duel, 'submit_local_targeting'):
                frame.duel.submit_local_targeting(None)
            return

        if request.numeric_options is not None:
            from gui.dialogs import NumericChoiceDialog
            def on_choose(val: int):
                if hasattr(frame.duel, 'submit_local_targeting'):
                    frame.duel.submit_local_targeting(val)
            NumericChoiceDialog(frame, request.prompt, request.numeric_options, on_choose)
            return

        self.enter_local_targeting(
            valid_targets=valid_targets,
            on_confirm=lambda target: (
                frame.duel.submit_local_targeting(target) if hasattr(frame.duel, 'submit_local_targeting') else None
            ),
            on_cancel=lambda: (
                frame.duel.submit_local_targeting(None) if hasattr(frame.duel, 'submit_local_targeting') else None
            ),
            prompt=request.prompt,
        )

    def enter_sacrifice_mode(self, serial: int, card, active, required_blood: int) -> None:
        """进入献祭选择模式。"""
        frame = self.frame
        frame.state._in_sacrifice_mode = True
        frame.state._sacrifice_serial = serial
        frame.state._sacrifice_card = card
        frame.state._sacrifice_active = active
        frame.state._sacrifice_required = required_blood
        frame.state._sacrifice_candidates = list(frame.duel.game.board.get_minions_of_player(active)) if frame.duel.game else []
        frame.state._selected_sacrifices = []
        frame.state._pending_sacrifices = []
        frame.hint_label.config(
            text=f"请选择献祭异象（需要{required_blood}点鲜血）| 点击选择/取消 | Enter确认 | ESC取消",
            font=("Microsoft YaHei", 11, "bold"), fg=UI_THEME["danger"]
        )
        frame._render_board()
        frame._render_info()
        frame._render_hand()

    def exit_sacrifice_mode(self) -> None:
        """退出献祭选择模式。"""
        frame = self.frame
        frame.state._in_sacrifice_mode = False
        frame.state._sacrifice_candidates = []
        frame.state._selected_sacrifices = []
        frame.state._sacrifice_required = 0
        frame.state._sacrifice_serial = None
        frame.state._sacrifice_card = None
        frame.state._sacrifice_active = None
        frame.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
        frame._render_board()
        frame._render_info()
        frame._render_hand()

    def confirm_sacrifice(self) -> None:
        """确认当前选择的献祭，进入部署位置选择。"""
        frame = self.frame
        total = sum(m.keywords.get("丰饶", 1) for m in frame.state._selected_sacrifices)
        if total < frame.state._sacrifice_required:
            frame.hint_label.config(text=f"献祭不足，已选{total}点，还需{frame.state._sacrifice_required - total}点", fg=UI_THEME["danger"])
            frame.after(1000, lambda: frame.hint_label.config(fg=UI_THEME["danger"]))
            return
        frame.state._pending_sacrifices = list(frame.state._selected_sacrifices)
        serial = frame.state._sacrifice_serial
        card = frame.state._sacrifice_card
        active = frame.state._sacrifice_active
        self.exit_sacrifice_mode()
        self.enter_deploy_targeting(serial, card, active)

    def exit_targeting_mode(self, preserve_pending=False) -> None:
        """退出指向模式。"""
        frame = self.frame
        frame.state._in_targeting_mode = False
        frame.state._targeting_valid_targets = []
        frame.state._targeting_on_confirm = None
        frame.state._targeting_on_cancel = None
        frame.state.valid_targets = []
        frame.state.selected_card = None
        frame.state.selected_card_idx = None
        frame.state._targeting_source_minion = None
        frame.state._current_targeting_mode = None
        if not preserve_pending:
            frame.state._pending_sacrifices = []
        frame.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
        frame._render_hand()
        frame._render_board()
        frame._render_info()

    def clear_attack_targets(self, pos) -> None:
        """清除指定异象的预设攻击目标。"""
        frame = self.frame
        if not frame.duel.game:
            return
        active = frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        m = frame.duel.game.board.get_minion_at(pos)
        if not m or m.owner != active:
            return
        frame.duel.submit_local_action({
            "type": "set_attack_targets",
            "pos": pos,
            "targets": [],
        })

    def clear_effect_target(self, pos) -> None:
        """清除指定异象的预设效果目标。"""
        frame = self.frame
        if not frame.duel.game:
            return
        active = frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        m = frame.duel.game.board.get_minion_at(pos)
        if not m or m.owner != active:
            return
        frame.duel.submit_local_action({
            "type": "set_effect_target",
            "pos": pos,
            "target": None,
        })

    # ------------------------------------------------------------------
    # 场上单位预设与手牌点击
    # ------------------------------------------------------------------
    def handle_board_unit_click(self, target, mode="attack") -> None:
        """处理玩家点击场上自己的异象（攻击预设或效果预设）。"""
        frame = self.frame
        if not frame.duel.game:
            return
        active = frame.duel.game.current_player
        if not active:
            return
        m = frame.duel.game.board.get_minion_at(target)
        if not m:
            return
        if frame.duel.is_remote and m.owner != frame.local_player:
            return
        if m.owner != active:
            return

        if mode == "attack":
            vision = m.keywords.get("视野", 0)
            if vision <= 0:
                return
            multi_attack = m.keywords.get("高频", 0)
            atk_candidates = get_attack_target_candidates(m, frame.duel.game)
            if not atk_candidates:
                return

            count = multi_attack if isinstance(multi_attack, int) and multi_attack > 0 else 1
            selected_atks: List[Any] = []

            def pick_next():
                if len(selected_atks) >= count:
                    frame.duel.submit_local_action({
                        "type": "set_attack_targets",
                        "pos": m.position,
                        "targets": selected_atks,
                    })
                    self.exit_targeting_mode()
                    return
                self.enter_local_targeting(
                    valid_targets=atk_candidates,
                    on_confirm=lambda t: (selected_atks.append(t), pick_next()),
                    on_cancel=self.exit_targeting_mode,
                    prompt=f"请选择 {m.name} 的攻击目标 ({len(selected_atks)+1}/{count})",
                )

            frame.state._targeting_source_minion = m
            frame.state._current_targeting_mode = "attack"
            pick_next()

        elif mode == "effect":
            scope_fn = getattr(m, '_effect_target_scope_fn', None)
            if not scope_fn:
                return
            candidates = scope_fn(active, frame.duel.game.board)
            if not candidates:
                return

            selected_effect: List[Any] = []

            def pick_next_effect():
                if len(selected_effect) >= 1:
                    frame.duel.submit_local_action({
                        "type": "set_effect_target",
                        "pos": m.position,
                        "target": selected_effect[0],
                    })
                    self.exit_targeting_mode()
                    return
                self.enter_local_targeting(
                    valid_targets=candidates,
                    on_confirm=lambda t: (selected_effect.append(t), pick_next_effect()),
                    on_cancel=self.exit_targeting_mode,
                    prompt=f"请选择 {m.name} 的效果目标",
                )

            frame.state._targeting_source_minion = m
            frame.state._current_targeting_mode = "effect"
            pick_next_effect()

    def _card_is_potentially_playable(self, serial: int, card, active) -> bool:
        """判断卡牌是否至少存在一个可打出的合法目标（考虑鲜血献祭）。"""
        if getattr(card, "can_play", True) is False:
            return False
        if isinstance(card, MinionCard):
            return self._minion_card_is_potentially_playable(serial, card, active)
        # 策略/阴谋等：只要任一合法目标满足 card_can_play 即可
        return any(active.card_can_play(serial, t)[0] for t in active.get_valid_targets(card))

    def _minion_card_is_potentially_playable(self, serial: int, card, active) -> bool:
        """考虑鲜血献祭，判断异象卡是否可能打出。"""
        game = self.frame.duel.game
        if not game:
            return False
        cost = active._get_play_cost(card)
        # 非鲜血费用必须直接支付
        temp_cost = cost.copy()
        temp_cost.b = 0
        if not temp_cost.can_afford(active):
            return False
        valid_targets = active.get_valid_targets(card)
        if not valid_targets:
            return False
        # 鲜血费用足够时直接可下
        if cost.b <= active.b_point:
            return True
        # 鲜血不足时，需要场上有足量友方异象可供献祭
        need = cost.b - active.b_point
        minions = list(game.board.get_minions_of_player(active))
        total_available = sum(m.keywords.get("丰饶", 1) for m in minions)
        return total_available >= need

    def _show_temporary_hint(self, text: str, color: str = UI_THEME["danger"], duration_ms: int = 1500) -> None:
        """安全地显示一条临时提示，duration_ms 后恢复引导文字。"""
        frame = self.frame
        hint = getattr(frame, "hint_label", None)
        if hint is None:
            return
        try:
            hint.config(text=text, font=("Microsoft YaHei", 10, "bold"), fg=color)
            frame.after(duration_ms, self.reset_guide_hint)
        except Exception:
            pass

    def _get_unplayable_reason(self, serial: int, card, active) -> str:
        """返回卡牌当前无法打出的原因（用于提示玩家）。"""
        frame = self.frame
        game = frame.duel.game if frame.duel else None

        if not game or game.current_phase != "action":
            return "当前不是出牌阶段"
        if frame.duel.is_remote and active != frame.local_player:
            return "当前不是你的回合"
        if getattr(card, "can_play", True) is False:
            return "该卡牌当前无法打出"

        cost = active._get_play_cost(card)
        ok, reason = cost.can_afford_detail(active)
        if not ok:
            return reason

        if isinstance(card, MinionCard):
            valid_positions = active.get_valid_targets(card)
            if not valid_positions:
                return "没有合法的部署位置"
            return "无法部署该异象"

        # 策略/阴谋/矿物：检查是否存在合法目标
        valid_targets = active.get_valid_targets(card)
        if not valid_targets:
            return "该卡牌没有合法目标"
        playable_targets = [t for t in valid_targets if active.card_can_play(serial, t)[0]]
        if not playable_targets:
            # 取第一个不合法目标的拒绝原因作为提示
            _, reason = active.card_can_play(serial, valid_targets[0])
            if reason:
                return reason
            return "没有可打出的合法目标"

        return "该卡牌当前无法打出"

    def on_hand_card_click(self, idx: int) -> None:
        """处理点击手牌。"""
        frame = self.frame
        if frame.state._is_playing_card:
            return
        frame.state._is_playing_card = True
        frame.after(500, lambda: setattr(frame.state, "_is_playing_card", False))

        active = frame.duel.game and frame.duel.game.current_player
        serial = idx + 1
        card = active._get_hand_card(serial) if active else None
        if card is None:
            frame.state._is_playing_card = False
            print(f"  [GUI] 点击手牌无效: serial={serial}, idx={idx}")
            return
        if frame.duel.is_remote and active != frame.local_player:
            frame.state._is_playing_card = False
            self._show_temporary_hint("当前不是你的回合")
            return

        if frame.state._in_targeting_mode and card in frame.state._targeting_valid_targets:
            frame.state._in_targeting_mode = False
            on_confirm = frame.state._targeting_on_confirm
            frame.state._targeting_on_confirm = None
            frame.state._targeting_on_cancel = None
            frame.state._targeting_valid_targets = []
            frame.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
            frame._render_board()
            frame._render_info()
            frame._render_hand()
            if on_confirm:
                on_confirm(card)
            return

        # 无法打出的卡牌给出明确原因提示
        if not self._card_is_potentially_playable(serial, card, active):
            reason = self._get_unplayable_reason(serial, card, active)
            self._show_temporary_hint(reason)
            frame.state._is_playing_card = False
            return

        if isinstance(card, Conspiracy):
            valid = [t for t in active.get_valid_targets(card) if active.card_can_play(serial, t)[0]]
            if len(valid) == 1 and valid[0] is None:
                self.submit_play(serial, None)
            elif valid:
                self.enter_local_targeting(
                    valid_targets=valid,
                    on_confirm=lambda t: self.submit_play(serial, t),
                    on_cancel=self.exit_targeting_mode,
                    prompt=f"请选择 [{card.name}] 的目标",
                )
            else:
                self.submit_play(serial, None)
            return

        if isinstance(card, MinionCard):
            cost = active._get_play_cost(card)
            if cost.b > 0:
                if active.b_point >= cost.b:
                    self.enter_deploy_targeting(serial, card, active)
                    return
                need = cost.b - active.b_point
                minions = list(frame.duel.game.board.get_minions_of_player(active)) if frame.duel.game else []
                if not minions:
                    frame.hint_label.config(text="B点不足，且场上没有可献祭的友方异象")
                    return
                self.enter_sacrifice_mode(serial, card, active, need)
                return
            self.enter_deploy_targeting(serial, card, active)
            return

        self.enter_effect_targeting(serial, card, active)

    def enter_deploy_targeting(self, serial: int, card, active) -> None:
        """进入异象卡部署位置选择。"""
        frame = self.frame
        sacrifices = getattr(frame.state, "_pending_sacrifices", [])
        valid = frame._calc_deploy_range(card, active, sacrifices)
        if not valid:
            self.submit_play(serial, None)
            return
        if len(valid) == 1:
            self.submit_play(serial, valid[0])
            return
        self.enter_local_targeting(
            valid_targets=valid,
            on_confirm=lambda t: self.submit_play(serial, t),
            on_cancel=self.exit_targeting_mode,
            prompt=f"[{card.name}] 请选择部署位置",
        )

    def enter_effect_targeting(self, serial: int, card, active) -> None:
        """进入策略/矿物卡效果目标选择。"""
        valid = [t for t in active.get_valid_targets(card) if active.card_can_play(serial, t)[0]]
        if not valid:
            self.submit_play(serial, None)
            return
        if len(valid) == 1 and valid[0] is None:
            self.submit_play(serial, None)
            return
        if len(valid) == 1:
            self.submit_play(serial, valid[0])
            return
        self.enter_local_targeting(
            valid_targets=valid,
            on_confirm=lambda t: self.submit_play(serial, t),
            on_cancel=self.exit_targeting_mode,
            prompt=f"[{card.name}] 请选择效果目标",
        )

    def flash_invalid_at(self, target) -> None:
        """在指定位置闪烁红色边框，提示非法操作。"""
        frame = self.frame
        if not frame.duel.game:
            return
        if isinstance(target, tuple) and len(target) == 2:
            logic_r, c = target
        elif hasattr(target, "position") and target.position:
            logic_r, c = target.position
        else:
            return
        display_r = frame._display_row(logic_r)
        cx = c * frame.state.cell_size + frame.state.cell_size // 2 + frame.state.board_offset_x
        cy = display_r * frame.state.cell_size + frame.state.cell_size // 2 + frame.state.board_offset_y
        frame.canvas.create_rectangle(cx - 40, cy - 40, cx + 40, cy + 40,
                                      outline=UI_THEME["danger"], width=4,
                                      tags="flash_hint")
        frame.after(200, lambda: frame.canvas.delete("flash_hint"))

    def on_canvas_click(self, event) -> None:
        """处理棋盘空白处点击。"""
        frame = self.frame
        active = frame.duel.game and frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        c = (event.x - frame.state.board_offset_x) // frame.state.cell_size
        display_r = (event.y - frame.state.board_offset_y) // frame.state.cell_size
        logic_r = frame._logic_row(display_r)
        target = (logic_r, c)

        if frame.state._in_sacrifice_mode:
            self.flash_invalid_at(target)
            frame.hint_label.config(text="请点击友方异象作为祭品", fg=UI_THEME["danger"])
            frame.after(500, lambda: frame.hint_label.config(fg=UI_THEME["danger"]) if frame.hint_label else None)
            return

        if frame.state._in_targeting_mode:
            clicked_target = None
            if target in frame.state._targeting_valid_targets:
                clicked_target = target
            else:
                if frame.duel.game:
                    m = frame.duel.game.board.get_minion_at(target)
                    if m and m in frame.state._targeting_valid_targets:
                        clicked_target = m
            if clicked_target is not None:
                frame.state._in_targeting_mode = False
                on_confirm = frame.state._targeting_on_confirm
                frame.state._targeting_on_confirm = None
                frame.state._targeting_on_cancel = None
                frame.state._targeting_valid_targets = []
                frame.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
                frame._render_board()
                frame._render_info()
                if on_confirm:
                    on_confirm(clicked_target)
            else:
                self.flash_invalid_at(target)
                frame.hint_label.config(text="点击的不是合法目标", fg=UI_THEME["danger"])
                frame.after(500, lambda: frame.hint_label.config(fg=UI_THEME["accent"]) if frame.hint_label else None)
            return

        if isinstance(frame.state.selected_card, MinionCard):
            if target in frame.state.valid_targets:
                self.submit_play(frame.state.selected_card_idx + 1, target)
            else:
                self.flash_invalid_at(target)
                frame.hint_label.config(text="点击的不是合法目标", fg=UI_THEME["danger"])
                frame.after(1000, self.reset_guide_hint)
            return
        clicked = None
        if frame.duel.game:
            clicked = frame.duel.game.board.get_minion_at(target)
        for t in frame.state.valid_targets:
            if t == target or (isinstance(t, Minion) and clicked is t):
                self.submit_play(frame.state.selected_card_idx + 1, t)
                return
        self.flash_invalid_at(target)
        frame.hint_label.config(text="点击的不是合法目标", fg=UI_THEME["danger"])
        frame.after(1000, self.reset_guide_hint)

    def submit_play(self, serial: int, target: Any) -> None:
        """提交出牌动作。"""
        frame = self.frame
        active = frame.duel.game.current_player if frame.duel.game else None
        card_name = "未知卡牌"
        is_conspiracy = False
        card = active._get_hand_card(serial) if active else None
        if card:
            card_name = card.name
            is_conspiracy = isinstance(card, Conspiracy)
            eff_cost = active._get_play_cost(card) if active else getattr(card, 'cost', None)
            if eff_cost and eff_cost.b >= 3:
                if not messagebox.askyesno("确认出牌", f"确定要打出 [{card.name}] 吗？\n费用: {eff_cost}"):
                    self.exit_targeting_mode(preserve_pending=True)
                    return
        sacrifices = getattr(frame.state, "_pending_sacrifices", None)
        self.exit_targeting_mode()
        action = {"type": "play", "serial": serial, "target": target}
        if sacrifices:
            action["sacrifices"] = sacrifices
            frame.state._pending_sacrifices = []
        frame._clear_selection()
        if is_conspiracy:
            frame._show_toast(f"阴谋 [{card_name}] 已暗中激活", UI_THEME["btn_secondary_bg"], 1500)
        frame.duel.submit_local_action(action)
        # 操作历史不再在这里写入，统一在 EVENT_CARD_PLAYED / EVENT_CONSPIRACY_TRIGGERED
        # 事件监听中写入，确保效果正式结算后才显示。
        frame.hint_label.config(text="已出牌，等待结果...")
        frame.after(2000, self.reset_guide_hint)

    def reset_guide_hint(self) -> None:
        """根据当前阶段恢复引导文字。"""
        frame = self.frame
        if not frame.duel.game or not frame.hint_label:
            return
        phase = frame.duel.game.current_phase
        if phase == "action":
            if frame.state._in_targeting_mode:
                frame.hint_label.config(text="指向模式：点击目标确认 | Enter确认 | ESC取消", fg=UI_THEME["danger"], font=("Microsoft YaHei", 12, "bold"))
            else:
                frame.hint_label.config(text="出牌阶段：点击手牌出牌 | 点击异象设攻击目标 | 双击拍铃/拉闸 | B拉闸 Space拍铃 | 1~9快捷选牌 | ESC取消", fg=UI_THEME["accent"], font=("Microsoft YaHei", 10))
        elif phase == "resolve":
            frame.hint_label.config(text="结算阶段进行中，请稍候...", fg=UI_THEME["danger_dark"], font=("Microsoft YaHei", 10))
        elif phase == "draw":
            frame.hint_label.config(text="抽牌阶段...", fg=UI_THEME["accent_dark"], font=("Microsoft YaHei", 10))

    def on_bell(self) -> None:
        """拍铃（委托给 ActionController）。"""
        self.frame.action_controller.on_bell()

    def on_brake(self) -> None:
        """拉闸（委托给 ActionController）。"""
        self.frame.action_controller.on_brake()

    def on_cancel(self) -> None:
        """取消当前选择/指向（委托给 ActionController）。"""
        self.frame.action_controller.on_cancel()
