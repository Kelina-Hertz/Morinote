label C1c1:
    scene block_n1 with dissolve
    play music "audio/bgm/yoru_demo.mp3"
    "我向着教学楼走去。"
    "要是换做几天前的我，这时一定带着书和习题册。"
    "但此时，除了之前抽奖抽中的书签奖品以外，就是两手空空。"
    "在操场上的百团大会逛了一大圈后，现在正准备动身前往动漫社的社员大会。"
    #show duou_confident as duou with chara_trans
    duou "社员大会上有动漫社各个分部的详细说明。方便新人认识，并决定自己要加入哪边。"
    ly "如果真的能有适合我的分部就好了……"
    #show duou_smile as duou with chara_trans
    duou "如果你决定加入组织部的话，组织部会一直欢迎你。"
    #hide duou
    #show xiquan_confident2 as xiquan with chara_trans
    xq "我可是强烈推荐你来加入我们组织部……"
    scene w12_1 with fade
    ly "……"
    ly "组织部啊……"
    scene w12_2 with fade
    stop music fadeout 1.0
    "进了教学楼的大门，正准备继续走进中庭……"
    "……"
    show wenzhu as wenzhu with dissolve
    play music "audio/bgm/wenzhu.mp3" volume 0.75
    "中庭的大理石台旁，站着一个女孩子。"
    "咖啡色的长发扎成麻花辫顺在身后。"
    "手上拎着白色的小提包，还别着一枚书签，和我手中的书签一模一样。"
    "她微微侧头，我和她对上了视线。"
    "下一秒，她面对着我，迈开腿小跑过来。"
    show wenzhu2 as wenzhu with chara_trans
    girl "请问，你也是去参加动漫社社员大会的吗？"
    "这声音很轻，很细，像怕惊动什么似的。"
    ly "是……同学你也是吗？"
    show wenzhu_smile as wenzhu with chara_trans
    girl "是的，但我找不到活动室在哪。"
    "这……是想要我带路的意思吧？"
    ly "这……是想要我带路的意思吧？"
    "她的脸上自然地露出舒心的微笑。"
    show wenzhu_smile2 as wenzhu with chara_trans
    girl "谢谢你，同学。请问怎么称呼你？"
    "……！"
    ly "我，我叫落鸢……"
    show wenzhu_smile as wenzhu with chara_trans
    girl "落鸢同学……嗯。我记住了。"
    girl "另外，叫我文竹就好。"
    "文竹……好文艺的名字……"
    ly "那……文竹同学，我们走吧。"
    show wenzhu2 as wenzhu with chara_trans
    wz "嗯。"
    "……"
    stop music fadeout 0.5
    scene black with dissolve
    with Pause(0.5)
    scene w12_2 with dissolve
    play music "audio/bgm/wenzhu.mp3" volume 0.6
    show wenzhu as wenzhu with dissolve
    "明明是第一次见面，明明只是帮她带个路，"
    "现在就已经知道彼此的名字了？"
    "这女孩子……不，文竹她，还真是自来熟……"
    "我和她并排走在中庭，随即转个方向，向楼梯口走去。"
    "文竹没有讲话，她走路很轻，踩在台阶上，听不见她的脚步声。"
    "说起来，今天白天也被渡鸥学姐这样指过路呢。"
    ly "那个……"
    "我决定试着敲开话匣子。"
    show wenzhu2 as wenzhu with chara_trans
    wz "唔？"
    ly "文竹你是怎么知道我也是去社员大会的？"
    "如果今天我如往常一样是去自习室的，在别人问路时就只能给你否定的回答了。"
    "本来这才是更常见的情况……"
    "但换做是我，那时一定会紧张加尴尬到不知所措。"
    show wenzhu_smile as wenzhu with chara_trans
    wz "其实很明显噢。"
    ly "嗯？"
    show wenzhu2 as wenzhu with chara_trans
    wz "你的口袋里有青枫的书签。"
    ly "啊……"
    "白天抽中的奖品，随手往口袋里一揣就出发了……"
    "低头看看，那书签确实露出来了一半，似乎快要掉了。"
    "我赶紧把它往里塞一塞。"
    ly "是这样啊……你观察还挺仔细的……"
    "一般人会观察到这点吗？"
    "……"
    ly "嗯。我们到了。"
    "我们到了一间大活动室门前。门半掩着。"
    "我推开活动室门，随即站到一侧。"
    show wenzhu_smile as wenzhu with chara_trans
    wz "谢谢你。"
    "轻声道过谢后，文竹迈着步子轻轻走了进去。"
    stop music fadeout 1.0

    scene room2 with dissolve
    #show wenzhu_smile as wenzhu with dissolve
    play music "audio/bgm/taikai01.ogg"
    "我在她之后也进了活动室。里面已经坐了不少人。"
    ly "人真多啊……"
    wz "动漫社的热度果然很高呢……"
    "我们在角落里找到位置坐了下来，社员大会没过一会儿就开始了。"
    "首先上台的想必是动漫社的社长……"
    
    show duou_confident as duou at leftin_dissolve
    duou "所有今天来参加社员大会的新人们，你们好！"
    "熟悉的嗓音，熟悉的那抹红色……"
    "渡鸥部长？"
    show duou_reliable as duou with chara_trans
    duou "因为今天社长临时有事缺席，所以今天首先由我，来为本年度青枫大家庭的新成员介绍我们动漫社的详细信息。"
    duou "我是青枫动漫社组织部部长，一二里。"
    show duou_confident2 as duou with chara_trans
    duou "这套衣服是白天在百团大会现场的cos服。"
    duou "时间原因没能来得及换衣服，所以我只能这样直接上台了。"
    "言毕，渡鸥部长露出了浅浅的苦笑。"
    show duou_smile as duou with chara_trans
    "但旋即而来的是满场热烈的掌声。"
    "汐泉赶忙跑到门口关上了活动室的大门。"
    hide duou with dissolve
    "等到掌声平息，渡鸥学姐正式开始了自己的讲演。"
    "她站在台前，身后的大屏幕上是各分部的结构图。"
    "银铃般的嗓音，随着双唇碰触仿佛瞬间穿透全场。"
    "即便面对观众，也毫不怯场；声音不大，但吐字清晰。"
    "连坐在最后角落里的我，都感受到了她洋溢出来的自信。"
    "不，那不仅仅是自信，"
    "还有面对所有听众，背靠整个社团的热情。"
    "社团总览的讲演比较短，很快就结束了。"
    "讲演完毕后，渡鸥学姐向全场致意，会场内又充满了热烈的掌声。"
    "……"
    #show wenzhu_smile as wenzhu with chara_trans
    "随后，各个部分的负责人轮流上台介绍。"
    "首先是绘画组，我注意到这时的文竹异常的专注，聚精会神地听着。"
    ly "你对绘画组感兴趣吗？"
    show wenzhu2 as wenzhu with chara_trans
    wz "是。我喜欢画画。"
    ly "那，你也会加入绘画组的吧？"
    show wenzhu_smile2 as wenzhu with chara_trans
    wz "对。"
    hide wenzhu with dissolve
    "绘画组……可我完全不懂绘画……"
    "绘画组讲演结束后，是轻音组的讲演。"
    "然后是舞团，配音部，cos组，Vtuber组……"
    "听完了几乎所有分部的讲演，但我仍然对自己想去的分部毫无主意。"
    "白天在百团大会上也是这样。"
    "我看遍了所有社团，但奈何我对这些全都一窍不通。"
    "即便所有的社团全都异口同声地“同样欢迎一窍不通但感兴趣的新人”，"
    "但我的眼前仿佛有一层厚障壁，让我没能再向前进，而是选择了后退。"
    "我原本以为自己在动漫社能有所变化……"
    ly "结果在动漫社也是一样的吗……"
    show xiquan_curious as xiquan at leftin_dissolve
    #voice "audio/xiquan/xq26.wav"
    xq "什么一样？"
    ly "呜哇！"
    "耳边突如其来但又独具特色的嗓音。"
    "一回头，汐泉正站在我旁边的过道里。"
    #voice "audio/xiquan/xq27.wav"
    show xiquan_curious2 as xiquan with chara_trans
    xq "你刚刚说什么一样？"
    ly "没，没什么……"
    #voice "audio/xiquan/xq28.wav"
    show xiquan_however as xiquan with chara_trans
    xq "是吗……"
    ly "……"
    xq "……"
    show wenzhu2 as wenzhu with dissolve:
        xpos 700
    show xiquan_however as xiquan with chara_trans:
        xpos 1300
    wz "那个……请问你是社长吗？"
    #voice "audio/xiquan/xq29.wav"
    show xiquan_confident as xiquan with chara_trans:
        xpos 1300
    xq "我？我不是社长。我只是组织部的副部长。"
    show wenzhu_smile as wenzhu with chara_trans:
        xpos 700
    wz "那么，学姐你知道自由交流环节什么时候开始吗？"
    #voice "audio/xiquan/xq30.wav"
    show xiquan_curious as xiquan with chara_trans:
        xpos 1300
    xq "嗯？啊，自由交流环节啊……接下来还有最后一个分部的讲演，然后就是自由交流环节了。"
    show wenzhu_smile2 as wenzhu with chara_trans:
        xpos 700
    wz "好的，谢谢你。"
    #voice "audio/xiquan/xq31.wav"
    show xiquan_smile as xiquan with chara_trans:
        xpos 1300
    xq "没事……不过这位同学你是新人吧？有想加入的分部吗？"
    show wenzhu2 as wenzhu with chara_trans:
        xpos 700
    wz "有。我想加入绘画部。"
    #voice "audio/xiquan/xq32.wav"
    show xiquan_smile2 as xiquan with chara_trans:
        xpos 1300
    xq "啊，绘画部啊，这样啊。真不错呢……"
    "她不会又想往组织部拉人吧？"
    hide wenzhu with dissolve
    #voice "audio/xiquan/xq33.wav"
    show xiquan_sneaky as xiquan with chara_trans:
        xpos 1300
    xq "所以，你考虑得如何？"
    ly "啊？考虑？"
    #voice "audio/xiquan/xq34.wav"
    show xiquan_angry as xiquan with chara_trans:
        xpos 1300
    xq "考虑加入组织部的事啊！……你不会有别的想加入的分部了吧？"
    ly "啊，那没有……"
    #voice "audio/xiquan/xq35.wav"
    show xiquan_serious as xiquan with chara_trans:
        xpos 1300
    xq "……马上就是组织部的讲演会了，你给我认真听。"
    hide xiquan with dissolve
    hide wenzhu with dissolve
    "她留下这样一句命令，然后转头跑走了。"
    "……"
    scene black with dissolve
    with Pause(0.5)
    jump C1c2

label C1c2:
    scene room2 with dissolve
    sy1 "那么，现在开始最后一个分部，组织部的讲演会！"
    sy1 "讲演会结束后将开始自由交流环节！"
    "组织部被放在最后一个，应该是压轴登场。"
    "渡鸥部长再一次登台了。仍然穿着那一抹红。"
    play music "audio/bgm/speech.ogg"
    show duou_confident as duou with dissolve
    duou "是的，各位同学。还是我，一二里。"
    "虽然早有预料，但台下掌声的热浪仍旧一浪高过一浪。"
    show duou_reliable as duou with chara_trans
    duou "身为组织部部长，组织部的讲演会当然有我给大家主持。"
    duou "在这座城市，在这所学校，有许许多多别样的演出和漫展活动。"
    show duou_confident2 as duou with chara_trans
    duou "十二月的江城冬日FES，四月的社团文化节，五月的萌歌会……"
    duou "这些活动每次举办时，都会吸引千万ACGN爱好者。"
    show duou_reliable2 as duou with chara_trans
    duou "包括之前的分部在内的所有人，大家同处一处，一同活动。"
    show duou_smile as duou with chara_trans
    duou "一起欢笑，一起高歌。"
    show duou_reliable as duou with chara_trans
    duou "为了这些活动能够顺利进行并圆满结束，当然需要一部分人集结起来。"
    duou "一起策划，一起商讨，为活动做准备。"
    show duou_strict as duou with chara_trans
    duou "而这，就是组织部。"
    "……"
    hide duou with dissolve
    "这一刻的渡鸥部长，和大会开始时讲解社团总览时的渡鸥学姐，"
    "似乎，又不一样了。"
    "面对听众，背靠社团，虽然她的嗓音依旧穿透全场，"
    "依旧自信，依旧落落大方，"
    "但渡鸥部长此时的讲演声中，透着一种成熟的稳重和认真。"
    "仿佛她背后的社团有千钧之重。"
    "她依旧稳步向前。"
    "……"
    show duou_reliable3 as duou with chara_trans
    duou "无论何时，无论何地。只要你还热爱着这里，热爱着这份美好，"
    duou "加入组织部，和我们一起创造，记录，回顾。"
    show duou_smile as duou with chara_trans
    duou "青枫动漫社活动组织部，欢迎你的加入。"
    "渡鸥部长面对听众，优雅地鞠了一躬。"
    "不知是第几遍了，耳畔又传来那热烈的掌声。"
    show duou_smile as duou with chara_trans:
        xpos 1300
    show wenzhu_smile as wenzhu with chara_trans:
        xpos 700
    wz "落鸢同学听得真认真呢。"
    ly "唔？啊……嗯，似乎是吧……"
    show wenzhu2 as wenzhu with chara_trans:
        xpos 700
    wz "你想加入组织部吗？"
    ly "这个……或许吧……"
    sy2 "分部讲演会到此结束！现在进入自由交流环节！"
    stop music fadeout 2.0
    show wenzhu_smile2 as wenzhu with chara_trans:
        xpos 700
    wz "啊，我要去一下绘画组那边。"
    hide wenzhu with dissolve
    hide duou with dissolve
    "文竹站起身，我赶忙起身为她让路。"
    "她向我致意后，小跑着往绘画组交流区去了。"
    ly "那么，我要去做什么呢……"
    "环顾四周，汐泉似乎不在这里，渡鸥部长也不在。"
    ly "再去转转看吧……"
    "抱着这样的想法，我也起身向前走去。"
    scene black with dissolve
    with Pause(0.5)
    scene room4 with fade
    "文竹似乎已经到绘画组交流区了。"
    "似乎正在自己的活页本上画着什么。"
    "旁边的配音部交流区则围了很多人，"
    "是配音部部长正在进行即兴配音表演。"
    "再往前走一走，前面的那是……"

    scene room3 with Dissolve(1)
    play music "audio/bgm/lanxue.mp3"
    "一个女生独自坐在那里。"
    "她低着头，黑色的长发自然地垂到两侧。"
    "双臂之间擎着一把吉他，修长的手指拨弄着吉他弦。"
    "身前的桌子上放着一叠五颜六色的彩纸，似乎是传单一类的东西。"
    ly "是轻音部的吗？怎么只有她一个人？"
    "不仅如此，在其他分部都人满为患的时候，这里却空无一人。"
    "说起来，白天的轻音部表演，的确有个弹吉他的高个子女生……"
    "会是她吗？"
    "……"
    "她似乎弹完了一曲，手从指板上滑了下来，捋了捋自己修长的黑发。"
    "我决定现在上前去看看。"
    show lanxue as lanxue with dissolve
    ly "请问……"
    #voice "audio/lanxue/lanxue01.wav"
    jyosei "啊，欢迎。这里是轻音部下属乐队，LIVE BOOM."
    "她的声音冷冷的，像冰一样。"
    ly "果……果然是轻音部啊。"
    "我拿起一张她身前的传单。"
    "传单上乐队特色、要求和联系方式都印得清清楚楚。"
    "也包括吉他手的名字。"
    "原来叫蓝雪啊……真是人如其名。"
    ly "今天白天时轻音部也在动漫社摊位旁边演出了，对吧？"
    #voice "audio/lanxue/lanxue02.wav"
    #show lanxue_relax as lanxue with chara_trans
    jyosei "那是路演活动。轻音部下属的乐队很多，我们只是其中一个。"
    #voice "audio/lanxue/lanxue03.wav"
    #show lanxue_curious as lanxue with chara_trans
    jyosei "你看了我们的表演了？"
    ly "嗯。看到了。学姐你就是吉他手蓝雪对吧？"
    #voice "audio/lanxue/lanxue04.wav"
    show lanxue_shame as lanxue with chara_trans
    lx "……学姐？"
    ly "啊，难……难道不是么……"
    #voice "audio/lanxue/lanxue05.wav"
    show lanxue as lanxue with chara_trans
    lx "我是今年的新生。"
    ly "啊……原来是这样啊……"
    lx "……"
    ly "……"
    #voice "audio/lanxue/lanxue06.wav"
    show lanxue_shame as lanxue with chara_trans
    lx "所以，你要加入吗？"
    ly "呃？我……我其实完全不懂音乐……"
    #voice "audio/lanxue/lanxue07.wav"
    show lanxue_kissing as lanxue with chara_trans
    lx "啊，那就不行了。我们只欢迎有演奏水准的新人加入。"
    "拒绝得真快……轻音部果然和别的分部大不相同……"
    #voice "audio/lanxue/lanxue08.wav"
    show lanxue as lanxue with chara_trans
    lx "轻音部和别的分部不一样。轻音部的演出和活动很多。"
    #voice "audio/lanxue/lanxue09.wav"
    #show lanxue_relax2 as lanxue with chara_trans
    lx "本来练习时间就很紧张，根本没时间辅导新人，更不可能有时间教新人学乐器。"
    ly "这样啊，那好吧。"
    "我放下传单，准备离开。"
    #voice "audio/lanxue/lanxue10.wav"
    show lanxue_worry as lanxue with chara_trans
    lx "等一下。"
    ly "嗯？"
    "蓝雪站起身，把我刚才放下的那张传单递给了我。"
    "她的个字的确很高……快和我一样高了。"
    #voice "audio/lanxue/lanxue11.wav"
    show lanxue_shame as lanxue with chara_trans
    lx "就是，那个……"
    #voice "audio/lanxue/lanxue12.wav"
    #show lanxue_realx as lanxue with chara_trans
    lx "……如果身边的人有会乐器的话，就请给他看这张传单。"
    "我接过了那张传单。"
    ly "是要我帮你做宣传吗？"
    #voice "audio/lanxue/lanxue13.wav"
    show lanxue_shame2 as lanxue with chara_trans
    lx "不是。其实是……"
    "她貌似怔住了，迟迟说不出话来。"
    "其实就是帮助做宣传吧。"
    show lanxue_shame as lanxue with chara_trans
    ly "好吧，我明白了。我会帮你的。"
    "我把传单卷了卷，塞进口袋里。"
    "蓝雪见我答应了她，又坐了下来。继续拨弄她的吉他。"
    hide lanxue with dissolve
    "我也转身走开了。"
    ly "只想让有演奏水准的人来，却害怕招不到人……"
    ly "真是个矛盾的女孩子……"
    scene black with dissolve
    stop music fadeout 1.0
    "………"
    "……"
    "…"

    jump C1c3

label C1c3:
    scene room2 with fade
    play music "audio/bgm/luoyuan01.ogg"
    "就像百团大会一样，我依旧走遍了所有的分部交流区。"
    "手上也拿了不少分部的传单。"
    "……"
    "不，直到现在我才意识到，"
    "并非我走遍了所有的分部，"
    "而是各个社团，各个分部从我的身边走过。"
    "熙熙攘攘，每个人都向前走去，"
    "而我仍然站在原地。任由他们从我的眼前路过。"
    "我好像想起了什么，试着向前伸出手……"
    "……但那里早已空无一人。"
    show duou_reliable as duou with chara_trans
    duou "选择是由自己做出的。"
    show duou_smile as duou with chara_trans
    duou "就算确实没有任何想法，只是参加社团的活动也可以。"
    "不，不行……"
    show duou_confident2 as duou with chara_trans
    duou "我可是强烈推荐你来加入我们……"
    "不能再这样止步不前了……"
    show duou_reliable3 as duou with chara_trans
    duou "无论何时，无论何地。只要你还热爱着这里，热爱着这份美好，"
    show duou_smile2 as duou with chara_trans
    duou "加入组织部，和我们一起创造，记录，回顾……"
    "我好像被某人引导着，"
    "不仅如此，我还被某人推了一把……"
    "只能跟上了，这熙熙攘攘向前的队伍。"
    "趁着还有机会……"
    "……"
    show duou_confident as duou with chara_trans:
        xpos 700
    show xiquan_confident as xiquan at leftin_dissolve:
        xpos 1300
    duou "快点快点，交流环节要结束了！"
    #voice "audio/xiquan/xq36.wav"
    show xiquan_curious as xiquan with chara_trans:
        xpos 1300
    xq "你先别急，慢慢来……"
    show duou_shock as duou with chara_trans:
        xpos 700
    duou "部长和副部长都不在，这怎么行！"
    "身后传来的熟悉的声音，"
    "我迈开脚步向那边走去。"
    ly "汐泉学姐！"
    #voice "audio/xiquan/xq37.wav"
    show xiquan_hachi as xiquan with chara_trans:
        xpos 1300
    xq "哇！"
    #voice "audio/xiquan/xq38.wav"
    show xiquan_smile as xiquan with chara_trans:
        xpos 1300
    xq "啊，是你啊……"
    show duou_confident as duou with chara_trans:
        xpos 700
    duou "落鸢同学，有什么事吗？"
    ly "渡鸥部长，"
    ly "我，我想要加入组织部！"
    "……"
    #voice "audio/xiquan/xq39.wav"
    show xiquan_shame as xiquan with chara_trans:
        xpos 1300
    xq "你……真的决定了？"
    ly "是的。我决定了。"
    show duou_reliable as duou with chara_trans:
        xpos 700
    duou "……之前说过，无论何时，无论何地……"
    show duou_smile as duou with chara_trans:
        xpos 700
    duou "欢迎你，落鸢同学。"
    duou "以后，你就是我们组织部的部员了。"
    ly "诶？不需要填表格之类的吗？"
    show duou_reliable2 as duou with chara_trans:
        xpos 700
    duou "不需要。现在的你已经是组织部部员了。"
    #voice "audio/xiquan/xq40.wav"
    show xiquan_confident2 as xiquan with chara_trans:
        xpos 1300
    xq "哦对了，还有一件重要的事。"
    "汐泉开始在手机上划来划去。"
    ly "什么？"
    #voice "audio/xiquan/xq41.wav"
    show xiquan_happy as xiquan with chara_trans:
        xpos 1300
    xq "快，加群！"
    "随后，她把一张明晃晃的群二维码伸到我眼前。"
    "我掏出手机，扫描了那张组织部群的二维码。"
    #voice "audio/xiquan/xq42.wav"
    show xiquan_smile2 as xiquan with chara_trans:
        xpos 1300
    xq "嘿嘿，我最喜欢给新人亮组织部群名片了！"
    #voice "audio/xiquan/xq43.wav"
    show xiquan_happy as xiquan with chara_trans:
        xpos 1300
    xq "毕竟这样就意味着组织部有新人加入了呀。"
    "她果然是在到处给组织部拉人手……"
    "而且她还一副乐在其中的样子……"
    sy2 "自由交流环节马上结束！各位社员可以有序离场！"
    #voice "audio/xiquan/xq44.wav"
    show xiquan_serious as xiquan with chara_trans:
        xpos 1300
    xq '时间快到了，今天就到这里吧。'
    show duou_reliable3 as duou with chara_trans:
        xpos 700
    duou "嗯，是啊。今天也忙坏了。"
    #voice "audio/xiquan/xq45.wav"
    show xiquan_smile as xiquan with chara_trans:
        xpos 1300
    xq "你要记得检查群消息嗷！我和渡鸥先回去了。"
    hide xiquan with dissolve
    hide duou with dissolve
    ly "啊，好的。路上小心。"
    "………"
    "……"
    "…"
    scene black with dissolve
    with Pause(0.5)

    scene block_n2 with fade
    play music "audio/bgm/yoru_demo.mp3"
    "我往宿舍的方向走去。"
    "要是换做几天前的我，这时一定带着书和习题册。"
    "但此时，不再是。"
    "在社员大会上加入组织部后，感到了一股奇妙的感觉。"
    "我无法描述这种感觉。"
    "但我知道，在动漫社的自己，正发生着变化……"
    "……"
    "嗯？有新消息……"
    call phonelabel_02
    $ unlock_achievement("first_launch2")
    "看来组织部的事务的确很多……"
    "不管怎样，既然已经决定了，干脆顺其自然好了。"
    "或许能在这里摆脱过去的阴影也说不定。"
    "嗯？手机怎么一直响……"
    call phonemsg_xiquan01
    $ unlock_achievement("xiquan_msg01")
    "……"
    "汐泉似乎相当关心渡鸥呢……"
    "白天就听渡鸥姐说过组织部部长事务很多，现在看来的确是这样。"
    "也难怪汐泉那么替渡鸥姐担心，应该是为了替她减负。"
    "或许那样努力拉新人也是这个原因吧。"
    "喔，正好渡鸥姐发信息了。"
    call phonemsg_duou01
    $ unlock_achievement("duou_msg01")
    $ check_achievements()
    "真神奇……"
    "被渡鸥姐这样一说，顿时有些期待后面的活动……"
    "这次一定要试试看。"
    ly "哎，这是……"
    ly "噢，是之前在网上认识的同好。"
    "今天一直没在看手机了……她怎么发这么多消息？"
    call phonemsg_hinata01
    "……"
    #call contact_friend_request("汐泉")
    stop music fadeout 2.5

    scene black with Dissolve(2.5)
    hinata "……"
    hinata "再等等吧……"
    hinata "我们马上就能见面了……"
    hinata "……"
    menu:
        "返回标题界面":
            return

