################################################################################
## 自定义“关于 / 帮助”界面
##
## 本文件重新定义引擎默认的 about（关于）与 help（帮助）屏幕，风格与
## custom_settings.rpy 保持一致：
##   - 主色使用本作青色 #00FFFF；
##   - 左侧为分类导航面板，右侧为内容面板；
##   - 左上/左下使用青色枫叶（gui/window_icon.png）作水印；
##   - 右上角放置游戏 LOGO（gui/title.png）；
##   - 内容按分类切换，无需在游戏菜单外层滚动。
##
## 关于页重点展示 STAFF、CAST 与制作声明；
## 帮助页提供键盘、鼠标、手柄三类操作说明。
################################################################################

init python:

    ## 关于页各分类的标题与说明
    def about_tab_label(tab):
        return {
            "staff": _("STAFF"),
            "cast": _("CAST"),
            "notice": _("声明"),
        }.get(tab, "")

    def about_tab_desc(tab):
        return {
            "staff": _("本作的制作团队与分工"),
            "cast": _("主要角色与配音演员"),
            "notice": _("版权、年龄限制与免责说明"),
        }.get(tab, "")

    def about_staff_rows():
        return [
            (_("总策划"), _("小野寺日向")),
            (_("原案 & 编剧"), _("HUST基米")),
            (_("脚本"), _("洛鸢羽 / HUST基米")),
            (_("美术 & 作画"), _("枝冬")),
            (_("背景 CG"), _("Venwil")),
            (_("配音导演"), _("小野寺日向")),
            (_("音乐"), _("洛鸢羽 / 柯良 / ハサミ")),
            (_("制作"), _("洛鸢羽")),
        ]

    def about_cast_rows():
        return [
            (_("燕渡鸥"), _("浮光")),
            (_("林汐泉"), _("清梦")),
            (_("喻文竹"), _("")),
            (_("蓝雪"), _("沐夏")),
            (_("朱梦龙"), _("屠神灭世")),
        ]

    def about_notices():
        return [
            _("本作品纯属虚构。游戏中一切人名、地名、组织名等均为架空设计，与现实无任何关联。如有雷同，纯属巧合。"),
            _("本作品适合 14 周岁以上人群，所有登场人物均已年满十八周岁。"),
            _("制作组保留对游戏内容的最终解释权。"),
            _("此版本仅为游戏试玩测试版，不代表最终版本内容与品质。"),
        ]

    ## 帮助页各分类的标题与说明
    def help_tab_label(device):
        return {
            "keyboard": _("键盘操作"),
            "mouse": _("鼠标操作"),
            "gamepad": _("手柄操作"),
        }.get(device, "")

    def help_tab_desc(device):
        return {
            "keyboard": _("常用键盘快捷键"),
            "mouse": _("鼠标按键与滚轮操作"),
            "gamepad": _("手柄按键映射"),
        }.get(device, "")

    def help_rows(device):
        if device == "keyboard":
            return [
                (_("回车"), _("推进对话并激活界面。")),
                (_("空格"), _("在没有选择的情况下推进对话。")),
                (_("方向键"), _("导航界面。")),
                (_("Esc"), _("访问游戏菜单。")),
                (_("Ctrl"), _("按住时快进对话。")),
                (_("Tab"), _("切换对话快进。")),
                (_("PageUp"), _("回退至先前的对话。")),
                (_("PageDown"), _("向前至后来的对话。")),
                ("H", _("隐藏用户界面。")),
                ("S", _("截图。")),
                ("V", _("切换辅助机器朗读。")),
                (_("Shift+A"), _("打开无障碍菜单。")),
            ]

        elif device == "mouse":
            return [
                (_("左键点击"), _("推进对话并激活界面。")),
                (_("中键点击"), _("隐藏用户界面。")),
                (_("右键点击"), _("访问游戏菜单。")),
                (_("滚轮上"), _("回退至先前的对话。")),
                (_("滚轮下"), _("向前至后来的对话。")),
            ]

        else:
            return [
                (_("右扳机键\nA/底键"), _("推进对话并激活界面。")),
                (_("左扳机键\n左肩键"), _("回退至先前的对话。")),
                (_("右肩键"), _("向前至后来的对话。")),
                (_("十字键 / 摇杆"), _("导航界面。")),
                (_("开始 / 向导 / B键"), _("访问游戏菜单。")),
                (_("Y / 顶键"), _("隐藏用户界面。")),
            ]

    def split_rows(rows):
        half = (len(rows) + 1) // 2
        return rows[:half], rows[half:]


screen about():

    tag menu

    default current_tab = "staff"

    use game_menu(_("关于")):

        hbox:
            spacing 16

            ## 左侧分类导航面板（带枫叶水印）
            frame:
                style "info_rail"

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
                        style_prefix "info_tab"
                        spacing 10
                        xpos 12
                        ypos 12

                        textbutton _("STAFF"):
                            selected (current_tab == "staff")
                            action SetScreenVariable("current_tab", "staff")

                        textbutton _("CAST"):
                            selected (current_tab == "cast")
                            action SetScreenVariable("current_tab", "cast")

                        textbutton _("声明"):
                            selected (current_tab == "notice")
                            action SetScreenVariable("current_tab", "notice")

            ## 右侧内容面板
            frame:
                style "info_card"

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
                        style_prefix "info"
                        spacing 5
                        xpos 0
                        ypos 0

                        text about_tab_label(current_tab) style "info_header_text"
                        text about_tab_desc(current_tab) style "info_header_desc"

                    ## 头部与内容之间的分隔线
                    add Solid("#00ffff2e", xysize=(1040, 2)):
                        xpos 0
                        ypos 124

                    ## 内容区
                    vbox:
                        style_prefix "info"
                        spacing 10
                        xpos 0
                        ypos 138
                        xsize 1040

                        $ left_rows, right_rows = split_rows(about_staff_rows() if current_tab == "staff" else (about_cast_rows() if current_tab == "cast" else []))

                        if current_tab == "staff":

                            hbox:
                                spacing 40
                                xsize 1040

                                vbox:
                                    spacing 8
                                    xsize 500

                                    hbox:
                                        text _("职务") style "info_table_header_text" xsize 220
                                        text _("成员") style "info_table_header_text" xsize 280

                                    for role, name in left_rows:
                                        hbox:
                                            spacing 14
                                            xsize 500
                                            text role style "info_table_role_text" xsize 220
                                            text name style "info_table_name_text" xsize 266

                                if right_rows:
                                    vbox:
                                        spacing 8
                                        xsize 500

                                        hbox:
                                            text _("职务") style "info_table_header_text" xsize 220
                                            text _("成员") style "info_table_header_text" xsize 280

                                        for role, name in right_rows:
                                            hbox:
                                                spacing 14
                                                xsize 500
                                                text role style "info_table_role_text" xsize 220
                                                text name style "info_table_name_text" xsize 266

                        elif current_tab == "cast":

                            hbox:
                                spacing 40
                                xsize 1040

                                vbox:
                                    spacing 8
                                    xsize 500

                                    hbox:
                                        text _("角色") style "info_table_header_text" xsize 220
                                        text _("配音") style "info_table_header_text" xsize 280

                                    for chara, voice in left_rows:
                                        hbox:
                                            spacing 14
                                            xsize 500
                                            text chara style "info_table_role_text" xsize 220
                                            text voice style "info_table_name_text" xsize 266

                                if right_rows:
                                    vbox:
                                        spacing 8
                                        xsize 500

                                        hbox:
                                            text _("角色") style "info_table_header_text" xsize 220
                                            text _("配音") style "info_table_header_text" xsize 280

                                        for chara, voice in right_rows:
                                            hbox:
                                                spacing 14
                                                xsize 500
                                                text chara style "info_table_role_text" xsize 220
                                                text voice style "info_table_name_text" xsize 266

                        else:

                            for notice in about_notices():
                                text notice style "info_notice_text" xsize 1040

                            null height 8

                            hbox:
                                spacing 12
                                add Solid("#00ffff", xysize=(12, 12)) yalign 0.5
                                text "[config.name!t]  ·  v[config.version!t]" style "info_meta_text" yalign 0.5

                        null height 2

                        hbox:
                            spacing 10

                            add Solid("#00ffff", xysize=(12, 12)) yalign 0.5

                            text _("所有信息以游戏内实际内容为准。") style "info_hint_text" yalign 0.5


screen help():

    tag menu

    default device = "keyboard"

    use game_menu(_("帮助")):

        hbox:
            spacing 16

            ## 左侧分类导航面板（带枫叶水印）
            frame:
                style "info_rail"

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
                        style_prefix "info_tab"
                        spacing 10
                        xpos 12
                        ypos 12

                        textbutton _("键盘"):
                            selected (device == "keyboard")
                            action SetScreenVariable("device", "keyboard")

                        textbutton _("鼠标"):
                            selected (device == "mouse")
                            action SetScreenVariable("device", "mouse")

                        if GamepadExists():
                            textbutton _("手柄"):
                                selected (device == "gamepad")
                                action SetScreenVariable("device", "gamepad")

            ## 右侧内容面板
            frame:
                style "info_card"

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
                        style_prefix "info"
                        spacing 5
                        xpos 0
                        ypos 0

                        text help_tab_label(device) style "info_header_text"
                        text help_tab_desc(device) style "info_header_desc"

                    ## 头部与内容之间的分隔线
                    add Solid("#00ffff2e", xysize=(1040, 2)):
                        xpos 0
                        ypos 124

                    ## 内容区
                    vbox:
                        style_prefix "info"
                        spacing 10
                        xpos 0
                        ypos 138
                        xsize 1040

                        $ left_rows, right_rows = split_rows(help_rows(device))

                        hbox:
                            spacing 40
                            xsize 1040

                            vbox:
                                spacing 12
                                xsize 500

                                for key, desc in left_rows:
                                    hbox:
                                        spacing 14
                                        xsize 500
                                        text key style "info_key_text" xsize 170
                                        text desc style "info_desc_text" xsize 316

                            if right_rows:
                                vbox:
                                    spacing 12
                                    xsize 500

                                    for key, desc in right_rows:
                                        hbox:
                                            spacing 14
                                            xsize 500
                                            text key style "info_key_text" xsize 170
                                            text desc style "info_desc_text" xsize 316

                        if device == "gamepad":

                            null height 8

                            hbox:
                                spacing 12

                                textbutton _("校准手柄") style "info_small_button" action GamepadCalibrate()

                                text _("如按键无响应，可重新校准手柄。") style "info_hint_text" yalign 0.5

                        null height 2

                        hbox:
                            spacing 10

                            add Solid("#00ffff", xysize=(12, 12)) yalign 0.5

                            text _("帮助信息仅涵盖常用操作。") style "info_hint_text" yalign 0.5


################################################################################
## 样式
################################################################################

## 内容面板与左侧导航面板（共用圆角纹理）
style info_card:
    xsize 1100
    ysize 600
    padding (30, 24)
    background Frame("test_script/set_card.png", 20, 20, 20, 20)

style info_rail:
    xsize 264
    ysize 320
    xpadding 12
    ypadding 12
    background Frame("test_script/set_card.png", 20, 20, 20, 20)

style info_vbox is vbox

## 分类标签
style info_tab_button is button
style info_tab_button_text is button_text

style info_tab_button:
    xsize 240
    xpadding 16
    ypadding 10
    background Solid("#00ffff08")
    hover_background Solid("#00ffff1f")
    selected_background Solid("#00ffff")
    selected_hover_background Solid("#66ffff")

style info_tab_button_text:
    size 31
    xalign 0.0
    color "#8fbcc4"
    hover_color "#eaffff"
    selected_color "#002626"
    selected_hover_color "#002626"

## 头部栏
style info_header_text is gui_text
style info_header_desc is gui_text

style info_header_text:
    size 38
    color "#00ffff"

style info_header_desc:
    size 24
    color "#7fd6d6"

## 关于页表格
style info_table_header_text is gui_text
style info_table_role_text is gui_text
style info_table_name_text is gui_text

style info_table_header_text:
    size 25
    color "#00ffff"
    xalign 0.0
    yalign 0.5

style info_table_role_text:
    size 27
    color "#bffcfc"
    xalign 0.0
    yalign 0.5

style info_table_name_text:
    size 27
    color "#eaffff"
    xalign 0.0
    yalign 0.5

## 关于页声明与说明文字
style info_notice_text is gui_text
style info_meta_text is gui_text
style info_hint_text is gui_text

style info_notice_text:
    size 25
    color "#bffcfc"
    line_spacing 7

style info_meta_text:
    size 23
    color "#6fd0d0"

style info_hint_text:
    size 24
    color "#57b8b8"

## 帮助页按键与说明
style info_key_text is gui_text
style info_desc_text is gui_text

style info_key_text:
    size 26
    color "#00ffff"
    xalign 0.0
    yalign 0.5

style info_desc_text:
    size 25
    color "#a8e6e6"
    xalign 0.0
    yalign 0.5

## 小按钮（校准手柄）
style info_small_button is gui_button
style info_small_button_text is gui_button_text

style info_small_button:
    xpadding 20
    ypadding 8
    background Solid("#00ffff14")
    hover_background Solid("#00ffff2e")
    yalign 0.5

style info_small_button_text:
    size 26
    color "#8ff6f6"
    hover_color "#ffffff"
