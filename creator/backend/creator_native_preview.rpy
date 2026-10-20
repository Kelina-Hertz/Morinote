# Development-only native observation/edit bridge. Original game statements execute normally.
default _cn_edit_mode = False
default _cn_source_objects = {}
default _cn_fragment_active = False
default _cn_fragment_done = False
default _cn_fragment_target = ""
default _cn_fragment_context = 0
default _cn_fragment_labels = []

init 999 python:
    import os as _cn_os
    import sys as _cn_sys
    import types as _cn_types
    import json as _cn_json
    import copy as _cn_copy
    if "_creator_native_client" not in _cn_sys.modules:
        _cn_client = _cn_types.ModuleType("_creator_native_client")
        _cn_client.started = False
        _cn_client.last = 0
        _cn_client.revision = int(_cn_os.environ.get("CREATOR_PREVIEW_REVISION", "0"))
        _cn_client.mode = _cn_os.environ.get("CREATOR_PREVIEW_MODE", "play")
        _cn_client.pending = _cn_json.loads(_cn_os.environ.get("CREATOR_NATIVE_TEST", "{}"))
        _cn_client.source = None
        _cn_client.label = None
        _cn_client.bases = {}
        _cn_client.originals = {}
        _cn_client.overrides = {}
        _cn_client.objects = {}
        _cn_client.variable_bases = {}
        _cn_sys.modules[_cn_client.__name__] = _cn_client
    _cn_client = _cn_sys.modules["_creator_native_client"]
    _cn_index_path = _cn_os.environ.get("CREATOR_NATIVE_INDEX", _cn_os.path.join(config.basedir, ".creator-native-index.json"))
    if _cn_os.path.isfile(_cn_index_path):
        with open(_cn_index_path, encoding="utf-8") as _cn_stream:
            _cn_client.index = _cn_json.load(_cn_stream)
    else:
        _cn_client.index = {"commands":{}, "variables":[]}

    def _cn_emit(kind, payload=None):
        client = _cn_sys.modules["_creator_native_client"]
        if getattr(client, "queue", None) is not None:
            client.queue.put({"sessionId": client.session, "type": kind, "payload": _cn_json.loads(_cn_json.dumps(payload or {}, default=str))})

    def _cn_worker():
        import urllib.request
        import time
        import queue
        client = _cn_sys.modules["_creator_native_client"]
        def request(path, item=None):
            data = _cn_json.dumps(item).encode("utf-8") if item is not None else None
            req = urllib.request.Request(client.url + path, data=data, headers={"Authorization":"Bearer " + client.token, "Content-Type":"application/json"})
            with urllib.request.urlopen(req, timeout=3) as response:
                return _cn_json.loads(response.read())
        pending = None
        while True:
            try:
                for unused in range(30):
                    if pending is None:
                        try: pending = client.queue.get_nowait()
                        except queue.Empty: break
                    request("/bridge/event", pending)
                    pending = None
                result = request("/bridge/poll?session=" + client.session + "&after=" + str(client.last))
                for command in result["commands"]:
                    client.last = command["id"]
                    renpy.invoke_in_main_thread(client.handler, command)
                time.sleep(.04)
            except Exception:
                time.sleep(.3)

    def _cn_start():
        import queue
        import threading
        client = _cn_sys.modules["_creator_native_client"]
        client.handler = _cn_command
        if client.started: return
        client.url = _cn_os.environ.get("CREATOR_BRIDGE_URL", "")
        client.token = _cn_os.environ.get("CREATOR_BRIDGE_TOKEN", "")
        client.session = _cn_os.environ.get("CREATOR_PREVIEW_SESSION", "")
        if not client.url.startswith("http://127.0.0.1:") or not client.token or not client.session: return
        client.queue = queue.Queue()
        client.started = True
        threading.Thread(target=_cn_worker, daemon=True, name="creator-native-preview").start()
        _cn_emit("ready", {"mode":client.mode, "native":True})

    def _cn_fragment_should_stop(label, target, stack, context, expected_context, allowed_labels):
        # A nested call (including phone conversations) owns an extra return
        # frame. Local labels belong to their enclosing scene. Guard only the
        # selected scene's frame, before the next label binds its parameters.
        return (context == expected_context and bool(stack) and stack[-1] == "_cn_fragment_return"
            and label not in allowed_labels and label != target and not label.startswith(target + ".") and not label.startswith("_cn_"))

    def _cn_finish_fragment(next_label=None):
        store._cn_fragment_active = False
        store._cn_fragment_done = True
        store._cn_edit_mode = False
        _cn_client.mode = "play"
        renpy.hide_screen("_cn_editor_overlay")
        for channel in _cn_client.index.get("audioChannels",["music","sound","voice"]):
            if renpy.music.channel_defined(channel): renpy.music.stop(channel=channel,fadeout=.3)
        _cn_emit("snapshot",{"fragmentDone":True,"scope":"fragment","nextLabel":next_label})
        _cn_emit("fragment_finished",{"label":store._cn_fragment_target,"nextLabel":next_label})

    def _cn_replay_fragment():
        _cn_client.pending = _cn_copy.deepcopy(_cn_client.test_entry)
        renpy.full_restart(transition=None,label="_cn_restart_entry")

    def _cn_label(name, abnormal):
        client = _cn_sys.modules["_creator_native_client"]
        _cn_start()
        if name and not name.startswith("_"):
            client.label = name
        if name == "start":
            client.bases = {}; client.overrides = {}; client.objects = {}
            client.originals = {}
            client.mode = _cn_os.environ.get("CREATOR_PREVIEW_MODE", "play")
            client.volume_bases = {}; client.dirty = False
            for obj,attr,value in client.variable_bases.values():
                if attr == "chan_volume": obj.set_volume(value)
                else: setattr(obj,attr,value)
            client.variable_bases = {}
        if name == "start" and client.pending:
            entry = client.pending
            client.pending = None
            for key, value in entry.get("state", {}).items():
                if key.startswith("persistent."):
                    setattr(persistent, key.split(".",1)[1], value)
                else: setattr(store, key, value)
            client.test_entry = entry
            client.mode = "play"  # initialization calls must complete before editing.
            renpy.jump("_cn_test_entry")

    def _cn_statement(name):
        client = _cn_sys.modules["_creator_native_client"]
        if name == "label" and getattr(store,"_cn_fragment_active",False):
            node = renpy.game.script.namemap.get(renpy.game.context().current)
            label = getattr(node,"name",None)
            if isinstance(label,str) and _cn_fragment_should_stop(label,store._cn_fragment_target,
                    renpy.get_return_stack(),renpy.context_nesting_level(),store._cn_fragment_context,store._cn_fragment_labels):
                _cn_finish_fragment(label)
                renpy.set_return_stack([])
                renpy.jump("_cn_fragment_complete")
        filename, line = renpy.get_filename_line()
        filename = filename.replace("\\", "/")
        if not filename.startswith("game/") or "creator_native_preview" in filename or "creator_motion_clip" in filename: return
        client.source = {"path":filename, "line":line}
        client.objects = _cn_copy.deepcopy(store._cn_source_objects)
        binding = client.index.get("commands", {}).get(filename + ":" + str(line))
        if binding:
            if binding.get("clear"): client.objects = {}; client.bases = {}; client.overrides = {}
            for item in binding.get("objects", []): client.objects[item["id"]] = item
        if name == "hide":
            for tag in list(client.objects):
                if not renpy.showing(tag): client.objects.pop(tag, None)
        store._cn_source_objects = _cn_copy.deepcopy(client.objects)

    def _cn_boxes():
        client = _cn_sys.modules["_creator_native_client"]
        result = []
        for tag, item in client.objects.items():
            try: bounds = renpy.get_image_bounds(tag)
            except Exception: bounds = None
            if bounds and bounds[2] > 0 and bounds[3] > 0:
                result.append(dict(item, bounds=list(bounds)))
        return result

    def _cn_snapshot():
        client = _cn_sys.modules["_creator_native_client"]
        state = {}
        for name in client.index.get("variables", []):
            try:
                value = getattr(persistent, name.split(".",1)[1]) if name.startswith("persistent.") else getattr(store, name)
                _cn_json.dumps(value)
                state[name] = value
            except Exception: pass
        _cn_emit("snapshot", {"native":True, "mode":client.mode, "fragmentDone":getattr(store,"_cn_fragment_done",False), "source":client.source, "context":{"nativeLabel":client.label}, "objects":_cn_boxes(), "state":state,
            "audio":{channel:{"file":renpy.music.get_playing(channel),"position":renpy.music.get_pos(channel)} for channel in client.index.get("audioChannels", ["music", "sound", "voice"]) if renpy.music.channel_defined(channel)}})

    def _cn_interact():
        client = _cn_sys.modules["_creator_native_client"]
        if not client.started or main_menu or not client.source: return
        store._cn_edit_mode = client.mode == "edit" and not getattr(store,"_cn_fragment_done",False)
        if store._cn_edit_mode: renpy.show_screen("_cn_editor_overlay")
        else: renpy.hide_screen("_cn_editor_overlay")
        _cn_snapshot()

    def _cn_apply(values):
        client = _cn_sys.modules["_creator_native_client"]
        operation = values.get("operation")
        if operation == "reset":
            for tag, original in getattr(client,"originals",{}).items():
                if tag in renpy.get_showing_tags():renpy.show(tag,tag=tag,what=original,at_list=[])
            for obj,attr,value in client.variable_bases.values():
                if attr=="chan_volume":obj.set_volume(value)
                else:setattr(obj,attr,value)
            client.originals={};client.bases={};client.overrides={};client.variable_bases={};client.volume_bases={}
            client.objects=_cn_copy.deepcopy(store._cn_source_objects)
            return
        if operation == "document_state":
            client.dirty = bool(values.get("dirty"))
            return
        if operation == "variable":
            name = values["name"]
            if "." in name:
                prefix, attr = name.split(".",1)
                if prefix not in ("audio", "gui", "config"): raise Exception("该表达式需要保存后重载。")
                obj = getattr(store,prefix) if prefix != "config" else config
            else: obj, attr = store, name
            key = name
            if key not in client.variable_bases: client.variable_bases[key] = (obj,attr,getattr(obj,attr,None))
            value = values.get("value")
            if isinstance(getattr(obj,attr,None),tuple) and isinstance(value,list): value=tuple(value)
            setattr(obj,attr,value)
            return
        tag = values.get("tag")
        if values.get("label") and values["label"] != client.label:
            # A called phone scene can retain a caller's displayed actor.
            active_source=client.objects.get(tag,{}).get("nativeSource") or {}
            requested=values.get("source") or {}
            if not active_source or any(active_source.get(k)!=requested.get(k) for k in ("path","line")):
                raise Exception("请先在引擎中运行到当前演出，再进行实时编辑。")
        if operation in ("property", "properties", "image"):
            if tag not in renpy.get_showing_tags(): raise Exception("此人物尚未在引擎中出现，请推进到对应台词。")
            from renpy.display.scenelists import scene_lists
            client.originals=getattr(client,"originals",{})
            if tag not in client.originals:client.originals[tag]=scene_lists().get_displayable_by_tag("master",tag)
            if operation == "image":
                old = scene_lists().get_displayable_by_tag("master",tag)
                placement = renpy.get_placement(old)
                item = client.objects.get(tag,{})
                desired_zoom = client.overrides.get(tag,{}).get("values",{}).get("zoom",item.get("scale",1))
                intrinsic = client.index.get("images",{}).get(values["image"],{}).get("zoom",1)
                geometry = {key:getattr(placement,key) for key in ("xpos","ypos","xanchor","yanchor","xoffset","yoffset","subpixel")}
                geometry["zoom"] = desired_zoom / intrinsic if intrinsic else 1
                renpy.show(values["image"], tag=tag, what=Transform(child=renpy.easy.displayable(values["image"]),**geometry),at_list=[])
                client.bases.pop(tag,None);client.overrides.pop(tag,None)
                item["scale"] = desired_zoom
                return
            if values.get("property")=="zorder":
                renpy.show(tag,tag=tag,what=scene_lists().get_displayable_by_tag("master",tag),at_list=[],zorder=int(values["value"]))
                return
            if tag not in client.bases:
                client.bases[tag] = scene_lists().get_displayable_by_tag("master",tag)
            properties = values.get("values") or {values["property"]:values["value"]}
            bases = values.get("bases") or {values.get("property"):values.get("base")}
            info = client.overrides.setdefault(tag,{"values":{},"bases":{}})
            for key,value in properties.items():
                if key not in info["bases"]: info["bases"][key]=bases.get(key)
                info["values"][key]=value
            kwargs = {}
            for key,value in info["values"].items():
                base=info["bases"].get(key)
                if key in ("xpos","ypos") and base is not None: kwargs["xoffset" if key=="xpos" else "yoffset"]=value-base
                elif key=="zoom" and base: kwargs[key]=value/base
                else: kwargs[key]=value
            renpy.show(tag, tag=tag, what=Transform(child=client.bases[tag], **kwargs), at_list=[])
            item=client.objects.get(tag,{})
            for key,value in properties.items():
                mapped={"xpos":"x","ypos":"y","zoom":"scale","xanchor":"anchorX","yanchor":"anchorY"}.get(key)
                if mapped:item[mapped]=value
        elif operation == "volume":
            channel=values.get("channel","music")
            if not renpy.music.channel_defined(channel): raise Exception("新声道需要保存并重载预览。")
            base=values.get("base",1)
            if not base and values["value"]: raise Exception("原播放相对音量为零，请保存后重播该场景。")
            key="volume:"+channel
            audio_channel=renpy.audio.audio.get_channel(channel)
            if key not in client.variable_bases:client.variable_bases[key]=(audio_channel,"chan_volume",audio_channel.chan_volume)
            original=client.variable_bases[key][2]
            client.volume_bases=getattr(client,"volume_bases",{})
            client.volume_bases.setdefault(channel,base)
            audio_channel.set_volume(original*values["value"]/client.volume_bases[channel] if client.volume_bases[channel] else 0)
        elif operation == "audio":
            channel=values.get("channel","music")
            if not renpy.music.channel_defined(channel): raise Exception("新声道需要保存并重载预览。")
            if values.get("file"):renpy.music.play(values["file"],channel=channel,fadeout=.5,fadein=.8)
            else:renpy.music.stop(channel=channel,fadeout=.5)
        else: raise Exception("此参数需要保存后重载预览。")

    def _cn_command(command):
        client = _cn_sys.modules["_creator_native_client"]
        if command.get("revision",0)<client.revision:return
        client.revision=command.get("revision",client.revision)
        try:
            kind=command.get("type")
            if kind=="native":
                if client.mode!="edit":raise Exception("请先切换到编辑模式。")
                _cn_apply(command["command"])
            elif kind=="mode":
                client.mode=command["mode"]
                store._cn_edit_mode=client.mode=="edit"
            elif kind=="reload":
                client.bases={};client.overrides={};client.objects={};client.variable_bases={}
                store._cn_edit_mode=False
                renpy.hide_screen("_cn_editor_overlay")
                renpy.reload_script()
                return
            elif kind=="fragment_replay":
                _cn_replay_fragment()
            elif kind=="screenshot":
                folder=_cn_os.path.join(_cn_os.environ.get("CREATOR_PREVIEW_OUTPUT",config.basedir),"screenshots")
                _cn_os.makedirs(folder,exist_ok=True)
                renpy.screenshot(_cn_os.path.join(folder,"editor-preview.png"))
                _cn_emit("screenshot",{"path":"screenshots/editor-preview.png"})
            _cn_interact()
            renpy.restart_interaction()
        except (renpy.game.FullRestartException,renpy.game.UtterRestartException,renpy.game.QuitException,renpy.game.JumpException,renpy.game.CallException):
            raise
        except Exception as error:
            _cn_emit("error",{"message":str(error)})

    def _cn_dragged(drags, drop):
        client=_cn_sys.modules["_creator_native_client"]
        client.dirty = True
        boxes={b["id"]:b for b in _cn_boxes()}
        for drag in drags:
            box=boxes.get(drag.drag_name)
            if not box:continue
            dx=drag.x-box["bounds"][0];dy=drag.y-box["bounds"][1]
            _cn_apply({"operation":"properties","tag":drag.drag_name,"values":{"xpos":box["x"]+dx,"ypos":box["y"]+dy},"bases":{"xpos":box["x"],"ypos":box["y"]}})
            box.update(x=box["x"]+dx,y=box["y"]+dy)
            client.objects[drag.drag_name].update(x=box["x"],y=box["y"])
            _cn_emit("native_drag",{"tag":drag.drag_name,"x":box["x"],"y":box["y"],"source":box["nativeSource"]})
        renpy.restart_interaction()
        return None

    def _cn_loaded():
        _cn_client.bases = {}; _cn_client.overrides = {}
        _cn_client.objects = _cn_copy.deepcopy(store._cn_source_objects)
        filename,line=renpy.get_filename_line()
        _cn_client.source={"path":filename,"line":line}
        _cn_snapshot()

    for _cn_callbacks, _cn_callback in ((config.label_callbacks,_cn_label),(config.statement_callbacks,_cn_statement),(config.interact_callbacks,_cn_interact),(config.after_load_callbacks,_cn_loaded)):
        _cn_callbacks[:] = [cb for cb in _cn_callbacks if getattr(cb,"__name__","") != _cn_callback.__name__]
        _cn_callbacks.append(_cn_callback)

label _cn_test_entry:
    python:
        for _cn_initializer in _cn_client.test_entry.get("initialize",[]):
            renpy.call_in_new_context(_cn_initializer)
        _cn_client.mode = _cn_os.environ.get("CREATOR_PREVIEW_MODE","play")
        _cn_target=_cn_client.test_entry.get("nativeLabel","start")
        _cn_args=_cn_client.test_entry.get("args",[])
        _cn_fragment_active=_cn_client.test_entry.get("scope","fragment")=="fragment"
        _cn_fragment_done=False
        _cn_fragment_target=_cn_target
        _cn_fragment_context=renpy.context_nesting_level()
        _cn_fragment_labels=[]
        def _cn_collect_label(node):
            if isinstance(node,renpy.ast.Label): _cn_fragment_labels.append(node.name)
        renpy.game.script.lookup(_cn_target).get_children(_cn_collect_label)
    if _cn_client.test_entry.get("motionPreview"):
        jump _cn_motion_clip
    call expression _cn_target pass (*_cn_args) from _cn_fragment_return
    if _cn_fragment_active:
        $ _cn_finish_fragment()
        jump _cn_fragment_complete
    return

label _cn_restart_entry:
    jump start

label _cn_fragment_complete:
    call screen _cn_fragment_finished
    return

screen _cn_fragment_finished():
    modal True
    zorder 2100
    key "dismiss" action NullAction()
    key "rollback" action NullAction()
    add Solid("#0c162bd9")
    frame:
        xalign .5
        yalign .5
        padding (48,36)
        background Solid("#192936")
        vbox:
            spacing 24
            text "片段试玩结束" size 40 color "#b6fff1"
            text _cn_fragment_target size 26 color "#ffffff"
            textbutton "重新试玩此片段" action Function(_cn_replay_fragment)
            textbutton "返回游戏标题" action MainMenu(confirm=False)
            textbutton "关闭试玩窗口" action Quit(confirm=False)

screen _cn_motion_controls():
    zorder 2100
    frame:
        xalign .5
        ypos 12
        background Solid("#10242bea")
        padding (18,10)
        hbox:
            spacing 24
            text "立绘动作预览" size 22 color "#b6fff1"
            textbutton "重播动作" action Jump("_cn_motion_clip")
            textbutton "关闭窗口" action Quit(confirm=False)

screen _cn_editor_overlay():
    zorder 2000
    modal True
    key "dismiss" action NullAction()
    key "rollback" action NullAction()
    key "game_menu" action NullAction()
    draggroup:
        for box in _cn_boxes():
            drag:
                drag_name box["id"]
                xpos box["bounds"][0]
                ypos box["bounds"][1]
                draggable (not getattr(_cn_client,"dirty",False))
                droppable False
                dragged _cn_dragged
                frame:
                    xysize (int(box["bounds"][2]),int(box["bounds"][3]))
                    background Solid("#8acdb019")
                    padding (6,6)
                    text box["id"] size 18 color "#aaffdb"
    frame:
        xalign .5
        ypos 12
        background Solid("#10242bea")
        padding (18,10)
        text "编辑预览 · 在 IDE 中切换试玩" size 18 color "#b6fff1"
