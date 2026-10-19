image alphaimage = "#0000"                # 用于测试的占位透明图
image betaimage = "#f5f5dc"
image gamaimage = "#FFFFFF"
image epsilonimage = "#00FF"
### 布局变量 （只要按需插入图片、根据你自己项目调整，其他部分完全不用管）################################################################
# 覆写旁白角色，添加发送信息的音效回调函数，不希望旁白有音效直接注释掉
#define nvl_narrator = NVLCharacter(who_style='nvl_label',what_style='nvl_thought',window_style='nvl_entry',type='nvl',mode='nvl',clear=False,kind=adv,callback=Phone_NarratorSound)

# 用于旁白信息的音频
define audio.phonenarrator = "audio/sound_phone_narratortext.mp3"
# 用于己方信息的音频
define audio.phonesend = "audio/sound_phone_sendtext.mp3"
# 用于对方信息的音频
define audio.phonereceive = "audio/sound_phone_receivetext.mp3"
 
default phone_bg = "gui/phone_background.png"              # 手机背景图片
default phone_fg = "alphaimage"              # 手机外框图片

# 默认 头像尺寸
default phone_avatar_xysize = (40,40)
# 默认 头像图片
#default phone_avatar = "epsilonimage"
# 默认 头像框图片
#default phone_avatar_frame = phone_avatar

# 默认 旁白的气泡
default phone_n_frame = "#0000"
# 默认 发信者的气泡
default phone_s_frame = "gamaimage"
# 默认 收信者的气泡
default phone_r_frame = "gamaimage"

default top_frame = "gamaimage"                 #标题气泡
default top_framesize = (600,100)               #标题气泡的大小，x与手机大小相同
default title_position = (740,95)
default intro_position = (740,135)


default phone_n_color = "#000000"             # 旁白文本颜色
default phone_s_color = "#000000"             # 发信者文本颜色
default phone_r_color = "#000000"             # 收信者文本颜色
 
default phone_xy = (0.5,0.45)                # 手机界面在屏幕上的坐标
default phone_xysize = (600,800)             # 手机界面的尺寸（就是外框的尺寸）

 
default p_frame_xy = (0.5,0.60)               # 聊天窗口在手机界面里的坐标
default p_frame_xysize = (590,790)           # 聊天窗口的尺寸，x方向略小于手机，y方向上方要留出空间放标题气泡
default p_frame_spacing = 10                  # 聊天消息之间的上下间隔
 
default p_narrator_width = 480                # 旁白消息的最大宽度
default p_narrator_padding = (0,0,0,0)    # 旁白消息文本到气泡框架的左上右下边距
default p_narrator_textsize = 18              # 旁白消息的字体大小
 
default p_message_width = 480                 # 普通消息的最大宽度
default p_message_padding = (20,10,20,15)     # 普通消息文本到气泡框架的左上右下边距
default p_message_textsize = 20               # 普通消息的字体大小
 
default p_message_xoffset = 0                 # 普通消息距离侧方边界的偏移
 
### 系统变量 #############################################################################
 
default nvl_mode = "phone"                    # 区分正常NVL模式和手机组件的变量
define config.nvl_list_length = 999           # 最大对话记录数(在gui中也存在一条,这里直接覆写)
 
define gui.nvl_thought_width = 0              # 旁白消息的最小宽度（覆写gui，否则上方的最大宽度会受到影响）
define gui.nvl_text_width = 0                 # 普通消息的最小宽度（覆写gui，否则上方的最大宽度会受到影响）
 
 
# 这里的最小宽度是消息气泡的最小宽度，如果文本比最小宽度长则自适应。否则文本比最小宽度短，气泡也会维持最小宽度。
# 上方的最大宽度，是字数到达一定宽度后，文本换行的宽度。一般来说，最小宽度需要一个比最大宽度小的值。
# 由于这里的变量是主要的接口和覆写原生自带的配置参数，因此单独划分
 
#########################################################################################
 
init -1 python:
 
    #可入参的showscreen文本标签
    def show_screen_handler(target):
        if "," in target:
            screen_name, params_str = target.split(",", 1)
            params = {}
            for pair in params_str.split(","):
                if "=" in pair:
                    key, val = pair.split("=", 1)
                    params[key.strip()] = val.strip()
            renpy.show_screen(screen_name, **params)
        else:
            renpy.show_screen(target)
        return True
 
    config.hyperlink_handlers["show"] = show_screen_handler
 
    def showscreen_tag(tag, argument, contents):
        return [
            (renpy.TEXT_TAG, f"a=show:{argument}"),
            *contents,
            (renpy.TEXT_TAG, "/a")
        ]
 
    config.custom_text_tags["showscreen"] = showscreen_tag

    # 旁白消息音效
    def Phone_NarratorSound(event,interact=True,**kwargs):
        if event == "show_done":
            renpy.sound.play(audio.phonenarrator)
 
    # 己方消息音效
    def Phone_SendSound(event,interact=True,**kwargs):
        if event == "show_done":
            renpy.sound.play(audio.phonesend)
     
    # 对方消息音效
    def Phone_ReceiveSound(event,interact=True,**kwargs):
        if event == "show_done":
            renpy.sound.play(audio.phonereceive)
        #global current_speaker 无视，被我优化掉了
        #if not interact:
        #    return
        #if event == "begin":
        #    current_speaker = name
 
# 消息动画效果（左右弹出，1为右，-1为左）
transform message_appear(pDirection):
    alpha 0.0
    xoffset 50 * pDirection
    parallel:
        ease 0.5 alpha 1.0
    parallel:
        easein_back 0.5 xoffset 0
# 头像动画效果（快速放大）
transform message_appear_icon():
    zoom 0.0
    easein_back 0.5 zoom 1.0
# 旁白动画效果（向上弹出）
transform message_narrator():
    alpha 0.0
    yoffset -50
    parallel:
        ease 0.5 alpha 1.0
    parallel:
        easein_back 0.5 yoffset 0

# 顶端标题显示界面
screen qq_totalgroup(title,intro):
    zorder 103
    text title:
        pos title_position
        anchor (0, 0)
        size 25
        color "#000000"
    text intro:
        pos intro_position
        anchor (0, 0) 
        size 18
        color "#000000"
    
 
# 一个用于聊天中缩略图放大功能的界面
screen phone_cg(phonecg):
    zorder 102
    modal True
    frame:
        anchor (0.5,0.5)
        xysize phone_xysize
        pos phone_xy
        background phone_bg
        foreground phone_fg
        imagebutton:
            align (0.5,0.5)
            idle phonecg
            action Hide("phone_cg")
# 手机对话界面主屏幕
screen phone_dialogue(dialogue,items=None):
    zorder 101

    frame:
        anchor (0.5,0.5)
        xysize phone_xysize
        pos phone_xy
        background phone_bg
        foreground phone_fg
        viewport:  # 可滚动区域
            anchor (0.5,0.5)
            xysize p_frame_xysize
            pos p_frame_xy
            draggable True
            mousewheel True
            yinitial 1.0  # 跟踪底部
            vbox:
                xalign 0.5
                xsize p_frame_xysize[0]
                spacing p_frame_spacing
                use phone_nvltext(dialogue)
                # 选项部分
                if items != None:
                    vbox:
                        xalign 1.0
                        xoffset -phone_avatar_xysize[0]//2-p_message_xoffset
                        for i in items:
                            textbutton i.caption:
                                background Frame(phone_s_frame,30,30,30,30) at message_narrator
                                padding p_message_padding
                                xsize p_message_width
                                text_size p_message_textsize
                                text_xalign 0.5
                                action i.action
    """
    frame:
        anchor (0.5,0)
        pos (0.5,0.05)
        xysize top_framesize
        background top_frame
    """
# 手机消息显示组件
screen phone_nvltext(dialogue):
    zorder 101
    # 动态刷新角色数据库
    #$ update_phone_avatars()
    # 初始化 上一条消息发送者
    $ previous_d_who = None    
    # 遍历所有对话
    for id_d,d in enumerate(dialogue):
        if d.who == None:
            frame:
                align (0.5,0.5)
                background Frame(phone_n_frame,30,30,30,30)
                padding p_narrator_padding
                if d.current:
                    at message_narrator
                text d.what:
                    align (0.5,0.5)
                    xsize p_narrator_width
                    size p_narrator_textsize
                    color phone_n_color
                    text_align 0.5
                    italic True
                    slow_cps False
                    id d.what_id
        # 角色消息
        else:
            # 从字典获取头像,头像框，对话框，如果为None或捕获不到，使用默认
            if d.who in phone_avatars and phone_avatars[d.who]["frame"]:
                $ message_frame = phone_avatars[d.who]["frame"]
            elif d.who == mc_nvl.name:
                $ message_frame = phone_s_frame
            else:
                $ message_frame = phone_r_frame
            if d.who in phone_avatars and phone_avatars[d.who]["avatar"]:
                $ message_avatar = phone_avatars[d.who]["avatar"]
            else:
                $ message_avatar = phone_avatar
            if d.who in phone_avatars and phone_avatars[d.who]["avatar_frame"]:
                $ message_avatar_frame = phone_avatars[d.who]["avatar_frame"]
            #else:
            #    $ message_avatar_frame = phone_avatar_frame
            hbox:
                if d.who == mc_nvl.name:
                    box_reverse True
                    xalign 1.0 xoffset -p_message_xoffset
                else:
                    xalign 0.0 xoffset p_message_xoffset
                spacing 10
                fixed:
                    xysize phone_avatar_xysize
                    if d.current:  # 只有当前消息才会应用动画
                        at message_appear_icon()
                    add message_avatar align (0.5,0.5)        # 添加头像
                    add message_avatar_frame align (0.5,0.5)  # 添加头像框
                vbox:
                    #if d.who != mc_nvl.name and previous_d_who != d.who:
                    #取消注释添加缩进：玩家不显示姓名，同时，只在新角色说话时才显示姓名
                    text d.who:
                        size 20
                        color "#808080"
                        if d.who == mc_nvl.name:
                            textalign 1.0
                            xalign 1.0
                            
                    # 消息气泡
                    frame:
                        background Frame(message_frame,30,30,30,30)
                        padding p_message_padding
                        if d.current:                  # 只有当前消息才会应用动画
                            if d.who == mc_nvl.name:
                                at message_appear(1)   # 发送消息从右出现
                            else:
                                at message_appear(-1)  # 接收消息从左出现
                        # 消息文本
                        text d.what:
                            align (0.5,0.5)
                            xsize p_message_width
                            size p_message_textsize
                            slow_cps False
                            if d.who == mc_nvl.name:
                                color phone_s_color
                                text_align 1.0
                            else:
                                color phone_r_color
                            id d.what_id
        # 更新 上一条消息发送者
        $ previous_d_who = d.who