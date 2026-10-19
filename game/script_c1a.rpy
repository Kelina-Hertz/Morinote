# 游戏的脚本置于此文件中。

# 声明此游戏使用的角色。颜色参数可使角色姓名着色。
define ly = Character("落鸢",what_prefix="「",what_suffix="」")
define duou = Character("渡鸥",what_prefix="「",what_suffix="」")
define yierli = Character("一二里",what_prefix="「",what_suffix="」")
define xq = Character("汐泉",what_prefix="「",what_suffix="」")
define ml = Character("梦龙",what_prefix="「",what_suffix="」")
define lx = Character("蓝雪",what_prefix="「",what_suffix="」")
define wz = Character("文竹",what_prefix="「",what_suffix="」")
define girl = Character("女孩子",what_prefix="「",what_suffix="」")
define jyosei = Character("女生",what_prefix="「",what_suffix="」")
define hinata = Character("？？？",what_prefix="「",what_suffix="」")
define by1 = Character("部员1",what_prefix="「",what_suffix="」")
define by2 = Character("部员2",what_prefix="「",what_suffix="」")
define sy1 = Character("社员1",what_prefix="「",what_suffix="」")
define sy2 = Character("社员2",what_prefix="「",what_suffix="」")

define xa = Character("三同学",what_prefix="「",what_suffix="」")
define x1 = Character("同学甲",what_prefix="「",what_suffix="」")
define x2 = Character("同学乙",what_prefix="「",what_suffix="」")
define x3 = Character("同学丙",what_prefix="「",what_suffix="」")

define hx = Character("幻协成员",what_prefix="「",what_suffix="」")
define sc = Character("诗协会员",what_prefix="「",what_suffix="」")
define lr1 = Character("路人1",what_prefix="「",what_suffix="」")
define lr2 = Character("路人2",what_prefix="「",what_suffix="」")

screen phone:
    zorder 105

    imagebutton:
        idle "images/phone_icon.png"
        hover "images/phone_icon_hover.png"
        xpos 500
        ypos 500
        action Show("phone_screen")


image splash = "#ffffff"
image intro = "gui/main_menu_fg.png"
image intro_bg = "gui/main_menu_bg.png"
image top_title:
    "gui/title.png"
    xanchor 0.5
    yanchor 0.5


define splash = """\
本作品纯属虚构。
游戏中一切人名，地名，组织名等均为架空设计，与现实无任何关联。
如有雷同，纯属巧合。

本作品适合于14周岁以上人群。
所有登场人物均已年满十八周岁。

本制作组保留对游戏的解释权。
\
"""

transform title_transform:
    pos (960,-300)
    linear 5.0 pos (960,1040)

# 游戏在此开始。
label splashscreen:
    show intro_bg
    with Pause(1)

    show text splash with Dissolve(1)
    with Pause(3)

    play music "audio/bgm/opening.ogg" volume 1.25
    pause 0.5
    hide text with Dissolve(2)
    with Pause(2)

    show intro with Dissolve(15)
    pause 0.1
    show top_title with moveintop:
        xpos 960
        ypos 460
    pause 0.5

    return


label start:
    #test
    #jump C1c2

    scene black
    play music "audio/bgm/start1.mp3" volume 0.5
    play sound "audio/sound/intro.mp3"
    "……"
    "刚从考场的大门走出，身边立刻被沸腾的人声俘获，"
    "热浪仍然裹挟着六月初的武汉，即使夕阳西下也丝毫不见消退。"
    "鲜花与欢呼声包裹着考场大门，周遭充斥着梦幻般的光怪陆离。"
    "「哈哈哈！考完啦！终于毕业啦！」"
    "和我一道走出考场的同学们，以及来迎接他们的父母们，"
    "他们互相寻找着彼此。会合后，每个人身上都带着笑或泪。"
    "我绕过嘈杂的人群，径直向家的方向走去。"
    stop sound fadeout 15.0
    "离开他们越远，身边的嘈杂声渐渐消散。"
    "希望一切真的就此结束……"
    "希望曾经的一切都能被深埋地下……"
    "……"
    "直到录取通知书被交到手上那一刻，我才安心地收起曾经那份忐忑。"
    "但我可能永远也忘不了那一刻。"
    "就在那间囚禁我整整三年的监牢中。"
    stop sound
    #stop music fadeout 1.0     #使用start1时注释
    scene black with dissolve
    jump C1a

label test:
    "这是进行特典小说测试"
    $ clear("duou01")


label C1a:
    scene goko with dissolve
    #play music "audio/bgm/start2.mp3" volume 2
    "那个后排靠窗的位置，面前的课桌上摊开着一本漫画。"
    "那是我看的第一本漫画，攒了好久才买的。"
    "现在是午自习，我已经写完了所有作业，于是决定忙里偷闲一下。"
    "但是，耳边却传来了不和谐的窃窃私语。"
    #voice "audio/npc/npc01.wav"
    x1 "看，就那个，他又在偷偷看什么呢？"
    x2 "看漫画呗，就日本鬼子画的那个。哎，小众哥觉得自己老高贵了……"
    x1 "你没看他平时都不说几句话，人家这叫逃避现实。"
    x3 "别管他了，今天晚上回家之后打不打？"
    xa "行/我没意见/算我一个。"
    "看似窃窃私语的话语，却跨过教室传进了我的耳朵里。"
    "我的手开始发抖，想反驳，但喉咙仿佛被一双大手狠狠掐住，发不出任何声音。"
    "我从小就一直这样——越着急越说不出话，越生气越张不开嘴。"
    "最后只得把千万句想说的话憋在肚子里。忍气吞声地任由他人言语。"
    "小时候妈妈带我去看医生，医生说这叫选择性缄默症，不是什么大毛病，大了就好了。"
    "可我现在已经十六岁了，还是没好。"
    "我只能坐在那里，对耳边的冷嘲热讽不理不睬。"
    "突然，一切的嘈杂戛然而止。身侧闪过一个人影。"
    "尽管对接下来会发生什么无比熟悉，但我仍然扭动僵硬的脖子，颤抖着抬起了头。"
    "映入眼帘的，是一张苍老的布满褶皱的脸，透过眼镜的目光死死地锁定了我的手中。"
    "我伸出了手。恐惧，无奈与不甘交织着……"
    "尽管并不情愿，尽管心有不甘……"
    play sound "audio/sound/voice.mp3"
    "……"
    "没有任何征兆，我的宝物化为了乌有，只留下五颜六色的碎纸片在眼前飞舞。"
    "世界在这一刻变得出奇的安静，"
    "我只感觉到一阵眩晕……"
    scene black
    stop sound
    stop music
    "眼前先是一片黑暗，紧接着是无边的煞白袭来……"
    "………"
    "……"
    "…"


    ly "啊……"
    "我猛然睁开双眼。"
    "眼前是熟悉的天花板。虽然是最近才刚熟悉的。"
    scene domitory with Dissolve(1.0)
    play music "audio/bgm/nichijyo2.ogg"
    "坐起身后环顾四周，环境渐渐熟悉了起来。"
    "午后的阳光从窗帘缝隙里挤进来，在地板上切出一道亮线。"
    "我这才渐渐从噩梦中抽出思绪来，"
    "……我已经上大学了。"
    ml "风哥你醒了啊，话说你睡个午觉怎么出那么多汗，还弄出了好大的动静。"
    ly "没什么，做了个噩梦……"
    "正在和我讲话的人，朱梦龙，是我的舍友。"
    "虽然开学只有一个多月，但他出乎意料得自来熟。"
    "军训时我们就能在一起聊天了。"
    "虽然在自我介绍时我告诉过他们我的本名“风落鸢”，并且告诉他们“叫我落鸢就好”，"
    "但他说我的姓太少见了，要叫我“风哥”。"
    "事到如今我已经不再计较这点了。"
    ml "又是噩梦吗，这才开学一个多月你都做了几次噩梦啦，是不是军训累着了啊？"
    ly "可能是吧，但我感觉没什么累的感觉。"
    ml "这种症状大概率就是劳累过度了。"
    ml "你想，军训结束之后，你天天不是在上课就是在图书馆自习，根本就没有好好休息过。"
    ly "可是，除了那些，我也不知道该做些什么……"
    ml "唉……你不要把大学高中化呀！我们学校有那么多有意思的活动。"
    ml "依我看，如果不知道做什么的话，去参加一个社团就不赖。"
    ly "可我除了看看漫画动漫，就没什么爱好了，参加什么社团呢？"
    ml "漫画动漫……你等等啊，我看看……"
    "不过，他说的没错。"
    "在刚开课的这一个月内，我仍然没有上大学。"
    "我依然在读高中一般。"
    "每天早上早起读书上课，晚上独自一人去自习室上晚自习，"
    "之前我并没有觉得这有什么不对，但最近老做噩梦的确让我睡眠质量下降了不少。"
    "即便已经毕业了，曾经的阴霾还没散去……"
    "我还被困在那里……"
    ml "诶，你不是喜欢动画那些的吗？咱们学校有个动漫社。"
    ly "动漫社？"
    ml "上次有人在咱宿舍楼底下贴海报，喏，你看。"
    "动漫社吗，看起来好像不错……"
    ml "海报上还有社团群聊二维码呢。"
    "先加进去看看好了。"

    #scene phone_scene
    
    call phonelabel_01
    $ unlock_achievement("first_launch")
    "百团大会……"
    ly "龙哥，百团大会是什么时候，在哪里啊？"
    ml "今天上午就开始了，在西操场那里。"
    ml "我就知道你小子会感兴趣的，走我带你去。"
    ly "好……"
    "不过，说到动画，漫画，我仍旧会回想起那片光景，"
    "我珍爱的第一本漫画书在我眼前被撕碎的场景。"
    "我该怎么和动漫社的大家相处呢？会收获难忘的回忆吗？"
    "还是会和过去那样，再次陷入窒息和痛苦？"
    "像我这样的人，真的可以收获美好的回忆吗，哪怕是最微小的……"
    stop music fadeout 4.0
    $ unlock_achievement("chapter11_clear")
    "………"
    "……"
    "…"
    scene black with fade


    jump C1b1
