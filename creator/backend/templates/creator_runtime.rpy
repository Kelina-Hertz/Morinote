# Creator runtime. Game state uses Ren'Py rollback-aware defaults.
default creator_state = {}
default creator_component_state = {}
default creator_component_types = {}
default creator_event_seen = set()
default creator_event_counts = {}
default creator_line_event_counts = {}
default creator_wait = None
default creator_wait_result = None
default creator_event_queue = []
default creator_event_processing = False
default creator_context = {}
default creator_visual = None
default creator_motion_enabled = True
default creator_audio = {}
default creator_shown_tags = []
default creator_overlay_instances = {}
default creator_messages = []
default creator_phone_title = "消息"
default creator_phone_active = False
default creator_auto_wait = None
default creator_auto_text = ""
default creator_auto_ready = False
default creator_auto_elapsed = 0.0
default creator_auto_tick_at = None
default creator_auto_token = 0
default creator_auto_line = None
default persistent.creator_states = {}

init -30 python:
    import copy as creator_copy
    import time as creator_time

    def creator_notify(kind, payload):
        # The optional desktop bridge replaces this function in preview builds.
        return None

    def creator_is_editing():
        return bool(getattr(store, "creator_edit_mode", False))

    def creator_snapshot():
        return {"context": dict(creator_context), "state": dict(creator_state),
                "componentState": dict(creator_component_state), "visual": creator_visual,
                "audio": creator_audio, "messages": list(creator_messages),
                "events": list(creator_event_seen)}

    def creator_get(variable):
        spec = creator_variables.get(variable, {})
        if spec.get("scope") == "persistent":
            return persistent.creator_states.get(creator_project_id, {}).get(variable, creator_copy.deepcopy(spec.get("initial")))
        if spec.get("scope") == "component":
            instance = creator_context.get("component", "scene:" + creator_context.get("scene", "default"))
            return creator_component_state.get(instance, {}).get(variable, creator_copy.deepcopy(spec.get("initial")))
        return creator_state.get(variable, creator_copy.deepcopy(spec.get("initial")))

    def creator_validate_value(variable, value):
        spec = creator_variables.get(variable)
        if spec is None:
            raise ValueError("Unknown state: " + variable)
        kind = spec["type"]
        if kind == "boolean" and type(value) is not bool:
            raise ValueError("State needs a boolean: " + variable)
        if kind == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError("State needs a number: " + variable)
        if kind == "string" and not isinstance(value, str):
            raise ValueError("State needs a string: " + variable)
        if kind == "enum" and value not in spec.get("values", []):
            raise ValueError("State enum value is invalid: " + variable)
        if kind == "set" and not isinstance(value, (list, tuple, set)):
            raise ValueError("State needs a collection: " + variable)
        return list(dict.fromkeys(value)) if kind == "set" else value

    def creator_set(variable, value, test=False):
        if creator_is_editing() and not test:
            return
        value = creator_validate_value(variable, value)
        if creator_variables[variable].get("scope") == "persistent":
            current = dict(persistent.creator_states.get(creator_project_id, {}))
            current[variable] = value
            persistent.creator_states[creator_project_id] = current
            renpy.save_persistent()
        elif creator_variables[variable].get("scope") == "component":
            instance = creator_context.get("component", "scene:" + creator_context.get("scene", "default"))
            if instance not in creator_component_state:
                creator_component_state[instance] = {}
            creator_component_state[instance][variable] = value
        else:
            creator_state[variable] = value
        creator_notify("state", {"variable": variable, "value": value, **creator_context})

    def creator_apply_test_state(state):
        for variable, value in state.items():
            creator_set(variable, value, test=True)

    def creator_condition(condition):
        if not condition:
            return True
        if "all" in condition:
            return all(creator_condition(c) for c in condition["all"])
        if "any" in condition:
            return any(creator_condition(c) for c in condition["any"])
        left, right, op = creator_get(condition["variable"]), condition.get("value"), condition["op"]
        if op == "eq": return left == right
        if op == "ne": return left != right
        if op == "gt": return left > right
        if op == "gte": return left >= right
        if op == "lt": return left < right
        if op == "lte": return left <= right
        if op == "contains": return right in left
        raise ValueError("Unknown condition operator: " + op)

    def creator_actions(actions):
        if creator_is_editing():
            return
        for action in actions:
            kind = action["type"]
            if kind == "emit":
                creator_emit("signal", action["event"])
            elif kind == "set":
                creator_set(action["variable"], creator_copy.deepcopy(action.get("value")))
            elif kind == "add":
                variable = action["variable"]
                previous = creator_get(variable)
                value = action.get("value", 1)
                if creator_variables[variable]["type"] == "set":
                    creator_set(variable, list(previous) + ([value] if not isinstance(value, list) else value))
                else:
                    creator_set(variable, previous + value)

    def creator_emit(trigger, target=None, payload=None):
        global creator_event_processing
        if creator_is_editing():
            return
        creator_event_queue.append((trigger, target, payload or {}))
        if creator_event_processing:
            return
        creator_event_processing = True
        executed = 0
        try:
            while creator_event_queue:
                current_trigger, current_target, current_payload = creator_event_queue.pop(0)
                for event in creator_events:
                    if event["trigger"] != current_trigger:
                        continue
                    if event.get("target") and event["target"] != current_target:
                        continue
                    if event.get("scope") and event["scope"] not in (creator_context.get("graph"), creator_context.get("scene"), creator_context.get("component")):
                        continue
                    if event.get("repeat") == "once" and event["id"] in creator_event_seen:
                        continue
                    if not creator_condition(event.get("condition")):
                        continue
                    executed += 1
                    if executed > 256:
                        raise RuntimeError("事件循环超过 256 次，请检查信号循环")
                    creator_event_seen.add(event["id"])
                    creator_notify("event", {"id": event["id"], "trigger": current_trigger, "payload": current_payload, **creator_context})
                    creator_actions(event.get("actions", []))
                    creator_event_counts[event["id"]] = creator_event_counts.get(event["id"], 0) + 1
        finally:
            creator_event_processing = False
            creator_event_queue[:] = []

    def creator_node_enter(graph, node):
        global creator_context
        creator_context = {"graph": graph, "node": node}
        creator_notify("node", dict(creator_context))
        creator_emit("node_enter", node)

    def creator_node_exit(graph, node):
        creator_emit("node_exit", node)

    def creator_scene_enter(scene):
        creator_context["scene"] = scene

    def creator_line_begin(scene, line, wait, text):
        global creator_auto_wait, creator_auto_text, creator_auto_line, creator_line_event_counts
        creator_auto_cancel()
        creator_line_event_counts = dict(creator_event_counts)
        creator_context.update(scene=scene, line=line)
        creator_auto_wait, creator_auto_text, creator_auto_line = wait, text, line
        creator_notify("line", dict(creator_context))
        creator_emit("line_begin", line)

    def creator_line_end(line):
        creator_auto_cancel()
        creator_emit("line_end", line)

    def creator_wait_begin(spec):
        global creator_wait, creator_wait_result
        creator_wait = {"event": spec["event"], "baseline": creator_line_event_counts.get(spec["event"], 0),
                        "timeout": spec.get("timeout"), "elapsed": 0.0, "tick": None}
        creator_wait_result = None

    def creator_wait_resume():
        if creator_wait is not None:
            creator_wait["tick"] = None

    def creator_wait_tick():
        global creator_wait_result
        if creator_wait is None:
            return True
        now = creator_time.monotonic()
        delta = min(max(now - (creator_wait["tick"] or now), 0.0), .1)
        creator_wait["tick"] = now
        if creator_is_editing() or renpy.context_nesting_level() != 0 or main_menu:
            return
        if creator_event_counts.get(creator_wait["event"], 0) > creator_wait["baseline"]:
            creator_wait_result = "completed"
            return True
        creator_wait["elapsed"] += delta
        timeout = creator_wait["timeout"]
        if timeout is not None and creator_wait["elapsed"] >= timeout:
            creator_wait_result = "timeout"
            creator_notify("stage_timeout", {"event": creator_wait["event"], "timeout": timeout, **creator_context})
            renpy.log("Creator stage timed out waiting for event: " + creator_wait["event"])
            return True

    def creator_wait_end():
        global creator_wait
        creator_wait = None

    def creator_asset(asset_id):
        asset = creator_assets.get(asset_id, {})
        path = asset.get("path", "")
        if asset.get("status") == "placeholder" or not path:
            label = asset.get("character", "") + " · " + asset.get("requirement", asset.get("name", "待补素材"))
            return Composite((430, 560), (0, 0), Solid("#293b50", xysize=(430, 560)), (25, 220), Text("占位\n" + label, size=30, xmaximum=380, color="#f6ddad"))
        if path.startswith("builtin:solid:"):
            return Solid(path.split(":", 2)[2], xysize=(config.screen_width, config.screen_height))
        if path.startswith("builtin:person:"):
            color = path.split(":", 2)[2]
            return Composite((380, 650), (105, 0), Solid(color, xysize=(170, 170)), (40, 200), Solid(color, xysize=(300, 450)), (80, 470), Text(asset.get("character", asset.get("name", "")), size=54, color="#102534", xmaximum=260))
        return path

    def creator_asset_image(asset_id):
        return creator_asset(asset_id)

    class CreatorMotion:
        def __init__(self, sprite):
            self.sprite = dict(sprite)
        def __call__(self, trans, st, at):
            sprite = self.sprite
            values = {"x": float(sprite.get("x", 960)), "y": float(sprite.get("y", 540)), "scale": float(sprite.get("scale", 1)), "alpha": float(sprite.get("alpha", 1))}
            animation = sprite.get("animation") or {}
            cursor, until = 0.0, 0.0
            for step in animation.get("steps", []):
                start = (cursor if animation.get("mode") == "sequence" else 0) + float(step.get("delay", 0))
                duration = float(step.get("duration", 0))
                end = start + duration
                prop = step["property"]
                before = values[prop]
                ratio = min(1.0, max(0.0, (st - start) / duration)) if duration else float(st >= start)
                values[prop] = before + (float(step["value"]) - before) * ratio
                cursor, until = end, max(until, end)
            trans.xpos, trans.ypos = int(values["x"]), int(values["y"])
            trans.zoom, trans.alpha = values["scale"], values["alpha"]
            return 0 if st < until else None

    def creator_apply_visual(visual):
        global creator_visual, creator_shown_tags, creator_motion_enabled
        previous = creator_visual or {}
        previous_motion_enabled = creator_motion_enabled
        replay = bool(getattr(store, "creator_preview_animate", False))
        creator_motion_enabled = not creator_is_editing() or replay
        if creator_visual is None:
            # Ren'Py starts with a black master-layer image. The first authored
            # composition replaces that initial scene; later backgrounds preserve people.
            renpy.scene(layer="master")
        creator_visual = creator_copy.deepcopy(visual)
        if visual.get("background"):
            renpy.show("creator_background", what=Transform(creator_asset(visual["background"]), xysize=(config.screen_width, config.screen_height), fit="cover"), zorder=-10000)
        previous_sprites = {s["id"]: s for s in previous.get("sprites", [])}
        shown = []
        for sprite in sorted(visual.get("sprites", []), key=lambda s: s.get("z", 0)):
            tag = "creator_sprite_" + sprite["id"]
            shown.append(tag)
            if previous_sprites.get(sprite["id"]) == sprite and renpy.showing(tag) and previous_motion_enabled == creator_motion_enabled and not replay:
                continue
            if creator_motion_enabled:
                transform = Transform(anchor=(sprite.get("anchorX", .5), sprite.get("anchorY", .5)), xzoom=-1 if sprite.get("flip") else 1, function=CreatorMotion(sprite))
            else:
                transform = Transform(anchor=(sprite.get("anchorX", .5), sprite.get("anchorY", .5)), xzoom=-1 if sprite.get("flip") else 1,
                    xpos=int(sprite.get("x", 960)), ypos=int(sprite.get("y", 540)), zoom=float(sprite.get("scale", 1)), alpha=float(sprite.get("alpha", 1)))
            renpy.show(tag, what=creator_asset(sprite["asset"]), at_list=[transform], zorder=int(sprite.get("z", 0)))
        for tag in creator_shown_tags:
            if tag not in shown:
                renpy.hide(tag)
        creator_shown_tags = shown
        active = {item["id"]: item for item in visual.get("components", [])}
        for instance in list(creator_overlay_instances):
            if instance.startswith("visual:") and instance[7:] not in active:
                creator_component_hide(instance)
        for instance, item in active.items():
            creator_component_show(item["component"], item.get("params", {}), "visual:" + instance)
        transition = visual.get("transition", "none")
        if creator_motion_enabled:
            if transition == "dissolve": renpy.transition(Dissolve(.25))
            elif transition == "fade": renpy.transition(Fade(.2, .1, .2))
        creator_notify("visual", {"visual": creator_visual, **creator_context})

    def creator_live_visual(visual):
        creator_apply_visual(visual)
        renpy.restart_interaction()

    def creator_audio_source(asset_id):
        asset = creator_assets.get(asset_id, {})
        return asset.get("path") if asset.get("status") == "ready" and not asset.get("path", "").startswith("builtin:") else None

    def creator_apply_audio(audio):
        global creator_audio
        previous = creator_audio
        creator_audio = dict(previous)
        creator_audio.update(creator_copy.deepcopy(audio))
        for name in ("music", "ambience", "sound", "voice"):
            channel = "creator_ambience" if name == "ambience" else name
            if name not in audio:
                continue
            track = audio[name]
            asset = track.get("asset", "")
            source = creator_audio_source(asset) if asset else None
            old = previous.get(name, {})
            if name in ("sound", "voice") or old.get("asset", "") != asset:
                if source:
                    renpy.music.play(source, channel=channel, loop=name in ("music", "ambience"), fadeout=float(track.get("fadeout", .5)), fadein=float(track.get("fadein", .8)))
                else:
                    renpy.music.stop(channel=channel, fadeout=float(track.get("fadeout", .5)))
            renpy.music.set_volume(float(track.get("volume", 1)), channel=channel)
        creator_notify("audio", {"audio": creator_audio, **creator_context})

    def creator_live_audio(audio):
        creator_apply_audio(audio)

    def creator_component_enter(instance, component):
        creator_context["component"] = instance
        creator_component_types[instance] = component
        if instance not in creator_component_state:
            creator_component_state[instance] = {v["id"]: creator_copy.deepcopy(v.get("initial")) for v in creator_components[component].get("state", [])}

    def creator_component_exit(instance, result=None):
        previous = creator_context.get("component")
        creator_context["component"] = instance
        creator_emit("component", result, {"instance": instance, "result": result})
        if previous and previous != instance: creator_context["component"] = previous
        else: creator_context.pop("component", None)
        creator_notify("component", {"instance": instance, "result": result, **creator_context})

    def creator_component_get(instance, key):
        return creator_component_state.get(instance, {}).get(key)

    def creator_component_set(instance, key, value):
        if creator_is_editing(): return
        if instance not in creator_component_state:
            raise ValueError("组件实例尚未初始化：" + instance)
        component = creator_components[creator_component_types[instance]]
        spec = next((s for s in component.get("state", []) if s["id"] == key), None)
        if spec is None:
            raise ValueError("组件状态未声明：" + key)
        creator_component_state[instance][key] = creator_copy.deepcopy(value)
        creator_notify("state", {"instance": instance, "variable": key, "value": value, **creator_context})

    def creator_component_emit(instance, event, payload=None):
        previous = creator_context.get("component")
        creator_context["component"] = instance
        try:
            creator_emit("component", event, {"instance": instance, **(payload or {})})
        finally:
            if previous: creator_context["component"] = previous
            else: creator_context.pop("component", None)

    def creator_component_show(component, params, instance):
        spec = creator_components[component]
        final_params = {p["id"]: p.get("default") for p in spec.get("props", [])}
        final_params.update(params)
        previous = creator_context.get("component")
        creator_component_enter(instance, component)
        creator_overlay_instances[instance] = {"component": component, "params": final_params}
        if previous: creator_context["component"] = previous
        else: creator_context.pop("component", None)
        renpy.show_screen("creator_component_host")

    def creator_component_hide(instance):
        if instance in creator_overlay_instances:
            creator_overlay_instances.pop(instance)
            creator_component_exit(instance, "closed")

    def creator_chat_open(title=None, sound=True):
        global creator_phone_active, creator_phone_title
        if not creator_phone_active:
            creator_messages[:] = []
        creator_phone_active = True
        if title: creator_phone_title = title
        asset = creator_phone_params().get("sound", "")
        source = creator_audio_source(asset) if asset else None
        if sound and source and not renpy.is_skipping(): renpy.sound.play(source)

    def creator_chat_append(speaker, text):
        creator_messages.append({"speaker": speaker, "text": text})
        creator_emit("component", "message", {"speaker": speaker, "text": text})

    def creator_chat_close():
        global creator_phone_active
        creator_phone_active = False

    def creator_literal(text):
        return str(text).replace("{", "{{").replace("[", "[[")

    def creator_phone_params():
        params = {p["id"]: p.get("default") for p in creator_components.get("phone", {}).get("props", [])}
        for instance in creator_overlay_instances.values():
            if instance["component"] == "phone":
                params.update(instance["params"])
                break
        return params

    def creator_character(name):
        return Character(creator_literal(name), callback=creator_say_callback, what_prefix="", what_suffix="", screen="say", afm=False)

    def creator_chat_character(name):
        return Character(creator_literal(name), callback=creator_say_callback, screen="creator_phone_say", afm=False)

    def creator_auto_cancel():
        global creator_auto_ready, creator_auto_elapsed, creator_auto_tick_at, creator_auto_token
        creator_auto_token += 1
        creator_auto_ready, creator_auto_elapsed, creator_auto_tick_at = False, 0.0, None
        renpy.hide_screen("creator_auto")

    def creator_say_callback(event, interact=True, last_segment=False, **kwargs):
        global creator_auto_ready, creator_auto_elapsed, creator_auto_tick_at
        if event == "begin": creator_auto_cancel()
        elif event == "slow_done" and interact and last_segment and creator_auto_line is not None:
            creator_auto_ready, creator_auto_elapsed, creator_auto_tick_at = True, 0.0, creator_time.monotonic()
            renpy.show_screen("creator_auto", token=(creator_auto_line, creator_auto_token))
            renpy.restart_interaction()
        elif event in ("interact_done", "end"): creator_auto_cancel()

    def creator_interaction_start():
        global creator_auto_tick_at
        creator_auto_tick_at = creator_time.monotonic() if creator_auto_ready else None
        creator_wait_resume()

    def creator_auto_tick(token):
        global creator_auto_elapsed, creator_auto_tick_at
        if token != (creator_auto_line, creator_auto_token) or not creator_auto_ready:
            return
        now = creator_time.monotonic()
        delta = min(max(now - (creator_auto_tick_at or now), 0.0), .1)
        creator_auto_tick_at = now
        if creator_is_editing() or renpy.context_nesting_level() != 0 or main_menu:
            return
        if not preferences.afm_enable or preferences.self_voicing or renpy.is_skipping():
            creator_auto_elapsed = 0.0
            return
        wait = creator_auto_wait
        if wait is None:
            if not preferences.afm_time: return
            wait = (config.afm_bonus + 1 + max(len(creator_auto_text), 1)) / float(config.afm_characters) * preferences.afm_time
        creator_auto_elapsed += delta
        if creator_auto_elapsed >= wait:
            if config.afm_callback is None or config.afm_callback():
                return True

    def creator_cleanup():
        global creator_visual, creator_audio, creator_shown_tags, creator_overlay_instances
        creator_auto_cancel()
        creator_wait_end()
        creator_chat_close()
        for tag in creator_shown_tags + ["creator_background"]: renpy.hide(tag)
        creator_shown_tags, creator_overlay_instances = [], {}
        renpy.hide_screen("creator_component_host")
        creator_visual, creator_audio = None, {}
        for channel in ("music", "creator_ambience", "sound", "voice"):
            renpy.music.stop(channel=channel)
            renpy.music.set_volume(1.0, channel=channel)

    def creator_reset():
        global creator_state, creator_component_state, creator_component_types, creator_event_seen, creator_event_counts, creator_line_event_counts, creator_event_queue, creator_context, creator_messages
        creator_cleanup()
        creator_state = {key: creator_copy.deepcopy(value.get("initial")) for key, value in creator_variables.items() if value.get("scope") == "game"}
        creator_component_state, creator_component_types, creator_event_seen, creator_event_queue, creator_context, creator_messages = {}, {}, set(), [], {}, []
        creator_event_counts, creator_line_event_counts = {}, {}

    renpy.music.register_channel("creator_ambience", mixer="music", loop=True)
    config.start_interact_callbacks.append(creator_interaction_start)
    config.after_load_callbacks.append(creator_auto_cancel)
    config.after_load_callbacks.append(creator_wait_resume)

define creator_narrator = Character(None, callback=creator_say_callback, afm=False)

screen creator_auto(token):
    zorder 0
    timer .05 repeat True modal True action Function(creator_auto_tick, token, _update_screens=False)

screen creator_stage_wait():
    key "dismiss" action NullAction()
    timer .05 repeat True modal True action Function(creator_wait_tick, _update_screens=False)
