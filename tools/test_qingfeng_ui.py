"""Run UI tests in a shadow project without accessing player saves.

Usage: python tools/test_qingfeng_ui.py --sdk G:/Morinote/renpy-8.5.3-sdk
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--case", default="ui_qa")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    project = repo / ".ui-test/project"
    game = project / "game"
    game.mkdir(parents=True, exist_ok=True)
    saves = game / "saves"
    if saves.exists():
        # Only remove generated shadow-test data, never any linked directory.
        assert saves.resolve() == project.resolve() / "game/saves"
        assert saves.resolve().is_relative_to(repo.resolve() / ".ui-test")
        shutil.rmtree(saves)
    excluded = {"saves", "cache", ".vscode", ".ui_qa_screens", "__pycache__"}
    copied = linked = 0
    for root, dirs, files in os.walk(repo / "game"):
        dirs[:] = [d for d in dirs if d not in excluded]
        for name in files:
            src = Path(root) / name
            relative = src.relative_to(repo / "game")
            if src.suffix in (".rpyc", ".rpymc", ".rpyb"):
                if src.with_suffix(".rpy").exists() or name not in ("phone_main.rpyc", "phone_main (1).rpyc"):
                    continue
            if src.suffix in (".save", ".bak", ".tmp", ".psd", ".psb"):
                continue
            dst = game / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.suffix in (".rpy", ".rpym", ".py", ".rpyc"):
                if dst.exists() and os.path.samefile(src, dst):
                    dst.unlink()
                shutil.copy2(src, dst)
                copied += 1
            elif not dst.exists() or not os.path.samefile(src, dst):
                if dst.exists():
                    dst.unlink()
                try:
                    os.link(src, dst)
                    linked += 1
                except OSError:
                    shutil.copy2(src, dst)
                    copied += 1

    # Ren'Py scans game/saves as well as --savedir. Both must be isolated.
    (game / "zz_qf_test_environment.rpy").write_text(
        'init 999 python:\n'
        '    config.savedir = config.gamedir + "/saves"\n'
        '    config.label_overrides["splashscreen"] = "_qf_test_splash"\n'
        '    _preferences.physical_size = (1280, 720)\n'
        'label _qf_test_splash:\n'
        '    return\n', encoding="utf-8")
    sdk_python = args.sdk / "lib/py3-windows-x86_64/python.exe"
    command = [str(sdk_python), str(args.sdk / "renpy.py"), str(project),
               "test", args.case, "--savedir", str(saves),
               "--overwrite-screenshots", "--report-detailed"]
    print(f"Isolated project: {project}; {copied} copied, {linked} linked", flush=True)
    return subprocess.run(command, cwd=project).returncode


if __name__ == "__main__":
    sys.exit(main())
