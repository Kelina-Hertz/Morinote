################################################################################
## 通讯录系统（与消息系统深度耦合）
##
## 功能：
##  1. 主界面（screen phone_screen / contacts_screen）类似手机 QQ：
##     显示联系人与群聊的头像、昵称、最后一条消息预览，以及未读红点/数字。
##  2. 点击联系人行即可进入对应聊天（沿用 msgsystem.rpy / message.rpy 的设置）；
##     聊天结束后自动返回通讯录，也可以随时点左上角“返回”退出。
##  3. 好友申请弹窗：脚本里调用
##         call contact_friend_request("联系人key")
##     即可弹出“XXX 请求添加为好友”，带“同意 / 拒绝”按钮；
##     同意后联系人会加入通讯录列表。
##  4. 与消息系统耦合方式：通过 config.all_character_callbacks 挂一个全局回调，
##     不修改 msgsystem.rpy / message.rpy 的任何内容。
##
## 脚本常用接口：
##    call contact_friend_request("key")            # 好友申请弹窗（阻塞，_return 为 True/False）
##    $ contact_add_friend("key", name=..., avatar=..., chat_label=..., kind=..., members=...)
##    $ contact_mark_unread("key", 5)               # 给某联系人增加 N 条未读
##    $ contact_set_unread("key", 120)              # 直接设置未读数量（>99 显示 99+）
##    $ contact_clear_unread("key")
##    $ contact_remove_friend("key")
##    show screen phone_screen                      # 打开通讯录主界面
##
## 未读说明：
##  - 剧情里直接 call 某个聊天（如 call phonemsg_hinata01）时不会自动计入未读，
##    如需表现“离线期间收到了消息”，请先用 contact_mark_unread / contact_set_unread
##    设置未读，再让玩家在通讯录里点开阅读（点开会自动清零）；
##  - 若在通讯录界面开着时播放剧情聊天，该聊天的消息会自动计入未读，
##    剧情播放完后可再用 contact_clear_unread 手动清零。
################################################################################

init python:

    import re

    # ------------------------------------------------------------------
    # 工具函数
    # ------------------------------------------------------------------

    def _contact_speaker_name(who):
        """统一讲话者名字，兼容翻译环境。"""
        try:
            return renpy.translate_string(who)
        except Exception:
            return who

    def contact_badge_text(n):
        """未读数字的显示文本：超过 99 显示 99+。"""
        n = int(n or 0)
        if n > 99:
            return "99+"
        return str(n)

    def contact_key_for_speaker(who):
        """根据讲话者名字找到对应的通讯录 key（先私聊后群聊）。"""
        who = _contact_speaker_name(who)
        for key, entry in contact_registry.items():
            if entry.get("kind") == "contact" and who in entry.get("members", []):
                return key
        for key, entry in contact_registry.items():
            if who in entry.get("members", []):
                return key
        return None

    def contact_session_key():
        """根据当前 NVL 会话里的第一条非玩家消息，推断当前聊天是哪个联系人。"""
        nvl = getattr(renpy.store, "nvl_list", None)
        if not nvl:
            return None
        try:
            player_name = _contact_speaker_name(renpy.store.mc_nvl.name)
        except Exception:
            player_name = None
        for entry in nvl:
            if not entry:
                continue
            who = entry[0]
            if who and who != player_name:
                return contact_key_for_speaker(who)
        return None

    # ------------------------------------------------------------------
    # 与消息系统的耦合：全局角色回调
    # ------------------------------------------------------------------
    # 每次手机消息显示时都会触发这个回调：
    #  - 更新该联系人的“最后一条消息”预览；
    #  - 如果当前正开着通讯录界面、且不是正在阅读的聊天，
    #    则把该联系人的未读数 +1（相当于“新消息送达”）。
    # 消息系统本身的文件完全不用改。

    def _contact_track_callback(event, interact=True, **kwargs):
        if event != "show":
            return
        if not interact:
            return
        if renpy.config.skipping:
            return
        if kwargs.get("type") != "nvl":
            return

        who = kwargs.get("who")
        what = kwargs.get("what")
        if not who or what is None:
            return

        # 优先使用“当前打开的聊天”，否则根据会话内容推断
        key = getattr(renpy.store, "contact_open_key", None)
        if key is None or key not in contact_registry:
            key = contact_session_key()
        if key is None:
            return

        # 更新最后一条消息预览（双方消息都会更新）
        contact_last_msg[key] = (who, what)

        # 只有对方发来的消息才会计入未读
        try:
            is_player = _contact_speaker_name(who) == _contact_speaker_name(renpy.store.mc_nvl.name)
        except Exception:
            is_player = False

        if not is_player:
            screens_open = (renpy.get_screen("phone_screen") or renpy.get_screen("contacts_screen"))
            reading = getattr(renpy.store, "contact_reading_key", None)
            if screens_open and reading != key:
                contact_unread[key] = contact_unread.get(key, 0) + 1

    config.all_character_callbacks.append(_contact_track_callback)

    # ------------------------------------------------------------------
    # 通讯录数据操作
    # ------------------------------------------------------------------

    def contact_add_friend(key, name=None, avatar=None, chat_label=None, members=None, kind="contact"):
        """把联系人加入通讯录（已存在则更新信息；未注册则新建默认条目）。"""
        if key not in contact_registry:
            contact_registry[key] = {
                "name": name or key,
                "avatar": avatar or "phone tx_b",
                "kind": kind,
                "chat_label": chat_label or "contact_empty_chat",
                "members": list(members) if members else [name or key],
            }
        else:
            entry = contact_registry[key]
            if name:
                entry["name"] = name
            if avatar:
                entry["avatar"] = avatar
            if chat_label:
                entry["chat_label"] = chat_label
            if members:
                entry["members"] = list(members)
            if kind:
                entry["kind"] = kind
        if key not in contact_list:
            contact_list.append(key)
        contact_unread.setdefault(key, 0)
        renpy.restart_interaction()

    def contact_remove_friend(key):
        """把联系人从通讯录中移除。"""
        if key in contact_list:
            contact_list.remove(key)
        contact_unread.pop(key, None)
        contact_last_msg.pop(key, None)
        renpy.restart_interaction()

    def contact_mark_unread(key, n=1):
        """给某联系人增加 n 条未读消息。"""
        if key not in contact_registry:
            return
        contact_unread[key] = contact_unread.get(key, 0) + max(0, int(n))
        renpy.restart_interaction()

    def contact_set_unread(key, n):
        """直接设置某联系人的未读消息数（>99 显示 99+）。"""
        if key not in contact_registry:
            return
        contact_unread[key] = max(0, int(n))
        renpy.restart_interaction()

    def contact_clear_unread(key):
        """清零某联系人的未读消息数。"""
        contact_unread[key] = 0
        renpy.restart_interaction()

    def contact_preview_text(key):
        """生成通讯录列表里的最后一条消息预览。"""
        last = contact_last_msg.get(key)
        if not last:
            return ""
        who, what = last
        try:
            what = re.sub(r"\{image=[^{}]*\}", "[图片]", what)
        except Exception:
            pass
        what = what.replace("\r", " ").replace("\n", " ")
        if len(what) > 22:
            what = what[:22] + "…"
        entry = contact_registry.get(key, {})
        try:
            is_player = _contact_speaker_name(who) == _contact_speaker_name(renpy.store.mc_nvl.name)
        except Exception:
            is_player = False
        if is_player:
            return "我：" + what
        if entry.get("kind") == "group":
            return who + "：" + what
        return what

    def contact_open_chat(key):
        """点击通讯录某一行的动作：清未读 -> 隐藏通讯录 -> 播放该聊天 -> 回到通讯录。"""
        entry = contact_registry.get(key)
        if entry is None:
            return
        renpy.store.contact_open_key = key
        renpy.store.contact_reading_key = key
        contact_unread[key] = 0
        renpy.hide_screen("phone_screen")
        renpy.hide_screen("contacts_screen")
        renpy.call(entry.get("chat_label") or "contact_empty_chat")
        renpy.show_screen("phone_screen")
        renpy.store.contact_reading_key = None
        renpy.store.contact_open_key = None

    def contact_close():
        """退出通讯录主界面（隐藏两种可能的入口 screen）。"""
        renpy.hide_screen("phone_screen")
        renpy.hide_screen("contacts_screen")


## 兜底头像：当聊天里出现没有注册头像的角色时使用，避免报错
default phone_avatar = "phone tx_b"

## 通讯录数据：所有联系人与群聊的注册信息
## 结构：key -> {name, avatar, kind, chat_label, members}
##   kind       : "contact" 私聊 / "group" 群聊
##   chat_label : 点击后进入的聊天标签（沿用 message.rpy 中已有的标签）
##   members    : 该聊天里会出现的话者名字（用于把消息归属到对应联系人）
default contact_registry = {
    "duou": {
        "name": "渡鸥",
        "avatar": "phone tx_duou",
        "kind": "contact",
        "chat_label": "phonemsg_duou01",
        "members": ["渡鸥", "落鸢"],
    },
    "xiquan": {
        "name": "汐泉",
        "avatar": "phone tx_xq",
        "kind": "contact",
        "chat_label": "phonemsg_xiquan01",
        "members": ["汐泉", "落鸢"],
    },
    "hinata": {
        "name": "日向hinata",
        "avatar": "phone tx_hinata",
        "kind": "contact",
        "chat_label": "phonemsg_hinata01",
        "members": ["日向hinata", "落鸢"],
    },
    "qun_qingfeng": {
        "name": "青枫动漫社(2000)",
        "avatar": "phone tx_ab",
        "kind": "group",
        "chat_label": "phonelabel_01",
        "members": [
            "Angel Beats", "FAGI", "你能做的，岂止如此", "棉花娃娃教主",
            "筑梦", "汐泉", "Ela", "春日野悠", "春日野穹", "一二里",
            "Wenvil", "落鸢",
        ],
    },
    "qun_zuzhibu": {
        "name": "青枫动漫社组织部",
        "avatar": "phone tx_fgo",
        "kind": "group",
        "chat_label": "phonelabel_02",
        "members": ["FGO", "Gilbert", "FAGI", "部员", "汐泉", "落鸢"],
    },
}

## 通讯录显示顺序（key 列表）
default contact_list = ["duou", "xiquan", "hinata", "qun_qingfeng", "qun_zuzhibu"]

## 各联系人的未读消息数
default contact_unread = {}

## 各联系人的最后一条消息 (who, what)
default contact_last_msg = {}

## 当前正在打开的聊天 key（由 contact_open_chat 维护）
default contact_open_key = None

## 当前正在阅读的聊天 key（用于未读排除）
default contact_reading_key = None


################################################################################
## 通讯录主界面（手机 QQ 风格）
################################################################################

## 手机图标点击后打开的入口（沿用 script_c1a.rpy 中 screen phone 的 action）
screen phone_screen():
    use contacts_screen


screen contacts_screen():
    zorder 100

    frame:
        anchor (0.5, 0.5)
        xysize phone_xysize
        pos phone_xy
        background phone_bg
        foreground phone_fg

        fixed:
            anchor (0.5, 0.5)
            pos p_frame_xy
            xysize p_frame_xysize

            ## 顶部栏
            frame:
                xsize p_frame_xysize[0]
                ysize 80
                background "#FFFFFF"

                fixed:
                    xsize p_frame_xysize[0]
                    ysize 80

                    textbutton "‹ 返回":
                        xpos 6
                        yalign 0.5
                        background None
                        hover_background None
                        text_size 22
                        text_color "#2B6CB0"
                        action Function(contact_close)

                    text "通讯录":
                        xalign 0.5
                        yalign 0.5
                        size 26
                        color "#111111"

                add Solid("#E6E6E6"):
                    xpos 0
                    ypos 79
                    xsize p_frame_xysize[0]
                    ysize 1

            ## 可滚动列表
            viewport:
                ypos 80
                xsize p_frame_xysize[0]
                ysize p_frame_xysize[1] - 80
                xalign 0.5
                draggable True
                mousewheel True

                vbox:
                    for _kind in ("contact", "group"):
                        $ _section_keys = [k for k in contact_list if contact_registry.get(k, {}).get("kind", "contact") == _kind]
                        if _section_keys:
                            text ("好友" if _kind == "contact" else "群聊"):
                                xpos 16
                                yoffset 10
                                size 15
                                color "#8F8F8F"
                            for key in _section_keys:
                                use contact_row(key)

                    if not contact_list:
                        text "通讯录还是空的，去添加好友吧~":
                            xalign 0.5
                            yoffset 20
                            size 18
                            color "#AAAAAA"


## 通讯录里的单行条目
screen contact_row(key):
    $ entry = contact_registry.get(key, {})
    $ unread = contact_unread.get(key, 0)

    button:
        xsize 590
        ysize 86
        background "#FFFFFF"
        hover_background "#EDF2F7"
        action Function(contact_open_chat, key)

        hbox:
            xpos 14
            yalign 0.5
            spacing 14

            ## 头像 + 未读红点
            fixed:
                xysize (58, 58)

                add entry.get("avatar", "phone tx_b"):
                    xysize (58, 58)
                    xalign 0.5
                    yalign 0.5

                if unread > 0:
                    fixed:
                        xysize (30, 30)
                        xalign 1.0
                        yalign 0.0

                        text "●":
                            size 30
                            color "#FF3B30"
                            xalign 0.5
                            yalign 0.5

                        text contact_badge_text(unread):
                            size 11
                            bold True
                            color "#FFFFFF"
                            xalign 0.5
                            yalign 0.5

            ## 昵称 + 最后一条消息预览
            vbox:
                xsize 470
                spacing 8

                text entry.get("name", key):
                    size 22
                    color "#111111"

                text contact_preview_text(key):
                    size 16
                    color "#8F8F8F"


################################################################################
## 好友申请
################################################################################

## 好友申请弹窗（同意/拒绝）
screen contact_friend_request_screen(key):
    modal True
    zorder 150

    $ entry = contact_registry.get(key, {})

    frame:
        align (0.5, 0.5)
        xysize (560, 380)
        background "#FFFFFF"
        padding (40, 34)

        vbox:
            spacing 12

            add entry.get("avatar", "phone tx_b"):
                xysize (92, 92)
                xalign 0.5

            text entry.get("name", key):
                size 26
                color "#111111"
                xalign 0.5

            text "请求添加为好友":
                size 18
                color "#8F8F8F"
                xalign 0.5

            text "你们可能认识，去打个招呼吧~":
                size 15
                color "#BBBBBB"
                xalign 0.5

            null height 16

            hbox:
                xalign 0.5
                spacing 28

                textbutton "拒绝":
                    xysize (190, 58)
                    background "#E7EAEF"
                    hover_background "#D8DCE3"
                    text_size 22
                    text_color "#333333"
                    action Return(False)

                textbutton "同意":
                    xysize (190, 58)
                    background "#12B7F5"
                    hover_background "#0FA5DE"
                    text_size 22
                    text_color "#FFFFFF"
                    action Return(True)


## 脚本触发好友申请的入口：
##   call contact_friend_request("联系人key")
## 同意后联系人会自动加入通讯录列表。
label contact_friend_request(key):
    if key not in contact_registry:
        return

    call screen contact_friend_request_screen(key)

    if _return:
        $ contact_add_friend(key)
        $ renpy.notify("%s 已成为你的好友" % contact_registry[key]["name"])
    else:
        $ renpy.notify("已拒绝 %s 的好友请求" % contact_registry[key]["name"])

    return


## 新加好友还没有聊天内容时使用的兜底聊天
label contact_empty_chat:
    $ _entry = contact_registry.get(contact_open_key, {})
    $ _cname = _entry.get("name", "联系人")

    $ nvl_mode = "phone"
    show screen qq_totalgroup(_cname, "你们已经成为好友了")
    nvl_narrator "你们已经成为好友了，还没有聊天记录，先打个招呼吧~"
    nvl clear
    hide screen qq_totalgroup
    $ nvl_mode = None
    return


################################################################################
## 演示入口（仅供测试，正式脚本里按需使用上面的接口即可）
################################################################################
label contact_system_demo:
    "【通讯录系统演示】先模拟一条“汐泉请求添加为好友”的提示。"
    call contact_friend_request("xiquan")

    "然后给“日向hinata”模拟 120 条未读消息（显示为 99+），再打开通讯录。"
    $ contact_mark_unread("hinata", 120)
    show screen phone_screen

    "现在可以点击任意联系人进入聊天，也可以点左上角“返回”退出通讯录。"
    #hide screen phone_screen

    "演示结束。"
    return
