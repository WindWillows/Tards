#!/usr/bin/env python3
"""提取项目中所有关键词、词条和标签。"""

import re
import ast
from pathlib import Path
import json

ROOT = Path("c:/Users/34773/Desktop/tards开发库")


def get_constants_keywords():
    """从 constants.py 中提取 GENERAL_KEYWORDS 和 TAG_TOKENS。"""
    path = ROOT / "tards" / "constants.py"
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    
    general = set()
    tags = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "GENERAL_KEYWORDS" and isinstance(node.value, ast.Set):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                general.add(elt.value)
                    elif target.id == "TAG_TOKENS" and isinstance(node.value, ast.Set):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                tags.add(elt.value)
    
    return general, tags


def extract_keywords_from_game_code():
    """从核心游戏代码中提取 .get('keyword', ...) 模式的关键词。"""
    keywords = set()
    files = [
        ROOT / "tards" / "game.py",
        ROOT / "tards" / "board.py",
        ROOT / "tards" / "cards.py",
        ROOT / "tards" / "player.py",
        ROOT / "tards" / "targeting.py",
    ]
    
    for path in files:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Match .get("keyword", ...) or .get('keyword', ...)
        for match in re.finditer(r'\.get\(["\']([^"\']+)["\']\s*,', content):
            kw = match.group(1)
            # Only keep Chinese keywords (2+ chars)
            if re.match(r'^[\u4e00-\u9fa5]+$', kw) and len(kw) >= 2:
                keywords.add(kw)
        
        # Match "keyword" in minion.keywords / card.keywords
        for match in re.finditer(r'["\']([^"\']+)["\']\s+in\s+(?:m\.keywords|minion\.keywords|card\.keywords|target\.keywords|self\.keywords)', content):
            kw = match.group(1)
            if re.match(r'^[\u4e00-\u9fa5]+$', kw) and len(kw) >= 2:
                keywords.add(kw)
    
    return keywords


def extract_keywords_from_card_packs():
    """从离散/冥刻/血契卡包 .py 文件中提取 keywords={...} 中的键。"""
    keywords = set()
    for pack in ["discrete.py", "underworld.py", "blood.py"]:
        path = ROOT / "card_pools" / pack
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find all keywords={"key": value, ...} patterns
        for block_match in re.finditer(r'keywords\s*=\s*\{([^}]*)\}', content):
            block = block_match.group(1)
            for kw_match in re.finditer(r'["\']([^"\']+)["\']\s*:', block):
                kw = kw_match.group(1)
                if len(kw) >= 2:
                    keywords.add(kw)
    
    return keywords


def extract_keywords_from_txt_sources():
    """从 .txt 卡包源文件中提取【keyword】格式的关键词。"""
    keywords = set()
    for txt_file in ROOT.glob("*.txt"):
        with open(txt_file, "r", encoding="utf-8") as f:
            content = f.read()
        for match in re.finditer(r'[【\[]([^【\]\[】]+)[】\]]', content):
            kw = match.group(1).strip()
            if len(kw) >= 2 and len(kw) <= 10:
                keywords.add(kw)
    return keywords


def extract_keywords_from_rules():
    """从 rules_text.txt 中提取关键词。"""
    keywords = set()
    path = ROOT / "rules_text.txt"
    if not path.exists():
        return keywords
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Match quoted terms
    for match in re.finditer(r'[【\[]([^【\]\[】]+)[】\]]', content):
        kw = match.group(1).strip()
        if len(kw) >= 2 and len(kw) <= 10 and not kw.startswith('http'):
            keywords.add(kw)
    
    # Match lines that look like keyword definitions
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('- ') or line.startswith('* '):
            term = line[2:].split('：')[0].split(':')[0].strip()
            if re.match(r'^[\u4e00-\u9fa5]+$', term) and 2 <= len(term) <= 8:
                keywords.add(term)
    
    return keywords


def main():
    general_kw, tag_tokens = get_constants_keywords()
    code_kw = extract_keywords_from_game_code()
    pack_kw = extract_keywords_from_card_packs()
    txt_kw = extract_keywords_from_txt_sources()
    rules_kw = extract_keywords_from_rules()
    
    # Known non-keywords to filter out
    non_keywords = {
        "当前", "回合", "阶段", "玩家", "游戏", "效果", "目标",
        "来源", "伤害", "攻击", "生命", "异象", "卡牌", "手牌",
        "牌库", "弃牌", "部署", "消灭", "结算", "行动", "选择",
        "敌方", "友方", "双方", "场上", "棋盘", "位置", "列名",
        "返回", "获得", "失去", "触发", "打印", "警告", "信息",
        "名称", "类型", "费用", "稀有度", "卡包", "实例", "对象",
        "属性", "方法", "函数", "导入", "配置", "设置", "默认",
        "判断", "检查", "获取", "更新", "增加", "减少", "修改",
        "删除", "添加", "随机", "全部", "所有", "任何", "每个",
        "如果", "否则", "然后", "当", "时", "可能", "需要",
        "成功", "失败", "有效", "无效", "合法", "存活", "死亡",
        "战斗", "防御", "护甲", "护盾", "召唤", "复制", "衍生物",
        "抽牌", "弃置", "磨牌", "搜索", "洗入", "费用", "资源",
        "点数", "上限", "开始", "结束", "准备", "恢复", "事件",
        "监听", "回调", "注册", "延迟", "条件", "状态", "追踪",
        "统计", "全局", "局部", "临时", "永久", "持续", "激活",
        "禁用", "失效", "过期", "文本", "字符串", "数字", "整数",
        "布尔", "列表", "字典", "元组", "集合", "文件", "路径",
        "目录", "模块", "测试", "调试", "验证", "确认", "完成",
        "生成", "构建", "编译", "运行", "执行", "创建", "销毁",
        "初始化", "清理", "重置", "复制", "粘贴", "剪切", "移动",
        "替换", "合并", "拆分", "分组", "排序", "过滤", "映射",
        "转换", "格式化", "解析", "编码", "解码", "上传", "下载",
        "同步", "备份", "登录", "注销", "权限", "角色", "用户",
        "系统", "环境", "平台", "框架", "接口", "协议", "规范",
        "标准", "注释", "文档", "说明", "描述", "定义", "参数",
        "返回值", "异常", "常量", "变量", "类", "继承", "多态",
        "封装", "抽象", "实现", "引用", "指针", "地址", "内存",
        "缓存", "线程", "进程", "队列", "栈", "锁", "循环",
        "递归", "迭代", "遍历", "分支", "跳转", "中断", "继续",
        "比较", "匹配", "查找", "插入", "追加", "清空", "克隆",
        "最大值", "最小值", "平均值", "总和", "计数", "长度",
        "大小", "容量", "索引", "键", "值", "项", "元素",
        "节点", "边", "根", "叶子", "深度", "高度", "层级",
        "父", "子", "兄弟", "祖先", "后代", "前驱", "后继",
        "邻居", "路径", "环", "树", "图", "网络", "表",
        "视图", "事务", "提交", "回滚", "查询", "连接", "联合",
        "定时器", "时钟", "日期", "时间", "时区", "速率", "带宽",
        "请求", "响应", "通知", "推送", "拉取", "订阅", "发布",
        "广播", "客户端", "服务端", "代理", "网关", "域名",
        "地址", "端口", "握手", "加密", "解密", "签名", "验证",
        "证书", "令牌", "票据", "会话", "模板", "样式", "主题",
        "皮肤", "布局", "组件", "控件", "部件", "属性", "标识",
        "动作", "行为", "模式", "视图", "模型", "控制器", "服务",
        "存储", "路由", "导航", "重定向", "转发", "拦截", "中间件",
        "管道", "钩子", "插件", "扩展", "选项", "偏好", "步长",
        "精度", "范围", "区间", "域", "数组", "字符串", "空值",
        "真值", "假值", "正数", "负数", "奇数", "偶数", "幂",
        "根", "对数", "指数", "排列", "组合", "概率", "均值",
        "方差", "标准差", "中位数", "众数", "样本", "总体", "矩阵",
        "向量", "张量", "标量", "维度", "行", "列", "秩", "迹",
        "积分", "微分", "极限", "级数", "收敛", "发散", "连续",
        "周期", "频率", "相位", "振幅", "波长", "波数", "波速",
        "能量", "动量", "力", "扭矩", "压强", "温度", "热量",
        "熵", "焓", "自由能", "电位", "电压", "电流", "电阻",
        "电容", "电感", "功率", "磁场", "电场", "引力", "质量",
        "电荷", "自旋", "光子", "电子", "质子", "中子", "原子",
        "分子", "离子", "化合物", "混合物", "元素", "同位素",
        "溶液", "溶剂", "溶质", "浓度", "密度", "粘度", "沸点",
        "熔点", "临界点", "相变", "扩散", "渗透", "吸附", "催化",
        "氧化", "还原", "酸碱", "电离", "水解", "沉淀", "有机",
        "无机", "聚合物", "单体", "凝胶", "泡沫", "乳液", "悬浮液",
        "胶体", "等离子体", "超导体", "半导体", "绝缘体", "导体",
        "铁磁", "压电", "热电", "形状记忆", "纳米材料", "复合材料",
        "生物材料", "能源材料", "信息材料", "环境材料",
        # Card names / non-keywords found in packs
        "火把", "离散", "冥刻", "血契", "信标", "命名牌", "时刻",
        "松鼠", "水路", "阵营", "描述", "取消", "对战", "抽取",
        "战斗伤害", "造成伤害", "移动", "策略", "请选择目标",
        "受到伤害时", "回合结束时", "部署时", "无法被选中",
        "也算作是",
        # Long phrases from docs that are not keywords
        "出牌阶段限一次", "回合结束时移除", "将敌方异象移到友方区域",
        "展示并选择", "攻击时优先目标", "无法被消灭",
        "无法选中直到结算阶段开始", "无视坚韧", "是哪几张牌",
        "本回合是否已使用过金锭", "本回合是否已兑换", "本回合未部署",
        "本次抽到的牌", "若指向僵尸村民", "被战斗消灭",
        "被某张特定卡指向时", "被策略效果消灭", "非友好", "非敌对",
        "丛林神殿", "书架受伤", "僵尸村民", "恶魂之泪", "恶魂亡语",
        "战吼", "抽两张牌", "沙漠神殿", "流浪商人", "溢出抽牌",
        "溴化银", "用手指点选", "看穿一切", "末影螨", "耕殖", "胶片",
        "萤石", "食蚁兽", "如可能", "响应并取消原效果", "强制攻击",
        "受伤异象", "抽两张牌", "是哪几张牌", "显影", "组队",
        # More doc phrases
        "取消原效果", "跳过阶段",
    }
    
    all_found = (code_kw | pack_kw | txt_kw | rules_kw) - non_keywords
    all_keywords = general_kw | tag_tokens | all_found
    
    # Categorize
    implemented = general_kw  # These are in GENERAL_KEYWORDS
    in_code = code_kw - non_keywords - general_kw
    in_packs_only = (pack_kw - non_keywords) - general_kw - code_kw
    in_docs_only = (txt_kw | rules_kw - non_keywords) - general_kw - code_kw - pack_kw
    
    lines = []
    lines.append("=" * 60)
    lines.append("Tards 项目关键词/词条/标签 完整清单")
    lines.append("=" * 60)
    
    lines.append(f"\n[A] 核心词条 GENERAL_KEYWORDS ({len(general_kw)} 个，已在引擎实现)")
    for kw in sorted(general_kw):
        lines.append(f"  - {kw}")
    
    lines.append(f"\n[B] 标签词库 TAG_TOKENS ({len(tag_tokens)} 个，用于异象分类)")
    for kw in sorted(tag_tokens):
        lines.append(f"  - {kw}")
    
    if in_code:
        lines.append(f"\n[C] 核心代码中引用但未在 GENERAL_KEYWORDS 定义 ({len(in_code)} 个)")
        for kw in sorted(in_code):
            lines.append(f"  - {kw}")
    
    if in_packs_only:
        lines.append(f"\n[D] 卡包定义中出现但未在核心代码引用 ({len(in_packs_only)} 个)")
        for kw in sorted(in_packs_only):
            lines.append(f"  - {kw}")
    
    if in_docs_only:
        lines.append(f"\n[E] 规则文档/txt源文件提及 ({len(in_docs_only)} 个)")
        for kw in sorted(in_docs_only):
            lines.append(f"  - {kw}")
    
    lines.append(f"\n总计: {len(all_keywords)} 个不同的关键词/标签/词条")
    lines.append(f"  - 引擎已实现 (GENERAL_KEYWORDS): {len(general_kw)}")
    lines.append(f"  - 引擎已引用 (代码中硬编码): {len(in_code)}")
    lines.append(f"  - 仅卡包定义: {len(in_packs_only)}")
    lines.append(f"  - 仅文档提及: {len(in_docs_only)}")
    
    output_text = "\n".join(lines)
    print(output_text)
    
    with open(ROOT / "keywords_index.txt", "w", encoding="utf-8") as f:
        f.write(output_text)
    
    output_json = {
        "GENERAL_KEYWORDS": sorted(general_kw),
        "TAG_TOKENS": sorted(tag_tokens),
        "REFERENCED_IN_CODE": sorted(in_code),
        "IN_PACKS_ONLY": sorted(in_packs_only),
        "IN_DOCS_ONLY": sorted(in_docs_only),
        "ALL_KEYWORDS": sorted(all_keywords),
    }
    with open(ROOT / "keywords_index.json", "w", encoding="utf-8") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存到 keywords_index.txt 和 keywords_index.json")


if __name__ == "__main__":
    main()
