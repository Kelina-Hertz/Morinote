################################################################################
## 自定义快捷菜单（quick_menu）
##
## 本文件重新定义了引擎默认的 quick_menu 屏幕，将原来的文字按钮替换为图片按钮。
##
## 素材位于 game/images/quick_button 目录，统一为 96x60：
##   back.png    回退（Rollback）
##   skip.png    快进（Skip），skiping.png 为正在快进时的状态
##   auto.png    自动播放（auto-forward），autoing.png 为正在自动播放时的状态
##   save.png    保存
##   load.png    读取
##   config.png  设置
##   title.png   回到标题
##   quit.png    退出游戏
##
## 以 ing 结尾的图片为“进行中”状态：按钮被选中（selected）时自动切换显示，
## 例如自动播放开启时显示 autoing.png，快进中显示 skiping.png。
## 悬停时按钮会轻微放大作为反馈（素材未提供专门 hover 图，故复用原图）。
################################################################################

screen quick_menu():

    zorder 100

    if quick_menu:

        hbox:
            xalign 0.5
            yalign 1.0
            spacing 12

            ## 回退
            imagebutton:
                idle "images/quick_button/back.png"
                hover Transform("images/quick_button/back.png", zoom=1.06)
                focus_mask True
                action Rollback()

            ## 快进（快进中显示 skiping.png；右键/长按快速快进）
            imagebutton:
                idle "images/quick_button/skip.png"
                hover Transform("images/quick_button/skip.png", zoom=1.06)
                selected_idle "images/quick_button/skiping.png"
                selected_hover Transform("images/quick_button/skiping.png", zoom=1.06)
                focus_mask True
                selected renpy.is_skipping()
                action Skip()
                alternate Skip(fast=True, confirm=True)

            ## 自动播放（自动播放中显示 autoing.png）
            imagebutton:
                idle "images/quick_button/auto.png"
                hover Transform("images/quick_button/auto.png", zoom=1.06)
                selected_idle "images/quick_button/autoing.png"
                selected_hover Transform("images/quick_button/autoing.png", zoom=1.06)
                focus_mask True
                selected _preferences.afm_enable
                action Preference("auto-forward", "toggle")

            ## 保存
            imagebutton:
                idle "images/quick_button/save.png"
                hover Transform("images/quick_button/save.png", zoom=1.06)
                focus_mask True
                action ShowMenu("save")

            ## 读取
            imagebutton:
                idle "images/quick_button/load.png"
                hover Transform("images/quick_button/load.png", zoom=1.06)
                focus_mask True
                action ShowMenu("load")

            ## 设置
            imagebutton:
                idle "images/quick_button/config.png"
                hover Transform("images/quick_button/config.png", zoom=1.06)
                focus_mask True
                action ShowMenu("preferences")

            ## 回到标题
            imagebutton:
                idle "images/quick_button/title.png"
                hover Transform("images/quick_button/title.png", zoom=1.06)
                focus_mask True
                action MainMenu()

            ## 退出游戏
            imagebutton:
                idle "images/quick_button/quit.png"
                hover Transform("images/quick_button/quit.png", zoom=1.06)
                focus_mask True
                action Quit(confirm=True)
