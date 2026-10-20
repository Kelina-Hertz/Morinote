# Built-in demo test suite. Only installed into isolated demo preview builds.
testsuite creator_smoke:
    before testcase:
        $ _test.timeout = 20.0
        $ _test.transition_timeout = 1.0
        $ _test.screenshot_directory = "screenshots"
        advance until screen "main_menu"
        $ preferences.afm_enable = False
        $ preferences.text_cps = 0
    teardown:
        exit

testcase creator_smoke.investigate:
    click "开始游戏"
    pause until "放学后的教室里，还亮着一盏灯。"
    assert eval ("creator_context['line'] == 'meet_1'")
    assert eval ("creator_get('visited') == ['社团']")
    advance until "桌上似乎放着什么。"
    pause .8
    assert eval ("len(creator_visual['sprites']) == 2")
    screenshot "creator-composition.png"
    advance until screen "choice"
    click "留在教室调查"
    pause until screen "creator_investigation"
    screenshot "creator-investigation.png"
    click "社团邀请函"
    pause until "大家到齐了吗？"
    assert eval ("creator_get('clue') is True and creator_phone_active")
    assert eval ("len(creator_messages) == 1 and len(creator_visual['sprites']) == 2")
    advance until "准备好了，明天见！"
    screenshot "creator-phone.png"
    $ renpy.save("creator-smoke-phone")
    run Function(renpy.load, "creator-smoke-phone")
    pause until "准备好了，明天见！"
    assert eval ("creator_phone_active and len(creator_messages) == 2")
    advance until "收起手机后，眼前的风景依旧。"
    assert eval ("not creator_phone_active and len(creator_visual['sprites']) == 2")
    advance until "原来邀请函上的日期就是今天。"
    advance until "这个小小的故事，才刚刚开始。"
    advance until screen "main_menu"

testcase creator_smoke.garden:
    click "开始游戏"
    advance until screen "choice"
    click "去庭院聊一聊"
    pause until "我们走到庭院，晚风轻轻吹过。"
    advance until "青递来一张邀请函，原来今天还有一场活动。"
    assert eval ("creator_get('trust') == 1 and creator_get('clue') is False")
    advance until "这个小小的故事，才刚刚开始。"
    advance until screen "main_menu"
