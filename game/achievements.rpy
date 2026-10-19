## 成就系统
##
## 本文件基于 Ren'Py 原生的 achievement 模块：
##   - achievement.register(name)  注册一个成就，并把它同步给 Steam 等后端
##   - achievement.grant(name)      解锁成就
##   - achievement.has(name)        判断成就是否已经解锁
##   - achievement.clear(name)      清除某个成就
##   - achievement.progress(...)    上报带进度的成就进度
##
## 原生模块本身只保存“成就 ID”和“是否已解锁”这两类信息，因此“成就名、
## 说明、达成条件、备注”需要在游戏侧自行维护。本文件就是通过一个 Python
## 列表统一维护这些资料，再配合原生 achievement 函数完成解锁与查询。


## 待弹出提示的成就 ID 队列。它仅作为当前交互的运行时状态使用。
default achievement_popup_queue = []


init python:

    ## ------------------------------------------------------------------
    ## 1. 成就资料表
    ## ------------------------------------------------------------------
    ## 每一项的字段说明：
    ##   id          成就唯一 ID，也是 achievement.register/grant/has 使用的名字。
    ##               Steam 上同名即可，不必与显示给玩家的标题相同。
    ##   name        显示给玩家的成就名。
    ##   description 显示给玩家的成就说明。
    ##   hint        未达成时向玩家展示的达成条件提示。
    ##   note        开发备注，只在 config.developer 为 True 时显示，供策划/程序使用。
    ##   condition   一个可调用对象（通常是 lambda），返回 True 表示条件已经满足。
    ##               之后调用 check_achievements() 会自动解锁所有满足条件的成就。
    ##               如果某个成就完全由剧情脚本手动触发，condition 可以省略。
    ##
    ## 下面是三个示例成就，请按需替换成实际内容。

    ACHIEVEMENTS = [
        {
            "id": "first_launch",
            "name": "That's how it starts",
            "description": "加入青枫动漫社总群",
            "hint": "？？？",
            "note": "",
            "condition":"",
        },
        {
            "id": "first_launch2",
            "name": "You gotta move~",
            "description": "加入青枫动漫社组织部群聊",
            "hint": "？？？",
            "note": "",
            "condition":"",
        },
        {
            "id": "chapter11_clear",
            "name": "我的一小步",
            "description": "完成第一章第一节的内容",
            "hint": "？？？",
            "note": "",
            "condition":"",
        },
        {
            "id": "duou_msg01",
            "name": "独偶一二里",
            "description": "和渡鸥成为好友并进行第一次聊天",
            "hint": "？？？",
            "note": "",
            "condition":"",
        },
        {
            "id": "xiquan_msg01",
            "name": "天使降临我身边",
            "description": "和汐泉成为好友并进行第一次聊天",
            "hint": "？？？",
            "note": "",
            "condition":"",
        },
        {
            "id": "OVA_nancy01",
            "name": "终将成为你",
            "description": "见证渡鸥与南曦二人的约定",
            "hint": "？？？",
            "note": "",
            "condition":"",
        },
        {
            "id": "total_complete",
            "name": "原来在动漫社真的能邂逅美少女！",
            "description": "完成demo的所有内容",
            "hint": "？？？",
            "note": "青枫动漫社的故事，还远不曾结束……",
            "condition": lambda: all(
                achievement.has(item["id"])
                for item in ACHIEVEMENTS
                if item["id"] != "total_complete"
            ),   
        }
    ]


    ## ------------------------------------------------------------------
    ## 2. 把资料表中的成就注册到 Ren'Py 原生系统
    ## ------------------------------------------------------------------
    ## register 只需在 init 阶段执行一次。steam 参数用于 Steam 后端；如果
    ## 你的 Steam 成就 ID 和本地 ID 相同，直接传 id 即可。
    for _achievement_data in ACHIEVEMENTS:
        achievement.register(_achievement_data["id"], steam=_achievement_data["id"])


    ## ------------------------------------------------------------------
    ## 3. 辅助函数
    ## ------------------------------------------------------------------

    def get_achievement(achievement_id):
        """根据 ID 返回成就资料，不存在时返回 None。"""
        for item in ACHIEVEMENTS:
            if item["id"] == achievement_id:
                return item
        return None


    def _normalize_achievement_popup_queue():
        """把旧存档中的字典队列迁移为 ID 队列，并移除无效项。"""
        normalized = []

        for queued_item in achievement_popup_queue:
            if isinstance(queued_item, dict):
                achievement_id = queued_item.get("id")
            else:
                achievement_id = queued_item

            if get_achievement(achievement_id) is not None and achievement_id not in normalized:
                normalized.append(achievement_id)

        achievement_popup_queue[:] = normalized


    def _clear_achievement_popup():
        """读档时清空运行时队列，避免旧弹窗与当前交互失配。"""
        achievement_popup_queue[:] = []
        renpy.hide_screen("achievement_notification", immediately=True)


    config.after_load_callbacks.append(_clear_achievement_popup)


    def achievement_unlocked_count():
        """已解锁成就数量。"""
        return sum(1 for item in ACHIEVEMENTS if achievement.has(item["id"]))


    def achievement_total_count():
        """成就总数。"""
        return len(ACHIEVEMENTS)


    def _show_next_achievement_popup():
        """从队列中取出一条成就并显示弹窗。"""
        _normalize_achievement_popup_queue()

        if achievement_popup_queue:
            renpy.show_screen(
                "achievement_notification",
                achievement_id=achievement_popup_queue[0],
                from_queue=True,
            )
        else:
            renpy.hide_screen("achievement_notification", immediately=True)

        # Python 调用可能发生在当前交互过程中，需要显式刷新才能立即更新屏幕。
        renpy.restart_interaction()


    def _dismiss_achievement_popup(achievement_id=None):
        """关闭当前弹窗，并显示队列中的下一条。"""
        _normalize_achievement_popup_queue()

        if achievement_popup_queue and (
            achievement_id is None or achievement_popup_queue[0] == achievement_id
        ):
            achievement_popup_queue.pop(0)

        renpy.hide_screen("achievement_notification", immediately=True)
        _show_next_achievement_popup()


    def unlock_achievement(achievement_id):
        """
        解锁指定成就，并在首次解锁时排队显示弹窗。

        如果成就已经解锁，函数不会重复解锁，也不会重复弹窗。
        返回 True 表示本次确实新解锁了一个成就。
        """
        item = get_achievement(achievement_id)
        if item is None:
            renpy.log("Unknown achievement id: %r" % (achievement_id,))
            return False

        if achievement.has(achievement_id):
            return False

        achievement.grant(achievement_id)

        _normalize_achievement_popup_queue()
        achievement_popup_queue.append(achievement_id)

        # 只在弹窗未显示时立即显示；已显示时只需刷新当前交互。
        if len(achievement_popup_queue) == 1 or renpy.get_screen("achievement_notification") is None:
            _show_next_achievement_popup()
        else:
            renpy.restart_interaction()

        return True


    def show_achievement_popup(achievement_id):
        """单独显示一个成就弹窗，不会改变解锁状态或弹窗队列。"""
        if get_achievement(achievement_id) is None:
            return False

        renpy.show_screen(
            "achievement_notification",
            achievement_id=achievement_id,
            from_queue=False,
        )
        renpy.restart_interaction()
        return True


    def check_achievements():
        """
        检查资料表中的所有 condition。

        凡是 condition 返回 True 且尚未解锁的成就，都会被自动解锁并弹窗。
        通常可以在章节结束、数值变化、读档后等时机调用。
        """
        changed = False

        for item in ACHIEVEMENTS:
            condition = item.get("condition")
            if not callable(condition):
                continue

            try:
                met = bool(condition())
            except Exception:
                # 条件函数中使用了尚未初始化的数据时，忽略本次检查。
                met = False

            if met and unlock_achievement(item["id"]):
                changed = True

        return changed


## ----------------------------------------------------------------------
## 4. 达成成就后的弹窗提示
## ----------------------------------------------------------------------
## 当调用 unlock_achievement() 时，会自动显示此屏幕。也可用：
##     show screen achievement_notification(achievement_id="chapter11_clear")
## 单独测试。

transform achievement_popup_appear:
    on show:
        alpha 0.0
        xoffset 40
        easein 0.25 alpha 1.0 xoffset 0
    on hide:
        easeout 0.25 alpha 0.0 xoffset 40


screen achievement_notification(achievement=None, achievement_id=None, from_queue=False):
    zorder 200

    $ achievement_data = achievement
    if achievement_id is not None:
        $ achievement_data = get_achievement(achievement_id)

    if achievement_data is not None:
        frame:
            at achievement_popup_appear
            xalign 1.0
            yalign 1.0
            xsize 350
            ysize 150
            background "#000000dd"
            padding (24, 18)

            vbox:
                spacing 8

                text _("成就达成！") size 20 color "#ffd966"
                text achievement_data["name"] size 26 color "#ffffff"
                text achievement_data["description"] size 16 color "#cccccc"

            if from_queue:
                timer 3.0 action Function(_dismiss_achievement_popup, achievement_data["id"])
            else:
                timer 3.0 action Hide("achievement_notification")
    else:
        timer 0.01 action Hide("achievement_notification")


## ----------------------------------------------------------------------
## 5. 成就浏览界面
## ----------------------------------------------------------------------
## 玩家可在标题菜单或游戏菜单中打开，浏览已达成和未达成的成就。

screen achievements():
    tag menu

    use game_menu(_("成就"), scroll="viewport"):

        vbox:
            spacing 14

            $ unlocked_count = achievement_unlocked_count()
            $ total_count = achievement_total_count()

            text _("已达成 [unlocked_count] / [total_count]") size 24 color "#ffffff"

            for item in ACHIEVEMENTS:
                $ is_unlocked = achievement.has(item["id"])

                frame:
                    xfill True
                    background ("#324133" if is_unlocked else "#202020")
                    padding (20, 16)

                    vbox:
                        spacing 5

                        hbox:
                            spacing 12

                            if is_unlocked:
                                text "✅" size 28 color "#9aff9a"
                            else:
                                text "🔒" size 28 color "#888888"

                            text item["name"] size 27 color ("#ffffff" if is_unlocked else "#999999")

                        if is_unlocked:
                            text item["description"] size 19 color "#dddddd"
                        else:
                            text (_("达成条件：") + item.get("hint", item.get("description", ""))) size 18 color "#999999"

                        if config.developer and item.get("note"):
                            text (item["note"]) size 15 color "#aaaaaa"
