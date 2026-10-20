# Development-only bridge. The exporter never copies this file.
default creator_edit_mode = False

init 100 python:
    import os as _cr_os
    import sys as _cr_sys
    import types as _cr_types
    import json as _cr_json
    import copy as _cr_copy

    if "_creator_preview_transport" not in _cr_sys.modules:
        _cr_transport = _cr_types.ModuleType("_creator_preview_transport")
        _cr_sys.modules[_cr_transport.__name__] = _cr_transport
        _cr_transport.started = False
        _cr_transport.last = 0
        _cr_transport.revision = int(_cr_os.environ.get("CREATOR_PREVIEW_REVISION", "0"))
        _cr_transport.restart = False
        _cr_transport.autostart = bool(_cr_os.environ.get("CREATOR_PREVIEW_SESSION"))
        _cr_transport.active = False
        _cr_transport.mode = _cr_os.environ.get("CREATOR_PREVIEW_MODE", "play")
    _cr_transport = _cr_sys.modules["_creator_preview_transport"]

    def creator_bridge_emit(kind, payload=None):
        client = _cr_sys.modules["_creator_preview_transport"]
        if getattr(client, "queue", None) is not None:
            try:
                clean = _cr_json.loads(_cr_json.dumps(payload or {}, default=str))
                client.queue.put_nowait({"sessionId": client.session, "type": kind, "payload": clean})
            except Exception:
                pass

    def creator_notify(kind, payload=None):
        if kind == "line":
            _cr_sys.modules["_creator_preview_transport"].active = True
        creator_bridge_emit(kind, payload)
        if kind in ("line", "state", "node", "component"):
            try:
                creator_bridge_emit("snapshot", creator_snapshot())
            except Exception:
                pass

    def creator_bridge_command(command):
        try:
            creator_bridge_apply_command(command)
        except (renpy.game.FullRestartException, renpy.game.UtterRestartException,
                renpy.game.QuitException, renpy.game.JumpException,
                renpy.game.JumpOutException, renpy.game.CallException, renpy.game.EndReplay):
            raise
        except Exception as error:
            creator_bridge_emit("error", {"message": str(error), "command": command.get("type")})

    def creator_bridge_apply_command(command):
        client = _cr_sys.modules["_creator_preview_transport"]
        if command.get("revision", 0) < client.revision:
            return
        client.revision = command.get("revision", client.revision)
        kind = command.get("type")
        if kind == "update":
            if "visual" in command and command["visual"] is not None:
                store.creator_preview_animate = bool(command.get("replayAnimations"))
                try:
                    creator_apply_visual(command["visual"])
                finally:
                    store.creator_preview_animate = False
            if "audio" in command and command["audio"] is not None:
                creator_apply_audio(command["audio"])
            if command.get("selection"):
                client.selection = command["selection"]
        elif kind == "mode":
            client.mode = command["mode"]
            store.creator_edit_mode = command["mode"] == "edit"
            if creator_bridge_visual():
                creator_apply_visual(creator_bridge_visual())
        elif kind == "reload":
            client.restart = True
            client.active = False
            store.creator_edit_mode = False
            renpy.hide_screen("creator_editor_overlay")
            renpy.reload_script()
            return
        elif kind == "screenshot":
            target = _cr_os.path.join(config.basedir, "screenshots")
            _cr_os.makedirs(target, exist_ok=True)
            renpy.screenshot(_cr_os.path.join(target, "editor-preview.png"))
            creator_bridge_emit("screenshot", {"path": "screenshots/editor-preview.png"})
        if store.creator_edit_mode and client.active:
            renpy.show_screen("creator_editor_overlay")
        else:
            renpy.hide_screen("creator_editor_overlay")
        renpy.restart_interaction()

    def creator_bridge_worker():
        import urllib.request
        import urllib.error
        import queue
        import time
        import sys
        client = sys.modules["_creator_preview_transport"]
        def request(path, data=None):
            payload = _cr_json.dumps(data).encode("utf-8") if data is not None else None
            req = urllib.request.Request(client.url + path, data=payload,
                headers={"Authorization": "Bearer " + client.token, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=2) as response:
                return _cr_json.loads(response.read())
        pending = None
        while True:
            try:
                for _ in range(30):
                    if pending is None:
                        try:
                            pending = client.queue.get_nowait()
                        except queue.Empty:
                            break
                    request("/bridge/event", pending)
                    pending = None
                result = request("/bridge/poll?session=" + client.session + "&after=" + str(client.last))
                for command in result["commands"]:
                    client.last = command["id"]
                    renpy.invoke_in_main_thread(client.handler, command)
                time.sleep(.04)
            except urllib.error.HTTPError as error:
                if error.code in (400, 409):
                    pending = None
                if error.code in (401, 404, 410):
                    return
                time.sleep(.4)
            except Exception:
                time.sleep(.4)

    def creator_bridge_start():
        import queue
        import threading
        client = _cr_sys.modules["_creator_preview_transport"]
        client.handler = creator_bridge_command
        store.creator_edit_mode = client.mode == "edit"
        if client.started:
            return
        client.url = _cr_os.environ.get("CREATOR_BRIDGE_URL", "")
        client.token = _cr_os.environ.get("CREATOR_BRIDGE_TOKEN", "")
        client.session = _cr_os.environ.get("CREATOR_PREVIEW_SESSION", "")
        if not client.url.startswith("http://127.0.0.1:") or not client.token or not client.session:
            return
        client.queue = queue.Queue()
        client.selection = {}
        client.started = True
        threading.Thread(target=creator_bridge_worker, daemon=True, name="creator-preview").start()
        creator_bridge_emit("ready", {"mode": "edit" if store.creator_edit_mode else "play"})

    def creator_bridge_overlay():
        # Ren'Py also runs interactions during its GL performance test. Starting
        # a modal editor screen there prevents the engine from reaching the game.
        client = _cr_sys.modules["_creator_preview_transport"]
        if client.started and client.active and store.creator_edit_mode and not main_menu:
            renpy.show_screen("creator_editor_overlay")
        else:
            renpy.hide_screen("creator_editor_overlay")

    def creator_bridge_after_load():
        client = _cr_sys.modules["_creator_preview_transport"]
        client.handler = creator_bridge_command
        if client.restart:
            client.restart = False
            client.autostart = True
            renpy.full_restart()

    def creator_bridge_visual():
        return getattr(store, "creator_current_visual", getattr(store, "creator_visual", {})) or {}

    def creator_bridge_boxes():
        visual = creator_bridge_visual()
        boxes = []
        for sprite in visual.get("sprites", []):
            width, height = 380, 650
            try:
                item = creator_asset_image(sprite.get("asset", ""))
                if isinstance(item, str):
                    width, height = renpy.image_size(item)
                elif creator_assets.get(sprite.get("asset"), {}).get("status") == "placeholder":
                    width, height = 430, 560
            except Exception:
                pass
            width = max(30, int(width * sprite.get("scale", 1)))
            height = max(30, int(height * sprite.get("scale", 1)))
            boxes.append(dict(id=sprite["id"], kind="sprite", x=int(sprite.get("x", 960) - width * sprite.get("anchorX", .5)),
                y=int(sprite.get("y", 540) - height * sprite.get("anchorY", .5)), w=width, h=height,
                anchorX=sprite.get("anchorX", .5), anchorY=sprite.get("anchorY", .5)))
        for instance in visual.get("components", []):
            spec = creator_components.get(instance.get("component"), {})
            params = {p["id"]: p.get("default") for p in spec.get("props", [])}
            params.update(instance.get("params", {}))
            for element in spec.get("elements", []):
                if not element.get("xProp") or not element.get("yProp"):
                    continue
                boxes.append(dict(id="component:" + instance["id"] + ":" + element["id"], kind="component",
                    instance=instance["id"], element=element["id"], xProp=element["xProp"], yProp=element["yProp"],
                    x=int(params.get(element["xProp"], 0)), y=int(params.get(element["yProp"], 0)),
                    w=max(24, int(params.get(element.get("widthProp", "width"), element.get("width", 200)))),
                    h=max(24, int(params.get(element.get("heightProp", "height"), element.get("height", 100)))),
                    anchorX=0, anchorY=0))
        return boxes

    def creator_bridge_dragged(drags, drop):
        visual = _cr_copy.deepcopy(creator_bridge_visual())
        boxes = {b["id"]: b for b in creator_bridge_boxes()}
        client = _cr_sys.modules["_creator_preview_transport"]
        for drag in drags:
            box = boxes.get(drag.drag_name)
            if not box:
                continue
            x = round(drag.x + box["w"] * box["anchorX"], 2)
            y = round(drag.y + box["h"] * box["anchorY"], 2)
            payload = dict(client.selection, x=x, y=y, revision=client.revision)
            if box["kind"] == "sprite":
                for sprite in visual.get("sprites", []):
                    if sprite["id"] == drag.drag_name:
                        sprite.update(x=x, y=y)
                payload["spriteId"] = drag.drag_name
            else:
                for instance in visual.get("components", []):
                    if instance["id"] == box["instance"]:
                        instance.setdefault("params", {}).update({box["xProp"]: x, box["yProp"]: y})
                payload.update(componentId=box["instance"], elementId=box["element"])
            creator_bridge_emit("edit", payload)
        creator_apply_visual(visual)
        renpy.restart_interaction()
        return None

    if creator_bridge_overlay not in config.interact_callbacks:
        config.interact_callbacks.append(creator_bridge_overlay)
    if creator_bridge_after_load not in config.after_load_callbacks:
        config.after_load_callbacks.append(creator_bridge_after_load)

label before_main_menu:
    if getattr(_cr_transport, "autostart", False):
        $ _cr_transport.autostart = False
        $ _cr_transport.active = False
        $ creator_bridge_start()
        $ Start("start")()
    return

screen creator_editor_overlay():
    zorder 2000
    modal True
    key "dismiss" action NullAction()
    key "rollback" action NullAction()
    key "game_menu" action NullAction()
    draggroup:
        for box in creator_bridge_boxes():
            drag:
                id box["id"]
                drag_name box["id"]
                xpos box["x"]
                ypos box["y"]
                draggable True
                droppable False
                dragged creator_bridge_dragged
                frame:
                    xysize (box["w"], box["h"])
                    padding (8, 8)
                    background Solid("#53d6c51a")
                    text box["id"] size 18 color "#b6fff1" outlines [(1, "#102525", 0, 0)]
    frame:
        xalign .5
        ypos 12
        padding (18, 10)
        background Solid("#10242bea")
        text "编辑预览　拖动人物调整位置　在制作器中切换试玩" size 20 color "#b6fff1"
