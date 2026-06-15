"""各种 Tkinter 弹窗对话框。

原位于 Gamestart.py，现独立出来供 BattleFrame 等模块使用。
"""

from typing import Any, Callable, List, Optional

import tkinter as tk
from tkinter import messagebox, scrolledtext

from tards import Minion
from tards.assets import get_asset_manager
from tards.card_db import DEFAULT_REGISTRY

from gui.theme import UI_THEME
from gui.battle.render_utils import calc_tab_width

try:
    from PIL import Image, ImageDraw, ImageTk  # noqa: F401
    _PIL_AVAILABLE = True
except Exception:
    _PIL_AVAILABLE = False


class SacrificeDialog(tk.Toplevel):
    def __init__(self, parent, minions: List[Minion], required_blood: int, on_confirm: Callable[[List[Minion]], None]):
        super().__init__(parent)
        self.title("献祭")
        self.geometry("500x380")
        self._parent = parent
        self.on_confirm = on_confirm
        self.transient(parent)
        self.grab_set()
        self.minions = minions
        self.required_blood = required_blood
        self.selected = set()
        self.card_frames = []
        self.card_canvases = []

        self.config(bg=UI_THEME["bg_main"])
        tk.Label(self, text=f"需要献祭 {required_blood} 点鲜血", font=("Microsoft YaHei", 12, "bold"),
                 fg=UI_THEME["danger"], bg=UI_THEME["bg_main"]).pack(pady=5)
        self.status_label = tk.Label(self, text="已选: 0 / 0", fg=UI_THEME["danger"], bg=UI_THEME["bg_main"])
        self.status_label.pack(pady=5)

        card_frame = tk.Frame(self, bg=UI_THEME["bg_main"])
        card_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cw, ch = 90, 144
        am = get_asset_manager()

        for i, m in enumerate(minions):
            defn = DEFAULT_REGISTRY.get(m.name)
            cost_str = defn.cost_str if defn else "?"
            TAB_W = calc_tab_width(cost_str)
            TAB_H = 16
            TAB_SLANT = max(5, TAB_W // 6)
            frame = tk.Frame(card_frame, bd=0)
            frame.pack(side=tk.LEFT, padx=5, pady=5)
            cvs = tk.Canvas(frame, width=cw, height=ch, highlightthickness=0, bd=0)
            cvs.pack()

            card_x1, card_y1 = 0, 0
            card_x2, card_y2 = cw, ch

            # 稀有度渐变背景
            rarity = defn.rarity if defn else None
            is_token = defn.is_token if defn else False
            bg_colors = None
            if rarity and not is_token:
                bg_colors = parent._RARITY_GRADIENTS.get(rarity)
            if not bg_colors:
                bg_colors = UI_THEME["rarity_none"]

            if _PIL_AVAILABLE:
                photo = parent._create_tab_gradient_photo(
                    cw, ch,
                    bg_colors[0], bg_colors[1],
                    tab_w=TAB_W, tab_h=TAB_H, slant=TAB_SLANT, radius=2
                )
                if photo:
                    cvs.create_image(
                        cw // 2,
                        ch // 2,
                        image=photo, tags="rarity_bg"
                    )
                    cvs.rarity_bg_image = photo

            # 标签区域填充（始终深灰，选中后变绿由边框表示）
            label_points = [
                card_x1, card_y1,
                card_x1 + TAB_W, card_y1,
                card_x1 + TAB_W + TAB_SLANT, card_y1 + TAB_H,
                card_x1, card_y1 + TAB_H,
            ]
            cvs.create_polygon(label_points, fill=UI_THEME["card_tab_default"], outline="", tags="cost_tab")

            # 卡面图（在费用文字之前绘制，避免覆盖）
            asset_id = defn.asset_id if defn else None
            if asset_id:
                img = am.get_card_face(asset_id, cw - 4, ch - 4)
                if img:
                    cvs.create_image(cw // 2, ch // 2, image=img, tags="card_img")
                    cvs.image = img

            # 费用文字
            cost_cx = card_x1 + (TAB_W + TAB_SLANT) // 2
            cost_cy = card_y1 + TAB_H // 2
            cvs.create_text(cost_cx, cost_cy, text=cost_str, fill="white",
                            font=("Microsoft YaHei", 8, "bold"), tags="card_text")

            # 卡名
            cvs.create_text(cw // 2, 20 + TAB_H, text=m.name, fill=UI_THEME["card_text_name"],
                            font=("Microsoft YaHei", 9, "bold"), tags="card_text")

            # 攻防 + 丰饶 + 位置
            feng_rang = m.keywords.get("丰饶", 1)
            pos_str = f"{m.position}" if getattr(m, "position", None) else ""
            bottom = f"{m.attack}/{m.health} 丰饶{feng_rang} {pos_str}".strip()
            cvs.create_text(cw // 2, ch - 12, text=bottom, fill=UI_THEME["card_text_type"],
                            font=("Microsoft YaHei", 8), tags="card_text")

            self.card_frames.append(frame)
            self.card_canvases.append(cvs)

            # 点击事件
            cvs.bind("<Button-1>", lambda e, idx=i: self._toggle(idx))
            cvs.bind("<Enter>", lambda e, cvs=cvs: cvs.config(cursor="hand2"))
            cvs.bind("<Leave>", lambda e, cvs=cvs: cvs.config(cursor=""))

        self.confirm_btn = tk.Button(self, text="确认献祭", font=("Microsoft YaHei", 10, "bold"),
                                      bg=UI_THEME["btn_danger_bg"], fg=UI_THEME["btn_danger_fg"],
                                      activebackground=UI_THEME["btn_danger_active"],
                                      relief=tk.RAISED, bd=1,
                                      command=self._confirm, state=tk.DISABLED)
        self.confirm_btn.pack(pady=5)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _toggle(self, idx: int):
        if idx in self.selected:
            self.selected.remove(idx)
        else:
            self.selected.add(idx)
        self._refresh_borders()
        self._update()

    def _refresh_borders(self):
        cw, ch = 90, 144
        card_x1, card_y1 = 0, 0
        card_x2, card_y2 = cw, ch
        r = 2
        for i, cvs in enumerate(self.card_canvases):
            defn = DEFAULT_REGISTRY.get(self.minions[i].name)
            cost_str = defn.cost_str if defn else "?"
            TAB_W = calc_tab_width(cost_str)
            TAB_SLANT = max(5, TAB_W // 6)
            body_y1 = card_y1 + 16
            shape_points = [
                card_x1, card_y1,
                card_x1 + TAB_W, card_y1,
                card_x1 + TAB_W + TAB_SLANT, body_y1,
                card_x2 - r, body_y1,
                card_x2, body_y1 + r,
                card_x2, card_y2 - r,
                card_x2 - r, card_y2,
                card_x1 + r, card_y2,
                card_x1, card_y2 - r,
                card_x1, body_y1,
            ]
            border_color = UI_THEME["success"] if i in self.selected else UI_THEME["card_border_default"]
            border_width = 2 if i in self.selected else 1
            cvs.delete("card_border")
            cvs.create_polygon(shape_points, fill="", outline=border_color, width=border_width,
                               joinstyle=tk.MITER, tags="card_border")

    def _update(self):
        total = sum(self.minions[i].keywords.get("丰饶", 1) for i in self.selected)
        enough = total >= self.required_blood
        self.status_label.config(text=f"已选: {total} / {self.required_blood}", fg=UI_THEME["success"] if enough else UI_THEME["danger"])
        self.confirm_btn.config(state=tk.NORMAL if enough else tk.DISABLED)

    def _confirm(self):
        selected = [self.minions[i] for i in self.selected]
        deathrattle_minions = [m for m in selected if m.keywords.get("亡语")]
        if deathrattle_minions:
            names = ", ".join(m.name for m in deathrattle_minions)
            if not messagebox.askyesno("确认献祭", f"以下异象具有亡语，献祭后将触发亡语效果：\n{names}\n\n确定要继续献祭吗？"):
                return
        self.grab_release()
        self.destroy()
        self.on_confirm(selected)

    def _on_close(self):
        self.grab_release()
        self.destroy()
        self.on_confirm([])


class DiscoverDialog(tk.Toplevel):
    def __init__(self, parent, names: List[str], on_choose: Callable[[str], None]):
        super().__init__(parent)
        self.title("开发")
        self.names = names
        self.on_choose = on_choose
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.config(bg=UI_THEME["bg_main"])
        tk.Label(self, text="选择一张卡牌加入手牌:", font=("Microsoft YaHei", 12),
                 bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(pady=10)

        card_frame = tk.Frame(self, bg=UI_THEME["bg_main"])
        card_frame.pack(pady=10)

        cw, ch = 90, 144
        am = get_asset_manager()

        for name in names:
            defn = DEFAULT_REGISTRY.get(name)
            cost_str = defn.cost_str if defn else "?"
            TAB_W = calc_tab_width(cost_str)
            TAB_H = 16
            TAB_SLANT = max(5, TAB_W // 6)
            frame = tk.Frame(card_frame, bd=0)
            frame.pack(side=tk.LEFT, padx=5)
            cvs = tk.Canvas(frame, width=cw, height=ch, highlightthickness=0, bd=0)
            cvs.pack()

            card_x1, card_y1 = 0, 0
            card_x2, card_y2 = cw, ch

            # 稀有度渐变背景
            rarity = defn.rarity if defn else None
            is_token = defn.is_token if defn else False
            bg_colors = None
            if rarity and not is_token:
                bg_colors = parent._RARITY_GRADIENTS.get(rarity)
            if not bg_colors:
                bg_colors = UI_THEME["rarity_none"]

            if _PIL_AVAILABLE:
                photo = parent._create_tab_gradient_photo(
                    cw, ch,
                    bg_colors[0], bg_colors[1],
                    tab_w=TAB_W, tab_h=TAB_H, slant=TAB_SLANT, radius=2
                )
                if photo:
                    cvs.create_image(
                        cw // 2,
                        ch // 2,
                        image=photo, tags="rarity_bg"
                    )
                    cvs.rarity_bg_image = photo

            # 标签区域填充
            label_points = [
                card_x1, card_y1,
                card_x1 + TAB_W, card_y1,
                card_x1 + TAB_W + TAB_SLANT, card_y1 + TAB_H,
                card_x1, card_y1 + TAB_H,
            ]
            cvs.create_polygon(label_points, fill=UI_THEME["card_tab_default"], outline="", tags="cost_tab")

            # 整体外形边框
            r = 2
            body_y1 = card_y1 + TAB_H
            shape_points = [
                card_x1, card_y1,
                card_x1 + TAB_W, card_y1,
                card_x1 + TAB_W + TAB_SLANT, body_y1,
                card_x2 - r, body_y1,
                card_x2, body_y1 + r,
                card_x2, card_y2 - r,
                card_x2 - r, card_y2,
                card_x1 + r, card_y2,
                card_x1, card_y2 - r,
                card_x1, body_y1,
            ]
            cvs.create_polygon(shape_points, fill="", outline=UI_THEME["card_border_default"], width=1,
                               joinstyle=tk.MITER, tags="card_border")

            # 费用文字（标签内，白色）
            cost_cx = card_x1 + (TAB_W + TAB_SLANT) // 2
            cost_cy = card_y1 + TAB_H // 2
            cvs.create_text(cost_cx, cost_cy, text=cost_str, fill="white",
                            font=("Microsoft YaHei", 8, "bold"), tags="card_text")

            # 卡面图
            asset_id = defn.asset_id if defn else None
            if asset_id:
                img = am.get_card_face(asset_id, cw - 4, ch - 4)
                if img:
                    cvs.create_image(cw // 2, ch // 2, image=img, tags="card_img")
                    cvs.image = img

            # 卡名
            cvs.create_text(cw // 2, 20 + TAB_H, text=name, fill=UI_THEME["card_text_name"],
                            font=("Microsoft YaHei", 9, "bold"), tags="card_text")

            # 类型/攻防
            type_str = ""
            stats = ""
            if defn:
                from tards.card_db import CardType
                if defn.card_type == CardType.MINION:
                    type_str = "【异象】"
                    stats = f"{defn.attack or 0}/{defn.health or 1}"
                elif defn.card_type == CardType.STRATEGY:
                    type_str = "【策略】"
                elif defn.card_type == CardType.CONSPIRACY:
                    type_str = "【阴谋】"
                elif defn.card_type == CardType.MINERAL:
                    type_str = "【矿物】"
            bottom = f"{type_str}{stats}"
            cvs.create_text(cw // 2, ch - 12, text=bottom, fill=UI_THEME["card_text_type"],
                            font=("Microsoft YaHei", 8), tags="card_text")

            # 点击事件
            cvs.bind("<Button-1>", lambda e, n=name: self._choose(n))
            cvs.bind("<Enter>", lambda e, cvs=cvs: cvs.config(cursor="hand2"))
            cvs.bind("<Leave>", lambda e, cvs=cvs: cvs.config(cursor=""))

    def _choose(self, name: str):
        self.on_choose(name)
        self.grab_release()
        self.destroy()

    def _on_close(self):
        if self.names:
            self.on_choose(self.names[0])
        self.grab_release()
        self.destroy()


class ChoiceDialog(tk.Toplevel):
    """通用抉择弹窗，支持自定义标题和选项文案。
    若选项全部为卡牌名，则以卡牌形式展示；否则保持文本按钮。"""

    def __init__(self, parent, title: str, options: List[str], on_choose: Callable[[str], None]):
        super().__init__(parent)
        self.title(title)
        self.options = options
        self.on_choose = on_choose
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # 判断选项是否全部为卡牌名
        card_defs = [DEFAULT_REGISTRY.get(opt) for opt in options]
        all_cards = all(d is not None for d in card_defs)

        if all_cards:
            self.geometry("600x280")
            self.config(bg=UI_THEME["bg_main"])
            tk.Label(self, text=title, font=("Microsoft YaHei", 12),
                     bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(pady=10)
            card_frame = tk.Frame(self, bg=UI_THEME["bg_main"])
            card_frame.pack(pady=10)

            cw, ch = 90, 144
            am = get_asset_manager()

            for opt, defn in zip(options, card_defs):
                cost_str = defn.cost_str if defn else "?"
                TAB_W = calc_tab_width(cost_str)
                TAB_H = 16
                TAB_SLANT = max(5, TAB_W // 6)
                frame = tk.Frame(card_frame, bd=0)
                frame.pack(side=tk.LEFT, padx=5)
                cvs = tk.Canvas(frame, width=cw, height=ch, highlightthickness=0, bd=0)
                cvs.pack()

                card_x1, card_y1 = 0, 0
                card_x2, card_y2 = cw, ch

                rarity = defn.rarity if defn else None
                is_token = defn.is_token if defn else False
                bg_colors = None
                if rarity and not is_token:
                    bg_colors = parent._RARITY_GRADIENTS.get(rarity)
                if not bg_colors:
                    bg_colors = UI_THEME["rarity_none"]

                if _PIL_AVAILABLE:
                    photo = parent._create_tab_gradient_photo(
                        cw, ch,
                        bg_colors[0], bg_colors[1],
                        tab_w=TAB_W, tab_h=TAB_H, slant=TAB_SLANT, radius=2
                    )
                    if photo:
                        cvs.create_image(
                            cw // 2,
                            ch // 2,
                            image=photo, tags="rarity_bg"
                        )
                        cvs.rarity_bg_image = photo

                label_points = [
                    card_x1, card_y1,
                    card_x1 + TAB_W, card_y1,
                    card_x1 + TAB_W + TAB_SLANT, card_y1 + TAB_H,
                    card_x1, card_y1 + TAB_H,
                ]
                cvs.create_polygon(label_points, fill=UI_THEME["card_tab_default"], outline="", tags="cost_tab")

                r = 2
                body_y1 = card_y1 + TAB_H
                shape_points = [
                    card_x1, card_y1,
                    card_x1 + TAB_W, card_y1,
                    card_x1 + TAB_W + TAB_SLANT, body_y1,
                    card_x2 - r, body_y1,
                    card_x2, body_y1 + r,
                    card_x2, card_y2 - r,
                    card_x2 - r, card_y2,
                    card_x1 + r, card_y2,
                    card_x1, card_y2 - r,
                    card_x1, body_y1,
                ]
                cvs.create_polygon(shape_points, fill="", outline=UI_THEME["card_border_default"], width=1,
                               joinstyle=tk.MITER, tags="card_border")

                cost_cx = card_x1 + (TAB_W + TAB_SLANT) // 2
                cost_cy = card_y1 + TAB_H // 2
                cvs.create_text(cost_cx, cost_cy, text=cost_str, fill="white",
                                font=("Microsoft YaHei", 8, "bold"), tags="card_text")

                asset_id = defn.asset_id if defn else None
                if asset_id:
                    img = am.get_card_face(asset_id, cw - 4, ch - 4)
                    if img:
                        cvs.create_image(cw // 2, ch // 2, image=img, tags="card_img")
                        cvs.image = img

                cvs.create_text(cw // 2, 20 + TAB_H, text=opt, fill=UI_THEME["card_text_name"],
                                font=("Microsoft YaHei", 9, "bold"), tags="card_text")

                type_str = ""
                stats = ""
                if defn:
                    from tards.card_db import CardType
                    if defn.card_type == CardType.MINION:
                        type_str = "【异象】"
                        stats = f"{defn.attack or 0}/{defn.health or 1}"
                    elif defn.card_type == CardType.STRATEGY:
                        type_str = "【策略】"
                    elif defn.card_type == CardType.CONSPIRACY:
                        type_str = "【阴谋】"
                    elif defn.card_type == CardType.MINERAL:
                        type_str = "【矿物】"
                bottom = f"{type_str}{stats}"
                cvs.create_text(cw // 2, ch - 12, text=bottom, fill=UI_THEME["card_text_type"],
                                font=("Microsoft YaHei", 8), tags="card_text")

                cvs.bind("<Button-1>", lambda e, o=opt: self._choose(o))
                cvs.bind("<Enter>", lambda e, cvs=cvs: cvs.config(cursor="hand2"))
                cvs.bind("<Leave>", lambda e, cvs=cvs: cvs.config(cursor=""))
        else:
            self.config(bg=UI_THEME["bg_main"])
            tk.Label(self, text="请选择一项：", font=("Microsoft YaHei", 12),
                     bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(pady=10)
            btn_frame = tk.Frame(self, bg=UI_THEME["bg_main"])
            btn_frame.pack(pady=10)
            for opt in options:
                btn = tk.Button(btn_frame, text=opt, width=14, height=2, font=("Microsoft YaHei", 10),
                                bg=UI_THEME["btn_primary_bg"], fg=UI_THEME["btn_primary_fg"],
                                activebackground=UI_THEME["btn_primary_active"],
                                relief=tk.RAISED, bd=1,
                                command=lambda o=opt: self._choose(o))
                btn.pack(side=tk.LEFT, padx=5)

    def _choose(self, option: str):
        self.on_choose(option)
        self.grab_release()
        self.destroy()

    def _on_close(self):
        if self.options:
            self.on_choose(self.options[0])
        self.grab_release()
        self.destroy()


class EffectTargetDialog(tk.Toplevel):
    """效果预设目标选择弹窗（调试用，替代Canvas指向）。"""

    def __init__(self, parent, minions: List[Any], on_choose: Callable[[Any], None],
                 on_cancel: Optional[Callable[[], None]] = None, prompt: str = "请选择效果目标"):
        super().__init__(parent)
        self.title("效果目标选择")
        self.geometry("360x400")
        self.on_choose = on_choose
        self.on_cancel = on_cancel
        self.minions = minions
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.config(bg=UI_THEME["bg_main"])

        tk.Label(self, text=prompt, font=("Microsoft YaHei", 12, "bold"),
                 fg=UI_THEME["danger"], bg=UI_THEME["bg_main"]).pack(pady=10)

        list_frame = tk.Frame(self, bg=UI_THEME["bg_main"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for m in minions:
            owner = "我方" if hasattr(m, 'owner') and m.owner and getattr(m.owner, 'player_id', None) == getattr(parent, 'local_player', None) and getattr(parent, 'local_player', None) is not None else "敌方"
            pos = f" 位置{m.position}" if hasattr(m, 'position') and m.position else ""
            text = f"{m.name} ({m.attack}/{m.health}) [{owner}]{pos}"
            btn = tk.Button(list_frame, text=text, font=("Microsoft YaHei", 10),
                            bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                            activebackground=UI_THEME["btn_secondary_active"],
                            relief=tk.RAISED, bd=1,
                            command=lambda mm=m: self._choose(mm))
            btn.pack(fill=tk.X, pady=3)

        cancel_btn = tk.Button(self, text="取消", font=("Microsoft YaHei", 10),
                               bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                               activebackground=UI_THEME["btn_secondary_active"],
                               relief=tk.RAISED, bd=1,
                               command=self._on_close)
        cancel_btn.pack(pady=10)

    def _choose(self, minion):
        self.grab_release()
        self.destroy()
        self.on_choose(minion)

    def _on_close(self):
        self.grab_release()
        self.destroy()
        if self.on_cancel:
            self.on_cancel()


class FeedbackDialog(tk.Toplevel):
    """反馈提交弹窗。

    允许玩家输入问题描述和反馈服务器地址，
    自动附带当前对战的最新日志。
    """

    def __init__(self, parent, player_name: str, on_submit: Callable[[str, str], None]):
        super().__init__(parent)
        self.title("提交反馈")
        self.geometry("450x380")
        self.resizable(False, False)
        self.on_submit = on_submit
        self._build_ui(player_name)
        self.grab_set()
        self.focus_force()

    def _build_ui(self, player_name: str):
        self.config(bg=UI_THEME["bg_main"])
        pad = {"padx": 10, "pady": 5}

        # 玩家名
        tk.Label(self, text=f"玩家: {player_name}", anchor="w",
                 bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(fill=tk.X, **pad)

        # 服务器地址
        addr_frame = tk.Frame(self, bg=UI_THEME["bg_main"])
        addr_frame.pack(fill=tk.X, **pad)
        tk.Label(addr_frame, text="反馈服务器:", bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(side=tk.LEFT)
        self.addr_entry = tk.Entry(addr_frame, width=25,
                                   bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                                   insertbackground=UI_THEME["text_primary"])
        self.addr_entry.pack(side=tk.LEFT, padx=5)
        # 加载上次使用的地址
        config = load_feedback_config()
        last_addr = config.get("server_address", "")
        if last_addr:
            self.addr_entry.insert(0, last_addr)
        else:
            self.addr_entry.insert(0, "127.0.0.1:9999")

        # 问题描述
        tk.Label(self, text="问题描述:", anchor="w",
                 bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(fill=tk.X, **pad)
        self.desc_text = scrolledtext.ScrolledText(self, height=8, wrap=tk.WORD,
                                                   bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                                                   relief=tk.FLAT, bd=0)
        self.desc_text.pack(fill=tk.BOTH, expand=True, **pad)

        # 日志提示
        tk.Label(
            self,
            text="✓ 将自动附带当前对战的最新日志（尾部500行）",
            fg=UI_THEME["success"],
            bg=UI_THEME["bg_main"],
            anchor="w",
        ).pack(fill=tk.X, **pad)

        # 按钮
        btn_frame = tk.Frame(self, bg=UI_THEME["bg_main"])
        btn_frame.pack(fill=tk.X, pady=10)
        tk.Button(btn_frame, text="提交", command=self._on_submit, width=10,
                  bg=UI_THEME["btn_primary_bg"], fg=UI_THEME["btn_primary_fg"],
                  activebackground=UI_THEME["btn_primary_active"], relief=tk.RAISED, bd=1).pack(side=tk.RIGHT, padx=10)
        tk.Button(btn_frame, text="取消", command=self.destroy, width=10,
                  bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                  activebackground=UI_THEME["btn_secondary_active"], relief=tk.RAISED, bd=1).pack(side=tk.RIGHT)

        # 绑定回车提交
        self.bind("<Return>", lambda e: self._on_submit())
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_submit(self):
        desc = self.desc_text.get("1.0", tk.END).strip()
        if not desc:
            messagebox.showwarning("提示", "请输入问题描述")
            return

        addr = self.addr_entry.get().strip()
        if not addr:
            messagebox.showwarning("提示", "请输入反馈服务器地址")
            return

        # 简单校验 ip:port 格式
        parts = addr.rsplit(":", 1)
        if len(parts) != 2:
            messagebox.showwarning("提示", "地址格式应为 IP:端口，如 192.168.1.100:9999")
            return
        host, port_str = parts
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showwarning("提示", "端口号必须是数字")
            return

        # 保存配置
        save_feedback_config({"server_address": addr})

        self.on_submit(desc, f"{host}:{port}")
        self.destroy()


class NumericChoiceDialog(tk.Toplevel):
    """数字选择弹窗，用于自然数目标的指向请求（如"第n行"）。"""

    def __init__(self, parent, title: str, options: List[int], on_choose: Callable[[int], None]):
        super().__init__(parent)
        self.title(title)
        self.options = options
        self.on_choose = on_choose
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        tk.Label(self, text="请选择一项：", font=("Microsoft YaHei", 12)).pack(pady=10)
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        for opt in options:
            btn = tk.Button(btn_frame, text=str(opt), width=10, height=2, font=("Microsoft YaHei", 10, "bold"),
                            bg="#e3f2fd", activebackground="#bbdefb",
                            command=lambda o=opt: self._choose(o))
            btn.pack(side=tk.LEFT, padx=5)

    def _choose(self, option: int):
        self.on_choose(option)
        self.grab_release()
        self.destroy()

    def _on_close(self):
        if self.options:
            self.on_choose(self.options[0])
        self.grab_release()
        self.destroy()
