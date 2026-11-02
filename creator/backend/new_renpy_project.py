"""Create standalone RPY projects, then attach the existing native IDE index."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid

from .project import _LOCK, EDITOR_PROJECT, atomic_json, safe_path
from .scene_metadata import scene_comment


def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _story(demo: bool) -> str:
    opening = scene_comment('开场', '第一章')
    if not demo:
        return f'''# 剧情源文件；可在 IDE 或其他文本编辑器中修改。
image bg opening = Solid("#182535")

{opening}
label start:
    scene bg opening
    "从这里写下你的故事。"
    return
'''
    return f'''# 独立的原生 Ren'Py 分支示例，不使用任何项目私有素材。
define guide = Character("向导", color="#98d5df")
default found_letter = False
image bg opening = Solid("#182535")
image bg courtyard = Solid("#354139")

{opening}
label start:
    scene bg opening
    "放学后的教室里，还亮着一盏灯。"
    guide "要先看看桌上的信，还是去庭院走走？"
    menu:
        "查看信件":
            jump read_letter
        "前往庭院":
            jump courtyard

{scene_comment('桌上的信', '第一章')}
label read_letter:
    scene bg opening
    "信封里是一张社团活动的邀请函。"
    $ found_letter = True
    jump reply

{scene_comment('庭院散步', '第一章')}
label courtyard:
    scene bg courtyard with dissolve
    guide "晚风很舒服，我们明天再来看那封信吧。"
    jump reply

{scene_comment('答复邀请', '第二章')}
label reply:
    scene bg opening with dissolve
    if found_letter:
        guide "你已经看过邀请函了，愿意参加吗？"
    else:
        guide "昨天桌上的信，其实是给你的邀请。"
    call farewell
    return

{scene_comment('约定再见', '第二章')}
label farewell:
    "一个新的故事，正要开始。"
    return
'''


def create_native_project(root: Path, title: str, demo: bool = False, *, sdk: Path | None = None) -> dict:
    """Prepare all files/indexes before publishing into a previously empty folder.

    The old JSON-project constructor remains available for old-project migration.
    This constructor never generates or recompiles an existing game.
    """
    from .compiler import sdk_path
    from .renpy_import import open_native

    root = Path(root).expanduser().resolve()
    title = (title or '').strip() or '未命名作品'
    if len(title) > 120 or any(ord(char) < 32 for char in title):
        raise ValueError('作品名称需为 1 至 120 个字符，且不能包含换行或控制字符。')
    sdk = Path(sdk).resolve() if sdk is not None else sdk_path()
    font = sdk / 'sdk-fonts/SourceHanSansLite.ttf'
    if not font.is_file():
        raise ValueError('随附 Ren’Py SDK 缺少中文字体，未创建项目。')
    template = Path(__file__).with_name('templates') / 'creator_screens.rpy'
    screens = template.read_text('utf-8').replace('creator_menu', 'game_menu').replace('creator_slots', 'file_slots')
    # Keep the template UI independent from the IDE bridge and generated runtime.
    screens = screens.replace('    gui.init(config.screen_width, config.screen_height)\n', '')
    screens += '''
screen input(prompt):
    window:
        xfill True
        yalign 1.0
        background Solid("#101d2bea")
        padding (110, 40)
        vbox:
            spacing 18
            text prompt
            input id "input"

screen history():
    tag menu
    use game_menu("对话历史"):
        viewport:
            xysize (1600, 760)
            scrollbars "vertical"
            mousewheel True
            draggable True
            vbox:
                spacing 16
                for entry in _history_list:
                    if entry.who:
                        text entry.who color "#98d5df"
                    text entry.what substitute False
'''
    with _LOCK:
        if root.exists() and (not root.is_dir() or any(root.iterdir())):
            raise ValueError('请使用空目录新建 Ren’Py 工程；已有项目请直接打开。')
        root.mkdir(parents=True, exist_ok=True)
        # Only this private staging folder is removed on failure, never authored files.
        with tempfile.TemporaryDirectory(prefix='.creator-new-', dir=root) as temporary:
            stage = Path(temporary).resolve()
            if not stage.is_relative_to(root) or stage.parent != root:
                raise ValueError('无效的新建工程临时目录。')
            key = 'story_' + uuid.uuid4().hex[:16]
            runtime_title = json.dumps(title.replace('{', '{{').replace('[', '[['), ensure_ascii=False)
            _write(stage / 'game/script.rpy', _story(demo))
            _write(stage / 'game/gui.rpy', '''# 基础布局；界面样式保存在 screens.rpy。
init -2 python:
    gui.init(1920, 1080)
define gui.text_font = "fonts/SourceHanSansLite.ttf"
define gui.name_text_font = "fonts/SourceHanSansLite.ttf"
define gui.interface_text_font = "fonts/SourceHanSansLite.ttf"
''')
            _write(stage / 'game/options.rpy', f'''# 游戏配置；原生 Ren'Py 启动和打包使用同一份文件。
define config.name = {runtime_title}
define config.version = "1.0"
define build.name = "{key}"
define config.save_directory = "{key}"
define config.has_music = True
define config.has_sound = True
define config.has_voice = True
define config.history_length = 250
define config.window = "auto"
default preferences.text_cps = 0
default preferences.afm_time = 15
''')
            _write(stage / 'game/screens.rpy', screens)
            (stage / 'game/fonts').mkdir()
            shutil.copy2(font, stage / 'game/fonts/SourceHanSansLite.ttf')
            license_file = sdk / 'LICENSE.txt'
            if license_file.is_file():
                shutil.copy2(license_file, stage / 'game/fonts/RENPY-THIRD-PARTY-LICENSES.txt')
            for folder in ('images', 'audio'):
                (stage / 'game' / folder).mkdir()
            atomic_json(stage / 'project.json', {'type': 'normal'})
            _write(stage / '.gitignore', '*.rpyc\n*.rpymc\ngame/cache/\ngame/saves/\n.creator/\nlog.txt\nerrors.txt\ntraceback.txt\n')
            _, document = open_native(stage)
            document['title'] = title
            document['nativeRenpy']['sourceName'] = root.name
            # Keep open_native's baseline, including its per-line source records.
            atomic_json(safe_path(stage, EDITOR_PROJECT), document)
            children = list(stage.iterdir())
            if any(item != stage for item in root.iterdir()):
                raise ValueError('新建期间目标目录出现其他文件，请选择空目录重试。')
            published = []
            try:
                for child in children:
                    target = root / child.name
                    if target.exists():
                        raise ValueError('目标文件已存在，未覆盖：' + child.name)
                    child.rename(target)
                    published.append(target)
            except (OSError, ValueError):
                # Return only the files published by this constructor to its staging area.
                for target in reversed(published):
                    target.rename(stage / target.name)
                raise
            return document
