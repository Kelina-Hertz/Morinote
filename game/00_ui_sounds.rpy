################################################################################
## UI sound placeholders
################################################################################

## Keep these values as None until the final UI audio files are available.
## Once they are ready, only replace the two lines below, for example:
## define ui_hover_sound = "audio/ui/hover.ogg"
## define ui_click_sound = "audio/ui/click.ogg"
define ui_hover_sound = None
define ui_click_sound = None


transform cyan_menu_enter:
    alpha 0.0
    xoffset 14
    ease 0.18 alpha 1.0 xoffset 0
