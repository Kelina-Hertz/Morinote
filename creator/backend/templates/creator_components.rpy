# Components are ordinary Ren'Py screens with params and an instance identifier.
screen creator_component_host():
    zorder 5
    for instance, data in creator_overlay_instances.items():
        if data["component"] != "phone" or not creator_phone_active:
            use expression creator_components[data["component"]]["entry"] pass (params=data["params"], instance=instance)

screen creator_phone_overlay(params={}, instance="phone"):
    frame:
        pos (int(params.get("x", 1370)), int(params.get("y", 100)))
        xysize (int(params.get("width", 480)), int(params.get("height", 730)))
        background Solid("#102333f2")
        padding (24, 20)
        vbox:
            spacing 18
            text params.get("title", creator_phone_title) size 30 color "#edf7ff"
            viewport:
                ymaximum int(params.get("height", 730)) - 100
                mousewheel True
                draggable True
                yinitial 1.0
                vbox:
                    spacing 14
                    for message in creator_messages:
                        frame:
                            background Solid(params.get("bubbleColor", "#244a69"))
                            xfill True
                            padding (16, 12)
                            vbox:
                                text creator_literal(message["speaker"]) size 23 color "#b6d8f2" substitute False
                                text creator_literal(message["text"]) size int(params.get("fontSize", 28)) color "#ffffff" substitute False

screen creator_phone_say(who, what):
    style_prefix "creator_phone"
    $ params = creator_phone_params()
    frame:
        pos (int(params.get("x", 1370)), int(params.get("y", 100)))
        xysize (int(params.get("width", 480)), int(params.get("height", 730)))
        padding (26, 22)
        background Solid("#102333f5")
        vbox:
            spacing 20
            text creator_phone_title size 32 color "#eaf4ff"
            viewport:
                ymaximum int(params.get("height", 730)) - 110
                yinitial 1.0
                mousewheel True
                vbox:
                    spacing 15
                    for message in creator_messages:
                        frame:
                            background Solid("#21384e")
                            xfill True
                            padding (18, 14)
                            vbox:
                                text creator_literal(message["speaker"]) size 22 color "#a9cce2" substitute False
                                text creator_literal(message["text"]) size int(params.get("fontSize", 28)) color "#e2ebf5" substitute False
                    frame:
                        background Solid(params.get("bubbleColor", "#356a88"))
                        xfill True
                        padding (18, 14)
                        vbox:
                            if who:
                                text who id "who" size 23 color "#ccedff"
                            text what id "what" size int(params.get("fontSize", 28)) color "#ffffff"
    use quick_menu

screen creator_investigation(params={}, instance="investigation"):
    modal True
    zorder 10
    frame:
        pos (int(params.get("x", 620)), int(params.get("y", 280)))
        xysize (int(params.get("width", 680)), int(params.get("height", 400)))
        padding (40, 32)
        background Solid("#142739f5")
        vbox:
            spacing 25
            text params.get("title", "调查桌面") size 38
            text "选择一件物品查看。" size 27 color "#bdd1e2"
            textbutton params.get("clue", "邀请函") action Return("found")
            textbutton "离开" action Return("leave")
