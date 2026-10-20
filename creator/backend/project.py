"""Versioned project storage. Never edits source projects while migrating."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import uuid

SCHEMA_VERSION = 1
ENGINE_VERSION = "8.5.3"
_LOCK = threading.RLock()
EDITOR_PROJECT = '.creator/editor/project.json'


def project_file(root: Path) -> Path:
    """Keep native Ren'Py packaging config separate from editor metadata."""
    root = Path(root)
    sidecar = safe_path(root, EDITOR_PROJECT)
    return sidecar if sidecar.is_file() else root / 'project.json'


def review_digest(document: dict) -> str:
    value = {k: v for k, v in document.items() if k not in {"revision", "review"}}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    root = Path(root).resolve()
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ":" in relative:
        raise ValueError("项目路径必须是相对路径")
    result = (root / relative).resolve()
    if not result.is_relative_to(root):
        raise ValueError("路径超出项目目录")
    return result


def atomic_json(path: Path, document: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def load_project(root: Path) -> dict:
    root = Path(root)
    if root.is_file() and root.name == 'project.json':
        root = root.parent
    from .source_transactions import recover
    with _LOCK:
        recover(root)
    path = project_file(root)
    if not path.is_file():
        if (root / 'game').is_dir() or any(root.glob('*.rpy')):
            raise ValueError('这是 Ren’Py 源工程，请使用“导入 / 迁移工程”，复制到新项目后打开。')
        raise ValueError('此文件夹没有制作器 project.json，请选择项目文件夹或使用“导入 / 迁移工程”。')
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(document, dict):
        raise ValueError('project.json 必须是项目对象。')
    if document.get("schemaVersion") != SCHEMA_VERSION:
        if (root / 'game').is_dir():
            raise ValueError('这是 Ren’Py 原工程，project.json 是打包配置；请使用“导入 / 迁移工程”。')
        raise ValueError('不支持的制作器项目版本：' + str(document.get('schemaVersion', '缺少 schemaVersion')) + '；当前支持版本 1。')
    if document.get('nativeRenpy') and document['nativeRenpy'].get('trackVersion',0)<2:
        with _LOCK:
            from .renpy_import import reindex_project
            backup = root / '.creator/migrations/native-tracks-v2'
            backup.mkdir(parents=True, exist_ok=True)
            if not (backup / 'project.json').exists():
                atomic_json(backup / 'project.json', document)
                atomic_json(backup / 'renpy-index.json', json.loads(safe_path(root, document['nativeRenpy']['indexPath']).read_text(encoding='utf-8')))
            document = reindex_project(root, document)
            document['revision'] += 1
            atomic_json(path, document)
    if document.get('nativeRenpy', {}).get('inPlace') and document['nativeRenpy'].get('assetLibraryVersion', 0) < 1:
        with _LOCK:
            from .renpy_import import index_sources, refresh_native_files
            index_path = safe_path(root, document['nativeRenpy']['indexPath'])
            previous = json.loads(index_path.read_text('utf-8')) if index_path.exists() else None
            refresh_native_files(root, document)
            baseline = index_sources(root, document, previous=previous)
            atomic_json(index_path, baseline)
            document['revision'] += 1
            atomic_json(path, document)
    return document


def save_project(root: Path, document: dict, expected_revision: int) -> dict:
    with _LOCK:
        root = Path(root)
        previous = load_project(root)
        if previous["revision"] != expected_revision:
            raise ValueError("项目已变化，请重新加载后再保存")
        if previous["id"] != document.get("id"):
            raise ValueError("不能更换项目 ID")
        if previous.get('nativeRenpy'):
            from .renpy_import import checked_projection
            if document.get('nativeRenpy') != previous['nativeRenpy']:
                raise ValueError('原工程索引不能直接修改，请重新扫描源码。')
            checked_projection(root, document)
        errors = [d for d in validate_project(document, root) if d["severity"] == "error" and d.get("category") != "asset"]
        if errors:
            raise ValueError("；".join(d["message"] for d in errors[:8]))
        result = copy.deepcopy(document)
        result["revision"] = expected_revision + 1
        if result.get('nativeRenpy'):
            from .renpy_import import reindex_project
            # RPY remains the authoring source. A native text save patches its
            # literal and refreshes the disposable visual projection.
            result = reindex_project(root, result)
        atomic_json(project_file(root), result)
        return result


def new_project(root: Path, title: str, demo: bool = False) -> dict:
    from .demo import make_project
    root = Path(root)
    with _LOCK:
        if (root / "project.json").exists():
            raise ValueError("此目录已有项目")
        if root.exists() and any(root.iterdir()):
            raise ValueError("请使用空目录新建项目")
        root.mkdir(parents=True, exist_ok=True)
        (root / "assets").mkdir(exist_ok=True)
        (root / "extensions").mkdir(exist_ok=True)
        document = make_project(title or "未命名作品", demo)
        atomic_json(root / "project.json", document)
        return document


def validate_project(document: dict, root: Path | None = None) -> list[dict]:
    """Collect precise diagnostics; asset errors may be saved but block compilation."""
    diagnostics = []
    def error(message, node=None, category="structure", severity="error"):
        diagnostics.append({"severity": severity, "message": message, "node": node, "category": category})
    if not isinstance(document, dict):
        return [{"severity": "error", "message": "项目必须是对象", "category": "structure"}]
    if document.get("schemaVersion") != SCHEMA_VERSION:
        error("不支持的项目版本")
    if document.get("engineVersion") != ENGINE_VERSION:
        error("项目需要 Ren’Py 8.5.3")
    if not document.get("id") or not isinstance(document.get("title"), str):
        error("项目缺少 ID 或标题")
    def indexed(key):
        value = document.get(key, [])
        if not isinstance(value, list):
            error(f"{key} 必须是列表")
            return {}
        items = {}
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                error(f"{key} 存在无效 ID")
                continue
            if item["id"] in items:
                error(f"{key} 中 ID 重复：{item['id']}", item["id"])
            items[item["id"]] = item
        return items
    graphs, scenes, assets, variables, components = [indexed(k) for k in ("graphs", "scenes", "assets", "variables", "components")]
    events = indexed("events")
    if document.get("entryGraph") not in graphs:
        error("项目入口流程不存在")
    res = document.get("resolution", [])
    if not isinstance(res, list) or len(res) != 2 or any(type(n) is not int or not 320 <= n <= 7680 for n in res):
        error("画面尺寸必须是 320–7680 的两个整数")
    def number(value, label, node, lo=None, hi=None):
        if type(value) not in (float, int) or not math.isfinite(value) or (lo is not None and value < lo) or (hi is not None and value > hi):
            error(f"{label} 数值无效", node)
    def objects(value, label, node):
        if not isinstance(value, list):
            error(label + "必须是列表", node)
            return []
        result = []
        for item in value:
            if not isinstance(item, dict): error(label + "必须包含对象", node)
            else: result.append(item)
        return result
    def value_matches(spec, value):
        kind = spec.get("type")
        return {"boolean": type(value) is bool, "number": type(value) in (int, float) and math.isfinite(value), "string": isinstance(value, str), "enum": value in spec.get("values", []), "set": isinstance(value, list)}.get(kind, False)
    def condition(value, node):
        if not isinstance(value, dict):
            error("条件必须是对象", node)
            return
        if "all" in value or "any" in value:
            children = value.get("all", value.get("any"))
            if not isinstance(children, list) or not children:
                error("组合条件不能为空", node)
            else:
                for child in children: condition(child, node)
        elif value.get("variable") not in variables or value.get("op") not in {"eq", "ne", "gt", "gte", "lt", "lte", "contains"}:
            error("条件引用未知状态或运算符", node)
        else:
            spec, op = variables[value["variable"]], value["op"]
            if op in {"gt", "gte", "lt", "lte"} and (spec.get("type") != "number" or type(value.get("value")) not in (int, float)):
                error("大小比较需要数值状态和数值", node)
            if op == "contains" and spec.get("type") not in {"set", "string"}:
                error("包含条件需要集合或字符串状态", node)
            if op in {"eq", "ne"} and not value_matches(spec, value.get("value")):
                error("条件值与状态类型不匹配", node)
    def actions(value, node):
        if not isinstance(value, list):
            error("动作必须是列表", node)
            return
        for action in value:
            if not isinstance(action, dict) or action.get("type") not in {"set", "add", "emit"}:
                error("未知动作", node)
            elif action["type"] != "emit" and action.get("variable") not in variables:
                error("动作引用未知状态", node)
            elif action["type"] == "emit" and not action.get("event"):
                error("信号名称不能为空", node)
            elif action["type"] == "set" and not value_matches(variables[action["variable"]], action.get("value")):
                error("赋值动作与状态类型不匹配", node)
            elif action["type"] == "add":
                kind = variables[action["variable"]].get("type")
                if kind not in {"number", "set"} or (kind == "number" and type(action.get("value", 1)) not in (int, float)):
                    error("增加动作需要数值或集合状态", node)
    for vid, variable in variables.items():
        kind, initial = variable.get("type"), variable.get("initial")
        if variable.get("scope") not in {"game", "persistent", "component"}:
            error("状态作用域无效", vid)
        valid = {"boolean": type(initial) is bool, "number": type(initial) in (int, float), "string": isinstance(initial, str), "enum": initial in variable.get("values", []), "set": isinstance(initial, list)}
        if not valid.get(kind, False): error("状态初始值与类型不匹配", vid)
        if kind == "number": number(initial, "状态初始值", vid)
    for aid, asset in assets.items():
        if document.get('nativeRenpy', {}).get('inPlace') and asset.get('virtual'):
            if asset.get('virtualStatus') != 'bound':
                error('素材待补：' + (asset.get('requirement') or asset.get('name', aid)), aid, 'asset', 'warning')
            continue
        if asset.get("kind") not in {"background", "sprite", "audio", "image"}:
            error("素材类型无效", aid)
        if asset.get("status") not in {"ready", "missing", "placeholder"}:
            error("素材处理状态无效", aid)
        if asset.get("status") == "missing":
            error("素材待补：" + asset.get("requirement", asset.get("name", aid)), aid, "asset")
        elif asset.get("status") == "placeholder":
            error("使用占位：" + asset.get("requirement", asset.get("name", aid)), aid, "asset", "warning")
        else:
            path = asset.get("path", "")
            if path.startswith("builtin:"):
                if not re.fullmatch(r"builtin:(solid|person):#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", path):
                    error("未知内置素材", aid, "asset")
                if asset.get("kind") == "audio": error("内置图形不能用于音轨", aid, "asset")
            elif root is not None:
                try:
                    file = safe_path(root, path)
                    if not file.is_file(): error("素材文件不存在：" + path, aid, "asset")
                except ValueError as exc: error(str(exc), aid, "asset")
    def asset_ref(aid, kinds, node):
        if not aid or aid not in assets:
            error("素材引用未设置或不存在", node, "asset")
        elif assets[aid].get("kind") not in kinds:
            error("素材类型与用途不匹配：" + aid, node, "asset")
    all_line_ids = set()
    for sid, scene in scenes.items():
        lines = scene.get("lines", [])
        if not isinstance(lines, list):
            error("场景文字必须是列表", sid)
            continue
        for line in lines:
            if not isinstance(line, dict):
                error("文字节点无效", sid)
                continue
            lid = line.get("id")
            if not isinstance(lid, str) or not lid or lid in all_line_ids: error("文字节点 ID 缺失或重复", sid)
            all_line_ids.add(lid)
            if line.get("kind") not in {"narration", "dialogue", "chat", "stage"}: error("文字类型无效", lid)
            if not isinstance(line.get("text", ""), str) or not isinstance(line.get("speaker", ""), str): error("文字和说话人必须是字符串", lid)
            if line.get("autoWait") is not None: number(line["autoWait"], "Auto 等待", lid, 0, 86400)
            if line.get("kind") == "stage": number(line.get("duration", 0), "演出时间", lid, 0, 86400)
            wait_for = line.get("waitFor")
            if wait_for is not None:
                if line.get("kind") != "stage": error("只有纯演出节点可以等待完成事件", lid)
                if not isinstance(wait_for, dict) or wait_for.get("event") not in events:
                    error("演出等待的事件不存在", lid)
                elif wait_for.get("timeout") is not None:
                    number(wait_for["timeout"], "事件等待超时", lid, 0, 86400)
            visual, audio = line.get("visual"), line.get("audio")
            if visual is not None:
                if not isinstance(visual, dict): error("画面设置无效", lid); continue
                if visual.get('background') or not document.get('nativeRenpy') or not visual.get('nativeUnknown'):
                    asset_ref(visual.get("background"), {"background", "image"}, lid)
                if visual.get("transition", "none") not in {"none", "fade", "dissolve"}: error("转场类型无效", lid)
                seen_sprites = set()
                for sprite in objects(visual.get("sprites", []), "立绘", lid):
                    sprite_id = sprite.get("id")
                    if not sprite_id or sprite_id in seen_sprites: error("立绘实例 ID 缺失或重复", lid)
                    seen_sprites.add(sprite_id)
                    asset_ref(sprite.get("asset"), {"sprite", "image"}, lid)
                    for key, default, lo, hi in [("x", 960, -10000, 10000), ("y", 540, -10000, 10000), ("scale", 1, .01, 20), ("anchorX", .5, 0, 1), ("anchorY", .5, 0, 1), ("z", 0, -1000, 1000)]:
                        number(sprite.get(key, default), key, lid, lo, hi)
                    animation = sprite.get("animation")
                    if animation:
                        if animation.get("mode") not in {"parallel", "sequence"}: error("动画组合方式无效", lid)
                        for step in objects(animation.get("steps", []), "动画步骤", lid):
                            if step.get("property") not in {"x", "y", "alpha", "scale"}: error("动画属性无效", lid)
                            number(step.get("value"), "动画值", lid)
                            number(step.get("duration"), "动画时长", lid, 0)
                            number(step.get("delay", 0), "动画延时", lid, 0)
                component_instances = set()
                for instance in objects(visual.get("components", []), "覆盖组件", lid):
                    if instance.get("component") not in components: error("未知覆盖组件", lid)
                    if not instance.get("id") or instance["id"] in component_instances: error("覆盖组件实例 ID 缺失或重复", lid)
                    component_instances.add(instance.get("id"))
            if audio is not None:
                if not isinstance(audio, dict): error("音乐设置无效", lid); continue
                for channel in ([c['id'] for c in document['nativeRenpy'].get('audioChannels', [])] if document.get('nativeRenpy',{}).get('audioChannels') else ("music", "ambience", "sound", "voice")):
                    track = audio.get(channel)
                    if track is None: continue
                    if not isinstance(track, dict): error("音轨设置无效", lid); continue
                    if track.get("asset"): asset_ref(track["asset"], {"audio"}, lid)
                    number(track.get("volume", 1), "音量", lid, 0, 10 if document.get('nativeRenpy') else 1)
                    for fade in ("fadein", "fadeout"): number(track.get(fade, .5), fade, lid, 0, 60)
    for gid, graph in graphs.items():
        parent, visited = graph.get("parent"), {gid}
        while parent:
            if parent in visited: error("章节包含关系形成循环", gid); break
            if parent not in graphs: error("上级章节不存在", gid); break
            visited.add(parent)
            parent = graphs[parent].get("parent")
        nodes = graph.get("nodes", [])
        if not isinstance(nodes, list): error("流程节点必须是列表", gid); continue
        ids = {node.get("id") for node in nodes if isinstance(node, dict)}
        if len(ids) != len(nodes) or None in ids or "" in ids: error("流程节点 ID 缺失或重复", gid)
        if graph.get("entry") not in ids: error("流程入口不存在", gid)
        for node in nodes:
            if not isinstance(node, dict): error("流程节点无效", gid); continue
            nid, kind = node.get("id"), node.get("type")
            refs = [node.get("next")] if node.get("next") else []
            if kind == "scene" and node.get("scene") not in scenes: error("场景不存在", nid)
            elif kind == "choice":
                if not node.get("options"): error("选项不能为空", nid)
                option_ids = set()
                for option in node.get("options", []):
                    if not option.get("id") or option.get("id") in option_ids: error("选项 ID 缺失或重复", nid)
                    option_ids.add(option.get("id"))
                    if not isinstance(option.get("text"), str): error("选项文字无效", nid)
                    refs.append(option.get("target"))
            elif kind == "condition":
                condition(node.get("condition"), nid)
                refs.extend([node.get("yes"), node.get("no")])
            elif kind == "call" and node.get("target") not in graphs: error("调用目标流程不存在", nid)
            elif kind == "component":
                if node.get("component") not in components: error("组件不存在", nid)
                refs.extend(node.get("resultRoutes", {}).values())
            elif kind not in {"scene", "choice", "condition", "call", "return", "end", "action", "component"}: error("未知流程节点类型", nid)
            if "actions" in node: actions(node["actions"], nid)
            for ref in refs:
                if ref not in ids: error("流程跳转目标不存在：" + str(ref), nid)
    for eid, event in events.items():
        if event.get("trigger") not in {"node_enter", "node_exit", "line_begin", "line_end", "component", "signal"}: error("事件触发类型无效", eid)
        if event.get("repeat") not in {"always", "once"}: error("事件重复规则无效", eid)
        if event.get("condition"): condition(event["condition"], eid)
        actions(event.get("actions", []), eid)
    for cid, component in components.items():
        if component.get("mode") not in {"overlay", "blocking"}: error("组件模式无效", cid)
        if not isinstance(component.get("entry"), str) or not re.fullmatch(r"[A-Za-z_]\w*", component.get("entry", "")):
            error("组件入口必须是 Screen 名称", cid)
        if component.get("source") and root is not None:
            try:
                source = safe_path(root, component["source"])
                if not source.is_relative_to((Path(root) / "extensions").resolve()) or source.suffix != ".rpy": error("组件源码必须位于 extensions/*.rpy", cid)
                elif not source.is_file(): error("组件源码不存在", cid)
            except ValueError as exc: error(str(exc), cid)
        prop_ids = set()
        for prop in objects(component.get("props", []), "组件参数", cid):
            if not prop.get("id") or prop["id"] in prop_ids: error("组件参数 ID 缺失或重复", cid)
            prop_ids.add(prop.get("id"))
            if prop.get("type") not in {"number", "string", "boolean", "color", "asset"}: error("组件参数类型无效", cid)
            elif prop["type"] == "number": number(prop.get("default"), "组件默认值", cid, prop.get("min"), prop.get("max"))
            elif prop["type"] == "boolean" and type(prop.get("default")) is not bool: error("组件默认值必须是布尔值", cid)
            elif prop["type"] in {"string", "asset", "color"} and not isinstance(prop.get("default"), str): error("组件默认值必须是文字", cid)
            if prop.get("type") == "asset" and prop.get("default"): asset_ref(prop["default"], {"background", "sprite", "image", "audio"}, cid)
        for element in objects(component.get("elements", []), "组件元素", cid):
            for key in ("xProp", "yProp", "scaleProp"):
                if element.get(key) and element[key] not in prop_ids: error("组件元素引用未知参数", cid)
    return diagnostics
