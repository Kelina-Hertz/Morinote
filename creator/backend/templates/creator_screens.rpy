# Minimal redistributable UI; no private project art is included.
init 10 python:
    gui.init(config.screen_width, config.screen_height)
    config.check_conflicting_properties = True
    style.default.font = "fonts/SourceHanSansLite.ttf"
    style.default.size = 32
    style.default.color = "#eef5ff"
    style.button.background = Solid("#274259")
    style.button.hover_background = Solid("#3d6482")
    style.button.padding = (22, 12)
    style.button_text.color = "#eaf3ff"
    style.button_text.hover_color = "#ffffff"
    style.bar.left_bar = Solid("#6cb8c9")
    style.bar.right_bar = Solid("#21394b")
    style.bar.ysize = 18
    style.slider.left_bar = Solid("#6cb8c9")
    style.slider.right_bar = Solid("#21394b")
    style.slider.ysize = 18
    config.overlay_screens.append("quick_menu")

screen say(who, what):
    window:
        id "window"
        xfill True
        yalign 1.0
        ysize 285
        background Solid("#101d2bea")
        padding (110, 34)
        vbox:
            spacing 13
            if who:
                text who id "who" size 35 color "#98d5df"
            text what id "what" size 34

screen choice(items):
    vbox:
        align (.5, .5)
        spacing 20
        for item in items:
            textbutton item.caption action item.action xsize 850

screen quick_menu():
    zorder 100
    if not main_menu:
        hbox:
            align (.98, .985)
            spacing 8
            textbutton "回退" action Rollback() text_size 22
            textbutton "存档" action ShowMenu("save") text_size 22
            textbutton "读档" action ShowMenu("load") text_size 22
            textbutton "Auto" action Preference("auto-forward", "toggle") text_size 22
            textbutton "跳过" action Skip() text_size 22
            textbutton "设置" action ShowMenu("preferences") text_size 22

screen main_menu():
    tag menu
    add Solid("#132337")
    vbox:
        align (.5, .45)
        spacing 28
        text config.name size 66 xalign .5
        textbutton "开始游戏" action Start() xalign .5
        textbutton "读取存档" action ShowMenu("load") xalign .5
        textbutton "设置" action ShowMenu("preferences") xalign .5
        textbutton "退出" action Quit(confirm=False) xalign .5

screen creator_menu(title):
    add Solid("#142638f8")
    vbox:
        pos (120, 65)
        spacing 25
        text title size 48
        transclude
    hbox:
        pos (120, 950)
        spacing 25
        textbutton "返回" action Return()
        textbutton "标题" action MainMenu(confirm=False)

screen save():
    tag menu
    use creator_menu("保存进度"):
        use creator_slots("save")

screen load():
    tag menu
    use creator_menu("读取进度"):
        use creator_slots("load")

screen creator_slots(mode):
    grid 3 2:
        spacing 25
        for slot in range(1, 7):
            button:
                xysize (510, 295)
                action (FileSave(slot) if mode == "save" else FileLoad(slot))
                vbox:
                    spacing 10
                    add FileScreenshot(slot) xysize (460, 215)
                    text FileTime(slot, format="%Y/%m/%d %H:%M", empty="空存档") size 24
    hbox:
        spacing 15
        textbutton "上一页" action FilePagePrevious()
        textbutton "下一页" action FilePageNext()

screen preferences():
    tag menu
    use creator_menu("设置"):
        vbox:
            spacing 28
            text "文字速度"
            bar value Preference("text speed") xsize 850
            text "自动阅读等待"
            bar value Preference("auto-forward time") xsize 850
            text "音乐音量"
            bar value Preference("music volume") xsize 850
            text "音效音量"
            bar value Preference("sound volume") xsize 850
            text "语音音量"
            bar value Preference("voice volume") xsize 850
            hbox:
                spacing 20
                textbutton "窗口" action Preference("display", "window")
                textbutton "全屏" action Preference("display", "fullscreen")

screen confirm(message, yes_action, no_action):
    modal True
    zorder 200
    frame:
        align (.5, .5)
        padding (50, 40)
        background Solid("#152a40")
        vbox:
            spacing 25
            text message
            hbox:
                spacing 30
                textbutton "确认" action yes_action
                textbutton "取消" action no_action

screen notify(message):
    zorder 200
    frame:
        pos (40, 40)
        background Solid("#152a40dd")
        text message
    timer 3.0 action Hide("notify")
