"""游戏循环控制器。

负责游戏线程启动、全局 gui_refresh_event 协调、刷新轮询、启动看门狗、胜负/断线/终止处理。
"""

from __future__ import annotations

import sys
import threading
import time
from tkinter import messagebox
from typing import Any, Optional

import tkinter as tk

from local_duel import LocalDuel
from tards.core.game_logger import GameLogger
from tards.constants import EVENT_CARD_PLAYED, EVENT_MINERAL_EXCHANGED
from tards.cards import MinionCard, Strategy, MineralCard
from gui.theme import UI_THEME


gui_refresh_event = threading.Event()


class GameLoopController:
    """管理游戏线程与 UI 刷新循环。"""

    def __init__(self, frame: Any):
        self.frame = frame
        self.disconnect_handled = False
        self.gameover_handled = False
        self._startup_timeout_warned = False
        self._battle_frame_created_at = time.time()

    # ------------------------------------------------------------------
    # 启动游戏线程
    # ------------------------------------------------------------------
    def start_game_thread(self) -> None:
        """启动后台游戏线程并注册回调。"""
        frame = self.frame
        gui_refresh_event.clear()
        frame.state._prev_hand_card_ids.clear()
        frame.state._prev_res_values.clear()
        frame.state._last_discarded_info.clear()
        frame.state._history_phase = None
        frame.state._history_action_counter = 0
        frame.state._last_public_actions.clear()
        frame.state._public_action_listeners_registered = False
        frame.reveal_controller.reset()

        frame.duel.local_turn_callback = lambda: gui_refresh_event.set()
        frame.duel.resolve_column_delay = 1.0
        frame.duel.game_over_callback = lambda winner: frame.after(0, lambda: self.on_gameover(winner))
        frame.duel.disconnect_callback = lambda: frame.after(0, self.on_disconnect)
        frame.duel.discover_request_callback = lambda names: frame.after(0, lambda: frame._show_discover(names))
        frame.duel.choice_request_callback = lambda options, title: frame.after(0, lambda: frame._show_choice(options, title))
        frame.duel.targeting_request_callback = lambda req, vt: frame.after(0, lambda: frame._show_targeting(req, vt))
        frame.duel.mulligan_request_callback = lambda player: frame.after(0, lambda: frame.mulligan_controller.show(player))
        frame.local_player.sacrifice_chooser = frame._make_sacrifice_chooser()
        frame.opponent.sacrifice_chooser = frame._make_sacrifice_chooser()

        def run() -> None:
            logger: Optional[GameLogger] = None
            try:
                is_local = isinstance(frame.duel._duel, LocalDuel)

                def ui_callback(line: str):
                    frame.after(0, lambda l=line: frame._log(l))

                logger = GameLogger.create_for_battle(ui_callback=ui_callback if is_local else None)
                frame._log_path = getattr(logger, "file_path", None)
                print("[GameThread] 游戏线程启动，准备运行 duel.run_game", file=sys.stderr)
                frame.duel.resolve_step_callback = lambda: (
                    gui_refresh_event.set(),
                    time.sleep(0.4),
                )
                frame.duel.run_game(frame.opponent, logger=logger)
                print("[GameThread] duel.run_game 已返回", file=sys.stderr)
            except Exception as e:
                import traceback
                error_msg = f"游戏线程异常: {e}\n{traceback.format_exc()}"
                print(error_msg, file=sys.stderr)
                if logger:
                    try:
                        logger.log_error(error_msg)
                    except Exception:
                        pass
                frame.after(0, lambda: messagebox.showerror("游戏错误", error_msg))
            finally:
                frame.duel.resolve_step_callback = None
                if logger:
                    try:
                        logger.close()
                    except Exception:
                        pass

        frame.state._game_thread = threading.Thread(target=run, daemon=True)
        frame.state._game_thread.start()

    # ------------------------------------------------------------------
    # 公开操作追踪（用于替换“等待玩家行动”提示）
    # ------------------------------------------------------------------
    @staticmethod
    def _format_card_action(event: Any) -> Optional[str]:
        """把 card_played 事件转换成“玩家 动作 卡牌”文本。"""
        player = event.data.get("player")
        card = event.data.get("card")
        if not player or not card:
            return None
        if isinstance(card, MinionCard):
            verb = "部署"
        elif isinstance(card, (Strategy, MineralCard)):
            verb = "使用"
        else:
            verb = "打出"
        return f"{player.name} {verb} {card.name}"

    def _register_public_action_listeners(self) -> None:
        """注册事件监听器，记录每位玩家最近一次公开操作。"""
        game = self.frame.duel.game if self.frame.duel else None
        if not game or self.frame.state._public_action_listeners_registered:
            return

        def on_card_played(event: Any) -> None:
            text = self._format_card_action(event)
            if text:
                self.frame.state._last_public_actions[event.data.get("player")] = text

        def on_mineral_exchanged(event: Any) -> None:
            player = event.data.get("player")
            card = event.data.get("card")
            if player and card:
                self.frame.state._last_public_actions[player] = f"{player.name} 兑换 {card.name}"

        game.register_listener(EVENT_CARD_PLAYED, on_card_played)
        game.register_listener(EVENT_MINERAL_EXCHANGED, on_mineral_exchanged)
        self.frame.state._public_action_listeners_registered = True

    # ------------------------------------------------------------------
    # 刷新循环
    # ------------------------------------------------------------------
    def schedule_refresh(self) -> None:
        """每 200ms 调度一次刷新。"""
        frame = self.frame
        try:
            self.try_refresh()
        except Exception as e:
            print(f"[_schedule_refresh] 异常: {e}")
            import traceback
            traceback.print_exc()
        try:
            frame.reveal_controller.try_show()
        except Exception as e:
            print(f"[_schedule_refresh] _try_show_reveal 异常: {e}")
            import traceback
            traceback.print_exc()
        try:
            frame.event_history_controller.expire_recent_events()
        except Exception as e:
            print(f"[_schedule_refresh] _expire_recent_events 异常: {e}")
            import traceback
            traceback.print_exc()
        frame.after(200, self.schedule_refresh)

    def try_refresh(self) -> None:
        """尝试刷新 UI 并更新阶段指示器。"""
        frame = self.frame
        try:
            if not frame.state._reveal_listeners_registered:
                if frame.duel and frame.duel.game:
                    frame.reveal_controller.register(frame.duel.game)
                    frame.state._reveal_listeners_registered = True
            self._register_public_action_listeners()

            need_refresh = gui_refresh_event.is_set() or frame.duel.is_remote
            if need_refresh:
                gui_refresh_event.clear()
                try:
                    frame._render_info()
                except Exception as e:
                    print(f"[_try_refresh] _render_info 异常: {e}")
                    import traceback
                    traceback.print_exc()
                try:
                    frame._render_board()
                except Exception as e:
                    print(f"[_try_refresh] _render_board 异常: {e}")
                    import traceback
                    traceback.print_exc()
                try:
                    frame._render_hand()
                except Exception as e:
                    print(f"[_try_refresh] _render_hand 异常: {e}")
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            print(f"[_try_refresh] 外层异常: {e}")
            import traceback
            traceback.print_exc()

        if frame.mulligan_controller.is_active() and frame.duel.game and frame.duel.game.current_turn > 0:
            frame.mulligan_controller.hide()

        if frame.duel.game and frame.duel.game.current_turn > 0:
            phase_map = {
                "draw": "抽牌阶段",
                "action": "出牌阶段",
                "resolve": "结算阶段",
                "start": "结算阶段开始",
                "end": "结算阶段结束",
            }
            phase_text = phase_map.get(frame.duel.game.current_phase, frame.duel.game.current_phase or "")
            turn = frame.duel.game.current_turn
            phase = frame.duel.game.current_phase

            active = frame.duel.game.current_player
            if not active:
                status_text = "游戏加载中..."
            elif frame.duel.is_remote:
                if active == frame.local_player:
                    status_text = "轮到你的行动"
                else:
                    remote_state = frame.duel._remote_decision_state
                    state_text = {
                        "discover": "正在开发...",
                        "choice": "正在抉择...",
                        "targeting": "正在选择目标...",
                        "mulligan": "正在调整手牌...",
                    }.get(remote_state, None)
                    if state_text is None:
                        action = frame.state._last_public_actions.get(active)
                        status_text = action if action else f"等待 {active.name} 行动"
                    else:
                        status_text = f"等待 {active.name} {state_text}"
            else:
                status_text = f"轮到 {active.name} 行动"

            display_text = f"回合 {turn} | {phase_text} | {status_text}"
            if phase == "resolve":
                frame.phase_label.config(text=display_text, bg=UI_THEME["btn_danger_bg"], fg=UI_THEME["btn_danger_fg"], font=("Microsoft YaHei", 12, "bold"))
            elif phase == "action":
                frame.phase_label.config(text=display_text, bg="#dcfce7", fg=UI_THEME["success_dark"], font=("Microsoft YaHei", 12, "bold"))
            else:
                frame.phase_label.config(text=display_text, bg=UI_THEME["bg_main"], fg=UI_THEME["danger"], font=("Microsoft YaHei", 12, "bold"))
            frame.app.root.title(f"Tards 对战 - 回合{turn} {phase_text}")
        else:
            if frame.duel.game is None:
                elapsed = time.time() - self._battle_frame_created_at
                if elapsed > 10 and not self._startup_timeout_warned:
                    self._startup_timeout_warned = True
                    diag = f"[StartupWatchdog] 游戏线程 {elapsed:.1f}s 仍未创建 Game 对象"
                    print(diag, file=sys.stderr)
                    thread = getattr(frame.state, "_game_thread", None)
                    if thread:
                        print(f"[StartupWatchdog] game_thread alive={thread.is_alive()}", file=sys.stderr)
                    frame.phase_label.config(text="游戏启动超时，请检查控制台日志或终止重试")
                else:
                    frame.phase_label.config(text="等待游戏开始...")
            else:
                frame.phase_label.config(text="等待游戏开始...")
            frame.app.root.title("Tards 对战 - 等待游戏开始")

        from tards.data.card_db import Pack
        if frame.duel.game and frame.duel.game.current_player:
            current = frame.duel.game.current_player
            has_discrete = current.immersion_points.get(Pack.DISCRETE, 0) >= 1
            has_underworld = current.immersion_points.get(Pack.UNDERWORLD, 0) >= 2
            if has_discrete:
                frame.exchange_btn.pack(side=tk.LEFT, padx=5)
            else:
                frame.exchange_btn.pack_forget()
            if has_underworld:
                frame.exchange_squirrel_btn.pack(side=tk.LEFT, padx=5)
                can_squirrel = (current.t_point >= 1 and
                                not current.squirrel_exchanged_this_turn and
                                current.squirrel_deck)
                if can_squirrel:
                    frame.exchange_squirrel_btn.config(state=tk.NORMAL, bg="#fff9c4", fg="#f57f17")
                else:
                    frame.exchange_squirrel_btn.config(state=tk.DISABLED, bg="#eeeeee", fg="#9e9e9e")
            else:
                frame.exchange_squirrel_btn.pack_forget()
        elif frame.local_player:
            has_discrete = frame.local_player.immersion_points.get(Pack.DISCRETE, 0) >= 1
            has_underworld = frame.local_player.immersion_points.get(Pack.UNDERWORLD, 0) >= 2
            if has_discrete:
                frame.exchange_btn.pack(side=tk.LEFT, padx=5)
            else:
                frame.exchange_btn.pack_forget()
            if has_underworld:
                frame.exchange_squirrel_btn.pack(side=tk.LEFT, padx=5)
                can_squirrel = (frame.local_player.t_point >= 1 and
                                not frame.local_player.squirrel_exchanged_this_turn and
                                frame.local_player.squirrel_deck)
                if can_squirrel:
                    frame.exchange_squirrel_btn.config(state=tk.NORMAL, bg="#e3f2fd", fg="#1565c0")
                else:
                    frame.exchange_squirrel_btn.config(state=tk.DISABLED, bg="#eeeeee", fg="#9e9e9e")
            else:
                frame.exchange_squirrel_btn.pack_forget()
        else:
            frame.exchange_btn.pack_forget()
            frame.exchange_squirrel_btn.pack_forget()

        frame.action_controller.refresh_mineral_bar()
        frame.action_controller.refresh_action_buttons()

    # ------------------------------------------------------------------
    # 胜负 / 断线
    # ------------------------------------------------------------------
    def on_gameover(self, winner_name: Optional[str]) -> None:
        """游戏结束回调。"""
        if self.gameover_handled or self.disconnect_handled:
            return
        self.gameover_handled = True
        self.disconnect_handled = True
        msg = f"游戏结束！胜者: {winner_name}" if winner_name else "游戏结束：平局"
        messagebox.showinfo("对战结束", msg)
        self.frame.duel.close()
        self.frame.app.show_menu()

    def on_disconnect(self) -> None:
        """对手断开连接时安全退出到主菜单。"""
        if self.disconnect_handled:
            return
        self.disconnect_handled = True
        frame = self.frame
        if frame.duel.game:
            frame.duel.game.game_over = True
        frame.duel.force_terminate()
        thread = getattr(frame.state, "_game_thread", None)
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        if self.gameover_handled or (frame.duel.game and frame.duel.game.game_over):
            self.gameover_handled = True
            frame.duel.close()
            frame.app.show_menu()
            return
        messagebox.showinfo("连接断开", "与对手的连接已断开，返回主菜单。")
        frame.duel.close()
        frame.app.show_menu()
