label test_OVA:
    $ nvl_mode = "ova"
    $ quick_menu = True
    $ ova_current_id = "test_OVA"
    $ ova_current_title = "雨后的活动室"

    stop music fadeout 1.0
    scene black

    n "雨是在傍晚停的。活动室的窗没有关严，潮湿的风把桌角那张纸吹得轻轻作响。"
    n "最后一个离开的人明明已经锁好了柜子，可桌上还是多出了一页手稿。纸面没有署名，只有一行被水晕开的字。"
    n "“如果有人读到这里，请替我把今天保存下来。”"

    n "窗外的积水映着晚霞。远处传来球鞋踩过水面的声音，又很快消失在走廊尽头。"
    n "手稿继续写着社团里再普通不过的一天：有人争论新番，有人趴在桌上补觉，还有人把没喝完的汽水忘在窗台。"
    n "“所谓值得纪念的日子，也许并不需要发生什么大事。只要在故事结束以前，还有一个人记得它。”"

    n "我把纸翻到背面，那里原本一片空白。"
    n "风再次掠过桌面时，一小行墨迹慢慢浮现，像是刚刚才被谁写下。"
    n "“谢谢你读到最后。现在，这一天不会消失了。”"
    n "【完】"

    nvl clear

    $ unlock_achievement("OVA_nancy01")
    $ ova_mark_completed("test_OVA")
    $ nvl_mode = "phone"
    $ ova_current_id = None
    $ ova_current_title = ""

    return