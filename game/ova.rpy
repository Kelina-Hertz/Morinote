## OVA 小说目录、阅读界面与篇章脚本。

define OVA_NOVELS = (
    {
        "id": "test_OVA",
        "label": "test_OVA",
        "index": "01",
        "title": "test_OVA",
        "subtitle": "",
        "description": "",
        "reading_time": "约 3 分钟",
    },
)

default persistent.ova_completed = []
default ova_current_id = None
default ova_current_title = ""


init python:
    def ova_get_novel(ova_id):
        for novel in OVA_NOVELS:
            if novel["id"] == ova_id:
                return novel
        return None


    def ova_is_completed(ova_id):
        completed = getattr(persistent, "ova_completed", None) or []
        return ova_id in completed


    def ova_completed_count():
        return sum(1 for novel in OVA_NOVELS if ova_is_completed(novel["id"]))


    def ova_mark_completed(ova_id):
        if ova_get_novel(ova_id) is None:
            renpy.error("Unknown OVA id: {}".format(ova_id))

        completed = list(getattr(persistent, "ova_completed", None) or [])
        if ova_id not in completed:
            completed.append(ova_id)
            persistent.ova_completed = completed
            renpy.save_persistent()


define n = Character(
    None,
    kind=nvl,
    what_style="ova_nvl_what",
    window_style="ova_nvl_entry",
)


screen OVA():
    tag menu

    add "gui/main_menu2.png"
    add Solid("#f1f5f1e8")

    key "game_menu" action ShowMenu("main_menu")

    frame:
        xfill True
        ysize 176
        background Solid("#14272de8")
        padding (120, 34)

        hbox:
            xfill True

            vbox:
                spacing 2

                text "OVA" style "ova_library_title"
                text "小说模式" style "ova_library_subtitle"

            null width 1050

            vbox:
                xsize 390
                yalign 0.5

                text "阅读记录" style "ova_library_counter_label" xalign 1.0
                text "[ova_completed_count()] / [len(OVA_NOVELS)]" style "ova_library_counter" xalign 1.0

    viewport:
        area (120, 220, 1680, 690)
        mousewheel True
        draggable True
        pagekeys True

        vbox:
            xsize 1640
            spacing 18

            for novel in OVA_NOVELS:
                $ completed = ova_is_completed(novel["id"])

                button:
                    style "ova_novel_button"
                    action Start(novel["label"])

                    hbox:
                        xfill True
                        yfill True

                        add Solid("#22a9c2") xsize 10 ysize 158

                        fixed:
                            xsize 150
                            yfill True

                            text novel["index"]:
                                style "ova_novel_index"
                                xalign 0.5
                                yalign 0.5

                        vbox:
                            xsize 1050
                            yalign 0.5
                            spacing 6

                            hbox:
                                spacing 18

                                text novel["title"] style "ova_novel_title"
                                text novel["subtitle"] style "ova_novel_subtitle" yalign 0.8

                            text novel["description"] style "ova_novel_description"
                            text novel["reading_time"] style "ova_novel_meta"

                        fixed:
                            xsize 400
                            yfill True

                            if completed:
                                text "已完成" style "ova_novel_completed" xalign 0.72 yalign 0.5
                            else:
                                text "开始阅读" style "ova_novel_unread" xalign 0.72 yalign 0.5

                            text ">" style "ova_novel_arrow" xalign 0.93 yalign 0.5

    textbutton "返回主菜单":
        style "ova_back_button"
        xpos 120
        yalign 0.965
        action ShowMenu("main_menu")


style ova_library_title is gui_text:
    size 60
    color "#ffffff"

style ova_library_subtitle is gui_text:
    size 25
    color "#8dd6df"

style ova_library_counter_label is gui_text:
    size 23
    color "#b8c7c9"

style ova_library_counter is gui_text:
    size 42
    color "#ffffff"

style ova_novel_button is button:
    xfill True
    ysize 158
    padding (0, 0)
    background Solid("#fffffff0")
    hover_background Solid("#e9f7f8f8")

style ova_novel_index is gui_text:
    size 46
    color "#1d343a"

style ova_novel_title is gui_text:
    size 35
    color "#17282d"

style ova_novel_subtitle is gui_text:
    size 24
    color "#537078"

style ova_novel_description is gui_text:
    size 24
    color "#43545a"

style ova_novel_meta is gui_text:
    size 20
    color "#77878b"

style ova_novel_completed is gui_text:
    size 25
    color "#2d8057"

style ova_novel_unread is gui_text:
    size 25
    color "#16758a"

style ova_novel_arrow is gui_text:
    size 40
    color "#16758a"

style ova_back_button is button:
    padding (28, 13)
    background Solid("#14272de8")
    hover_background Solid("#16758a")

style ova_back_button_text is button_text:
    size 25
    color "#ffffff"
    hover_color "#ffffff"


screen ova_nvl(dialogue, items=None):
    add "gui/scene/classroom1.png"
    add Solid("#f4f7f2f2")
    add Solid("#22a9c2") xsize 14 ysize 1080
    
    frame:
        xfill True
        ysize 104
        background Solid("#14272df2")
        padding (76, 20)

        hbox:
            xfill True
            yalign 0.5

            text "OVA" style "ova_reader_brand"
            text ova_current_title style "ova_reader_title" yalign 0.62
    """
    hbox:
        xpos 1690
        ypos 22
        spacing 14

        imagebutton:
            id "ova_save_button"
            xsize 82
            ysize 60
            idle Transform("images/quick_button/save.png", zoom=0.78)
            hover Transform("images/quick_button/save.png", zoom=0.84)
            action ShowMenu("save")

        imagebutton:
            id "ova_load_button"
            xsize 82
            ysize 60
            idle Transform("images/quick_button/load.png", zoom=0.78)
            hover Transform("images/quick_button/load.png", zoom=0.84)
            action ShowMenu("load")
    """
    viewport:
        area (250, 150, 1420, 780)
        yinitial 1.0
        mousewheel True
        draggable True
        pagekeys True

        vbox:
            xfill True
            spacing 32

            for d in dialogue:
                window:
                    id d.window_id
                    style "ova_nvl_entry"

                    has vbox
                    spacing 8

                    if d.who is not None:
                        text d.who:
                            id d.who_id
                            style "ova_nvl_who"

                    text d.what:
                        id d.what_id
                        style "ova_nvl_what"

            if items:
                vbox:
                    id "menu"
                    xfill True
                    spacing 12

                    for i in items:
                        if i.action:
                            textbutton i.caption:
                                style "ova_nvl_choice"
                                action i.action
                        else:
                            text i.caption style "ova_nvl_what"


style ova_reader_brand is gui_text:
    size 42
    color "#ffffff"

style ova_reader_title is gui_text:
    size 25
    color "#8dd6df"
    left_margin 30

style ova_nvl_entry is empty:
    xfill True
    padding (0, 0)

style ova_nvl_who is gui_text:
    xsize 1380
    size 26
    color "#16758a"

style ova_nvl_what is gui_text:
    xsize 1380
    size 34
    color "#182428"
    line_spacing 12
    textalign 0.0
    layout "tex"

style ova_nvl_choice is button:
    xfill True
    padding (24, 14)
    background Solid("#ffffffcc")
    hover_background Solid("#dceff0")

style ova_nvl_choice_text is button_text:
    size 30
    color "#182428"
    hover_color "#16758a"