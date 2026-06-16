"""回归测试：确保 render_mixin 中使用的弹窗类已正确导入。

此前 _show_choice / _show_discover / _make_sacrifice_chooser 引用 ChoiceDialog、
DiscoverDialog、SacrificeDialog 时因未导入而抛出 NameError，导致抉择/开发/献祭
弹窗无法打开，游戏线程永久等待。"""


def test_render_mixin_dialog_imports():
    import gui.battle.render_mixin as rm

    assert hasattr(rm, "ChoiceDialog")
    assert hasattr(rm, "DiscoverDialog")
    assert hasattr(rm, "SacrificeDialog")
