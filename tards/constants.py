# 事件常量
# 宏观时间节点（已有）
EVENT_DEPLOY = "deploy"
EVENT_DEATH = "death"
EVENT_PLAYER_DAMAGE = "player_damage"
EVENT_PHASE_START = "phase_start"
EVENT_PHASE_END = "phase_end"
EVENT_TURN_START = "turn_start"
EVENT_TURN_END = "turn_end"
EVENT_BELL = "bell"
EVENT_CARD_PLAYED = "card_played"
EVENT_DRAW = "draw"
EVENT_SACRIFICE = "sacrifice"

# 微观操作事件 — Before（可取消/修改）
EVENT_BEFORE_HEALTH_CHANGE = "before_health_change"
EVENT_BEFORE_T_CHANGE = "before_t_change"
EVENT_BEFORE_C_CHANGE = "before_c_change"
EVENT_BEFORE_DRAW = "before_draw"
EVENT_BEFORE_DISCARD = "before_discard"
EVENT_BEFORE_MILL = "before_mill"
EVENT_BEFORE_DEPLOY = "before_deploy"
EVENT_BEFORE_PLAY = "before_play"
EVENT_BEFORE_ATTACK = "before_attack"
EVENT_BEFORE_DAMAGE = "before_damage"
EVENT_BEFORE_DESTROY = "before_destroy"
EVENT_BEFORE_MOVE = "before_move"
EVENT_BEFORE_REMOVE = "before_remove"
EVENT_BEFORE_POINT = "before_point"   # 指向事件

# 微观操作事件 — 主事件（已发生，只读）
EVENT_HEALTH_CHANGED = "health_changed"
EVENT_T_CHANGED = "t_changed"
EVENT_C_CHANGED = "c_changed"
EVENT_DRAWN = "drawn"
EVENT_DISCARDED = "discarded"
EVENT_MILLED = "milled"
EVENT_DEPLOYED = "deployed"
EVENT_PLAYED = "played"
EVENT_ATTACKED = "attacked"
EVENT_DAMAGED = "damaged"
EVENT_DESTROYED = "destroyed"
EVENT_MOVED = "moved"
EVENT_REMOVED = "removed"
EVENT_POINTED = "pointed"

# 微观操作事件 — After（只读）
EVENT_AFTER_ATTACK = "after_attack"
EVENT_AFTER_DAMAGE = "after_damage"
EVENT_AFTER_DESTROY = "after_destroy"
EVENT_AFTER_DEPLOY = "after_deploy"
EVENT_AFTER_PLAY = "after_play"

# 资源上限变化事件（通用）
EVENT_T_MAX_CHANGED = "t_max_changed"
EVENT_C_MAX_CHANGED = "c_max_changed"

# 开发事件
EVENT_DEVELOPED = "developed"

# 关键词变化事件
EVENT_KEYWORD_GAINED = "keyword_gained"
EVENT_KEYWORD_LOST = "keyword_lost"

# 棋盘常量
BOARD_SIZE = 5
COL_NAMES = ["高地", "山脊", "中路", "河岸", "水路"]

# 通用词条（可被"恐惧"清除）
GENERAL_KEYWORDS = {
    "迅捷", "协同", "独行", "藤蔓", "水生", "两栖", "串击", "穿刺",
    "空袭", "防空", "潜水", "潜行", "绝缘", "尖刺", "回响", "坚韧",
    "视野", "横扫", "高频", "先攻", "休眠", "成长", "献祭", "丰饶",
    "破甲", "重甲", "冰冻", "眩晕", "高地", "漂浮物", "脆弱",
    "三重打击", "穿透", "亡语", "恐惧",
}

# 标签词库（用于异象分类，与 GENERAL_KEYWORDS 可能重叠）
TAG_TOKENS = {
    "友好", "敌对", "中立",
    "生物", "非生命",
    "地狱", "精灵",
    "陆地", "飞禽", "昆虫", "陆生", "肉食动物",
    # 以下同时是 keyword，但雕像效果等也依赖它们作为 tag 查询
    "水生", "两栖",
}

# 常用标签常量（避免硬编码字符串）
TAG_FRIENDLY = "友好"
TAG_HOSTILE = "敌对"
TAG_NEUTRAL = "中立"
TAG_BIOLOGICAL = "生物"
TAG_NONLIVING = "非生命"
TAG_HELL = "地狱"
TAG_SPIRIT = "精灵"
TAG_LAND = "陆地"
TAG_AMPHIBIOUS = "两栖"
