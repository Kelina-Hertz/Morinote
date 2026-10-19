transform leftin_dissolve:
    alpha 0.0                # 起始完全透明
    xoffset -150             # 起始X轴偏移-300像素（从左侧外开始）
    parallel:
        easein 0.6 xoffset 0    # X轴用0.8秒平滑移动回原位
    parallel:
        linear 0.5 alpha 1.0    # 透明度用0.6秒线性恢复到完全不透明

transform rightout_dissolve:
    alpha 1.0
    xoffset 0
    parallel:
        easein 0.6 xoffset 150
    parallel:
        linear 0.5 alpha 0.0

#define rightout_dissolve = MoveTransition(0.6, leave=rightout_dissolve_atl)

define chara_trans = Dissolve(0.2)

label C1b1:
    scene block with dissolve
    play music "audio/bgm/nichijyo.ogg" volume 0.75
    ly "所谓的“百团大会”，是说我们真的有一百个社团吗？"
    ml "嗯……我也没数过到底有多少个。"
    ml "社团规模有大有小，几十人到上百人的都有。最大的社团据说有两千人。"
    ly "两……两千人？！"
    ml "社团大多是某个方面的同好聚集到一起而成立的。所以每个社团都可以算一个或多个同好会。"
    ml "“百团大会”就是各个社团在入学季寻找新人同好的时机。"
    ly "原来这样吗……"
    ml "所以你不用担心加入某个社团会挤占你的学习时间。"
    "……"
    "我其实并没有这样想……"
    ml "嗯。我们到了。"

    scene westcorch
    ly "哇……这就是百团大会吗，人好多……"
    ml "不愧是百团大会，果然热闹，哈哈。"
    ml "走吧，我带你去找一下所谓的动漫社。"
    ly "谢谢龙哥！"
    ml "客气什么，都是兄弟嘛。哈哈。"
    ly "龙哥就是龙！"
    "……"
    "所以……"
    "动漫社在哪里？"
    ly "总之，一边逛一边找吧。"
    scene black with fade
    with Pause(0.5)

    scene westcorch_l with dissolve
    ml "这里是……象棋协会。"
    ly "还有现场对弈活动呢。"
    "应该是老社员和新人对弈吧。"
    "……"
    "不，那是一位保安大爷在和社员对弈。"
    ml "可我又不会下象棋……"
    ly "我也是……"
    ly "还是先走吧……"
    "……"
    scene black with fade
    with Pause(0.5)
    scene westcorch_l with dissolve
    "这是……科幻协会？"
    "看来是科幻爱好者同好会。"
    "摊位一侧还竖着一块米黄色的留言板。"
    ly "让我看看这里的留言……哇，真多呢。"
    ly "“人类总是重复着同样的悲剧……”"
    ly "“老人是无法创造新世纪的！”"
    "……"
    "……？？！好熟悉的台词……"
    "好吧，那也可以算科幻。"
    hx "关注幻协喵，关注幻协谢谢喵。"
    ly "这样看来，或许动漫社也有科幻爱好者呢。"
    "接下来去右边看看。"
    "………"
    "……"
    "…"
    scene black with fade
    with Pause(0.5)

    scene westcorch_r with dissolve            
    ly "诗词协会……喔，总算看到一个安静些的社团了。"
    sc "劝君更尽一杯酒……？"
    "是在玩说上句接下句的游戏吧。"
    "我想想，这句话的下一句是……"
    ml "……与尔同销万古愁。"
    "？？？"
    "这不对吧？"
    sc "这句对的好！算得上今天“无关上下句对对子”活动对的最好的！"
    ly "“无关上下句”？“对对子”？"
    ml "要求一个人说上句，另一个人接一句其他诗词里的句子作为下句。"
    ml "而且要求无缝衔接。"
    ly "还可以这样玩的吗？"
    "……"
    scene black with fade
    with Pause(0.5)
    scene westcorch_r with dissolve
    ly "喔，这是……军事爱好者协会？"
    lr1 "唉，激光枪模型没有后坐力，真没意思。"
    lr2 "有激光枪模型就不错啦，而且还是M4A1呢……今天真爽……"
    ml "真是硬核！"
    ly "的确硬核……硬核到吓人一跳……"
    "………"
    "……"
    "…"
    scene black with fade

    scene westcorch2 with dissolve
    "科幻协会，龙舟社，协会，外语协会……"
    "已经逛过好几个摊位了。"
    "但一个社团都没有加入。"
    "他还真厉害呢，即使跟陌生人也能顺理成章地搭上话……"
    "而我一路上好像话都没说几句，一直在自言自语……"
    "而且，对社团活动内容一窍不通的我，即便想加入也很困难……"
    "只能寄希望于动漫社了吗……"
    ml "别这么垂头丧气的嘛，前面还有几个摊位，估计动漫社就在那里吧。"
    ly "但愿如此吧……"
    stop music fadeout 0.5
    "四下张望着，寻找动漫社的踪影……"
    "……"
    "……看到了。"
    "就在那路演舞台的旁边。"
    scene qf with Dissolve(2.0)
    "巨大的塑料牌挂在遮阳棚上方，写着五个大字，"
    "青枫动漫社。"
    ly "终于找到你了……"
    ml "哈哈，找到就好了，那我就先去摄影社那边看看去了。"
    ly "好。"
    "我迈开步子，准备向动漫社的摊位走去……"
    ly "啊……"
    "我被另一种超然的场景吸引了。"
    "并不是别的社团摊位，也不是别的演出。"
    "而是……"
    ly "这人也太多了吧？！"
    "动漫社摊位前，一条长长的队伍一直拖到远处。"
    "队伍旁边还有一群人围在一起。"
    ly "不行，人太多了……"
    "人一多起来我就会紧张，一紧张我就会不知所措，说不出话来，也不敢上前去……"
    "站在离摊位十几米远的地方，我就这样一直观望着动漫社的摊位活动。"
    "不时左右移动几步，但只要试图向前迈步，双腿仿佛灌了铅一样沉重。"
    "现在怎么办？难不成要一直这样站着？"
    "………"
    "……"
    "…"
    scene black with fade

    jump C1b2

label C1b2:
    stop music
    scene westcorch with dissolve
    #voice "audio/duou/duou01.wav"
    yierli "总算搞定了……战斗服穿起来还是这么麻烦，辛苦你了，汐泉。"
    show xiquan as xiquan at leftin_dissolve:
        xpos 700
    show duou_confident as duou at leftin_dissolve:
        xpos 1300
    play music "audio/bgm/duou01.ogg" volume 0.5
    #voice "audio/xiquan/xq01.wav"
    xq "我还是觉得你出校服那一套就好了，穿起来既方便又舒服。"
    #voice "audio/duou/duou02.wav"
    show duou_confident2 as duou with chara_trans:
        xpos 1300
    yierli "那怎么行，肯定是这款战斗服最经典嘛。"
    yierli "再说了，既然答应下来要出cosplay，那就得拿出十二分精神认真对待。"
    yierli "你看，肩上的装甲片、胸前的红色条纹，还有这副手套，"
    show duou_smile2 as duou with chara_trans:
        xpos 1300
    yierli "这才是她的灵魂所在啊。"
    yierli "虽然出这套是很麻烦，但是能让大家开心，这也是值得的。"
    #voice "audio/xiquan/xq02.wav"
    xq "你还真是重视动漫社的大家呢……"
    show duou_surprise as duou with chara_trans:
        xpos 1300
    #voice "audio/xiquan/xq03.wav"
    xq "不过，我其实没想到这次你会答应cos组的委托。"
    #voice "audio/duou/duou07.wav"
    show duou_confident2 as duou with chara_trans:
        xpos 1300
    yierli "本来我就喜欢cos之类的活动嘛。没办法。所以我才能一直坚持下去。"
    #voice "audio/duou/duou08.wav"
    show duou_confident as duou with chara_trans:
        xpos 1300
    yierli "摊位这边的活动，就麻烦你了，我再去看看有没有新人需要引导的。"
    #voice "audio/xiquan/xq04.wav"
    xq "哎，你不休息一下吗？明明昨天晚上还在准备活动的物资，今天上午一上完课又马不停蹄地赶了过来..."
    #voice "audio/duou/duou09.wav"
    yierli "今年来咱们摊位的同学似乎比去年还多，很多新人可能对社团的活动形式、入社流程都不太熟悉，我去转一转，一定能帮上忙。"
    #voice "audio/duou/duou10.wav"
    show duou_smile as duou with chara_trans:
        xpos 1300
    yierli "而且，穿着cos服去做引导，能为动漫社吸收新成员，这样我也不觉得累啦！"
    show duou_smile as duou at rightout_dissolve:
        xpos 1300
    pause 0.6
    hide duou
    #voice "audio/xiquan/xq05.wav"
    xq "唉，做自己喜欢的事果然拦都拦不住。"
    show xiquan as xiquan at rightout_dissolve:
        xpos 700
    pause 0.6
    hide xiquan
    "……"
    scene black with fade
    with Pause(1)

    scene qf with dissolve
    sy1 "参与抽奖活动的大家请排好队！不要拥挤，更不要插队！"
    sy2 "完成抽奖的同学可以参加其他活动，给后面的同学节省一点时间！"
    ly "其他社团大多在招呼新人，动漫社却要求新人排好队不要拥挤……"
    "不过这个动漫社似乎包罗万象，也难怪这里人多呢。"
    "忽然，眼角似乎闪过一抹红色……"
    ly "嗯？那是……"
    lr1 "哇，一二里来了！"
    "是之前群里提到的……"
    show duou_confident as duou at leftin_dissolve
    #voice "audio/duou/duou11.wav"
    yierli "大家好！都玩得开心吗？"
    show duou_smile as duou with chara_trans
    lr2 "真的欸！还是这套战斗服，肯定是一二里出的！"
    "看到那一抹红色，直觉已经猜到了是明日香，"
    "不过……"
    ly "真好看啊……"
    "特别是这身战斗服……肩甲的金属光泽，还有发箍上的蝴蝶结……"
    ly "还原度真高！"
    sy2 "部长昨天为了活动物资忙到很晚，今天还自己出cos来招新，她真的，我哭死。"
    lr1 "前辈，可以和你合影吗！"
    #voice "audio/duou/duou12.wav"
    yierli "我这就来，大家不用着急。"
    hide duou with dissolve
    "啊，大家都去合影去了……"
    "就连队伍里也有不少人跑去合影。"
    ml "哇，这么多人围在那里是在干什么？"
    ly "啊，他们是在和出cos的老师合影。"
    ml "我看看，我去，真的好漂亮！我也要去合影。"
    ml "美女，美女，可以合个影吗？"
    "这个社交恐怖分子……"
    show duou_confident as duou at leftin_dissolve
    #voice "audio/duou/duou13.wav"
    yierli "可以啊同学，等我找个角度。"
    show duou_reliable as duou with chara_trans
    "不过龙哥的身材着实有些……过于魁梧了？"
    "摆了好久都没有找到一个很好的姿势。"
    show duou_reliable3 as duou with chara_trans
    #voice "audio/duou/duou14.wav"
    yierli "这下有些难办呢……"
    show duou_confident2 as duou with chara_trans
    yierli "欸，这位同学，帮个忙呗？"
    "她带着灿烂的笑容，把手机递给了我。"
    ly "我……我吗？"
    voice "audio/duou/duou15.wav"
    yierli "就是你呀，同学，帮我们拍个照好吗？"
    ly "哦，好的。"
    ly "请看镜头。三，二，一!"
    "这种骄傲又坚强的感觉……"
    "仿佛我不是在给一位coser老师拍，而是在给真正的明日香拍照一样……"
    "拍完照片，我把手机还给前辈。"
    ly "老师，你的明日香出的实在太棒了！"
    ly "刻意做旧的左手手套，暗红色的发带，居然连这种细节都能完美还原，实在是……"
    "激动促使着我一反常态的主动和人搭话，结果一口气说出了这么多话……"
    show duou_surprise as duou with chara_trans
    #voice "audio/duou/duou16.wav"
    yierli "欸，你注意到了吗同学！"
    show duou_smile as duou with chara_trans
    #voice "audio/duou/duou17.wav"
    yierli "没想到真的会有人注意到我所有的还原细节。"
    ly "！"
    "没想到这位老师似乎更加惊喜，一把握住了我的手。"
    "这反而让我接下来的话有些难以出口……"
    show duou_ds as duou with chara_trans
    #voice "audio/duou/duou18.wav"
    yierli "抱歉同学，有些失态了。"
    #voice "audio/duou/duou19.wav"
    yierli "我也是没想到有人能挖掘出我的小巧思，所以才有点过于激动了。"
    show duou_confident2 as duou with chara_trans
    #voice "audio/duou/duou20.wav"
    yierli "不过，如果你也对我们社团感兴趣的话，可以去摊位那边玩。"
    #voice "audio/duou/duou21.wav"
    yierli "那边有答题抽奖活动。"
    show duou_reliable3 as duou with chara_trans
    sy2 "渡鸥部长！"
    show duou_confident2 as duou with chara_trans
    #voice "audio/duou/duou22.wav"
    yierli "啊，来啦！"
    hide duou with dissolve
    "一二里前辈简单致意后，向另一边的人群走去了。"
    "不仅热情，还很细腻体贴。"
    "只是……"
    ly "可恶，明明就差一点，想要合影集邮的愿望就能说出来的……"
    "合影排队的人实在是太多了。算了，还是先去尝试一下她介绍的答题活动吧。"
    "不过话说回来，龙哥去哪了？"
    "………"
    "……"
    "…"
    scene black with dissolve
    with Pause(0.5) 
    jump C1b3


label C1b3:
    scene qf with dissolve
    "这些题目……"
    "似乎有些过于简单了？"
    sy1 "同学，你连对了20道题，可以抽奖五次。"
    ly "这些题目果然很简单。能抽奖五次吗。让我看看……"
    show xiquan_shame as xiquan at leftin_dissolve
    #voice "audio/xiquan/xq06.wav"
    xq "呼……终于忙活完了……她那么开心，剩下的先交给她吧……我先回摊位前坐一会儿……"
    by2 "啊，汐泉，你来得正好。我们发现一个连对20道题的同学。"
    show xiquan_curious as xiquan with chara_trans
    #voice "audio/xiquan/xq07.wav"
    xq "什么，还有这么厉害的同学？"
    ly "唔嗯？谁在说话……"
    #voice "audio/xiquan/xq08.wav"
    show xiquan_angry as xiquan with chara_trans
    xq "是我！"
    "一个女生从摊位后面走了出来。正仰着头看着我。"
    show xiquan_serious as xiquan with chara_trans
    #voice "audio/xiquan/xq09.wav"
    xq "诶？是新面孔呢。你是新生？"
    ly "是的是的，这是我第一次参加咱们社的活动。"
    show xiquan as xiquan with chara_trans
    #voice "audio/xiquan/xq10.wav"
    xq "噢，是新人啊，我还以为是有人故意拿我开玩笑。"
    hide xiquan with dissolve
    "手上抓着五张纸签，我把纸签递给坐台的社员。"
    by2 "我看看……"
    by2 "只中了一次C奖……"
    ly "……啊……这样啊……"
    #voice "audio/xiquan/xq11.wav"
    show xiquan as xiquan with chara_trans
    xq "奖品是青枫动漫社书签一套。"
    "我从她手里接过书签奖品。"
    show xiquan_serious as xiquan with chara_trans
    #voice "audio/xiquan/xq12.wav"
    xq "话说你是一个人吗，没有遇上什么难处吧。"
    ly "一开始是有点不知所措，不过幸好有个出cos的老师帮助我，给我介绍了社团的活动……"
    #voice "audio/xiquan/xq13.wav"
    xq "噢，一位coser啊……是社团工作员吗？"
    ly "这……这我也不清楚……应该是吧……"
    #voice "audio/xiquan/xq14.wav"
    show xiquan as xiquan with chara_trans
    xq "嗯，没关系，今晚的社员大会上你可以留意一下。"
    ly "社员大会？"
    yierli "汐泉，怎么样？活动还顺利吗？"
    #voice "audio/duou/duou23.wav"
    show xiquan as xiquan with dissolve:
        xpos 1300
    show duou_confident as duou at leftin_dissolve:
        xpos 700
    "明日香来了……"
    "更正，是cos明日香的那位一二里前辈回来了。"
    #voice "audio/xiquan/xq15.wav"
    show xiquan_hachi as xiquan with chara_trans:
        xpos 1300
    xq "渡鸥部长！你怎么这么快就回来了？"
    ly "……部长？"
    show xiquan as xiquan with chara_trans:
        xpos 1300
    #voice "audio/duou/duou24.wav"
    show duou_reliable2 as duou with chara_trans:
        xpos 700
    duou "被百团大会风纪委员会赶走了，说是不让多人聚集。"
    by2 "只是多人合影而已吧。况且疫情都过去几年了……"
    #voice "audio/duou/duou25.wav"
    duou "多人聚集原本就比较乱吧，也不好维持秩序。"
    #voice "audio/duou/duou26.wav"
    show duou_smile as duou with chara_trans:
        xpos 700
    duou "不过算啦，正好可以稍微休息一下。摄影组也拍了照片，到时候记得挑几张放进社团相册。"
    #voice "audio/duou/duou27.wav"
    show duou_confident2 as duou with chara_trans:
        xpos 700
    duou "啊，是刚才的新人啊。又见面了，同学。"
    #voice "audio/duou/duou28.wav"
    show duou_confident as duou with chara_trans:
        xpos 700
    duou "怎么样，我们的摊位你满意吗？"
    ly "“明日香”居然就是……"
    #voice "audio/duou/duou29.wav"
    duou "啊，对。我是青枫动漫社组织部部长。花名“一二里”。"
    show xiquan_smile as xiquan with chara_trans:
        xpos 1300
    #voice "audio/xiquan/xq16.wav"
    xq "我是副部长汐泉。"
    ly "那……那个，我叫落鸢，是今年的大一新生……"
    ly "另外，刚刚真是非常感谢你为我介绍动漫社的活动，渡鸥前辈！"
    #voice "audio/duou/duou30.wav"
    show duou_confident as duou with chara_trans:
        xpos 700
    duou "那是组织部的职责，别在意。"
    #voice "audio/duou/duou31.wav"
    duou "而且能被说还原，正说明我的努力没有白费呢。"
    #voice "audio/duou/duou32.wav"
    show duou_reliable as duou with chara_trans:
        xpos 700
    duou "你是专门来看cosplay的吗？还是对我们社团的其他活动感兴趣？"
    ly "我……我一直很喜欢动漫，但是从来没有参加过活动。"
    ly "看到社团的招新海报，所以打算尝试一下。但是……"
    ly "最初看到摊位人好多，有点不敢过来……"
    #voice "audio/duou/duou33.wav"
    show duou_smile as duou with chara_trans:
        xpos 700
    duou "其实完全不用害怕。社内的大家都很友善的。"
    #voice "audio/duou/duou34.wav"
    show duou_confident2 as duou with chara_trans:
        xpos 700
    duou "另外，我们动漫社有很多分部，你有感兴趣的吗？"
    ly "这个嘛……暂时还没有……"
    #voice "audio/duou/duou35.wav"
    duou "唔嗯……那也没关系。如果下定了决心，可以直接联系各分部的部长。"
    #voice "audio/duou/duou36.wav"
    show xiquan_curious2 as xiquan with chara_trans:
        xpos 1300
    xq "说起来，我一直都想问你，你是怎么知道部长的名字的？"
    #voice "audio/xiquan/xq17.wav"
    ly "那是因为，前辈她为我介绍活动的时候有人这样叫她，所以就记下来了……"
    ly "如果这样不合适的话我会更正的……"
    "意识到可能的问题后，我只好赶紧先低头认错。"
    #voice "audio/xiquan/xq18.wav"
    show xiquan_sneaky as xiquan with chara_trans:
        xpos 1300
    xq "唔嗯……"
    "……"
    #voice "audio/xiquan/xq19.wav"
    xq "倒也不是不合适，只是那是部长在组织部内用的名字。"
    ly "是这样吗？"
    #voice "audio/xiquan/xq20.wav"
    xq "是的。一般组织部部员这样叫她。“渡鸥部长”“渡鸥学姐”之类的。"
    #voice "audio/xiquan/xq21.wav"
    xq "既然这样的话……"
    ly "什……什么？"
    #voice "audio/xiquan/xq22.wav"
    show xiquan_smile as xiquan with chara_trans:
        xpos 1300
    xq "这位同学，如果你没能决定好想要加入的分部的话，我觉得组织部对你来说是个好去处——"
    ly "组织部……"
    #voice "audio/duou/duou36.wav"
    show duou_reliable2 as duou with chara_trans:
        xpos 700
    duou "主要负责组织各类活动，社团活动的计划，筹备和准备之类的工作。也负责和各分部商讨沟通的工作。"
    #voice "audio/xiquan/xq23.wav"
    show xiquan_confident as xiquan with chara_trans:
        xpos 1300
    xq "总之就是动漫社的核心啦。严格的讲组织部都不叫分部，而是本部了。"
    "但是……这需要非常强的沟通能力吧？"
    "我能做到吗……"
    #voice "audio/duou/duou37.wav"
    show duou_reliable as duou with chara_trans:
        xpos 700
    duou "不过，组织部的工作会比较多，但也相当充实。"
    #voice "audio/xiquan/xq24.wav"
    show xiquan_smile2 as xiquan with chara_trans:
        xpos 1300
    xq "嗯。在加上有渡鸥部长在，工作就更多啦。对于像你这样还没决定好想要加入什么分部的新人，我可是强烈推荐你来加入我们组织部……"
    show duou_strict as duou with chara_trans:
        xpos 700
    duou "好了，汐泉，选择是由自己做出的。"
    #voice "audio/duou/duou38.wav"
    show duou_stern as duou with chara_trans:
        xpos 700
    duou "你不要再恐吓新人了。再说就让你散场后搬桌子。"
    #voice "audio/xiquan/xq25.wav"
    show xiquan_shame as xiquan with chara_trans:
        xpos 1300
    xq "……哼。"
    show xiquan_shame as xiquan at rightout_dissolve:
        xpos 1300
    pause 0.6
    hide xiquan

    "汐泉一个人跑掉了……"
    #voice "audio/duou/duou39.wav"
    show duou_reliable3 as duou with chara_trans:
        xpos 700
    duou "总之，落鸢同学，要加入什么分部由自己来决定。就算确实没有想法，只是参加社团的活动也可以。"
    "渡鸥学姐低着头划着手机，好像在整理照片。"
    #voice "audio/duou/duou40.wav"
    show duou_smile2 as duou with chara_trans:
        xpos 700
    duou "欸，落鸢同学，说了这么多，你还没有和我合影呢。"
    ly "啊，是，是的，我本来是想的……"
    #voice "audio/duou/duou41.wav"
    show duou_confident2 as duou with chara_trans:
        xpos 700
    duou "那，要来一张吗？"
    "我站在原地犹豫着，没有上前。"
    #voice "audio/duou/duou42.wav"
    show duou_shame as duou with chara_trans:
        xpos 700
    duou "怎，怎么了？是不愿意吗……"
    ly "不，不是的，我，我很愿意……"
    #voice "audio/duou/duou43.wav"
    show duou_confident as duou with chara_trans:
        xpos 700
    duou "那就来吧。"
    "……"
    "我慢慢走上前，站在渡鸥学姐身旁。"
    "学姐没有找其他人帮忙拍照，而是举起手机，对好角度，然后立刻按下了快门。"
    ly "渡鸥学姐，谢谢你。今天你出的cos非常棒。就好像你不只是在cos，而是真的在成为她。"
    #voice "audio/duou/duou44.wav"
    show duou_smile as duou with chara_trans:
        xpos 700
    duou "真的吗？你能喜欢，我很高兴。"
    duou "加一下好友吧，我把照片发给你。"
    "渡鸥学姐伸出手，亮出自己的二维码名片。"
    ly "好的。"
    "我掏出手机，扫描下了学姐的名片。"
    #voice "audio/duou/duou45.wav"
    show duou_reliable as duou with chara_trans:
        xpos 700
    duou "社员大会上有动漫社各个分部的详细说明。方便新人认识，并决定自己要加入哪边。感兴趣的话可以来看看。"
    ly "好的。我一定会去的！"
    #voice "audio/duou/duou46.wav"
    show duou_strict as duou with chara_trans:
        xpos 700
    duou "另外，身为组织部部长，我还是想对你这样的新人说，"
    #voice "audio/duou/duou47.wav"
    show duou_smile as duou with chara_trans:
        xpos 700
    duou "如果你决定加入组织部的话，组织部会一直欢迎你。"
    "………"
    "……"
    "…"
    stop music fadeout 3.0
    scene black with fade
    with Pause(1)

    jump C1c1

