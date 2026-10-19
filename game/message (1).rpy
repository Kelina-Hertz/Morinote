# 测试用图片-头像
image phone tx_own = "gui/avatars/ly.png"
image phone tx_duou = "gui/avatars/duou.png"
image phone tx_xq = "gui/avatars/xiquan.png"
image phone tx_ela =  "gui/avatars/ela.png"
image phone tx_sora = "gui/avatars/sora.png"
image phone tx_haru = "gui/avatars/haru.png"
image phone tx_beimu = "gui/avatars/beimu.png"
image phone tx_hachiji = "gui/avatars/hachiji.png"
image phone tx_doragon = "gui/avatars/zhumeng.png"
image phone tx_ab = "gui/avatars/ab.png"
image phone tx_hinata = "gui/avatars/hinata.png"
image phone tx_ffagi = "gui/avatars/ffagi.png"
image phone tx_fgo = "gui/avatars/fgo.png"
image phone tx_wenvil = "gui/avatars/wenvil.png"
image phone tx_gilbert = "gui/avatars/gilbert.png"
image phone tx_hinata = "gui/avatars/hinata1.png"

image phone tx_b:
    Solid("#FF0000")
    xysize(40,40)

# 测试用图片-可放大的CG
image phone cg01:
    Solid("#FF00FF")
    xysize(300,300)
image phone cg01ex:
    Solid("#FF00FF")
    xysize(608,1080)
image phone cg02:
    Solid("#00FF")
    xysize(300,300) 
image phone cg02ex:
    xysize(608,1080)
    Solid("#000")
    pause 0.5
    Solid("#00f")
    pause 0.5
    Solid("#0ff")
    pause 0.5
    Solid("#fff")
    pause 0.5
    repeat
# 定义角色
 
# 写法如下，只是增加了kind=nvl参数，然后callback=Phone_NarratorSound/SendSound/ReceiveSound（发信息时角色自动使用的音效，对应第一部分设置的三个音效）
define mc_nvl = Character("落鸢",kind=nvl,callback=Phone_SendSound)# 这是第一视角的角色，定义一个新的或者对应上你的角色
#define mc_nvl = 和你的主角内容相同，只是把kind=nvl加进去，再填callback=音效函数
 
define qunyou_nvl = Character("群友",kind=nvl,callback=Phone_ReceiveSound)# 范例角色
define yierli_nvl = Character("一二里",kind=nvl,callback=Phone_ReceiveSound)# 范例角色

define xiquan_nvl = Character("汐泉",kind=nvl,callback=Phone_ReceiveSound)
define buyuan_nvl = Character("部员",kind=nvl,callback=Phone_ReceiveSound)

define hinata_nvl = Character("日向hinata",kind=nvl,callback=Phone_ReceiveSound)
define duou_nvl = Character("渡鸥",kind=nvl,callback=Phone_ReceiveSound)

define beimu = Character("棉花娃娃教主",kind=nvl,callback=Phone_ReceiveSound)
define wenvil = Character("Wenvil",kind=nvl,callback=Phone_ReceiveSound)
define ffagi = Character("FAGI",kind=nvl,callback=Phone_ReceiveSound)
define hachiji = Character("你能做的，岂止如此",kind=nvl,callback=Phone_ReceiveSound)
define ela = Character("Ela",kind=nvl,callback=Phone_ReceiveSound)
define haru = Character("春日野悠",kind=nvl,callback=Phone_ReceiveSound)
define sora = Character("春日野穹",kind=nvl,callback=Phone_ReceiveSound)
define ab = Character("Angel Beats",kind=nvl,callback=Phone_ReceiveSound)
define doragon = Character("筑梦",kind=nvl,callback=Phone_ReceiveSound)
define fgo = Character("FGO",kind=nvl,callback=Phone_ReceiveSound)
define gilbert = Character("Gilbert",kind=nvl,callback=Phone_ReceiveSound)

 
# 数据列表，由于这个系统读取的不是实例，而是记录了字符串，所以要多写一个字典来查找角色
# 结构为 {某个角色：某个角色的数据字典}
# 角色数据字典结构为 {"avatar":角色头像,"avatar_frame":角色头像框,"frame":角色对话框}
# 角色数据均可填None，为None时系统使用第一部分设置的默认头像/头像框/对话框

default phone_avatars = {
            # 玩家（发送方）
            renpy.translate_string(mc_nvl.name):{"avatar":"phone tx_own","avatar_frame":"phone tx_own","frame":None},
            # 其他角色
            renpy.translate_string(beimu.name):{"avatar":"phone tx_beimu","avatar_frame":"phone tx_beimu","frame":None},
            renpy.translate_string(wenvil.name):{"avatar":"phone tx_wenvil","avatar_frame":"phone tx_venwil","frame":None},
            renpy.translate_string(ffagi.name):{"avatar":"phone tx_ffagi","avatar_frame":"phone tx_ffagi","frame":None},
            renpy.translate_string(hachiji.name):{"avatar":"phone tx_hachiji","avatar_frame":"phone tx_hachiji","frame":None},
            renpy.translate_string(ela.name):{"avatar":"phone tx_ela","avatar_frame":"phone tx_ela","frame":None},
            renpy.translate_string(haru.name):{"avatar":"phone tx_haru","avatar_frame":"phone tx_haru","frame":None},
            renpy.translate_string(sora.name):{"avatar":"phone tx_sora","avatar_frame":"phone tx_sora","frame":None},
            renpy.translate_string(ab.name):{"avatar":"phone tx_ab","avatar_frame":"phone tx_ab","frame":None},
            renpy.translate_string(doragon.name):{"avatar":"phone tx_doragon","avatar_frame":"phone tx_doragon","frame":None},
            renpy.translate_string(yierli_nvl.name):{"avatar":"phone tx_duou","avatar_frame":"phone tx_duou","frame":None},
            renpy.translate_string(duou_nvl.name):{"avatar":"phone tx_duou","avatar_frame":"phone tx_duou","frame":None},
            renpy.translate_string(buyuan_nvl.name):{"avatar":"phone tx_b","avatar_frame":"phone tx_b","frame":None},
            renpy.translate_string(gilbert.name):{"avatar":"phone tx_gilbert","avatar_frame":"phone tx_gilbert","frame":None},
            renpy.translate_string(fgo.name):{"avatar":"phone tx_fgo","avatar_frame":"phone tx_fgo","frame":None},
            renpy.translate_string(xiquan_nvl.name):{"avatar":"phone tx_xq","avatar_frame":"phone tx_xq","frame":None},
            renpy.translate_string(hinata_nvl.name):{"avatar":"phone tx_hinata","avatar_frame":"phone tx_hinata","frame":None},
            }

# 手机信息事件：
label phonelabel_01:
    $ nvl_mode = "phone" # 先打开手机模式
    show screen qq_totalgroup("青枫动漫社(2000)","群主很懒，还没有群介绍噢~")
    nvl_narrator "13：22"(interact=False)
    nvl_narrator "你加入了 青枫动漫社 "
    #$$ achievement.grant("first_launch")
    ab "欢迎新人！"
    ffagi "欢迎新人！"
    hachiji "新人新人！"
    beimu "每年这个时候你社都蒸蒸日上"
    beimu "不赖"
    beimu "{image=phone/emoji/nainiumao.png}"
    hachiji "现在还有群友在西操吗"
    doragon "有的兄弟有的"
    doragon "下午还有活动的"
    ab "羡慕能去百团大会的"
    hachiji "@筑梦 豪德，下午过去玩（）"
    xiquan_nvl "【自动发送】 @落鸢 欢迎来到我们青枫大家庭！群文件里可以提前了解分部信息，百团上欢迎来我们摊位看看。"
    ela "自动发送就是好用，有人懂吗（）"
    haru "汐泉都开自动回复了"
    haru "难道说，要出cos？"
    yierli_nvl "不是她，是我要出"
    ffagi "原来是一二里部长"
    ffagi "难怪一上午都没见到你"
    yierli_nvl "毕竟要招新，当然要出啊"
    xiquan_nvl "这次的cosplay很复杂，准备起来很麻烦"
    yierli_nvl "出什么暂时保密，下午你们就知道了"
    wenvil "期待"
    hachiji "期待"
    ela "期待"
    ffagi "期待"
    haru "期待"
    sora "期待"
    nvl clear # 清空nvl界面，释放缓存
    hide screen qq_totalgroup
    #$ nvl_mode = None # 关闭手机模式（养成封闭习惯）
    return

label phonelabel_02:
    $ nvl_mode = "phone"
    show screen qq_totalgroup("青枫动漫社组织部","来了就要干活嗷")
    nvl_narrator "你加入了 青枫动漫社活动组织部"
    fgo "还有新人？"
    gilbert "哇，百团最后一天还有新人！"
    fgo "欢迎新人！"
    ffagi "渡鸥部长发力了"
    gilbert "汐泉大人发力了"
    menu(nvl=True):
        "自我介绍一下":
            mc_nvl "大家好，我是组织部新部员，落鸢，"
            mc_nvl "今后请大家多多指教"
            pass
    gilbert "哦，我想起来了"
    gilbert "是今天那个连对二十道题的强人！"
    ffagi "太强了"
    gilbert "太强了"
    buyuan_nvl "太强了"
    xiquan_nvl "太强了"
    buyuan_nvl "所以我们组织部今年招新就结束了？"
    xiquan_nvl "又不是过了百团就不能加组织部"
    xiquan_nvl "以后还会有新人的"
    buyuan_nvl "哦？汐泉姐要继续发力了"
    xiquan_nvl "@全体成员 百团大会到今天就彻底结束了"
    xiquan_nvl "各位部员们辛苦了 今天早点休息"
    xiquan_nvl "后面还有很多大型活动 还需要大家出力呢"
    buyuan_nvl "结束啦！"
    buyuan_nvl "明白"
    buyuan_nvl "忠！诚！"
    nvl clear # 清空nvl界面，释放缓存
    hide screen qq_totalgroup
    $ nvl_mode = None # 关闭手机模式（养成封闭习惯）
    return

label phonemsg_duou01:
    $ nvl_mode = "phone"
    show screen qq_totalgroup("渡鸥","是鸥不是鸦")
    nvl_narrator "22:49"(interact=False)
    duou_nvl "抱歉，刚卸完妆，没来得及欢迎一下你"
    mc_nvl "不，没关系的，部长"
    mc_nvl "组织部员都很热情，而且汐泉副部长也来欢迎了"
    mc_nvl "今天一天，部长也累坏了，就不用麻烦你了"
    duou_nvl "确实，今天的确忙坏了"
    duou_nvl "虽说要忙的事情还在后面就是了"
    mc_nvl "另外，渡鸥部长，你今天的cos真的太棒了"
    mc_nvl "你也是cos组成员吗？"
    duou_nvl "当然是"
    duou_nvl "组织部的事务忙不过来，所以就退出cos组了"
    duou_nvl "但现在是cos组的编外人员，活动时也会出cos"
    mc_nvl "组织部的要忙的事原来这么多嘛"
    duou_nvl "也和组织部部长这个职位有关系啦"
    duou_nvl "今天当了一天明日香，不少新人都直接叫我“明日香”，搞得我都反应不过来了"
    duou_nvl "给那么一大群人集邮也很累……还好被风纪委员会赶走了"
    mc_nvl "渡鸥部长既然累了的话就多休息"
    mc_nvl "平常工作的时候也是"
    duou_nvl "嗯。谢谢你"
    duou_nvl "既然当了组织部部长，就要做好部长该做的工作"
    duou_nvl "不过嘛，cosplay的活动，我还是想继续下去"
    mc_nvl "是因为喜欢cos吗？"
    mc_nvl "我觉得渡鸥部长你一定很喜欢cosplay"
    mc_nvl "今天的cos，如果不是非常喜爱cosplay的人，是绝对做不到那么还原的"
    duou_nvl "hhhh让你说中了"
    duou_nvl "今天的cos我的确准备了很长时间，因为我热爱cosplay"
    duou_nvl "人做着自己真正热爱的事，是不会觉得累的。反而会觉得动力源源不断"
    duou_nvl "不过，谢谢你今天捧场，也谢谢你的提醒"
    duou_nvl "青枫动漫社组织部部长，燕渡鸥，欢迎你的加入。"
    duou_nvl "过段时间会有组织部特别会议，要商讨一个大型活动的策划方案"
    mc_nvl "是什么大型活动？"
    duou_nvl "十二月的江城冬日fes"
    duou_nvl "关注群通知，记得准时参加哦！"
    nvl clear # 清空nvl界面，释放缓存
    hide screen qq_totalgroup
    $ nvl_mode = None # 关闭手机模式（养成封闭习惯）
    return

label phonemsg_xiquan01:
    $ nvl_mode = "phone"
    show screen qq_totalgroup("汐泉","好孩子不玩身高梗")
    nvl_narrator "21:32"(interact=False)
    xiquan_nvl "我是青枫动漫社活动组织部副部长，汐泉"
    xiquan_nvl "同学，你是谁呀？"
    menu(nvl=True):
        "我是组织部新部员，落鸢":
            mc_nvl "我是组织部新部员，落鸢"
            pass
        "副部长你不记得我了吗":
            mc_nvl "副部长我们刚刚还一起说过话来着"
            xiquan_nvl "我是说，我是青枫动漫社活动组织部副部长，汐泉"
            xiquan_nvl "同学，你是谁呀？"
            menu(nvl=True):
                "我是组织部新部员，落鸢":
                    mc_nvl "我是组织部新部员，落鸢"
                    pass
    xiquan_nvl "哦~原来你是新部员呀！"
    xiquan_nvl "我还以为你已经忘了自己是组织部部员了呢~"
    xiquan_nvl "所以你既然知道自己是新部员 为什么不来主动加我"
    xiquan_nvl "我猜你也没加渡鸥的联系方式吧"
    mc_nvl "哦不是，渡鸥部长以及加上了"
    xiquan_nvl "？！什么时候的事？"
    mc_nvl "下午的百团，和她一起合了影，要发一下照片所以加上了"
    xiquan_nvl "哦"
    xiquan_nvl "好吧"
    xiquan_nvl "不过活动现场的筹备还是我负责的"
    xiquan_nvl "活动有很多，记得来当苦力噢"
    xiquan_nvl "啊不是"
    xiquan_nvl "刚刚发错了，是参与活动的准备"
    mc_nvl "具体要做些什么呢"
    xiquan_nvl "嗯……挺多的。等活动筹备时"

    mc_nvl "不，不会的"
    mc_nvl "我也是组织部员，加一下副部长的联系方式很有必要"
    xiquan_nvl "那部长的呢"
    xiquan_nvl "哦 想起来了 你俩早就加上了"
    xiquan_nvl "我问你 你加入组织部是因为谁 我还是渡鸥部长"
    mc_nvl "这是……什么意思？"
    xiquan_nvl "就是问你是谁让你决定了要加组织部的"
    xiquan_nvl "少废话 选一个"
    mc_nvl "必须选一个？"
    xiquan_nvl "对 不能有其他答案"
    menu(nvl=True):
        "是你":
            mc_nvl "是你"
            xiquan_nvl "？"
            xiquan_nvl "为什么是我"
            mc_nvl "毕竟是你首先向我推荐组织部的"
            mc_nvl "社员大会上还命令我仔细听组织部的讲演"
            mc_nvl "我几乎是被你拉进组织部的"
            xiquan_nvl "好吧 你还挺机灵的"
            xiquan_nvl "我果然没看错人 你这种最适合的就是组织部"
            pass
        "是渡鸥部长":
            mc_nvl "是渡鸥部长"
            xiquan_nvl "呵"
            xiquan_nvl "猜到了"
            xiquan_nvl "但我难道就没有一点功劳吗"
            xiquan_nvl "到底是谁在满场跑 不遗余力地拉新人"
            xiquan_nvl "你回答我"
            mc_nvl "汐泉姐你的宣传确实非常有力"
            mc_nvl "但自己的选择终究还是自己做出的"
            mc_nvl "加入组织部是我的选择"
            xiquan_nvl "完了 新人的讲话方式已经被渡鸥传染了"
            pass
    xiquan_nvl "我提前说好 渡鸥部长要求很严格的"
    xiquan_nvl "工作迟到一分钟 她能用眼神把你钉在墙上"
    xiquan_nvl "上次fes申请场地 我交表少盖一个章 她让我从头到尾重搞一份"
    xiquan_nvl "她真的是完美主义者 容不下一丁点马虎"
    mc_nvl "我觉得这样很好啊"
    mc_nvl "渡鸥部长工作认真，组织部员们的工作也会认真起来"
    xiquan_nvl "尤其是对我这个副部长 我可是她的重点关注对象"
    xiquan_nvl "所以说 新人你要做好准备 要是工作马虎会被部长训斥嗷"
    mc_nvl "明白，我会认真工作的"
    xiquan_nvl "哎哎 不过嘛 上次我生病 是她帮我代了三天班"
    xiquan_nvl "组织部的工作本来就多 她一人还顶下了部长和副部长的所有工作"
    xiquan_nvl "而且还不让任何人告诉我"
    xiquan_nvl "她就是这样 什么事都默默扛"
    xiquan_nvl "所以不要有压力 包括我和渡鸥在内 组织部的所有人都是一个大家庭"
    mc_nvl "好的，谢谢你告诉我这些"
    xiquan_nvl "哎哎哎 刚才那些话不要告诉渡鸥啊"
    xiquan_nvl "更别告诉别人是我告诉你的"
    xiquan_nvl "不 你干脆什么人都不要告诉"
    xiquan_nvl "要是守口不严小心我捶你"
    nvl clear # 清空nvl界面，释放缓存
    hide screen qq_totalgroup
    $ nvl_mode = None # 关闭手机模式（养成封闭习惯）
    return               

label phonemsg_hinata01:
    $ nvl_mode = "phone"
    show screen qq_totalgroup("日向","向那道光奔去")
    nvl_narrator "09：13"(interact=False)
    hinata_nvl "早，今天是周末，应该休息吧"(interact=False)
    hinata_nvl "我今天就宅家里看漫画"(interact=False)
    nvl_narrator "12：42"(interact=False)
    hinata_nvl "怎么不回消息"(interact=False)
    hinata_nvl "该不会还没起吧"(interact=False)
    nvl_narrator "13：45"(interact=False)
    hinata_nvl "是真的在忙吗？"(interact=False)
    hinata_nvl "还是在睡午觉？"(interact=False)
    nvl_narrator "15：31"(interact=False)
    hinata_nvl "哇我跟你说，我刚发现一部超赞的小众冷门漫画"(interact=False)
    hinata_nvl "不行，必须狠狠给你安利一下"(interact=False)
    hinata_nvl "总之快回我消息"(interact=False)
    nvl_narrator "17：21"(interact=False)
    hinata_nvl "你今天到底干啥去了，一整天都没动静"(interact=False)
    hinata_nvl "大学周末难不成要没收手机？"(interact=False)
    nvl_narrator "18：25"(interact=False)
    hinata_nvl "在不在在不在在不在在不在"(interact=False)
    nvl_narrator "19：37"(interact=False)
    hinata_nvl "{image=phone/emoji/shitsubo.png}"(interact=False)
    mc_nvl "抱歉，日向，今天一直忙到现在"
    hinata_nvl "呦，我们的大忙人终于有空回复消息了"
    hinata_nvl "你白天都忙什么江山社稷的大事呢"
    mc_nvl "也没什么"
    mc_nvl "今天我去参加了我们学校的百团大会"
    hinata_nvl "百团大会？是什么对抗演习吗"
    mc_nvl "不是。是社团的招新大会。所有社团都会一起在操场上招收新人，"
    mc_nvl "还有表演，互动，路演之类的"
    hinata_nvl "羡慕大学生"
    hinata_nvl "为什么我们学校没有这些"
    hinata_nvl "{image=phone/emoji/cry.png}"
    mc_nvl "你还是高中生，等你上了大学也会有这些的"
    hinata_nvl "那有动漫社吗"
    mc_nvl "当然有啊，动漫社活动可丰富了"
    mc_nvl "答题抽奖，轻音部路演，会场还有coser"
    mc_nvl "还有超级多的分部"
    hinata_nvl "{image=phone/emoji/wao.png}"
    hinata_nvl "你那是什么神仙学校，活动这么丰富"
    hinata_nvl "叫什么来着，新熊屋大学？"
    mc_nvl "新屋熊大学"
    hinata_nvl "哦哦，对，新屋熊大学"
    mc_nvl "说起来，你今年也高三了吧"
    mc_nvl "有自己心仪的大学吗"
    hinata_nvl "别吵，我有我的打算"
    mc_nvl "高三了还抱着手机玩吗"
    hinata_nvl "你怎么跟我妈一样教训起我来了"
    hinata_nvl "都说了我有我的打算"
    mc_nvl "那好吧"
    mc_nvl "不过，高三还是注意休息"
    mc_nvl "我先睡了，晚安"
    hinata_nvl "嗯嗯。晚安哦"
    hinata_nvl "{image=phone/emoji/oyasumi.png}"
    nvl clear # 清空nvl界面，释放缓存
    hide screen qq_totalgroup
    $ nvl_mode = None # 关闭手机模式（养成封闭习惯）
    return         

