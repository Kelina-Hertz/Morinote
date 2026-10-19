testsuite ui_qa:

    before testcase:
        $ _test.timeout = 4.0
        $ _test.transition_timeout = 0.2
        $ _test.screenshot_directory = "game/.ui_qa_screens"

        if not screen "main_menu":
            run MainMenu(confirm=False)

    teardown:
        exit


testcase ui_layout:

    run ShowMenu("preferences", _transition=None)
    pause 0.5
    click "文字"
    pause 0.2
    screenshot "preferences_text.png"

    click "音频"
    pause 0.2
    screenshot "preferences_audio.png"

    run ShowMenu("about", _transition=None)
    pause 0.5
    screenshot "about.png"

    run ShowMenu("help", _transition=None)
    pause 0.5
    screenshot "help.png"

    run Start("_ui_qa_scene")
    advance until "快捷菜单视觉检查"
    assert eval ("quick_menu")
    pause 0.2
    screenshot "quick_menu.png"

    click "历史"
    pause 0.2
    assert screen "history"


screen _ui_qa_quick_menu():

    zorder 200

    hbox:
        xalign 0.5
        yalign 1.0
        spacing 10

        use quick_button_entry("back", Rollback(), button_alt=_("回退"))
        use quick_button_entry("log", ShowMenu("history"), button_width=114, button_alt=_("历史"))
        use quick_button_entry(
            "skip",
            Skip(),
            click_image="images/quick_button/skiping.png",
            selected=renpy.is_skipping(),
            selected_image="images/quick_button/skiping.png",
            alternate_action=Skip(fast=True, confirm=True),
            button_alt=_("快进"),
        )
        use quick_button_entry(
            "auto",
            Preference("auto-forward", "toggle"),
            click_image="images/quick_button/autoing.png",
            selected=_preferences.afm_enable,
            selected_image="images/quick_button/autoing.png",
            button_alt=_("自动播放"),
        )
        use quick_button_entry("save", ShowMenu("save"), button_alt=_("保存"))
        use quick_button_entry("load", ShowMenu("load"), button_alt=_("读取"))
        use quick_button_entry("config", ShowMenu("preferences"), button_alt=_("设置"))
        use quick_button_entry("title", MainMenu(), button_alt=_("回到标题"))
        use quick_button_entry("record", ShowMenu("achievements"), button_alt=_("成就"))
        use quick_button_entry("quit", Quit(confirm=True), button_alt=_("退出游戏"))


label _ui_qa_scene:
    scene black
    $ quick_menu = True
    show screen _ui_qa_quick_menu
    "快捷菜单视觉检查"
    return
