"""回归测试：确保 render_mixin 中使用的弹窗类已正确导入。

此前 _show_choice / _show_discover / _make_sacrifice_chooser 引用 ChoiceDialog、
DiscoverDialog、SacrificeDialog 时因未导入而抛出 NameError，导致抉择/开发/献祭
弹窗无法打开，游戏线程永久等待。"""


def test_render_mixin_dialog_imports():
    import gui.battle.render_mixin as rm

    assert hasattr(rm, "ChoiceDialog")
    assert hasattr(rm, "DiscoverDialog")
    assert hasattr(rm, "SacrificeDialog")


def test_render_mixin_has_create_tab_gradient_photo():
    """DiscoverDialog/ChoiceDialog/SacrificeDialog 依赖 parent._create_tab_gradient_photo
    渲染卡牌稀有度渐变背景；该方法必须存在，否则弹窗初始化会抛出 AttributeError，
    导致卡牌选择弹窗空白。"""
    import gui.battle.render_mixin as rm

    assert hasattr(rm.RenderMixin, "_create_tab_gradient_photo")
