## Run through tools/test_qingfeng_ui.py --case campus_qa in the isolated project.
## These fixtures are never called by the story.
testsuite campus_qa:
    before testcase:
        $ _test.timeout = 8.0
        $ _test.transition_timeout = 0.2
        $ _test.screenshot_directory = "screenshots"
        if not screen "main_menu":
            run MainMenu(confirm=False)
        $ _preferences.text_cps = 0
        $ _preferences.afm_enable = False
    teardown:
        exit

    testcase block:
        run Start("_campus_qa_block")
        advance until "校园背景检查：block。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260417_143507.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260417_143507.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("block") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-block.png"

    testcase westcorch:
        run Start("_campus_qa_westcorch")
        advance until "校园背景检查：westcorch。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_162320.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_162320.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("westcorch") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-westcorch.png"

    testcase westcorch_l:
        run Start("_campus_qa_westcorch_l")
        advance until "校园背景检查：westcorch_l。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_162614.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_162614.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("westcorch_l") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-westcorch_l.png"

    testcase westcorch_r:
        run Start("_campus_qa_westcorch_r")
        advance until "校园背景检查：westcorch_r。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_161743.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_161743.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("westcorch_r") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-westcorch_r.png"

    testcase westcorch2:
        run Start("_campus_qa_westcorch2")
        advance until "校园背景检查：westcorch2。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_161827.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_161827.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("westcorch2") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-westcorch2.png"

    testcase block_n1:
        run Start("_campus_qa_block_n1")
        advance until "校园背景检查：block_n1。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_194119.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_194119.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("block_n1") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-block_n1.png"

    testcase block_n2:
        run Start("_campus_qa_block_n2")
        advance until "校园背景检查：block_n2。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_194725.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_194725.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("block_n2") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-block_n2.png"

    testcase w12_1:
        run Start("_campus_qa_w12_1")
        advance until "校园背景检查：w12_1。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_194453_1.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_194453_1.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("w12_1") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-w12_1.png"

    testcase w12_2:
        run Start("_campus_qa_w12_2")
        advance until "校园背景检查：w12_2。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_192935.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_192935.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("w12_2") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-w12_2.png"

    testcase room1:
        run Start("_campus_qa_room1")
        advance until "校园背景检查：room1。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_195653.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_195653.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("room1") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-room1.png"

    testcase room2:
        run Start("_campus_qa_room2")
        advance until "校园背景检查：room2。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_195651.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_195651.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("room2") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-room2.png"

    testcase room3:
        run Start("_campus_qa_room3")
        advance until "校园背景检查：room3。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_195754.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_195754.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("room3") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-room3.png"

    testcase room4:
        run Start("_campus_qa_room4")
        advance until "校园背景检查：room4。"
        assert eval (renpy.loadable("gui/scene/campus/IMG_20260418_195721.png"))
        assert eval (renpy.image_size("gui/scene/campus/IMG_20260418_195721.png") == (2048, 1152))
        assert eval (renpy.get_image_bounds("room4") == (0, 0, 1920, 1080))
        pause 0.4
        screenshot "campus-room4.png"

    testcase story_day:
        run Start("C1b1")
        advance until "所谓的"
        assert eval (renpy.showing("block"))
        assert eval (renpy.get_image_bounds("block") == (0, 0, 1920, 1080))

    testcase story_night:
        run Start("C1c1")
        advance until "我向着教学楼走去"
        assert eval (renpy.showing("block_n1"))
        assert eval (renpy.get_image_bounds("block_n1") == (0, 0, 1920, 1080))

label _campus_qa_block:
    scene block
    show duou
    $ quick_menu = True
    duou "校园背景检查：block。"
    return

label _campus_qa_westcorch:
    scene westcorch
    show duou
    $ quick_menu = True
    duou "校园背景检查：westcorch。"
    return

label _campus_qa_westcorch_l:
    scene westcorch_l
    show duou
    $ quick_menu = True
    duou "校园背景检查：westcorch_l。"
    return

label _campus_qa_westcorch_r:
    scene westcorch_r
    show duou
    $ quick_menu = True
    duou "校园背景检查：westcorch_r。"
    return

label _campus_qa_westcorch2:
    scene westcorch2
    show duou
    $ quick_menu = True
    duou "校园背景检查：westcorch2。"
    return

label _campus_qa_block_n1:
    scene block_n1
    show duou
    $ quick_menu = True
    duou "校园背景检查：block_n1。"
    return

label _campus_qa_block_n2:
    scene block_n2
    show duou
    $ quick_menu = True
    duou "校园背景检查：block_n2。"
    return

label _campus_qa_w12_1:
    scene w12_1
    show duou
    $ quick_menu = True
    duou "校园背景检查：w12_1。"
    return

label _campus_qa_w12_2:
    scene w12_2
    show duou
    $ quick_menu = True
    duou "校园背景检查：w12_2。"
    return

label _campus_qa_room1:
    scene room1
    show duou
    $ quick_menu = True
    duou "校园背景检查：room1。"
    return

label _campus_qa_room2:
    scene room2
    show duou
    $ quick_menu = True
    duou "校园背景检查：room2。"
    return

label _campus_qa_room3:
    scene room3
    show duou
    $ quick_menu = True
    duou "校园背景检查：room3。"
    return

label _campus_qa_room4:
    scene room4
    show duou
    $ quick_menu = True
    duou "校园背景检查：room4。"
    return
