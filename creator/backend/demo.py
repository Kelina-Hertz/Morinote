"""Original, redistributable demo content made only from engine primitives."""
from __future__ import annotations
import uuid


def component_catalog():
    return [
        {"id": "phone", "name": "手机聊天", "version": "1.0.0", "mode": "overlay", "entry": "creator_phone_overlay", "previewEntry": "creator_phone_overlay",
         "props": [{"id": "title", "label": "标题", "type": "string", "default": "消息"}, {"id": "x", "label": "横坐标", "type": "number", "default": 1370}, {"id": "y", "label": "纵坐标", "type": "number", "default": 100}, {"id": "width", "label": "宽度", "type": "number", "default": 480, "min": 200, "max": 1800}, {"id": "height", "label": "高度", "type": "number", "default": 730, "min": 200, "max": 1000}, {"id": "bubbleColor", "label": "气泡颜色", "type": "color", "default": "#244a69"}, {"id": "fontSize", "label": "文字大小", "type": "number", "default": 28, "min": 12, "max": 60}, {"id": "sound", "label": "提示音", "type": "asset", "default": ""}],
         "elements": [{"id": "body", "label": "手机", "xProp": "x", "yProp": "y"}], "state": [], "events": ["message", "closed"], "actions": ["append", "clear", "close"], "results": []},
        {"id": "investigation", "name": "调查线索", "version": "1.0.0", "mode": "blocking", "entry": "creator_investigation", "previewEntry": "creator_investigation",
         "props": [{"id": "title", "label": "标题", "type": "string", "default": "调查桌面"}, {"id": "clue", "label": "线索", "type": "string", "default": "邀请函"}, {"id": "x", "label": "横坐标", "type": "number", "default": 620}, {"id": "y", "label": "纵坐标", "type": "number", "default": 280}, {"id": "width", "label": "宽度", "type": "number", "default": 680, "min": 200}, {"id": "height", "label": "高度", "type": "number", "default": 400, "min": 200}],
         "elements": [{"id": "panel", "label": "调查面板", "xProp": "x", "yProp": "y"}], "state": [], "events": ["found", "leave"], "actions": [], "results": ["found", "leave"]},
    ]


def make_project(title: str, demo: bool = False) -> dict:
    assets = [{"id": "room", "kind": "background", "name": "深蓝舞台", "path": "builtin:solid:#182535", "status": "ready"}]
    def visual(background="room", people=False):
        return {"background": background, "transition": "dissolve", "sprites": ([{"id": "a", "asset": "a", "x": 540, "y": 700, "scale": 1, "flip": False, "z": 0, "anchorX": .5, "anchorY": .5}, {"id": "b", "asset": "b", "x": 1350, "y": 700, "scale": 1, "flip": True, "z": 1, "anchorX": .5, "anchorY": .5}] if people else [])}
    def line(id, text, kind="narration", speaker="", **kwargs):
        return {"id": id, "kind": kind, "text": text, "speaker": speaker, "autoWait": None, "visual": None, "audio": None, **kwargs}
    document = {"schemaVersion": 1, "engineVersion": "8.5.3", "id": "project_" + uuid.uuid4().hex[:12], "revision": 1, "title": title, "resolution": [1920, 1080], "entryGraph": "main", "graphs": [], "scenes": [], "assets": assets, "variables": [], "events": [], "components": component_catalog()}
    if not demo:
        document["graphs"] = [{"id": "main", "title": "故事", "parent": None, "entry": "opening", "nodes": [{"id": "opening", "type": "scene", "title": "开场", "scene": "opening", "next": "end"}, {"id": "end", "title": "结束", "type": "end"}]}]
        document["scenes"] = [{"id": "opening", "title": "开场", "lines": [line("first_line", "从这里写下你的故事。", visual=visual())]}]
        return document
    assets.extend([{"id": "garden", "kind": "background", "name": "暮色舞台", "path": "builtin:solid:#354139", "status": "ready"}, {"id": "a", "kind": "sprite", "name": "蓝色角色", "character": "青", "costume": "几何演示", "expression": "默认", "path": "builtin:person:#73bad0", "status": "ready"}, {"id": "b", "kind": "sprite", "name": "橙色角色", "character": "橙", "costume": "几何演示", "expression": "默认", "path": "builtin:person:#f6be8a", "status": "ready"}])
    document["variables"] = [{"id": "clue", "name": "找到邀请函", "type": "boolean", "initial": False, "scope": "game"}, {"id": "trust", "name": "信任", "type": "number", "initial": 0, "scope": "game"}, {"id": "visited", "name": "已拜访", "type": "set", "initial": [], "scope": "game"}]
    document["events"] = [{"id": "first_arrival", "trigger": "node_enter", "target": "meet", "actions": [{"type": "add", "variable": "visited", "value": "社团"}], "repeat": "once"}]
    document["graphs"] = [
        {"id": "main", "title": "总流程", "parent": None, "entry": "chapter1", "nodes": [{"id": "chapter1", "type": "call", "title": "第一章 · 邀请", "target": "chapter1", "next": "chapter2"}, {"id": "chapter2", "type": "call", "title": "第二章 · 答复", "target": "chapter2", "next": "end"}, {"id": "end", "type": "end", "title": "结束"}]},
        {"id": "chapter1", "title": "第一章 · 邀请", "parent": "main", "entry": "meet", "nodes": [{"id": "meet", "type": "scene", "title": "相遇", "scene": "meet", "next": "route"}, {"id": "route", "type": "choice", "title": "去哪里", "options": [{"id": "desk", "text": "留在教室调查", "target": "investigate"}, {"id": "outside", "text": "去庭院聊一聊", "target": "garden"}]}, {"id": "investigate", "type": "component", "title": "调查桌面", "component": "investigation", "params": {"clue": "社团邀请函"}, "resultRoutes": {"found": "found", "leave": "messages"}, "next": "messages"}, {"id": "found", "type": "action", "title": "记录线索", "actions": [{"type": "set", "variable": "clue", "value": True}], "next": "messages"}, {"id": "garden", "type": "scene", "title": "庭院", "scene": "garden", "next": "trust"}, {"id": "trust", "type": "action", "title": "记录对话", "actions": [{"type": "add", "variable": "trust", "value": 1}], "next": "messages"}, {"id": "messages", "type": "call", "title": "手机消息", "target": "chat", "next": "return"}, {"id": "return", "type": "return", "title": "章节结束"}]},
        {"id": "chat", "title": "手机插曲", "parent": "chapter1", "entry": "chat", "nodes": [{"id": "chat", "type": "scene", "title": "聊天", "scene": "chat", "next": "return"}, {"id": "return", "type": "return", "title": "返回"}]},
        {"id": "chapter2", "title": "第二章 · 答复", "parent": "main", "entry": "check", "nodes": [{"id": "check", "type": "condition", "title": "找到邀请函？", "condition": {"variable": "clue", "op": "eq", "value": True}, "yes": "known", "no": "unknown"}, {"id": "known", "type": "scene", "title": "知晓邀请", "scene": "known", "next": "ending"}, {"id": "unknown", "type": "scene", "title": "新的发现", "scene": "unknown", "next": "ending"}, {"id": "ending", "type": "scene", "title": "汇合", "scene": "ending", "next": "return"}, {"id": "return", "type": "return", "title": "返回总流程"}]},
    ]
    motion = visual(people=True)
    motion["sprites"][0]["animation"] = {"mode": "parallel", "steps": [{"property": "x", "value": 650, "duration": .8}, {"property": "alpha", "value": 1, "duration": .5}]}
    document["scenes"] = [
        {"id": "meet", "title": "相遇", "lines": [line("meet_1", "放学后的教室里，还亮着一盏灯。", visual=visual()), line("meet_2", "你来得正好。要一起看看社团的准备吗？", "dialogue", "青", visual=motion), line("meet_3", "桌上似乎放着什么。", "dialogue", "橙")]},
        {"id": "garden", "title": "庭院", "lines": [line("garden_1", "我们走到庭院，晚风轻轻吹过。", visual=visual("garden", True)), line("garden_2", "谢谢你愿意陪我。", "dialogue", "青")]},
        {"id": "chat", "title": "手机插曲", "lines": [line("chat_history", "社团群已建立。", "chat", "系统", advance=False, phone={"title": "准备小组", "prefill": True}), line("chat_1", "大家到齐了吗？", "chat", "青", phone={"title": "准备小组"}), line("chat_2", "准备好了，明天见！", "chat", "橙", autoWait=1.5), line("after_chat", "收起手机后，眼前的风景依旧。", "narration")]},
        {"id": "known", "title": "知晓邀请", "lines": [line("known_1", "原来邀请函上的日期就是今天。", visual=visual(people=True))]},
        {"id": "unknown", "title": "新的发现", "lines": [line("unknown_1", "青递来一张邀请函，原来今天还有一场活动。", visual=visual(people=True))]},
        {"id": "ending", "title": "汇合", "lines": [line("ending_1", "无论走过哪条路，我们终于在这里会合。", visual=visual("garden", True)), line("ending_2", "这个小小的故事，才刚刚开始。", "dialogue", "青")]},
    ]
    return document
