"""Deterministic Ren'Py compiler. Generated files are disposable; extensions are not."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

from .project import load_project, review_digest, safe_path, validate_project

TEMPLATES = Path(__file__).resolve().parent / "templates"


def symbol(value: str) -> str:
    value = str(value)
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    # Avoid distinct Unicode/punctuation IDs colliding after sanitization.
    if cleaned != value or not cleaned or cleaned[0].isdigit():
        cleaned = "id_" + cleaned + "_" + hashlib.sha256(value.encode()).hexdigest()[:8]
    return cleaned


def label(graph: str, node: str) -> str:
    return "cr_" + symbol(graph) + "_" + symbol(node)


def line_label(line: str) -> str:
    return "cr_line_" + symbol(line)


def literal(value) -> str:
    return repr(value)


def renpy_text(text: str) -> str:
    # Keep literal user wording, including bracket/tag-like text, without evaluating it.
    return json.dumps(text.replace("{", "{{").replace("[", "[["), ensure_ascii=False)


def sdk_path() -> Path:
    candidates = [os.environ.get("CREATOR_RENPY_SDK", ""), Path(__file__).resolve().parents[1] / "renpy-sdk", Path(__file__).resolve().parents[1] / "runtime" / "renpy", Path(__file__).resolve().parents[2] / "renpy-8.5.3-sdk"]
    for candidate in candidates:
        if candidate and (Path(candidate) / "renpy.py").exists():
            return Path(candidate).resolve()
    raise ValueError("找不到随附的 Ren’Py 8.5.3 SDK")


class Writer:
    def __init__(self): self.lines, self.map = [], {}
    def add(self, text="", source=None):
        self.lines.append(text)
        if source: self.map[str(len(self.lines))] = source
    def text(self): return "\n".join(self.lines) + "\n"


def generate_project(root: Path, output: Path, entry: dict | None = None, preview: bool = False) -> dict:
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or root.is_relative_to(output):
        raise ValueError("生成目录不能覆盖项目根目录")
    document = load_project(root)
    if document.get('nativeRenpy', {}).get('inPlace') and output.is_relative_to(root / 'game'):
        raise ValueError('试玩／生成目录不能位于原工程 game 内。')
    diagnostics = validate_project(document, root)
    errors = [d for d in diagnostics if d["severity"] == "error" and not (document.get('nativeRenpy', {}).get('inPlace') and d.get('category') == 'asset')]
    if errors: raise ValueError("；".join(d["message"] for d in errors[:12]))
    if document.get("review", {}).get("required") and document["review"].get("confirmedHash") != review_digest(document):
        raise ValueError("导入的正式剧本仍需原工作台正文确认；本制作器不会制造确认记录")
    if document.get('nativeRenpy'):
        from .renpy_import import generate_native
        return generate_native(root, output, document, entry=entry, preview=preview)
    game = output / "game"
    generated = game / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    assets = copy.deepcopy(document["assets"])
    copied_assets = set()
    for asset in assets:
        if asset.get("status") != "ready" or asset["path"].startswith("builtin:"): continue
        source = safe_path(root, asset["path"])
        relative = "assets/" + symbol(asset["id"]) + source.suffix.lower()
        target = game / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_assets.add(target.resolve())
        asset["path"] = relative
    if (game / "assets").exists():
        for stale in (game / "assets").rglob("*"):
            if stale.is_file() and stale.resolve().is_relative_to((game / "assets").resolve()) and stale.resolve() not in copied_assets:
                stale.unlink()
    extensions = root / "extensions"
    target_extensions = game / "extensions"
    target_extensions.mkdir(exist_ok=True)
    keep_extensions = set()
    if extensions.exists():
        for source in sorted(extensions.rglob("*")):
            if not source.is_file() or source.suffix not in {".rpy", ".py", ".json"}: continue
            relative = source.relative_to(extensions)
            source = safe_path(extensions, str(relative))
            target = target_extensions / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            keep_extensions.add(target.resolve())
    # Remove only stale generated copies, never the authored extension sources.
    for stale in target_extensions.rglob("*"):
        if stale.is_file() and stale.resolve() not in keep_extensions:
            stale.unlink()
    font = sdk_path() / "sdk-fonts" / "SourceHanSansLite.ttf"
    if font.exists():
        (game / "fonts").mkdir(exist_ok=True)
        shutil.copy2(font, game / "fonts" / "SourceHanSansLite.ttf")
    for name in ("creator_runtime.rpy", "creator_components.rpy", "creator_screens.rpy"):
        shutil.copy2(TEMPLATES / name, generated / name)
    smoke_target = generated / "creator_smoke.rpy"
    if preview and {"meet", "chat", "garden", "known", "unknown", "ending"}.issubset({s["id"] for s in document["scenes"]}):
        shutil.copy2(TEMPLATES / "creator_smoke.rpy", smoke_target)
    else:
        smoke_target.unlink(missing_ok=True)
        smoke_target.with_suffix(".rpyc").unlink(missing_ok=True)
    graphs = {g["id"]: g for g in document["graphs"]}
    scenes = {s["id"]: s for s in document["scenes"]}
    components = {c["id"]: c for c in document["components"]}
    w = Writer()
    w.add("# Generated by Ren'Py Creator. Edit project.json, not this file.")
    w.add("label start:")
    w.add("    $ creator_reset()")
    if entry and entry.get("state"):
        w.add("    $ creator_apply_test_state(" + literal(entry["state"]) + ")")
    selected_graph = graphs.get((entry or {}).get("graph", document["entryGraph"]))
    if selected_graph is None: raise ValueError("试玩流程不存在")
    selected_node = (entry or {}).get("node", selected_graph["entry"])
    if selected_node not in {n["id"] for n in selected_graph["nodes"]}: raise ValueError("试玩节点不存在")
    target = label(selected_graph["id"], selected_node)
    selected_scene = (entry or {}).get("scene")
    selected_line = (entry or {}).get("line")
    if selected_line and not selected_scene:
        selected_scene = next((s["id"] for s in scenes.values() if any(l["id"] == selected_line for l in s["lines"])), None)
        if not selected_scene: raise ValueError("试玩文字不存在")
    if selected_scene:
        scene = scenes.get(selected_scene)
        if not scene: raise ValueError("试玩场景不存在")
        if selected_line and selected_line not in {l["id"] for l in scene["lines"]}: raise ValueError("试玩文字不属于场景")
        w.add("    $ creator_context = " + literal({"graph": selected_graph["id"], "node": selected_node, "scene": selected_scene}))
        # Restore only preceding authored cues; never execute earlier story effects.
        before = {"visual": None, "audio": None}
        for line in scene["lines"]:
            if line["id"] == selected_line: break
            if not selected_line: break
            for track in before:
                if line.get(track) is not None: before[track] = line[track]
        for track, payload in before.items():
            if payload is not None: w.add("    $ creator_apply_" + track + "(" + literal(payload) + ")")
        target = line_label(selected_line) if selected_line else "cr_scene_" + symbol(selected_scene)
    w.add("    call " + target + " from cr_start_return")
    w.add("    $ creator_cleanup()")
    w.add("    return")
    for graph in document["graphs"]:
        gid = graph["id"]
        for node in graph["nodes"]:
            nid, kind = node["id"], node["type"]
            source = {"graph": gid, "node": nid}
            w.add()
            w.add("label " + label(gid, nid) + ":", source)
            w.add("    $ creator_node_enter(" + literal(gid) + ", " + literal(nid) + ")", source)
            if node.get("actions"): w.add("    $ creator_actions(" + literal(node["actions"]) + ")", source)
            if kind == "scene":
                w.add("    call cr_scene_" + symbol(node["scene"]) + " from " + label(gid, nid) + "_scene_return", source)
            elif kind == "choice":
                w.add("    menu:", source)
                for option in node["options"]:
                    w.add("        " + renpy_text(option["text"]) + ":", {**source, "option": option["id"]})
                    w.add("            $ creator_node_exit(" + literal(gid) + ", " + literal(nid) + ")")
                    w.add("            jump " + label(gid, option["target"]))
                continue
            elif kind == "condition":
                w.add("    $ creator_node_exit(" + literal(gid) + ", " + literal(nid) + ")")
                w.add("    if creator_condition(" + literal(node["condition"]) + "):")
                w.add("        jump " + label(gid, node["yes"]))
                w.add("    else:")
                w.add("        jump " + label(gid, node["no"]))
                continue
            elif kind == "call":
                called = graphs[node["target"]]
                w.add("    call " + label(called["id"], called["entry"]) + " from " + label(gid, nid) + "_return", source)
                w.add("    $ creator_context = " + literal(source))
            elif kind == "component":
                component = components[node["component"]]
                params = {p["id"]: p.get("default") for p in component.get("props", [])}
                params.update(node.get("params", {}))
                instance = gid + ":" + nid
                w.add("    $ creator_component_enter(" + literal(instance) + ", " + literal(component["id"]) + ")")
                if component["mode"] == "blocking":
                    screen = component.get("entry", "creator_investigation")
                    if not re.fullmatch(r"[A-Za-z_]\w*", screen): raise ValueError("组件入口必须是 Screen 名称")
                    w.add("    call screen " + screen + "(params=" + literal(params) + ", instance=" + literal(instance) + ")", source)
                    w.add("    $ creator_component_exit(" + literal(instance) + ", _return)")
                    for result, destination in node.get("resultRoutes", {}).items():
                        w.add("    if _return == " + literal(result) + ":")
                        w.add("        $ creator_node_exit(" + literal(gid) + ", " + literal(nid) + ")")
                        w.add("        jump " + label(gid, destination))
                else:
                    w.add("    $ creator_component_show(" + literal(component["id"]) + ", " + literal(params) + ", " + literal(instance) + ")")
            w.add("    $ creator_node_exit(" + literal(gid) + ", " + literal(nid) + ")")
            if kind == "end":
                w.add("    $ creator_cleanup()")
                w.add("    $ renpy.full_restart()")
            elif kind == "return" or not node.get("next"):
                w.add("    return")
            else: w.add("    jump " + label(gid, node["next"]))
    for scene in document["scenes"]:
        sid = scene["id"]
        w.add()
        w.add("label cr_scene_" + symbol(sid) + ":", {"scene": sid})
        w.add("    $ creator_scene_enter(" + literal(sid) + ")")
        for line in scene["lines"]:
            lid = line["id"]
            source = {"scene": sid, "line": lid, "source": line.get("source")}
            w.add("label " + line_label(lid) + ":", source)
            w.add("    $ creator_line_begin(" + literal(sid) + ", " + literal(lid) + ", " + literal(line.get("autoWait")) + ", " + literal(line.get("text", "")) + ")", source)
            if line.get("visual") is not None: w.add("    $ creator_apply_visual(" + literal(line["visual"]) + ")", source)
            if line.get("audio") is not None: w.add("    $ creator_apply_audio(" + literal(line["audio"]) + ")", source)
            kind, text = line["kind"], line.get("text", "")
            if kind == "chat":
                audible = line.get("advance", True) and not line.get("phone", {}).get("prefill", False)
                w.add("    $ creator_chat_open(" + literal(line.get("phone", {}).get("title")) + ", sound=" + literal(audible) + ")")
                if line.get("advance", True) and not line.get("phone", {}).get("prefill", False):
                    w.add("    creator_chat_character(" + literal(line.get("speaker", "")) + ") " + renpy_text(text), source)
                w.add("    $ creator_chat_append(" + literal(line.get("speaker", "")) + ", " + literal(text) + ")", source)
            else:
                w.add("    $ creator_chat_close()")
                if kind == "stage":
                    if line.get("waitFor"):
                        w.add("    $ creator_wait_begin(" + literal(line["waitFor"]) + ")", source)
                        w.add("    call screen creator_stage_wait", source)
                        w.add("    $ creator_wait_end()", source)
                    else:
                        w.add("    pause " + str(float(line.get("duration", 0))), source)
                else:
                    speaker = "creator_narrator" if kind == "narration" else "creator_character(" + literal(line.get("speaker", "")) + ")"
                    w.add("    " + speaker + " " + renpy_text(text) + (" (interact=False)" if not line.get("advance", True) else ""), source)
            w.add("    $ creator_line_end(" + literal(lid) + ")", source)
        w.add("    $ creator_chat_close()")
        w.add("    return")
    generated_story = generated / "creator_story.rpy"
    names = set()
    for statement in w.lines:
        match = re.match(r"label ([A-Za-z_][A-Za-z0-9_]*):", statement) or re.search(r"\bfrom ([A-Za-z_][A-Za-z0-9_]*)$", statement)
        if match:
            name = match[1]
            if name in names:
                raise ValueError("生成标签重复，请修改冲突的流程或节点 ID：" + name)
            names.add(name)
    generated_story.write_text(w.text(), encoding="utf-8", newline="\n")
    data = "# Generated constants. Runtime state is separate.\n"
    data += "define config.name = " + literal(document["title"]) + "\n"
    data += "define config.version = '1.0'\n"
    data += "define build.name = " + literal(symbol(document["id"])) + "\n"
    data += "define build.directory_name = " + literal(symbol(document["id"]) + "-1.0") + "\n"
    data += "init python:\n"
    for excluded in ("source_map.json", "screenshots/**", "*.log", "saves/**", ".creator/**"):
        data += "    build.classify(" + literal(excluded) + ", None)\n"
    data += "define config.screen_width = " + str(document["resolution"][0]) + "\n"
    data += "define config.screen_height = " + str(document["resolution"][1]) + "\n"
    data += "define config.save_directory = " + literal("creator-" + document["id"] + ("-preview" if preview else "")) + "\n"
    data += "define config.default_text_cps = 40\n"
    data += "define config.developer = " + repr(bool(preview)) + "\n"
    for name, value in [("creator_assets", {a["id"]: a for a in assets}), ("creator_variables", {v["id"]: v for v in document["variables"]}), ("creator_events", document["events"]), ("creator_components", components), ("creator_project_revision", document["revision"]), ("creator_project_id", document["id"])]:
        data += "define " + name + " = " + literal(value) + "\n"
    (generated / "creator_data.rpy").write_text(data, encoding="utf-8", newline="\n")
    source_map = {"schemaVersion": 1, "project": document["id"], "revision": document["revision"], "files": {"game/generated/creator_story.rpy": w.map}}
    (output / "source_map.json").write_text(json.dumps(source_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not preview:
        for file in (game / "creator_bridge.rpy", game / "creator_bridge.rpyc", generated / "creator_bridge.rpy", generated / "creator_bridge.rpyc"):
            file.unlink(missing_ok=True)
    return {"output": str(output), "sourceMap": source_map, "diagnostics": diagnostics}
