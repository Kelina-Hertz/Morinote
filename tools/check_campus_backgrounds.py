"""Verify campus PNGs, source photographs, hashes, and Demo registrations offline."""
import hashlib
import json
from pathlib import Path
import re

from PIL import Image


def main():
    repo = Path(__file__).resolve().parents[1]
    assets = repo / "game/gui/scene/campus"
    manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
    errors = []
    items = manifest["items"]
    by_id = {item["id"]: item for item in items}
    if len(items) != 90 or len(by_id) != 90:
        errors.append("Expected 90 unique manifest items")
    if {p.name for p in assets.glob("*.png")} != {i["file"] for i in items}:
        errors.append("PNG directory differs from manifest")
    for item in items:
        try:
            path = assets / item["file"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError("Generated PNG hash mismatch")
            if path.stat().st_size != item["bytes"]:
                raise ValueError("Generated PNG byte count mismatch")
            with Image.open(path) as image:
                image.load()
                if image.format != "PNG" or image.size != (2048, 1152):
                    raise ValueError("Expected a decoded 2048x1152 PNG")
            source = repo / manifest["source_directory"] / item["source_photo"]
            if hashlib.sha256(source.read_bytes()).hexdigest() != item["source_sha256"]:
                raise ValueError("Original photograph hash mismatch or LFS not downloaded")
        except Exception as exc:
            errors.append(f"{item['id']}: {exc}")
    settings = (repo / "game/settings.rpy").read_text(encoding="utf-8")
    replacements = manifest["demo_replacements"]
    if len(replacements) != 13 or len({i["tag"] for i in replacements}) != 13:
        errors.append("Expected 13 unique Demo replacements")
    for replacement in replacements:
        tag = replacement["tag"]
        if replacement["file"] != by_id[replacement["id"]]["file"]:
            errors.append(f"{tag}: mapping differs from source manifest")
        expected = (f'image {tag} = Transform("gui/scene/campus/{replacement["file"]}", '
                    'xysize=(1920, 1080))')
        if expected not in settings or len(re.findall(rf"^image {re.escape(tag)}[=: ]", settings, re.M)) != 1:
            errors.append(f"{tag}: missing, cropped, or duplicate image registration")
    for name in ("qingfeng_ui.rpy", "ova.rpy"):
        text = (repo / "game" / name).read_text(encoding="utf-8")
        if 'add "room1"' not in text or 'add "gui/scene/classroom1.png"' in text:
            errors.append(f"{name}: novel backdrop bypasses room1")
    print(json.dumps({"images": len(items), "replacements": len(replacements),
                      "bytes": sum(i["bytes"] for i in items), "errors": errors}, ensure_ascii=True))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
