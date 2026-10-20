"""Copy legacy timeline v2 into an independent creator project, preserving provenance."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil

from .compiler import symbol
from .demo import make_project
from .project import atomic_json, safe_path


def image_aliases(game: Path) -> dict:
    """Accept only unambiguous single-image aliases; arbitrary ATL stays unresolved."""
    candidates = {}
    for source in sorted(game.rglob("*.rpy")):
        text = source.read_text(encoding="utf-8-sig")
        blocks = re.finditer(r"(?m)^image\s+([\w ]+?)\s*(?:=\s*([^\n]+)|:\s*\n((?:[ \t]+[^\n]*\n|\s*\n)*))", text)
        for match in blocks:
            name = match[1]
            body = match[2] or match[3] or ""
            strings = re.findall(r'[\"\']([^\"\'\n]+\.(?:png|jpe?g|webp))[\"\']', body, re.I)
            # A single raw image plus static transforms can be safely reused as a raw file.
            if len(strings) != 1 or re.search(r"\b(choice|repeat|parallel|pause|contains|function|ConditionSwitch)\b", body):
                candidates.setdefault(name, []).append(None)
            else:
                candidates.setdefault(name, []).append(strings[0])
    return {name: paths[0] for name, paths in candidates.items() if len(paths) == 1 and paths[0]}


def import_timeline(root: Path, source_draft: Path, source_project: Path) -> dict:
    root, source_draft, source_project = Path(root), Path(source_draft), Path(source_project)
    original = json.loads(source_draft.read_text(encoding="utf-8-sig"))
    if original.get("timeline_version") != 2:
        raise ValueError("迁移需要旧工作台 timeline_version 2 数据")
    if root.exists() and any(root.iterdir()): raise ValueError("迁移目标必须为空目录")
    game = source_project / "game" if (source_project / "game").is_dir() else source_project
    aliases = image_aliases(game)
    document = make_project(original.get("title", "迁移项目"), False)
    document["legacySource"] = copy.deepcopy(original)
    document["sourceRecords"] = [copy.deepcopy(node) for node in original["nodes"] if node.get("kind") in {"note", "direction"}]
    document["migration"] = {"sourceName": source_draft.name, "sha256": hashlib.sha256(source_draft.read_bytes()).hexdigest(), "warnings": []}
    document["assets"] = []
    root.mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir()
    (root / "extensions").mkdir()
    (root / "sources").mkdir()
    shutil.copy2(source_draft, root / "sources" / "legacy-draft.json")
    word = source_draft.parent / "source.docx"
    if word.exists(): shutil.copy2(word, root / "sources" / "source.docx")
    kind_map = {"scene": "background", "portrait": "sprite", "music": "audio", "image": "image"}
    for asset in original.get("assets", []):
        copied = {"id": asset["id"], "kind": kind_map.get(asset["kind"], asset["kind"]), "name": asset.get("name", asset["id"]), "path": "", "status": "missing", "requirement": asset.get("context", asset.get("name", asset["id"])), "legacy": copy.deepcopy(asset)}
        for key in ("character", "costume", "expression"):
            if key in asset: copied[key] = asset[key]
        if asset.get("status") == "placeholder": copied["status"] = "placeholder"
        elif asset.get("status") in {"mapped", "ready"}:
            mapping = asset.get("mapping", asset.get("path", ""))
            raw = aliases.get(mapping, mapping)
            try:
                path = safe_path(game, raw)
                if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".ogg", ".wav", ".mp3", ".flac", ".opus"}:
                    target = "assets/" + symbol(asset["id"]) + path.suffix.lower()
                    shutil.copy2(path, root / target)
                    copied.update(path=target, status="ready")
            except ValueError:
                pass
            if copied["status"] != "ready": document["migration"]["warnings"].append("素材映射需要重新确认：" + asset["id"])
        document["assets"].append(copied)
    def convert(node):
        line = {"id": node["id"], "kind": node["kind"], "speaker": node.get("speaker", ""), "text": node.get("text", ""), "autoWait": node.get("auto_wait"), "advance": node.get("advance", node.get("interact", True)), "visual": copy.deepcopy(node.get("visual")), "audio": {"music": copy.deepcopy(node["audio"])} if node.get("audio") is not None else None, "source": copy.deepcopy(node)}
        if line["kind"] == "chat": line["phone"] = {"title": node.get("chat_title", "消息"), "prefill": not line["advance"]}
        if line["visual"] is not None:
            for sprite in line["visual"].get("sprites", []):
                sprite["anchorX"] = sprite.pop("anchor_x", .5)
                sprite["anchorY"] = sprite.pop("anchor_y", .5)
            cg = line["visual"].pop("cg", "")
            if cg:
                line["visual"]["sprites"] = []
                line["visual"].setdefault("components", []).append({"id": "legacy_cg", "component": "legacy_cg", "params": {"asset": cg}})
                if not any(c["id"] == "legacy_cg" for c in document["components"]):
                    document["components"].append({"id": "legacy_cg", "name": "原稿插图", "version": "1.0.0", "mode": "overlay", "source": "extensions/legacy_cg.rpy", "entry": "creator_legacy_cg", "props": [{"id": "asset", "label": "插图", "type": "asset", "default": cg}], "elements": []})
                    (root / "extensions/legacy_cg.rpy").write_text('screen creator_legacy_cg(params={}, instance="legacy_cg"):\n    add creator_asset(params["asset"]) fit "contain" xysize (1920, 850)\n', encoding="utf-8")
        return line
    visible = {"narration", "dialogue", "chat"}
    raw_nodes = original["nodes"]
    known_options = {n["id"] for n in raw_nodes if n["kind"] == "choice"}
    if any(n.get("branch") and n["branch"] not in known_options for n in raw_nodes):
        raise ValueError("旧稿存在未知分支，不能无损迁移")
    scenes, nodes = [], []
    serial = 0
    def build_sequence(sequence, next_id):
        nonlocal serial
        units = []
        pending = []
        consumed = set()
        for node in sequence:
            if node["id"] in consumed: continue
            if node["kind"] in visible:
                pending.append(node)
            elif node["kind"] == "choice":
                if pending: units.append(("scene", pending)); pending = []
                group = node.get("choice_group") or node["id"]
                options = [n for n in sequence if n["kind"] == "choice" and (n.get("choice_group") or n["id"]) == group]
                consumed.update(n["id"] for n in options)
                units.append(("choice", options))
        if pending: units.append(("scene", pending))
        head = next_id
        for kind, content in reversed(units):
            serial += 1
            uid = "import_" + str(serial)
            if kind == "scene":
                scenes.append({"id": uid, "title": content[0].get("speaker") or "剧情片段", "lines": [convert(n) for n in content]})
                nodes.append({"id": uid, "type": "scene", "title": scenes[-1]["title"], "scene": uid, "next": head})
            else:
                options = []
                for option in content:
                    children = [n for n in raw_nodes if n.get("branch") == option["id"]]
                    target = build_sequence(children, head)
                    options.append({"id": option["id"], "text": option.get("text", ""), "target": target, "source": copy.deepcopy(option)})
                nodes.append({"id": uid, "type": "choice", "title": "选项", "options": options})
            head = uid
        return head
    entry = build_sequence([n for n in raw_nodes if not n.get("branch")], "end")
    nodes.append({"id": "end", "type": "end", "title": "结束"})
    document["graphs"] = [{"id": "main", "title": original.get("title", "导入剧情"), "parent": None, "entry": entry, "nodes": nodes}]
    document["scenes"] = scenes
    if not original.get("is_demo"):
        document["review"] = {"required": True, "confirmedHash": None, "source": "sources/legacy-draft.json"}
    atomic_json(root / "project.json", document)
    return document
