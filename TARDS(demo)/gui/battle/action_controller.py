"""对战动作控制器。

负责拍铃、拉闸、取消、终止、矿物/松鼠兑换、矿物面板展开/收起、按钮可用性刷新。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any, Optional

from tards.data.card_db import DEFAULT_REGISTRY, CardType
from tards.net.net_game import NetworkDuel
from gui.theme import UI_THEME


class ActionController:
    """管理对战界面中玩家可执行的动作按钮与兑换逻辑。"""

    def __init__(self, frame: Any):
        self.frame = frame

    # ------------------------------------------------------------------
    # 主操作按钮
    # ------------------------------------------------------------------
    def on_bell(self) -> None:
        """拍铃。"""
        frame = self.frame
        if getattr(frame.state, "_is_belling", False):
            return
        frame.state._is_belling = True
        frame.after(500, lambda: setattr(frame.state, "_is_belling", False))
        active = frame.duel.game and frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        frame._clear_selection()
        frame.duel.submit_local_action({"type": "bell"})
        frame.event_history_controller.add_history("拍铃")
        frame.hint_label.config(text="拍铃")
        frame.after(1500, frame.input_controller.reset_guide_hint)

    def on_brake(self) -> None:
        """拉闸。"""
        frame = self.frame
        if getattr(frame.state, "_is_braking", False):
            return
        frame.state._is_braking = True
        frame.after(500, lambda: setattr(frame.state, "_is_braking", False))
        active = frame.duel.game and frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        frame._clear_selection()
        frame.duel.submit_local_action({"type": "brake"})
        frame.event_history_controller.add_history("拉闸")
        frame.hint_label.config(text="拉闸")
        frame.after(1500, frame.input_controller.reset_guide_hint)

    def on_cancel(self) -> None:
        """取消当前选择/指向。"""
        frame = self.frame
        if frame.state._in_sacrifice_mode:
            frame.input_controller.exit_sacrifice_mode()
            frame.input_controller._clear_selection()
            return
        if frame.state._in_targeting_mode:
            on_cancel = frame.state._targeting_on_cancel
            frame.input_controller.exit_targeting_mode()
            if on_cancel:
                on_cancel()
        else:
            frame.input_controller._clear_selection()

    def on_terminate_game(self) -> None:
        """终止当前对局并返回主菜单。"""
        frame = self.frame
        if frame.game_loop_controller.disconnect_handled:
            return
        frame.game_loop_controller.gameover_handled = True
        if messagebox.askyesno("终止游戏", "确定要终止当前对局吗？\n日志将保存到 logs/ 目录。"):
            if frame.duel.game:
                frame.duel.game.game_over = True
            frame.duel.force_terminate()
            thread = getattr(frame.state, "_game_thread", None)
            if thread and thread.is_alive():
                thread.join(timeout=2.0)
            log_info = "\n日志已保存到 logs/ 目录。"
            messagebox.showinfo("游戏已终止", f"对局已手动终止。{log_info}")
            frame.duel.close()
            frame.app.show_menu()

    # ------------------------------------------------------------------
    # 兑换
    # ------------------------------------------------------------------
    def on_toggle_squirrel_draw(self) -> None:
        """切换抽松鼠选项。"""
        frame = self.frame
        active = frame.duel.game and frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        active.squirrel_draw_enabled = frame.squirrel_draw_var.get()
        state = "开启" if active.squirrel_draw_enabled else "关闭"
        print(f"  {active.name} 抽松鼠选项已{state}")

    def on_exchange_squirrel(self) -> None:
        """兑换松鼠。"""
        frame = self.frame
        active = frame.duel.game and frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        from tards.data.card_db import Pack
        if active.immersion_points.get(Pack.UNDERWORLD, 0) < 2:
            messagebox.showinfo("兑换松鼠", "你需要至少2级冥刻沉浸度才能兑换松鼠")
            return
        if active.squirrel_exchanged_this_turn:
            messagebox.showinfo("兑换松鼠", "本回合已兑换过松鼠")
            return
        if not active.squirrel_deck:
            messagebox.showinfo("兑换松鼠", "松鼠牌堆已空")
            return
        if active.t_point < 1:
            messagebox.showinfo("兑换松鼠", "T点不足（需要1T）")
            return
        frame.duel.submit_local_action({"type": "exchange_squirrel"})
        frame.event_history_controller.add_history("兑换松鼠", is_play=True)

    def on_exchange_mineral(self, mineral_type: str) -> None:
        """按快捷键直接兑换指定矿物（I/G/D/M）。"""
        frame = self.frame
        active = frame.duel.game and frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        from tards.data.card_db import Pack
        if active.immersion_points.get(Pack.DISCRETE, 0) < 1:
            messagebox.showinfo("兑换矿物", "你没有离散沉浸度，无法兑换矿物")
            return

        target_name = None
        for name, card_def in DEFAULT_REGISTRY._cards.items():
            if card_def.card_type == CardType.MINERAL and card_def.mineral_type == mineral_type:
                tmp_card = card_def.to_game_card(active)
                if tmp_card.exchange_cost.can_afford(active):
                    target_name = name
                    break

        if not target_name:
            mineral_names = {"I": "铁锭", "G": "金锭", "D": "钻石", "M": "青金石"}
            messagebox.showinfo("兑换矿物", f"当前无法兑换{mineral_names.get(mineral_type, mineral_type)}")
            return

        self.do_exchange_mineral(target_name)

    def do_exchange_mineral(self, name: str) -> None:
        """直接兑换指定名称的矿物，收起展开面板。"""
        frame = self.frame
        active = frame.duel.game and frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        frame.duel.submit_local_action({"type": "exchange", "card_name": name})
        frame.event_history_controller.add_history(f"兑换矿物 [{name}]", is_play=True)
        frame.hint_label.config(text=f"已兑换 {name}")
        frame.after(1500, frame.input_controller.reset_guide_hint)
        if frame.mineral_bar.winfo_ismapped():
            frame.mineral_bar.pack_forget()
            frame.exchange_btn.config(bg="#fff9c4")

    def toggle_mineral_bar(self) -> None:
        """展开/收起矿物快捷兑换面板。"""
        frame = self.frame
        if frame.mineral_bar.winfo_ismapped():
            frame.mineral_bar.pack_forget()
            frame.exchange_btn.config(bg="#fff9c4")
        else:
            self.refresh_mineral_bar()
            frame.mineral_bar.pack(fill=tk.X, pady=(0, 5), before=frame.hint_label)
            frame.exchange_btn.config(bg="#fff59d")

    def refresh_mineral_bar(self) -> None:
        """根据当前玩家资源刷新4个矿物按钮的可用状态。"""
        frame = self.frame
        active = frame.duel.game and frame.duel.game.current_player
        if not active:
            for btn in frame.state._mineral_buttons.values():
                btn.config(state=tk.DISABLED, bg=UI_THEME["btn_secondary_active"], fg=UI_THEME["text_muted"])
            return

        from tards.data.card_db import Pack
        can_exchange = active.immersion_points.get(Pack.DISCRETE, 0) >= 1

        for mtype, btn in frame.state._mineral_buttons.items():
            target_name = None
            for name, card_def in DEFAULT_REGISTRY._cards.items():
                if card_def.card_type == CardType.MINERAL and card_def.mineral_type == mtype:
                    target_name = name
                    break
            if not target_name or not can_exchange:
                btn.config(state=tk.DISABLED, bg=UI_THEME["btn_secondary_active"], fg=UI_THEME["text_muted"])
                continue
            tmp_card = DEFAULT_REGISTRY.get(target_name).to_game_card(active)
            if tmp_card.exchange_cost.can_afford(active):
                btn.config(state=tk.NORMAL, bg="#fef3c7", fg=UI_THEME["res_mineral"])
            else:
                btn.config(state=tk.DISABLED, bg=UI_THEME["btn_secondary_active"], fg=UI_THEME["text_muted"])

    # ------------------------------------------------------------------
    # 按钮状态
    # ------------------------------------------------------------------
    def set_btn_disabled(self, btn: tk.Button) -> None:
        """将按钮设为不可用并显示灰色。"""
        btn.config(state=tk.DISABLED, bg=UI_THEME["btn_secondary_active"], fg=UI_THEME["text_muted"])

    def set_btn_enabled(self, btn: tk.Button, bg: str, fg: str) -> None:
        """将按钮设为可用并恢复指定配色。"""
        btn.config(state=tk.NORMAL, bg=bg, fg=fg)

    def refresh_action_buttons(self) -> None:
        """根据当前游戏状态启用/禁用拍铃、拉闸、取消选择、终止按钮。"""
        frame = self.frame
        game = frame.duel.game
        if not game or not game.current_player:
            self.set_btn_disabled(frame.bell_btn)
            self.set_btn_disabled(frame.brake_btn)
            self.set_btn_disabled(frame.cancel_btn)
            self.set_btn_disabled(frame.terminate_btn)
            return

        active = game.current_player
        phase = game.current_phase
        is_local_turn = (not frame.duel.is_remote) or active == frame.local_player
        opponent = game.p2 if active == game.p1 else game.p1

        self.set_btn_enabled(frame.terminate_btn,
                             bg=UI_THEME["btn_danger_bg"], fg=UI_THEME["btn_danger_fg"])

        can_cancel = (frame.state._in_sacrifice_mode or frame.state._in_targeting_mode
                      or frame.state.selected_card_idx is not None)
        if can_cancel:
            self.set_btn_enabled(frame.cancel_btn,
                                 bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"])
        else:
            self.set_btn_disabled(frame.cancel_btn)

        can_act = is_local_turn and phase == "action" and not active.braked
        if can_act:
            self.set_btn_enabled(frame.brake_btn,
                                 bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"])
            if opponent.braked:
                self.set_btn_disabled(frame.bell_btn)
            else:
                self.set_btn_enabled(frame.bell_btn,
                                     bg=UI_THEME["btn_warning_bg"], fg=UI_THEME["btn_warning_fg"])
        else:
            self.set_btn_disabled(frame.bell_btn)
            self.set_btn_disabled(frame.brake_btn)
