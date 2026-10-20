# Authored per-line Auto overrides. Loaded only when the author adds an override.
default creator_native_auto_id = None
default creator_native_auto_wait = None
default creator_native_auto_ready = False
default creator_native_auto_elapsed = 0.0
default creator_native_auto_at = None
default creator_native_auto_token = 0

init -10 python:
    import time as creator_native_auto_clock

    def creator_native_auto_cancel():
        global creator_native_auto_ready,creator_native_auto_elapsed,creator_native_auto_at,creator_native_auto_token
        creator_native_auto_token += 1
        creator_native_auto_ready = False
        creator_native_auto_elapsed = 0.0
        creator_native_auto_at = None
        renpy.hide_screen("creator_native_auto_timer")

    def creator_native_auto_prepare(node, wait):
        global creator_native_auto_id,creator_native_auto_wait
        creator_native_auto_cancel()
        creator_native_auto_id,creator_native_auto_wait = node,wait

    def creator_native_auto_callback(event,interact=True,last_segment=False,**kwargs):
        global creator_native_auto_ready,creator_native_auto_at,creator_native_auto_id
        if creator_native_auto_id is None:return
        if event == "begin":creator_native_auto_cancel()
        elif event == "slow_done" and interact and last_segment:
            creator_native_auto_ready = True
            creator_native_auto_at = creator_native_auto_clock.monotonic()
            renpy.show_screen("creator_native_auto_timer",token=creator_native_auto_token)
            renpy.restart_interaction()
        elif event in ("interact_done","end"):
            creator_native_auto_cancel()
            if event == "end":creator_native_auto_id = None

    def creator_native_auto_resume():
        global creator_native_auto_at
        creator_native_auto_at = creator_native_auto_clock.monotonic() if creator_native_auto_ready else None

    def creator_native_auto_tick(token):
        global creator_native_auto_elapsed,creator_native_auto_at
        if token != creator_native_auto_token or not creator_native_auto_ready:return
        now = creator_native_auto_clock.monotonic()
        delta = min(max(now-(creator_native_auto_at or now),0),.1)
        creator_native_auto_at = now
        if main_menu or renpy.context_nesting_level()!=0 or getattr(store,"_cn_edit_mode",False):return
        if not preferences.afm_enable or preferences.self_voicing or renpy.is_skipping():
            creator_native_auto_elapsed = 0.0
            return
        creator_native_auto_elapsed += delta
        if creator_native_auto_elapsed >= creator_native_auto_wait:
            if config.afm_callback is None or config.afm_callback():return True

    config.all_character_callbacks.append(creator_native_auto_callback)
    config.start_interact_callbacks.append(creator_native_auto_resume)
    config.after_load_callbacks.append(creator_native_auto_cancel)

screen creator_native_auto_timer(token):
    zorder 0
    timer .05 repeat True modal True action Function(creator_native_auto_tick,token,_update_screens=False)
