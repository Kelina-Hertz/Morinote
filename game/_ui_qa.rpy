## Run with tools/test_qingfeng_ui.py, which isolates saves and preferences.
## This file has no game-time overlays or callbacks.
testsuite ui_qa:
    before testcase:
        $ _test.timeout = 6.0
        $ _test.transition_timeout = 0.2
        $ _test.screenshot_directory = "screenshots"
        if not screen "main_menu":
            run MainMenu(confirm=False)
        $ _preferences.text_cps = 0
        $ _preferences.afm_enable = False
        $ _preferences.afm_time = 30
        $ _preferences.font_size = 1.0

    teardown:
        exit

    testcase main_menu:
        assert id "qf_main_start"
        assert id "qf_main_load"
        assert id "qf_main_settings"
        assert id "qf_main_ova"
        assert id "qf_main_achievements"
        assert id "qf_main_quit"
        pause 0.6
        screenshot "01-main-menu.png"
        click id "qf_main_load"
        assert screen "load"
        pause 0.6
        screenshot "02-empty-load.png"
        keysym "K_ESCAPE"
        assert screen "main_menu"
        click id "qf_main_quit"
        assert screen "confirm"
        pause 0.6
        screenshot "03-confirm-quit.png"
        keysym "K_ESCAPE"
        assert not screen "confirm"
        click id "qf_main_start"
        advance until "刚从考场的大门走出"
        assert screen "say"

    testcase settings:
        click id "qf_main_settings"
        assert screen "preferences"
        pause 0.6
        screenshot "04-reading.png"
        click id "qf_range_文字速度" pos (0.5, 0.5)
        assert eval (_preferences.text_cps > 0)
        run Preference("text speed", 0)
        click "声音"
        pause 0.6
        screenshot "05-audio.png"
        $ _qf_before = _preferences.get_volume("music")
        click id "qf_range_音乐音量" pos (0.3, 0.5)
        assert eval (_preferences.get_volume("music") != _qf_before)
        click id "qf_mute"
        assert eval (qf_all_muted())
        click id "qf_mute"
        assert eval (not qf_all_muted())
        click "显示"
        pause 0.6
        screenshot "06-display.png"
        $ _qf_before = _preferences.show_empty_window
        click id "qf_empty_window"
        assert eval (_preferences.show_empty_window != _qf_before)
        click id "qf_empty_window"
        click "快进"
        pause 0.6
        screenshot "07-skipping.png"
        $ _qf_before = _preferences.skip_unseen
        click id "qf_skip_unread"
        assert eval (_preferences.skip_unseen != _qf_before)
        click id "qf_skip_unread"
        $ _qf_before = _preferences.skip_after_choices
        click id "qf_skip_choices"
        assert eval (_preferences.skip_after_choices != _qf_before)
        keysym "K_ESCAPE"
        assert screen "main_menu"

    testcase reading_and_choice:
        run Start("_qf_qa_scene")
        advance until "这是青枫动漫社的阅读界面"
        pause 0.6
        screenshot "08-dialogue-day.png"
        click id "qf_quick_auto"
        assert eval (_preferences.afm_enable)
        pause 0.6
        screenshot "09-auto-selected.png"
        click id "qf_quick_auto"
        assert eval (not _preferences.afm_enable)
        run ShowMenu("history")
        assert screen "history"
        pause 0.6
        screenshot "10-history.png"
        keysym "K_ESCAPE"
        assert not screen "history"
        advance until screen "choice"
        keysym "K_DOWN"
        pause 0.6
        screenshot "11-choice-keyboard.png"
        click id "qf_choice_1"
        advance until "你选择了较长的选项"
        assert eval (_qf_qa_choice == 2)
        advance
        pause 0.6
        screenshot "12-dialogue-night.png"

    testcase save_load:
        run Start("_qf_qa_save_scene")
        advance until "存读档测试位置"
        run FilePage("99")
        click id "qf_quick_save"
        assert screen "save"
        click id "qf_slot_1"
        assert eval (FileLoadable(1))
        pause 0.6
        screenshot "13-save.png"
        click id "qf_slot_1"
        assert screen "confirm"
        pause 0.6
        screenshot "14-confirm-overwrite.png"
        click id "qf_cancel"
        assert not screen "confirm"
        click id "qf_slot_1"
        click id "qf_confirm"
        assert not screen "confirm"
        keysym "K_ESCAPE"
        assert not screen "save"
        $ _qf_qa_marker = 2
        click id "qf_quick_load"
        click id "qf_slot_1"
        assert screen "confirm"
        click id "qf_confirm"
        assert screen "say"
        assert eval (_qf_qa_marker == 1)
        run ShowMenu("load")
        run FilePage("1")
        assert eval (not FileLoadable(1))
        run FilePage("99")
        assert eval (FileLoadable(1))
        move id "qf_slot_1"
        pause 0.2
        keysym "K_DELETE"
        assert screen "confirm"
        click id "qf_confirm"
        assert eval (not FileLoadable(1))

    testcase information:
        click id "qf_main_achievements"
        assert screen "achievements"
        pause 0.6
        screenshot "15-achievements.png"
        click "关于作品"
        assert screen "about"
        pause 0.6
        screenshot "16-about.png"
        click "配音演员"
        click "作品声明"
        pause 0.6
        screenshot "17-notices.png"
        click "操作帮助"
        pause 0.6
        screenshot "18-help.png"
        click "鼠标"
        click "手柄"
        keysym "K_ESCAPE"
        assert screen "main_menu"

    testcase ova_reading:
        click id "qf_main_ova"
        assert screen "OVA"
        pause 0.6
        screenshot "19-ova-library.png"
        click "test_OVA"
        advance until "雨是在傍晚停的"
        assert screen "nvl"
        assert eval (nvl_mode == "ova")
        pause 0.6
        screenshot "20-ova-first.png"
        advance until "【完】"
        pause 0.6
        screenshot "21-ova-last.png"
        advance until screen "main_menu"
        assert eval (ova_is_completed("test_OVA"))

label _qf_qa_scene:
    scene expression "gui/scene/classroom1.png"
    show duou
    $ quick_menu = True
    $ _qf_qa_choice = 0
    duou "这是青枫动漫社的阅读界面。窗外的光落在桌边，今天也有许多想与你分享的故事。文字和枫叶细节都应该清楚而舒适。"
    menu:
        "一起准备社团活动吧。":
            $ _qf_qa_choice = 1
        "先看看这份写满了大家灵感的社刊，再一起商量周末的社团活动。":
            $ _qf_qa_choice = 2
        "等一会儿再做决定。":
            $ _qf_qa_choice = 3
    duou "你选择了较长的选项。"
    scene expression "gui/scene/block_n1.png"
    duou "夜间阅读检查：浅色底板保持文字清晰，轻透的叶印只留在边缘。"
    return

label _qf_qa_save_scene:
    scene expression "gui/scene/classroom1.png"
    show duou
    $ quick_menu = True
    $ _qf_qa_marker = 1
    $ save_name = "青枫动漫社的存读档测试与很长的章节名称"
    duou "存读档测试位置：读取存档后，应回到这一句台词与原有变量。"
    "测试结束。"
    return
