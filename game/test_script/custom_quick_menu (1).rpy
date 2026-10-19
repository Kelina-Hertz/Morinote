################################################################################
## Image quick menu
################################################################################

define quick_button_click_duration = 0.08


## A short delayed action lets the click artwork render before actions such as
## ShowMenu replace the current screen. Each use of this screen owns its state.
screen quick_button_entry(button_name, button_action, click_image=None,
        selected=False, selected_image=None, alternate_action=None,
        button_width=96, button_alt=""):

    default pressed = False
    default pending_action = NullAction()

    $ idle_image = selected_image if selected and selected_image else "images/quick_button/%s.png" % button_name
    $ hover_image = selected_image if selected and selected_image else "images/quick_button/%s_hover.png" % button_name
    $ pressed_image = click_image if click_image else "images/quick_button/%s_click.png" % button_name
    $ resolved_alternate = alternate_action if alternate_action is not None else button_action

    if pressed:
        timer quick_button_click_duration action [SetLocalVariable("pressed", False), pending_action]

    fixed:
        xysize (button_width, 60)

        imagebutton:
            align (0.5, 0.5)
            idle (pressed_image if pressed else idle_image)
            hover (pressed_image if pressed else hover_image)
            selected_idle (pressed_image if pressed else idle_image)
            selected_hover (pressed_image if pressed else hover_image)
            focus_mask True
            alt button_alt
            selected selected
            hover_sound ui_hover_sound
            activate_sound ui_click_sound
            action If(pressed, NullAction(), [
                SetLocalVariable("pending_action", button_action),
                SetLocalVariable("pressed", True),
            ])
            alternate If(pressed, NullAction(), [
                SetLocalVariable("pending_action", resolved_alternate),
                SetLocalVariable("pressed", True),
            ])


screen quick_menu():

    zorder 100

    if quick_menu:

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


## Touch uses the same artwork and state changes without any scaling animation.
screen quick_menu():
    variant "touch"

    zorder 100

    if quick_menu:

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
