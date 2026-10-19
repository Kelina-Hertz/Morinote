################################################################################
## 自定义“设置”界面（v2）
##
## 本文件重新定义了引擎默认的 preferences（设置）屏幕，用于替换默认设置界面。
##
## 设计要点（v2）：
##   - 主题色采用本作青色 #00FFFF，整体配色围绕青色系展开；
##   - 左上/左下以青色枫叶（datas/window_icon.png）作水印装饰；
##   - 右上角放置游戏 LOGO（datas/title.png）；
##   - 左侧为独立的分类导航面板，右侧为内容面板，无需滚动；
##   - 顶部为“分类标题 + 说明 + LOGO”的头部栏，内容区按分类展示；
##   - 滑条旁实时显示当前数值，所有修改即时生效并自动保存。
##
## 文件位于 game/test_script 目录，Ren'Py 会自动加载；
## 由于本文件的定义晚于 screens.rpy 中的同名屏幕，因此会替换默认设置界面。
################################################################################

init python:

    ## 各分类标签的标题与说明文字
    def set_tab_label(tab):
        return {
            "display": _("显示设置"),
            "text": _("文字设置"),
            "audio": _("音频设置"),
            "skip": _("快进设置"),
        }.get(tab, "")

    def set_tab_desc(tab):
        return {
            "display": _("调整窗口模式与画面显示效果"),
            "text": _("调整文字速度与阅读体验"),
            "audio": _("调整各音轨的音量大小"),
            "skip": _("调整快进的范围与行为"),
        }.get(tab, "")


screen preferences():

    tag menu

    default current_tab = "display"

    use game_menu(_("设置")):

        hbox:
            spacing 16

            ## 左侧分类导航面板（带枫叶水印）
            frame:
                style "set_rail"

                fixed:
                    xfill True
                    yfill True

                    add "gui/window_icon.png":
                        xalign 1.0
                        yalign 1.0
                        alpha 0.12
                        zoom 0.9
                        xoffset 2
                        yoffset 2

                    vbox:
                        style_prefix "set_tab"
                        spacing 10
                        xpos 12
                        ypos 12

                        textbutton _("显示"):
                            selected (current_tab == "display")
                            action SetScreenVariable("current_tab", "display")

                        textbutton _("文字"):
                            selected (current_tab == "text")
                            action SetScreenVariable("current_tab", "text")

                        textbutton _("音频"):
                            selected (current_tab == "audio")
                            action SetScreenVariable("current_tab", "audio")

                        textbutton _("快进"):
                            selected (current_tab == "skip")
                            action SetScreenVariable("current_tab", "skip")

            ## 右侧内容面板
            frame:
                style "set_card"

                fixed:
                    xfill True
                    yfill True

                    ## 左下角枫叶水印
                    add "gui/window_icon.png":
                        xalign 0.0
                        yalign 1.0
                        alpha 0.13
                        zoom 1.0
                        xoffset 2
                        yoffset 4

                    ## 右上角 LOGO
                    add "gui/title.png":
                        xalign 1.0
                        yalign -0.0
                        xsize 370
                        ysize 108
                        xoffset -4
                        yoffset -6

                    ## 头部栏：当前分类标题与说明
                    vbox:
                        style_prefix "set"
                        spacing 5
                        xpos 0
                        ypos 0

                        text set_tab_label(current_tab) style "set_header_text"
                        text set_tab_desc(current_tab) style "set_header_desc"

                    ## 头部与内容之间的分隔线
                    add Solid("#00ffff2e", xysize=(1040, 2)):
                        xpos 0
                        ypos 124

                    ## 内容区
                    vbox:
                        style_prefix "set"
                        spacing 13
                        xpos 0
                        ypos 142
                        xsize 1040

                        if current_tab == "display":

                            label _("窗口模式")

                            hbox:
                                spacing 28

                                textbutton _("窗口") style "set_radio" action Preference("display", "window")
                                textbutton _("全屏") style "set_radio" action Preference("display", "fullscreen")

                            null height 8

                            label _("文本窗口")

                            hbox:
                                spacing 28

                                textbutton _("无文本时也显示窗口") style "set_check" selected _preferences.show_empty_window action Preference("show empty window", "toggle")

                            null height 8

                            label _("转场")

                            hbox:
                                spacing 28

                                textbutton _("显示转场效果") style "set_check" selected (_preferences.transitions != 0) action Preference("transitions", "toggle")

                        elif current_tab == "text":

                            label _("文字速度")

                            hbox:
                                spacing 18

                                bar value Preference("text speed") style "set_slider"

                                if _preferences.text_cps == 0:
                                    text _("即时") style "set_value_text" xsize 130 textalign 0.5 yalign 0.5
                                else:
                                    text "[_preferences.text_cps] 字/秒" style "set_value_text" xsize 130 textalign 0.5 yalign 0.5

                            label _("自动前进间隔")

                            hbox:
                                spacing 18

                                bar value Preference("auto-forward time") style "set_slider"

                                if _preferences.afm_time == 0:
                                    text _("关闭") style "set_value_text" xsize 130 textalign 0.5 yalign 0.5
                                else:
                                    text "[_preferences.afm_time] 秒" style "set_value_text" xsize 130 textalign 0.5 yalign 0.5

                            label _("界面字体大小")

                            hbox:
                                spacing 18

                                bar value Preference("font size") style "set_slider"

                                text "[int(_preferences.font_size * 100)]%" style "set_value_text" xsize 130 textalign 0.5 yalign 0.5

                        elif current_tab == "audio":

                            label _("音乐音量")

                            hbox:
                                spacing 18

                                bar value Preference("music volume") style "set_slider"

                                text "[int(_preferences.volumes.get('music', 1.0) * 100)]%" style "set_value_text" xsize 130 textalign 0.5 yalign 0.5

                            label _("音效音量")

                            hbox:
                                spacing 18

                                bar value Preference("sound volume") style "set_slider"

                                text "[int(_preferences.volumes.get('sound', 1.0) * 100)]%" style "set_value_text" xsize 130 textalign 0.5 yalign 0.5

                                if config.sample_sound:
                                    textbutton _("试听") style "set_small_button" action Play("sound", config.sample_sound)

                            label _("语音音量")

                            hbox:
                                spacing 18

                                bar value Preference("voice volume") style "set_slider"

                                text "[int(_preferences.volumes.get('voice', 1.0) * 100)]%" style "set_value_text" xsize 130 textalign 0.5 yalign 0.5

                                if config.sample_voice:
                                    textbutton _("试听") style "set_small_button" action Play("voice", config.sample_voice)

                            null height 4

                            hbox:
                                spacing 18

                                textbutton _("全部静音") style "set_check" selected (all(_preferences.mute.values()) if _preferences.mute else False) action Preference("all mute", "toggle")

                                text _("一键关闭或恢复所有声音") style "set_hint_text" yalign 0.5

                        else:

                            label _("快进范围")

                            hbox:
                                spacing 28

                                textbutton _("仅已读文本") style "set_radio" selected (not _preferences.skip_unseen) action Preference("skip", "seen")
                                textbutton _("全部文本") style "set_radio" selected _preferences.skip_unseen action Preference("skip", "all")

                            null height 8

                            label _("快进行为")

                            hbox:
                                spacing 28

                                textbutton _("选项后继续") style "set_check" selected _preferences.skip_after_choices action Preference("after choices", "toggle")

                        null height 2

                        hbox:
                            spacing 10

                            add Solid("#00ffff", xysize=(12, 12)) yalign 0.5

                            text _("设置会即时生效并自动保存。") style "set_hint_text" yalign 0.5


################################################################################
## 样式
################################################################################

## 内容面板与左侧导航面板（共用圆角纹理）
style set_card:
    xsize 1100
    ysize 600
    padding (30, 24)
    background Frame("test_script/set_card.png", 20, 20, 20, 20)

style set_rail:
    xsize 264
    ysize 320
    xpadding 12
    ypadding 12
    background Frame("test_script/set_card.png", 20, 20, 20, 20)

style set_vbox is vbox

## 分类标签
style set_tab_button is button
style set_tab_button_text is button_text

style set_tab_button:
    xsize 240
    xpadding 16
    ypadding 10
    background Solid("#00ffff08")
    hover_background Solid("#00ffff1f")
    selected_background Solid("#00ffff")
    selected_hover_background Solid("#66ffff")

style set_tab_button_text:
    size 31
    xalign 0.0
    color "#8fbcc4"
    hover_color "#eaffff"
    selected_color "#002626"
    selected_hover_color "#002626"

## 头部栏
style set_header_text is gui_text
style set_header_desc is gui_text

style set_header_text:
    size 38
    color "#00ffff"

style set_header_desc:
    size 24
    color "#7fd6d6"

## 单选 / 复选按钮
style set_radio is radio_button
style set_radio_text is radio_button_text
style set_check is check_button
style set_check_text is check_button_text

style set_radio_text:
    size 30

style set_check_text:
    size 30

## 滑条
style set_slider is slider
style set_slider:
    xsize 760

## 文本
style set_label is gui_label
style set_label_text is gui_label_text
style set_value_text is gui_text
style set_hint_text is gui_text

style set_label_text:
    size 32
    color "#bffcfc"

style set_value_text:
    size 26
    color "#6fd0d0"

style set_hint_text:
    size 24
    color "#57b8b8"

## 小按钮（试听）
style set_small_button is gui_button
style set_small_button_text is gui_button_text

style set_small_button:
    xpadding 20
    ypadding 8
    background Solid("#00ffff14")
    hover_background Solid("#00ffff2e")
    yalign 0.5

style set_small_button_text:
    size 26
    color "#8ff6f6"
    hover_color "#ffffff"
