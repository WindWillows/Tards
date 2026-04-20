import re
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .player import Player


class Cost:
    """费用系统，支持 T/C/B/S 资源以及手牌矿物 I/G/D/M。
    
    同时支持 CT 费用（XCT 表示 X 点，每点可以是 1C 或 1T）。
    """

    def __init__(
        self,
        t: int = 0,
        c: int = 0,
        b: int = 0,
        s: int = 0,
        ct: int = 0,
        minerals: Optional[Dict[str, int]] = None,
    ):
        self.t = t          # 通用点数
        self.c = c          # 兑换槽（通常不直接出现在卡牌费用中，除了获得C的策略）
        self.b = b          # 鲜血
        self.s = s          # 血契
        self.ct = ct        # CT 组合费用点数
        self.minerals = minerals or {}  # 手牌矿物需求，如 {"I": 2, "G": 1}

    @classmethod
    def from_string(cls, s: str) -> "Cost":
        """解析费用字符串。
        
        支持格式：
        - "3T2B" -> t=3, b=2
        - "2CT" -> ct=2
        - "1D1G1I1T" -> minerals={"D":1,"G":1,"I":1}, t=1
        - "0T" -> t=0
        """
        s = s.strip()
        if not s or s == "0":
            return cls()

        # 先处理 CT：如 2CT, 3CT
        if s.endswith("CT"):
            num = s[:-2]
            if num.isdigit():
                return cls(ct=int(num))
            raise ValueError(f"无法解析 CT 费用: {s}")

        # 普通组合费用：匹配所有 数字+字母 片段
        pattern = re.compile(r"(\d+)([A-Z])")
        matches = pattern.findall(s)
        if not matches:
            raise ValueError(f"无法解析费用: {s}")

        t = c = b = s_val = 0
        minerals = {}
        for num_str, symbol in matches:
            num = int(num_str)
            if symbol == "T":
                t = num
            elif symbol == "C":
                c = num
            elif symbol == "B":
                b = num
            elif symbol == "S":
                s_val = num
            elif symbol in ("I", "G", "D", "M"):
                minerals[symbol] = num
            else:
                raise ValueError(f"未知的费用符号: {symbol} in {s}")

        return cls(t=t, c=c, b=b, s=s_val, minerals=minerals)

    def copy(self) -> "Cost":
        return Cost(
            t=self.t,
            c=self.c,
            b=self.b,
            s=self.s,
            ct=self.ct,
            minerals=dict(self.minerals) if self.minerals else {},
        )

    def __repr__(self) -> str:
        parts = []
        if self.t:
            parts.append(f"{self.t}T")
        if self.c:
            parts.append(f"{self.c}C")
        if self.b:
            parts.append(f"{self.b}B")
        if self.s:
            parts.append(f"{self.s}S")
        if self.ct:
            parts.append(f"{self.ct}CT")
        for k, v in sorted(self.minerals.items()):
            parts.append(f"{v}{k}")
        return "".join(parts) if parts else "0"

    def can_afford_detail(self, player: "Player") -> tuple[bool, str]:
        """检查玩家当前资源是否足够支付此费用，返回 (是否可支付, 失败原因)。"""
        # 检查 T/B/S
        if player.t_point < self.t:
            return False, f"T点不足（需要{self.t}T，当前{player.t_point}T）"
        if player.b_point < self.b:
            return False, f"鲜血不足（需要{self.b}B，当前{player.b_point}B）"
        if player.s_point < self.s:
            return False, f"血契不足（需要{self.s}S，当前{player.s_point}S）"

        # 检查 CT（组合费用）：支付 t 后，剩余的 t + c 必须 >= ct
        if self.ct > 0:
            remaining_t = player.t_point - self.t
            if remaining_t + player.c_point < self.ct:
                return False, f"CT不足（需要{self.ct}CT，当前剩余T+C={remaining_t + player.c_point}）"

        # 检查手牌中的矿物卡
        from .cards import MineralCard
        hand_minerals = {}
        for card in player.card_hand:
            if isinstance(card, MineralCard):
                hand_minerals[card.mineral_type] = hand_minerals.get(card.mineral_type, 0) + 1

        for mtype, need in self.minerals.items():
            if hand_minerals.get(mtype, 0) < need:
                return False, f"手牌矿物不足（需要{need}张{mtype}，当前{hand_minerals.get(mtype, 0)}张）"

        return True, ""

    def can_afford(self, player: "Player") -> bool:
        """检查玩家当前资源是否足够支付此费用。"""
        return self.can_afford_detail(player)[0]

    def pay(self, player: "Player") -> bool:
        """执行支付。支付前会自动检查，若无法支付则返回 False。"""
        if not self.can_afford(player):
            return False

        from .cards import MineralCard

        # 支付资源
        if self.t:
            player.t_point_change(-self.t)
        if self.b:
            player.b_point -= self.b
        if self.s:
            player.s_point -= self.s

        # 支付 CT：优先消耗 C，再消耗 T
        if self.ct > 0:
            pay_c = min(player.c_point, self.ct)
            pay_t = self.ct - pay_c
            if pay_c:
                player.c_point_change(-pay_c)
            if pay_t:
                player.t_point_change(-pay_t)

        # 支付手牌矿物（从后往前移除，避免索引问题）
        if self.minerals:
            for mtype, need in self.minerals.items():
                removed = 0
                for i in range(len(player.card_hand) - 1, -1, -1):
                    card = player.card_hand[i]
                    if isinstance(card, MineralCard) and card.mineral_type == mtype:
                        player.card_hand.pop(i)
                        removed += 1
                        if removed >= need:
                            break

        return True
