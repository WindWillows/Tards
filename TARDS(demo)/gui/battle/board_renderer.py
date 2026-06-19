"""棋盘渲染器。

负责绘制棋盘网格、异象头像、关键词/状态条等纯 UI 渲染逻辑，
使 BattleFrame 专注于输入控制与状态协调。
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

import tkinter as tk

from tards import Minion, MinionCard, Strategy
from tards.assets import get_asset_manager
from gui.theme import UI_THEME
from gui.battle.render_utils import (
    create_minion_portrait_photo,
    get_minion_attack_color,
    get_minion_hp_color,
    interpolate_color,
)


class BoardRenderer:
    """棋盘渲染器：封装棋盘、异象头像、关键词条的绘制。"""

    def __init__(
        self,
        canvas: tk.Canvas,
        cell_size: int,
        board_offset_x: int,
        board_offset_y: int,
        col_names: list,
        minion_size: int,
        minion_corner_leg: int,
        keyword_box: int,
        keyword_gap: int,
        display_row_fn: Callable[[int], int],
    ):
        self.canvas = canvas
        self.cell_size = cell_size
        self.board_offset_x = board_offset_x
        self.board_offset_y = board_offset_y
        self.col_names = col_names
        self.minion_size = minion_size
        self.minion_corner_leg = minion_corner_leg
        self.keyword_box = keyword_box
        self.keyword_gap = keyword_gap
        self.display_row_fn = display_row_fn

        self.tile_image_refs: Dict[Any, Any] = {}
        self.minion_image_refs: Dict[str, Any] = {}

    def update_dimensions(
        self,
        cell_size: int,
        board_offset_x: int,
        board_offset_y: int,
    ) -> None:
        """当 Canvas 大小变化时更新棋盘尺寸。"""
        self.cell_size = cell_size
        self.board_offset_x = board_offset_x
        self.board_offset_y = board_offset_y

    def clear_minion_refs(self) -> None:
        """重新渲染异象前清空图片引用。"""
        self.minion_image_refs.clear()

    def draw_grid(self) -> None:
        """绘制 5×5 棋盘网格与列标签。"""
        am = get_asset_manager()
        # 清理旧网格（避免 resize 时重叠绘制）
        self.canvas.delete("board_grid")
        for r in range(5):
            for c in range(5):
                self.canvas.delete(f"cell_{r}_{c}")
        self.tile_image_refs.clear()

        # 半场渐变配色（从上到下）：敌方淡蓝、中立纯白、友方暖黄
        GRADIENT_STEPS = 10
        row_top_colors = {
            0: UI_THEME["board_enemy_top"],
            1: UI_THEME["board_enemy_top"],
            2: UI_THEME["board_neutral"],
            3: UI_THEME["board_friendly_top"],
            4: UI_THEME["board_friendly_top"],
        }
        row_bottom_colors = {
            0: UI_THEME["board_enemy_bottom"],
            1: UI_THEME["board_enemy_bottom"],
            2: UI_THEME["board_neutral"],
            3: UI_THEME["board_friendly_bottom"],
            4: UI_THEME["board_friendly_bottom"],
        }

        for logic_r in range(5):
            for c in range(5):
                display_r = self.display_row_fn(logic_r)
                x1 = c * self.cell_size + self.board_offset_x
                y1 = display_r * self.cell_size + self.board_offset_y
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                terrain_id = None
                if display_r in (0, 1):
                    terrain_id = "terrain_enemy"
                elif display_r == 2:
                    terrain_id = "terrain_neutral"
                elif display_r in (3, 4):
                    terrain_id = "terrain_friendly"

                # 绘制垂直渐变背景（用细条模拟）
                top_c = row_top_colors[display_r]
                bot_c = row_bottom_colors[display_r]
                step_h = self.cell_size / GRADIENT_STEPS
                for i in range(GRADIENT_STEPS):
                    t = i / GRADIENT_STEPS
                    color = interpolate_color(top_c, bot_c, t)
                    sy1 = int(y1 + i * step_h)
                    sy2 = int(y1 + (i + 1) * step_h)
                    self.canvas.create_rectangle(
                        x1, sy1, x2, sy2, fill=color, outline="",
                        tags=f"cell_{logic_r}_{c}",
                    )

                # 尝试加载地形纹理（覆盖在渐变之上，半透明）
                if terrain_id:
                    tile = am.get_board_tile(terrain_id, self.cell_size)
                    if tile:
                        self.tile_image_refs[(logic_r, c)] = tile
                        self.canvas.create_image(
                            x1 + self.cell_size // 2, y1 + self.cell_size // 2,
                            image=tile, tags=f"cell_{logic_r}_{c}",
                        )

                # 格子边框（内阴影感）
                self.canvas.create_rectangle(
                    x1, y1, x2, y2, outline=UI_THEME["board_line"], width=1,
                    tags=f"cell_{logic_r}_{c}",
                )

        # 列名标签（带主题色底）
        col_label_colors = UI_THEME["board_label_bg"]
        for c, name in enumerate(self.col_names):
            x1 = c * self.cell_size + self.board_offset_x
            x2 = x1 + self.cell_size
            label_y = 5 * self.cell_size + self.board_offset_y
            label_bg = col_label_colors[c % len(col_label_colors)]
            self.canvas.create_rectangle(
                x1, label_y, x2, label_y + 22, fill=label_bg,
                outline=UI_THEME["border_strong"], width=1, tags="board_grid",
            )
            self.canvas.create_text(
                x1 + self.cell_size // 2, label_y + 11, text=name, anchor=tk.CENTER,
                font=("Microsoft YaHei", 10, "bold"), fill=UI_THEME["board_label_text"],
                tags="board_grid",
            )

    def draw_minion_portrait(
        self,
        cx: int,
        cy: int,
        m: "Minion",  # type: ignore[name-defined]
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        tag: str,
        is_enemy: bool = False,
    ) -> None:
        """绘制 3 号区域：淡色渐变背景 + 异象名称。敌方左下角裁掉小三角。"""
        size = x2 - x1
        bg_colors = (UI_THEME["minion_bg_top"], UI_THEME["minion_bg_bottom"])

        photo = create_minion_portrait_photo(
            size, bg_colors[0], bg_colors[1],
            is_enemy=is_enemy, corner_leg=self.minion_corner_leg,
        )
        if photo:
            ref_key = f"{tag}_portrait"
            self.minion_image_refs[ref_key] = photo
            self.canvas.create_image(
                (x1 + x2) // 2, (y1 + y2) // 2,
                image=photo, tags=(tag, "minion", "portrait"),
            )
        else:
            # PIL 不可用时回退：绘制多边形
            if is_enemy:
                points = [
                    x1, y1, x2, y1, x2, y2, x1 + self.minion_corner_leg, y2,
                    x1, y2 - self.minion_corner_leg,
                ]
            else:
                points = [x1, y1, x2, y1, x2, y2, x1, y2]
            self.canvas.create_polygon(
                points, fill=UI_THEME["minion_bg"], outline="",
                tags=(tag, "minion", "portrait"),
            )

        # 名称（自动换行，限制在 3 号区域内）
        self.canvas.create_text(
            (x1 + x2) // 2, (y1 + y2) // 2, text=m.name,
            fill="black", font=("Microsoft YaHei", 9, "bold"),
            width=max(10, size - 8), justify=tk.CENTER,
            tags=(tag, "minion", "portrait_text"),
        )

    def _get_visible_keywords(
        self,
        m: "Minion",  # type: ignore[name-defined]
    ) -> List[Tuple[str, Any]]:
        """返回应显示在关键词条区域的有效词条/状态列表（已按优先级排序）。"""
        priority = {
            "恐惧": 0, "冰冻": 0, "眩晕": 0, "休眠": 0,
            "亡语": 1, "迅捷": 1, "潜行": 1, "潜水": 1,
            "成长": 2, "视野": 3, "高频": 3, "先攻": 3,
        }
        active = []
        for k, v in m.display_keywords.items():
            if v is False or v is None:
                continue
            if isinstance(v, int) and v == 0:
                continue
            # 默认值为 1 的“丰饶/献祭”不显示
            if k in ("丰饶", "献祭") and v == 1:
                continue
            active.append((k, v))
        active.sort(key=lambda x: priority.get(x[0], 99))
        return active

    def draw_minion_keyword_bar(
        self,
        cx: int,
        cy: int,
        m: "Minion",  # type: ignore[name-defined]
        tag: str,
    ) -> None:
        """绘制 4 号区域：附着在正方形右侧外部的小方框，每个词条/状态一个字。"""
        r = self.minion_size // 2
        box = self.keyword_box
        gap = self.keyword_gap
        start_x = cx + r + gap
        start_y = cy - r

        active = self._get_visible_keywords(m)

        # 词条/状态配色（背景，前景文字）
        keyword_styles = {
            "恐惧": (UI_THEME["kw_fear"], "white"),
            "冰冻": (UI_THEME["kw_frozen"], "white"),
            "眩晕": (UI_THEME["kw_stun"], "white"),
            "休眠": (UI_THEME["kw_dormant"], "white"),
            "亡语": (UI_THEME["kw_deathrattle"], "white"),
            "迅捷": (UI_THEME["kw_swift"], "white"),
            "潜水": (UI_THEME["kw_dive"], "white"),
            "潜行": (UI_THEME["kw_stealth"], "white"),
            "成长": (UI_THEME["kw_grow"], "white"),
            "视野": (UI_THEME["kw_vision"], "black"),
            "高频": (UI_THEME["kw_multi"], "white"),
            "防空": (UI_THEME["kw_anti_air"], "white"),
            "尖刺": (UI_THEME["kw_thorns"], "black"),
            "穿刺": (UI_THEME["kw_pierce"], "white"),
            "串击": (UI_THEME["kw_chain"], "white"),
            "横扫": (UI_THEME["kw_sweep"], "white"),
            "丰饶": (UI_THEME["kw_fertility"], "white"),
            "献祭": (UI_THEME["kw_sacrifice"], "white"),
            "协同": (UI_THEME["kw_synergy"], "white"),
            "独行": (UI_THEME["kw_solo"], "white"),
        }
        default_style = (UI_THEME["minion_bar_bg"], "black")

        am = get_asset_manager()
        # 按可用高度截断
        max_boxes = max(1, self.minion_size // (box + gap))
        for i, (k, v) in enumerate(active[:max_boxes]):
            x1 = start_x
            y1 = start_y + i * (box + gap)
            x2 = x1 + box
            y2 = y1 + box
            icon = am.get_icon(k, box)
            if icon is not None:
                # 像素图标优先显示，保留引用防止被 GC
                ref_key = f"{tag}_kw_{i}"
                self.minion_image_refs[ref_key] = icon
                self.canvas.create_image(
                    x1, y1, image=icon, anchor=tk.NW,
                    tags=(tag, "minion", "keyword_icon"),
                )
            else:
                bg, fg = keyword_styles.get(k, default_style)
                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=bg, outline=UI_THEME["border"], width=1,
                    tags=(tag, "minion", "keyword_box"),
                )
                self.canvas.create_text(
                    (x1 + x2) // 2, (y1 + y2) // 2, text=k[0],
                    fill=fg, font=("Microsoft YaHei", 8, "bold"),
                    tags=(tag, "minion", "keyword_text"),
                )

            # 层数/计数徽章（图标右侧，不遮挡图标主体；布尔值只显示图标，不显示 true）
            if type(v) is int and v >= 1:
                badge_font = ("Microsoft YaHei", max(6, box // 2 - 1), "bold")
                # 黑色阴影增加可读性
                self.canvas.create_text(
                    x2 + 2, y2, text=str(v), anchor=tk.SW,
                    fill="black", font=badge_font,
                    tags=(tag, "minion", "keyword_badge_shadow"),
                )
                self.canvas.create_text(
                    x2 + 1, y2 - 1, text=str(v), anchor=tk.SW,
                    fill="white", font=badge_font,
                    tags=(tag, "minion", "keyword_badge_text"),
                )

    # ------------------------------------------------------------------
    # 棋盘整体渲染
    # ------------------------------------------------------------------
    def render_board(self, frame: Any) -> None:
        """绘制整个棋盘：异象、指示器、预设连线、高亮等。"""
        # 如果当前浮窗对应的异象已离开战场，自动隐藏浮窗
        if frame._tooltip_source and isinstance(frame._tooltip_source, Minion):
            if frame._tooltip_source not in frame.duel.game.board.minion_place.values():
                frame._hide_tooltip()

        self.canvas.delete("minion")
        self.canvas.delete("target_hint")
        self.canvas.delete("deploy_preview")
        self.canvas.delete("resolve_column_highlight")
        self.canvas.delete("recent_event_highlight")
        if not frame.duel.game:
            return

        self.clear_minion_refs()
        game = frame.duel.game
        local_player = frame.local_player
        cell_size = self.cell_size
        offset_x = self.board_offset_x
        offset_y = self.board_offset_y
        minion_size = self.minion_size
        r = minion_size // 2
        bh = frame.MINION_STAT_BAR_HEIGHT
        slant = frame.MINION_STAT_BAR_SLANT

        def _stat_bar_width(text) -> int:
            return max(21, len(str(text)) * 9 + 11)

        def _cell_center(logic_r: int, c: int):
            display_r = self.display_row_fn(logic_r)
            cx = c * cell_size + cell_size // 2 + offset_x
            cy = display_r * cell_size + cell_size // 2 + offset_y
            return cx, cy, display_r

        # 绘制每个异象
        for (logic_r, c), m in game.board.minion_place.items():
            cx, cy, display_r = _cell_center(logic_r, c)
            tag = f"minion_{logic_r}_{c}"

            # 只有当有异象需要展示右侧关键词条时，才向左偏移以腾出空间
            if self._get_visible_keywords(m):
                cx += frame.MINION_OFFSET_X

            # 清除该 tag 上所有旧事件绑定
            for seq in ("<Enter>", "<Leave>", "<Motion>", "<Button-1>", "<Double-Button-1>"):
                self.canvas.tag_unbind(tag, seq)

            is_enemy = m.owner.side != local_player.side

            # 3 号区域：淡色渐变背景 + 名称
            self.draw_minion_portrait(
                cx, cy, m, cx - r, cy - r, cx + r, cy + r, tag,
                is_enemy=is_enemy,
            )

            # 1 号区域：左上角攻击栏
            atk_w = _stat_bar_width(m.attack)
            atk_color = get_minion_attack_color(m)
            atk_points = [
                cx - r, cy - r,
                cx - r + atk_w, cy - r,
                cx - r + atk_w - slant, cy - r + bh,
                cx - r, cy - r + bh,
            ]
            self.canvas.create_polygon(atk_points, fill=atk_color, outline="",
                                       tags=(tag, "minion", "atk_bar"))
            atk_cx = cx - r + atk_w / 2 - slant / 4
            atk_cy = cy - r + bh / 2 - 1
            self.canvas.create_text(atk_cx, atk_cy, text=str(m.attack), fill="black",
                                    font=("Small Fonts", 11, "bold"),
                                    tags=(tag, "minion", "atk_text"))

            # 2 号区域：右下角 HP 栏
            hp_w = _stat_bar_width(m.health)
            hp_color = get_minion_hp_color(m)
            hp_points = [
                cx + r - hp_w + slant, cy + r - bh,
                cx + r, cy + r - bh,
                cx + r, cy + r,
                cx + r - hp_w, cy + r,
            ]
            self.canvas.create_polygon(hp_points, fill=hp_color, outline="",
                                       tags=(tag, "minion", "hp_bar"))
            hp_cx = cx + r - hp_w / 2 + slant / 4
            hp_cy = cy + r - bh / 2 - 1
            self.canvas.create_text(hp_cx, hp_cy, text=str(m.health), fill="black",
                                    font=("Small Fonts", 11, "bold"),
                                    tags=(tag, "minion", "hp_text"))

            # 4 号区域：关键词/状态小方框
            self.draw_minion_keyword_bar(cx, cy, m, tag)

            # 事件绑定
            self.canvas.tag_bind(tag, "<Enter>",
                                 lambda e, mm=m: (frame._show_minion_tooltip(e, mm), frame._update_detail_text(mm)))
            self.canvas.tag_bind(tag, "<Leave>", lambda e: frame._hide_tooltip())
            self.canvas.tag_bind(tag, "<Motion>", lambda e: frame._move_tooltip(e.x_root, e.y_root))
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, mm=m: frame._on_minion_click(mm))
            self.canvas.tag_bind(tag, "<Double-Button-1>", lambda e, mm=m: frame._on_minion_double_click(mm))

            # 指向模式：合法目标高亮
            if frame._in_targeting_mode and m in frame._targeting_valid_targets:
                self.canvas.create_rectangle(cx - 32, cy - 27, cx + 32, cy + 27,
                                             outline=UI_THEME["card_border_target"], width=4,
                                             tags="target_hint")

            # 献祭模式：合法祭品黄框，已选祭品绿框，左上角显示丰饶等级
            if frame._in_sacrifice_mode and m in frame._sacrifice_candidates:
                color = UI_THEME["success"] if m in frame._selected_sacrifices else UI_THEME["card_border_target"]
                self.canvas.create_rectangle(cx - 32, cy - 27, cx + 32, cy + 27,
                                             outline=color, width=4, tags="target_hint")
                fertility = m.keywords.get("丰饶", 1)
                self.canvas.create_oval(cx - 30, cy - 26, cx - 18, cy - 14,
                                        fill=UI_THEME["danger"], outline="white", width=1,
                                        tags=(tag, "minion", "sacrifice_fertility"))
                self.canvas.create_text(cx - 24, cy - 20, text=str(fertility), fill="white",
                                        font=("Microsoft YaHei", 9, "bold"),
                                        tags=(tag, "minion", "sacrifice_fertility"))

            # 待设置攻击目标次数
            stars = frame._get_minion_pending_stars(m)
            if stars > 0:
                self.canvas.create_text(cx + 22, cy - 18, text=str(stars), fill=UI_THEME["kw_vision"],
                                        font=("Microsoft YaHei", 12, "bold"),
                                        tags=(tag, "minion", "pending_star"))

            # 清除攻击预设按钮
            pending = getattr(m, "_pending_attack_targets", None)
            if pending and isinstance(pending, list) and len(pending) > 0:
                clear_x, clear_y = cx + 22, cy + 18
                clear_tag = f"clear_pending_{logic_r}_{c}"
                self.canvas.tag_unbind(clear_tag, "<Button-1>")
                self.canvas.create_rectangle(clear_x - 6, clear_y - 6, clear_x + 6, clear_y + 6,
                                             fill=UI_THEME["danger"], outline="white", width=1,
                                             tags=(clear_tag, "minion"))
                self.canvas.create_text(clear_x, clear_y, text="×", fill="white",
                                        font=("Microsoft YaHei", 8, "bold"),
                                        tags=(clear_tag, "minion"))
                self.canvas.tag_bind(clear_tag, "<Button-1>",
                                     lambda e, pos=m.position: frame._clear_attack_targets(pos))

            # 清除效果预设按钮
            effect_pending = getattr(m, "_pending_effect_target", None)
            if effect_pending is not None:
                clear_x, clear_y = cx - 22, cy + 18
                clear_tag = f"clear_effect_{logic_r}_{c}"
                self.canvas.tag_unbind(clear_tag, "<Button-1>")
                self.canvas.create_rectangle(clear_x - 6, clear_y - 6, clear_x + 6, clear_y + 6,
                                             fill=UI_THEME["accent"], outline="white", width=1,
                                             tags=(clear_tag, "minion"))
                self.canvas.create_text(clear_x, clear_y, text="×", fill="white",
                                        font=("Microsoft YaHei", 8, "bold"),
                                        tags=(clear_tag, "minion"))
                self.canvas.tag_bind(clear_tag, "<Button-1>",
                                     lambda e, pos=m.position: frame._clear_effect_target(pos))

            # 可交互指示器（行动阶段可设置攻击目标）
            if (game.current_phase == "action"
                    and m.owner == game.current_player
                    and m.can_attack_this_turn(game.current_turn)):
                vision = m.keywords.get("视野", 0)
                multi = m.keywords.get("高频", 0)
                if vision > 0 or (isinstance(multi, int) and multi > 0):
                    self.canvas.create_oval(cx + 18, cy - 22, cx + 26, cy - 14,
                                            fill=UI_THEME["success"], outline="white", width=1,
                                            tags=(tag, "minion", "interactive_dot"))

            # 可交互指示器（行动阶段可设置效果目标）
            if (game.current_phase == "action"
                    and m.owner == game.current_player):
                scope_fn = getattr(m, '_effect_target_scope_fn', None)
                if scope_fn and getattr(m, '_pending_effect_target', None) is None:
                    self.canvas.create_oval(cx - 26, cy - 22, cx - 18, cy - 14,
                                            fill=UI_THEME["accent"], outline="white", width=1,
                                            tags=(tag, "minion", "interactive_dot"))

        # 攻击预设连线
        for (logic_r, c), m in game.board.minion_place.items():
            pending = getattr(m, "_pending_attack_targets", None)
            if not pending or not isinstance(pending, list):
                continue
            x1, y1, _ = _cell_center(logic_r, c)
            for target in pending:
                if hasattr(target, "position") and target.position:
                    t_logic_r, tc = target.position
                    x2, y2, _ = _cell_center(t_logic_r, tc)
                    self.canvas.create_line(x1, y1, x2, y2,
                                            fill=UI_THEME["kw_vision"], dash=(4, 4), width=2,
                                            arrow=tk.LAST, tags=("target_arrow", "minion"))

        # 效果预设连线（预输入阶段）
        for (logic_r, c), m in game.board.minion_place.items():
            pending = getattr(m, "_pending_effect_target", None)
            if pending is None:
                continue
            hidden = getattr(m, '_hidden_effect_pending', False)
            if hidden and m.owner != local_player:
                continue
            x1, y1, _ = _cell_center(logic_r, c)
            target = pending
            if hasattr(target, "position") and target.position:
                t_logic_r, tc = target.position
                x2, y2, _ = _cell_center(t_logic_r, tc)
                self.canvas.create_line(x1, y1, x2, y2,
                                        fill=UI_THEME["accent"], dash=(4, 4), width=2,
                                        arrow=tk.LAST, tags=("target_arrow", "minion"))

        # 已完成指向的锁定连线
        for (logic_r, c), m in game.board.minion_place.items():
            locked = getattr(m, "_ankang_locked_target", None)
            if locked is None:
                continue
            x1, y1, _ = _cell_center(logic_r, c)
            target = locked
            if hasattr(target, "position") and target.position:
                t_logic_r, tc = target.position
                x2, y2, _ = _cell_center(t_logic_r, tc)
                self.canvas.create_line(x1, y1, x2, y2,
                                        fill=UI_THEME["accent"], dash=(4, 4), width=2,
                                        arrow=tk.LAST, tags=("target_arrow", "minion"))

        # 献祭模式：实时预览部署合法范围
        if (frame._in_sacrifice_mode and frame._sacrifice_card
                and frame._sacrifice_active):
            preview = frame._calc_deploy_range(frame._sacrifice_card, frame._sacrifice_active, frame._selected_sacrifices)
            for pr, pc in preview:
                vcx, vcy, _ = _cell_center(pr, pc)
                self.canvas.create_rectangle(vcx - 38, vcy - 38, vcx + 38, vcy + 38,
                                             outline=UI_THEME["kw_vision"], width=4,
                                             fill="#fffbeb", stipple="gray50",
                                             tags="deploy_preview")

        # 高亮指向来源异象
        if frame._targeting_source_minion and frame._targeting_source_minion.position:
            sr, sc = frame._targeting_source_minion.position
            scx, scy, _ = _cell_center(sr, sc)
            self.canvas.create_rectangle(scx - 34, scy - 29, scx + 34, scy + 29,
                                         outline=UI_THEME["kw_vision"], width=4, tags="target_hint")

        # 高亮合法目标位置
        if frame.valid_targets:
            for t in frame.valid_targets:
                if isinstance(t, tuple) and len(t) == 2:
                    vr, vc = t
                    vcx, vcy, _ = _cell_center(vr, vc)
                    self.canvas.create_rectangle(vcx - 38, vcy - 38, vcx + 38, vcy + 38,
                                                 outline=UI_THEME["kw_vision"], width=4,
                                                 fill="#fffbeb", stipple="gray50",
                                                 tags="target_hint")

        # 结算阶段高亮当前正在结算的列
        if (game.current_phase == "resolve"
                and getattr(game, "_current_resolve_column", None) is not None):
            col = game._current_resolve_column
            x1 = col * cell_size + offset_x
            x2 = x1 + cell_size
            y1 = offset_y
            y2 = offset_y + 5 * cell_size
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="", width=0,
                fill=UI_THEME["btn_danger_bg"], stipple="gray50",
                tags="resolve_column_highlight",
            )

        # 最近动作高亮（伤害/死亡/治疗等事件发生的格子）
        import time
        now = time.time()
        recent_events = getattr(frame, "_recent_events", [])
        for event in recent_events:
            age = now - event.get("time", 0)
            if age > 2.5:
                continue
            for pos in event.get("positions", []):
                if isinstance(pos, tuple) and len(pos) == 2:
                    er, ec = pos
                    ecx, ecy, _ = _cell_center(er, ec)
                    # 越新越粗
                    width = max(2, 5 - int(age))
                    self.canvas.create_rectangle(
                        ecx - 38, ecy - 38, ecx + 38, ecy + 38,
                        outline=UI_THEME["danger"], width=width,
                        tags="recent_event_highlight",
                    )

    def preview_deploy_positions(self, frame: Any, serial: int) -> None:
        """悬停手牌时预览合法目标位置（绿色虚线方框）。"""
        if not frame.duel.game:
            return
        active = frame.local_player if frame.duel.is_remote else frame.duel.game.current_player
        card = active._get_hand_card(serial) if active else None
        if card is None:
            return

        valid = []
        if isinstance(card, MinionCard):
            for t in active.get_valid_targets(card):
                if isinstance(t, tuple) and frame.duel.game.board.is_valid_deploy(t, active, card):
                    existing = frame.duel.game.board.get_minion_at(t)
                    if existing is None or (
                        ("漂浮物" in existing.keywords and existing.owner == active) or
                        ("藤蔓" in card.keywords and existing.owner == active)
                    ):
                        valid.append(t)
        elif isinstance(card, Strategy):
            valid = [t for t in active.get_valid_targets(card) if t is not None]

        for target in valid:
            if isinstance(target, tuple) and len(target) == 2:
                logic_r, c = target
                cx, cy, _ = self._cell_center(logic_r, c)
                self.canvas.create_rectangle(cx - 38, cy - 38, cx + 38, cy + 38,
                                             outline=UI_THEME["deploy_preview"], width=2, dash=(4, 4),
                                             tags="preview_hint")
            elif hasattr(target, "position") and target.position:
                logic_r, c = target.position
                cx, cy, _ = self._cell_center(logic_r, c)
                self.canvas.create_rectangle(cx - 38, cy - 38, cx + 38, cy + 38,
                                             outline=UI_THEME["deploy_preview"], width=2, dash=(4, 4),
                                             tags="preview_hint")

    def _cell_center(self, logic_r: int, c: int):
        """返回指定逻辑格子的中心像素坐标与显示行。"""
        display_r = self.display_row_fn(logic_r)
        cx = c * self.cell_size + self.cell_size // 2 + self.board_offset_x
        cy = display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
        return cx, cy, display_r

