## Selected B / 剪贴色签 UI. Runtime assets live under gui/qingfeng/.
## Explicit late init replaces the legacy screens without touching story logic.
init offset = 20

define QF_ROOT = "gui/qingfeng/"
define QF_LABEL_FONT = "fonts/qingfeng/Round-Semibold.otf"
define QF_UI_FONT = "fonts/qingfeng/Round-Medium.otf"
define QF_BODY_FONT = "SourceHanSansLite.ttf"
define QF_INK = "#193f55"
define QF_MUTED = "#527387"

init python:
    import math

    def qf_asset(family, state="normal"):
        return QF_ROOT + "components/{}-{}.png".format(family, state)

    def qf_frame(family, state="normal"):
        borders = (18, 15, 20, 15) if family == "quick" else (48, 30, 56, 30)
        return Frame(qf_asset(family, state), *borders)

    def qf_panel(name="settings"):
        return Frame(QF_ROOT + "components/" + name + ".png", 80, 100, 190, 110)

    def qf_choice_height(caption):
        plain = renpy.filter_text_tags(caption, allow=[])
        lines = sum(max(1, int(math.ceil(len(line) / 20.0))) for line in plain.split("\n"))
        return max(88, 40 * lines + 32)

    def qf_speed_label():
        return _("即时") if _preferences.text_cps == 0 else _("{} 字/秒").format(int(_preferences.text_cps))

    def qf_percent(mixer):
        return "{}%".format(int(round(_preferences.get_volume(mixer) * 100)))

    def qf_all_muted():
        return all(_preferences.get_mute(m) for m in ("music", "sfx", "voice"))

    def qf_save_title(slot):
        title = renpy.filter_text_tags(FileSaveName(slot) or _("剧情存档"), allow=[])
        return title[:12] + "…" if len(title) > 13 else title

# Generic text and menus inherit readable body text, with explicit UI hierarchies.
style default:
    font QF_BODY_FONT

style gui_text:
    font QF_UI_FONT
    color QF_INK

style qf_label is gui_text:
    font QF_LABEL_FONT
    size 38
    kerning 2

style qf_text is gui_text:
    font QF_UI_FONT
    size 28

style qf_hint is qf_text:
    font QF_BODY_FONT
    size 23
    color QF_MUTED

style qf_button is button:
    background qf_frame("button")
    hover_background qf_frame("button", "focus")
    activate_background qf_frame("button", "pressed")
    selected_idle_background qf_frame("button", "selected")
    selected_hover_background qf_frame("button", "selected-focus")
    insensitive_background qf_frame("button", "disabled")
    padding (20, 8)
    hover_sound ui_hover_sound
    activate_sound ui_click_sound

style qf_button_text is button_text:
    font QF_LABEL_FONT
    size 27
    color QF_INK
    hover_color QF_INK
    selected_color QF_INK
    insensitive_color "#79909d"
    outlines []
    xalign 0.5
    yalign 0.5
    textalign 0.5
    kerning 1.2

style qf_tab is qf_button:
    background qf_frame("tab")
    hover_background qf_frame("tab", "focus")
    activate_background qf_frame("tab", "pressed")
    selected_idle_background qf_frame("tab", "selected")
    selected_hover_background qf_frame("tab", "selected-focus")
    insensitive_background qf_frame("tab", "disabled")

style qf_tab_text is qf_button_text:
    size 26

style qf_page is qf_button:
    background qf_frame("quick")
    hover_background qf_frame("quick", "focus")
    activate_background qf_frame("quick", "pressed")
    selected_idle_background qf_frame("quick", "selected")
    selected_hover_background qf_frame("quick", "selected-focus")
    insensitive_background qf_frame("quick", "disabled")
    padding (8, 5)

style qf_page_text is qf_button_text:
    font QF_UI_FONT
    size 25

style qf_slider is slider:
    xsize 560
    ysize 44
    left_bar QF_ROOT + "components/range-full.png"
    right_bar QF_ROOT + "components/range-empty.png"
    thumb QF_ROOT + "components/thumb-normal.png"
    hover_thumb QF_ROOT + "components/thumb-focus.png"
    thumb_offset 22
    left_gutter 0
    right_gutter 0

style vscrollbar:
    base_bar Solid("#afc8cd55")
    thumb Solid("#59a99bcc")
    hover_thumb Solid("#289fba")
    xsize 8
    unscrollable "hide"

screen qf_button(caption, action, width=216, height=68, kind="button", selected=None, button_id=None, default_focus=False):
    textbutton caption:
        id button_id
        style ("qf_" + kind)
        xysize (width, height)
        selected selected
        default_focus default_focus
        action action

screen qf_heading(caption, x=462, y=176, on_dark=False):
    add QF_ROOT + ("icons/leaf-solid-white.png" if on_dark else "icons/leaf-solid-green.png") pos (x, y+9) xysize (31, 31)
    text caption style "qf_label" pos (x+48, y) color ("#f3faf8" if on_dark else QF_INK)

screen qf_backdrop():
    if main_menu:
        add QF_ROOT + "main_visual.png"
    add Solid("#06162680")

screen qf_navigation():
    vbox:
        pos (92, 174)
        spacing 10
        if not main_menu:
            use qf_button(_("保存存档"), ShowMenu("save"))
        use qf_button(_("读取存档"), ShowMenu("load"))
        use qf_button(_("游戏设置"), ShowMenu("preferences"))
        if not main_menu:
            use qf_button(_("对话历史"), ShowMenu("history"))
        use qf_button(_("小说模式"), ShowMenu("OVA"))
        use qf_button(_("成就一览"), ShowMenu("achievements"))
        use qf_button(_("关于作品"), ShowMenu("about"))
        use qf_button(_("操作帮助"), ShowMenu("help"))
    fixed:
        pos (92, 924)
        xysize (216, 68)
        use qf_button(_("返回"), Return(), button_id="qf_return")

# Keep all six actual main-menu actions. Logo pixels are already in main_visual.
screen main_menu():
    tag menu
    add QF_ROOT + "main_visual.png"
    for key, x, width, action, alt_text in (
        ("start", 120, 330, Start(), _("开始游戏")),
        ("load", 468, 252, ShowMenu("load"), _("读取存档")),
        ("ova", 738, 252, ShowMenu("OVA"), _("小说模式")),
        ("achievements", 1008, 252, ShowMenu("achievements"), _("成就一览")),
        ("settings", 1278, 252, ShowMenu("preferences"), _("游戏设置")),
        ("quit", 1548, 252, Quit(confirm=True), _("退出游戏")),
    ):
        imagebutton:
            id ("qf_main_" + key)
            pos (x, 954)
            xysize (width, 92)
            idle QF_ROOT + "menu/" + key + "-normal.png"
            hover QF_ROOT + "menu/" + key + "-focus.png"
            activate_foreground QF_ROOT + "menu/" + key + "-pressed.png"
            insensitive QF_ROOT + "menu/" + key + "-disabled.png"
            alt alt_text
            action action

screen say(who, what):
    window:
        id "window"
        style "qf_say_window"
        if who is not None:
            $ name_width = min(540, max(230, 102 + len(renpy.filter_text_tags(who, allow=[]))*30))
            window:
                id "namebox"
                style "qf_namebox"
                xsize name_width
                text who id "who" style "qf_name"
        text what id "what" style "qf_dialogue"
        add QF_ROOT + "icons/icon-next-ink.png" pos (1679, 152) xysize (28, 28)
    if not renpy.variant("small"):
        add SideImage() xalign 0.0 yalign 1.0

style qf_say_window is default:
    pos (80, 770)
    xysize (1760, 280)
    background QF_ROOT + "components/dialogue.png"
    padding (0, 0)

style qf_namebox is default:
    pos (44, -28)
    ysize 62
    background Frame(QF_ROOT + "components/name-demo.png", 70, 25, 40, 25)
    padding (66, 0, 20, 0)

style qf_name is default:
    font QF_LABEL_FONT
    size 28
    color QF_INK
    xalign 0.5
    yalign 0.5
    kerning 1.2
    outlines []

style qf_dialogue is default:
    font QF_BODY_FONT
    size 34
    color QF_INK
    pos (82, 63)
    xsize 1500
    line_spacing 16
    adjust_spacing False
    outlines []

# Character injects these native styles into the named screen widgets.
# Clear legacy properties so old textbox/namebox art cannot override B.
style window is qf_say_window:
    clear
style namebox is qf_namebox:
    clear
style say_label is qf_name:
    clear
style say_dialogue is qf_dialogue:
    clear
style say_thought is qf_dialogue:
    clear

screen choice(items):
    $ heights = [qf_choice_height(i.caption) for i in items]
    $ total = sum(heights) + max(0, len(items)-1)*18
    viewport:
        id "qf_choice_viewport"
        pos (240, max(110, (890-min(590, total))//2))
        xysize (820, min(590, total))
        mousewheel True
        draggable True
        pagekeys True
        scrollbars "vertical"
        side_yfill True
        vbox:
            spacing 18
            for index, i in enumerate(items):
                textbutton i.caption:
                    id ("qf_choice_" + str(index))
                    style "qf_choice"
                    ysize heights[index]
                    action i.action

style qf_choice is qf_button:
    xsize 800
    background qf_frame("choice")
    hover_background qf_frame("choice", "focus")
    activate_background qf_frame("choice", "pressed")
    selected_idle_background qf_frame("choice", "selected")
    selected_hover_background qf_frame("choice", "selected-focus")
    insensitive_background qf_frame("choice", "disabled")
    padding (94, 14, 59, 14)

style qf_choice_text is qf_button_text:
    font QF_UI_FONT
    size 30
    xalign 0.0
    textalign 0.0
    kerning 0.4
    layout "greedy"

screen quick_menu():
    zorder 100
    if quick_menu and not main_menu and not renpy.context()._menu:
        hbox:
            pos (766, 985)
            spacing 8
            use qf_quick("back", _("回退"), Rollback())
            use qf_quick("skip", _("快进"), Skip(), selected=bool(renpy.is_skipping()), alternate=Skip(fast=True, confirm=True))
            use qf_quick("auto", _("自动"), Preference("auto-forward", "toggle"), selected=_preferences.afm_enable)
            use qf_quick("save", _("保存"), ShowMenu("save"))
            use qf_quick("load", _("读取"), ShowMenu("load"))
            use qf_quick("settings", _("设置"), ShowMenu("preferences"))
            use qf_quick("title", _("标题"), MainMenu())
            use qf_quick("quit", _("退出"), Quit(confirm=True))

screen qf_quick(icon, caption, action, selected=None, alternate=None):
    button:
        id ("qf_quick_" + icon)
        style "qf_quick"
        action action
        alternate alternate
        selected selected
        alt caption
        hbox:
            xalign 0.5
            yalign 0.5
            spacing 7
            add QF_ROOT + "icons/icon-" + icon + "-ink.png" xysize (25, 25) yalign 0.5
            text caption style "qf_quick_text" yalign 0.5

style qf_quick is qf_page:
    xysize (116, 50)
    padding (12, 7)

style qf_quick_text is qf_button_text:
    size 22
    kerning 0.7

# The standard wrapper also skins existing / future menu consumers.
screen game_menu(title, scroll=None, yinitial=0.0, spacing=0):
    use qf_backdrop
    add qf_panel() pos (350, 110) xysize (1480, 860)
    use qf_heading(title, 414, 145)
    use qf_navigation
    if main_menu:
        key "game_menu" action ShowMenu("main_menu")
    fixed:
        pos (414, 260)
        xysize (1330, 630)
        if scroll:
            viewport:
                yinitial yinitial
                mousewheel True
                draggable True
                pagekeys True
                scrollbars "vertical"
                side_yfill True
                vbox:
                    xsize 1290
                    spacing spacing
                    transclude
        else:
            transclude

screen qf_setting_bar(caption, value, readout, y):
    text caption style "qf_text" pos (470, y-6)
    bar:
        id ("qf_range_" + caption)
        style "qf_slider"
        pos (749, y-4)
        value value
    text readout style "qf_text" xpos 1420 xanchor 1.0 ypos y-6

screen qf_setting_toggle(caption, action, selected, y, hint=None, button_id=None):
    text caption style "qf_text" pos (470, y)
    if hint:
        text hint style "qf_hint" pos (470, y+43) xsize 700
    imagebutton:
        id button_id
        pos (1220, y)
        xysize (80, 48)
        idle QF_ROOT + "components/toggle-off.png"
        hover QF_ROOT + "components/toggle-off-focus.png"
        selected_idle QF_ROOT + "components/toggle-on.png"
        selected_hover QF_ROOT + "components/toggle-on-focus.png"
        insensitive QF_ROOT + "components/toggle-disabled.png"
        selected selected
        action action
        alt caption
    text (_("开启") if selected else _("关闭")) style "qf_text" pos (1320, y+6) size 25

screen preferences():
    tag menu
    default qf_tab = "text"
    use qf_backdrop
    use qf_navigation
    add QF_ROOT + "components/settings.png" pos (400, 140)
    use qf_heading(_("游戏设置"))
    hbox:
        pos (465, 253)
        spacing 14
        for caption, key in ((_("阅读"), "text"), (_("声音"), "audio"), (_("显示"), "display"), (_("快进"), "skip")):
            use qf_button(caption, SetScreenVariable("qf_tab", key), width=180, height=60, kind="tab", selected=qf_tab==key)
    if qf_tab == "text":
        use qf_setting_bar(_("文字速度"), Preference("text speed"), qf_speed_label(), 374)
        use qf_setting_bar(_("自动阅读间隔"), Preference("auto-forward time"), _("{:.1f} 秒").format(_preferences.afm_time), 496)
        use qf_setting_bar(_("字体大小"), Preference("font size"), "{}%".format(int(_preferences.font_size*100)), 618)
    elif qf_tab == "audio":
        use qf_setting_bar(_("音乐音量"), Preference("music volume"), qf_percent("music"), 374)
        use qf_setting_bar(_("音效音量"), Preference("sound volume"), qf_percent("sfx"), 470)
        use qf_setting_bar(_("语音音量"), Preference("voice volume"), qf_percent("voice"), 566)
        use qf_setting_toggle(_("全部静音"), Preference("all mute", "toggle"), qf_all_muted(), 672, button_id="qf_mute")
    elif qf_tab == "display":
        text _("窗口模式") style "qf_text" pos (470, 364)
        hbox:
            pos (743, 350)
            spacing 14
            use qf_button(_("窗口"), Preference("display", "window"), width=216)
            use qf_button(_("全屏"), Preference("display", "fullscreen"), width=216)
        use qf_setting_toggle(_("显示文本窗口"), Preference("show empty window", "toggle"), _preferences.show_empty_window, 486,
            hint=_("无台词时也保留阅读底板。"), button_id="qf_empty_window")
        use qf_setting_toggle(_("转场效果"), Preference("transitions", "toggle"), _preferences.transitions != 0, 614,
            hint=_("切换场景时显示过渡动画。"), button_id="qf_transitions")
    else:
        use qf_setting_toggle(_("跳过未读文本"), Preference("skip", "toggle"), _preferences.skip_unseen, 364,
            hint=_("关闭时只快进已读过的内容。"), button_id="qf_skip_unread")
        use qf_setting_toggle(_("选项后继续快进"), Preference("after choices", "toggle"), _preferences.skip_after_choices, 514,
            hint=_("关闭时在选项之后停止快进。"), button_id="qf_skip_choices")
    text _("设置即时生效并自动保存。") style "qf_hint" pos (470, 807) size 21
    fixed:
        pos (1230, 782)
        xysize (216, 68)
        use qf_button(_("返回"), Return(), button_id="qf_settings_return")
    if main_menu:
        key "game_menu" action ShowMenu("main_menu")

screen save():
    tag menu
    use file_slots(_("保存存档"), saving=True)

screen load():
    tag menu
    use file_slots(_("读取存档"))

screen file_slots(title, saving=False):
    default page_name_value = FilePageNameInputValue(pattern=_("第 {} 页"), auto=_("自动存档"), quick=_("快速存档"))
    use qf_backdrop
    use qf_heading(title, 170, 70, on_dark=True)
    hbox:
        pos (850, 65)
        spacing 10
        use qf_button(_("保存"), ShowMenu("save"), width=150, selected=saving)
        use qf_button(_("读取"), ShowMenu("load"), width=150, selected=not saving)
        use qf_button(_("设置"), ShowMenu("preferences"), width=150)
        use qf_button(_("返回"), Return())
    button:
        pos (170, 136)
        xysize (460, 48)
        background None
        key_events True
        action page_name_value.Toggle()
        input:
            id "qf_page_name"
            style "qf_text"
            color "#f3faf8"
            value page_name_value
    grid 3 2:
        pos (170, 200)
        xspacing 75
        yspacing 56
        for slot in range(1, 7):
            button:
                id ("qf_slot_" + str(slot))
                style "qf_slot"
                action FileAction(slot)
                alt ((_("存档位 ") + str(slot)) if FileLoadable(slot) else (_("空存档位 ") + str(slot)))
                fixed:
                    if FileLoadable(slot):
                        viewport:
                            pos (22, 22)
                            xysize (406, 172)
                            add FileScreenshot(slot) xysize (406, 172) fit "cover"
                        frame:
                            pos (30, 30)
                            xysize (53, 39)
                            background Solid("#effaf7")
                            padding (0, 0)
                            text "{:02d}".format(slot) style "qf_text" size 22 xalign 0.5 yalign 0.5
                        text qf_save_title(slot):
                            style "qf_text"
                            font QF_LABEL_FONT
                            pos (32, 207)
                            size 27
                            xsize 380
                            substitute False
                            layout "nobreak"
                        text FileTime(slot, format="%Y-%m-%d %H:%M") style "qf_hint" pos (32, 249) size 21
                    else:
                        text "＋" style "qf_text" size 43 xalign 0.5 ypos 94
                        text _("空存档位") style "qf_text" size 26 xalign 0.5 ypos 174
                        text "{:02d}".format(slot) style "qf_hint" size 20 pos (32, 243)
                key "save_delete" action FileDelete(slot)
    hbox:
        pos (220, 944)
        spacing 8
        use qf_button("<", FilePagePrevious(), width=70, height=50, kind="page")
        if config.has_autosave:
            use qf_button(_("自动"), FilePage("auto"), width=94, height=50, kind="page")
        if config.has_quicksave:
            use qf_button(_("快速"), FilePage("quick"), width=94, height=50, kind="page")
        for page in range(1, 10):
            use qf_button(str(page), FilePage(page), width=70, height=50, kind="page")
        use qf_button(">", FilePageNext(), width=70, height=50, kind="page")
    key "save_page_prev" action FilePagePrevious()
    key "save_page_next" action FilePageNext()
    if main_menu:
        key "game_menu" action ShowMenu("main_menu")

style qf_slot is qf_button:
    xysize (450, 294)
    padding (0, 0)
    background qf_asset("slot")
    hover_background qf_asset("slot", "focus")
    activate_background qf_asset("slot", "pressed")
    selected_idle_background qf_asset("slot", "selected")
    selected_hover_background qf_asset("slot", "selected-focus")
    insensitive_background qf_asset("slot", "disabled")

screen confirm(message, yes_action, no_action):
    modal True
    zorder 200
    add Solid("#041320a0")
    add QF_ROOT + "components/modal.png" pos (580, 333)
    text _("请确认") style "qf_label" pos (632, 373) size 36
    text _(message):
        style "qf_hint"
        pos (632, 445)
        xsize 645
        size 28
        layout "subtitle"
    fixed:
        pos (632, 569)
        xysize (216, 68)
        use qf_button(_("取消"), no_action, default_focus=True, button_id="qf_cancel")
    fixed:
        pos (1067, 569)
        xysize (216, 68)
        use qf_button(_("确定"), yes_action, button_id="qf_confirm")
    key "game_menu" action no_action

# History keeps all original dialogue text, names and allowed tags.
screen history():
    tag menu
    predict False
    use game_menu(_("对话历史"), scroll="viewport", yinitial=1.0, spacing=24):
        if not _history_list:
            text _("尚无对话历史记录。") style "qf_hint"
        for h in _history_list:
            vbox:
                spacing 8
                if h.who:
                    text h.who style "qf_text" font QF_LABEL_FONT substitute False
                text renpy.filter_text_tags(h.what, allow=gui.history_allow_tags):
                    font QF_BODY_FONT
                    color QF_INK
                    size 30
                    xsize 1240
                    substitute False
                add Solid("#8ebec444") xysize (1240, 1)

screen about():
    tag menu
    default qf_about_tab = "staff"
    use game_menu(_("关于作品")):
        vbox:
            spacing 28
            hbox:
                spacing 14
                for caption, key in ((_("制作团队"), "staff"), (_("配音演员"), "cast"), (_("作品声明"), "notice")):
                    use qf_button(caption, SetScreenVariable("qf_about_tab", key), width=216, height=60, kind="tab", selected=qf_about_tab==key)
            viewport:
                ysize 490
                mousewheel True
                scrollbars "vertical"
                vbox:
                    spacing 16
                    if qf_about_tab == "notice":
                        for line in about_notices():
                            text line style "qf_text" xsize 1220
                        text ("Ren'Py " + renpy.version_only) style "qf_hint"
                    else:
                        for role, name in (about_staff_rows() if qf_about_tab=="staff" else about_cast_rows()):
                            hbox:
                                text role style "qf_hint" xsize 270
                                text (name or _("待公布")) style "qf_text" xsize 940

screen help():
    tag menu
    default device = "keyboard"
    use game_menu(_("操作帮助")):
        vbox:
            spacing 28
            hbox:
                spacing 14
                for caption, key in ((_("键盘"), "keyboard"), (_("鼠标"), "mouse"), (_("手柄"), "gamepad")):
                    use qf_button(caption, SetScreenVariable("device", key), width=180, height=60, kind="tab", selected=device==key)
            viewport:
                ysize 490
                scrollbars "vertical"
                mousewheel True
                vbox:
                    spacing 16
                    for key, desc in help_rows(device):
                        hbox:
                            text key style "qf_text" font QF_LABEL_FONT xsize 270
                            text desc style "qf_hint" xsize 940
                    if device == "gamepad":
                        use qf_button(_("校准手柄"), GamepadCalibrate())

screen achievements():
    tag menu
    use game_menu(_("成就一览"), scroll="viewport", spacing=18):
        text _("已达成 [achievement_unlocked_count()] / [achievement_total_count()]") style "qf_text"
        for item in ACHIEVEMENTS:
            $ unlocked = achievement.has(item["id"])
            frame:
                background qf_frame("choice", "selected" if unlocked else "normal")
                xsize 1280
                padding (42, 22)
                hbox:
                    spacing 26
                    add QF_ROOT + ("icons/leaf-solid-green.png" if unlocked else "icons/leaf-outline-green.png") xysize (34, 34)
                    vbox:
                        spacing 8
                        text item["name"] style "qf_text" font QF_LABEL_FONT
                        text (item["description"] if unlocked else (_("达成条件：")+item.get("hint", ""))) style "qf_hint" xsize 1100

screen OVA():
    tag menu
    use game_menu(_("小说模式"), scroll="viewport", spacing=24):
        text _("阅读记录 [ova_completed_count()] / [len(OVA_NOVELS)]") style "qf_hint"
        for novel in OVA_NOVELS:
            button:
                style "qf_button"
                xsize 1280
                ysize 190
                action Start(novel["label"])
                fixed:
                    text novel["index"] style "qf_label" pos (20, 18)
                    vbox:
                        pos (110, 20)
                        spacing 9
                        text novel["title"] style "qf_text" font QF_LABEL_FONT
                        if novel["subtitle"]:
                            text novel["subtitle"] style "qf_hint"
                        if novel["description"]:
                            text novel["description"] style "qf_hint" xsize 840
                        text novel["reading_time"] style "qf_hint"
                    text (_("已完成") if ova_is_completed(novel["id"]) else _("开始阅读")) style "qf_text" xpos 1060 ypos 55

screen ova_nvl(dialogue, items=None):
    add "gui/scene/classroom1.png"
    add Solid("#06162680")
    add qf_panel() pos (120, 70) xysize (1680, 880)
    use qf_heading(ova_current_title or _("小说模式"), 184, 105)
    viewport:
        pos (220, 210)
        xysize (1480, 680)
        yinitial 1.0
        mousewheel True
        draggable True
        pagekeys True
        vbox:
            xsize 1420
            spacing 28
            for d in dialogue:
                window:
                    id d.window_id
                    style "qf_nvl_entry"
                    vbox:
                        spacing 8
                        if d.who is not None:
                            text d.who id d.who_id style "qf_text" font QF_LABEL_FONT
                        text d.what id d.what_id style "qf_nvl_body"
            if items:
                vbox:
                    id "menu"
                    spacing 12
                    for i in items:
                        textbutton i.caption style "qf_choice" action i.action

style qf_nvl_entry is empty:
    xfill True
    background None

style qf_nvl_body is default:
    font QF_BODY_FONT
    size 34
    color QF_INK
    line_spacing 14
    xsize 1420

screen input(prompt):
    window:
        style "qf_say_window"
        vbox:
            pos (82, 35)
            spacing 15
            text prompt style "qf_text"
            input id "input" style "qf_text" color QF_INK

screen notify(message):
    zorder 100
    frame:
        pos (48, 44)
        background qf_frame("choice")
        padding (32, 18)
        text message style "qf_text" size 24
    timer 3.25 action Hide("notify")

screen skip_indicator():
    zorder 100
    frame:
        pos (48, 44)
        background qf_frame("choice", "selected")
        padding (28, 14)
        hbox:
            spacing 12
            add QF_ROOT + "icons/icon-skip-ink.png" xysize (30, 30)
            text _("正在快进") style "qf_text" size 24
