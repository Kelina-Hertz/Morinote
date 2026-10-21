from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend.compiler import generate_project, label, line_label, renpy_text
from backend.migration import import_timeline
from backend.project import atomic_json, load_project, new_project, review_digest, safe_path, save_project, validate_project


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "source"
        self.doc = new_project(self.root, "测试", demo=True)

    def tearDown(self): self.tmp.cleanup()

    def test_new_project_not_overwritten(self):
        with self.assertRaises(ValueError): new_project(self.root, "other")
        self.assertEqual(load_project(self.root), self.doc)

    def test_revision_conflict_is_atomic(self):
        saved = save_project(self.root, self.doc, 1)
        self.assertEqual(saved["revision"], 2)
        with self.assertRaises(ValueError): save_project(self.root, self.doc, 1)
        self.assertEqual(load_project(self.root), saved)

    def test_draft_missing_allowed_but_compile_blocked(self):
        self.doc["assets"][0]["status"] = "missing"
        save_project(self.root, self.doc, 1)
        with self.assertRaisesRegex(ValueError, "待补"): generate_project(self.root, self.base / "build")

    def test_explicit_placeholder_generates_report(self):
        self.doc["assets"][0]["status"] = "placeholder"
        save_project(self.root, self.doc, 1)
        output = generate_project(self.root, self.base / "build")
        self.assertTrue(any(d["severity"] == "warning" for d in output["diagnostics"]))

    def test_split_boundaries_and_null_survive_save(self):
        self.doc["scenes"][0]["lines"][1]["visual"] = copy.deepcopy(self.doc["scenes"][0]["lines"][0]["visual"])
        saved = save_project(self.root, self.doc, 1)
        self.assertEqual(saved["scenes"][0]["lines"][0]["visual"], saved["scenes"][0]["lines"][1]["visual"])
        self.assertIsNone(saved["scenes"][0]["lines"][2]["visual"])

    def test_invalid_destination_rejected(self):
        self.doc["graphs"][0]["nodes"][0]["next"] = "absent"
        self.assertTrue(any("目标不存在" in d["message"] for d in validate_project(self.doc)))
        with self.assertRaises(ValueError): save_project(self.root, self.doc, 1)

    def test_containment_cycle_rejected_flow_cycle_allowed(self):
        self.doc["graphs"][0]["parent"] = "chapter1"
        self.assertTrue(any("包含关系" in d["message"] for d in validate_project(self.doc)))
        self.doc["graphs"][0]["parent"] = None
        self.doc["graphs"][0]["nodes"][1]["next"] = "chapter1"
        self.assertFalse(any(d["severity"] == "error" for d in validate_project(self.doc)))

    def test_text_literal_does_not_evaluate_tags_or_interpolation(self):
        value = renpy_text('[variable] {color=#fff} "quote"\nnext')
        self.assertIn("[[variable]", value)
        self.assertIn("{{color=", value)
        self.assertIn('\\"quote\\"', value)

    def test_compile_deterministic_and_source_mapped(self):
        output = self.base / "build"
        result = generate_project(self.root, output)
        script = (output / "game/generated/creator_story.rpy").read_bytes()
        generate_project(self.root, output)
        self.assertEqual(script, (output / "game/generated/creator_story.rpy").read_bytes())
        mapping = result["sourceMap"]["files"]["game/generated/creator_story.rpy"]
        self.assertTrue(any(value.get("line") == "chat_history" for value in mapping.values()))
        text = script.decode()
        self.assertIn("call cr_chapter1_meet", text)
        self.assertIn("creator_condition", text)
        self.assertIn("call screen creator_investigation", text)
        self.assertNotIn('creator_chat_character(\'系统\')', text)

    def test_assets_copied_and_extension_source_not_overwritten(self):
        extension = self.root / "extensions/custom.rpy"
        extension.write_text("# owned by author\n", encoding="utf-8")
        generate_project(self.root, self.base / "build")
        self.assertEqual(extension.read_text(), "# owned by author\n")
        self.assertTrue((self.base / "build/game/extensions/custom.rpy").exists())

    def test_entry_restores_prior_cues_without_prior_events(self):
        result = generate_project(self.root, self.base / "build", entry={"scene": "meet", "line": "meet_3", "state": {"trust": 8}}, preview=True)
        script = (Path(result["output"]) / "game/generated/creator_story.rpy").read_text(encoding="utf-8")
        start = script.split("label cr_main_chapter1:")[0]
        self.assertIn("creator_apply_visual", start)
        self.assertIn("call cr_line_meet_3", start)
        self.assertNotIn("creator_actions", start)

    def test_production_output_strips_bridge(self):
        output = self.base / "build"
        (output / "game").mkdir(parents=True)
        (output / "game/creator_bridge.rpy").write_text("# preview-only")
        generate_project(self.root, output)
        self.assertFalse((output / "game/creator_bridge.rpy").exists())
        self.assertFalse((output / "game/generated/creator_smoke.rpy").exists())

    def test_stage_wait_validates_event_and_compiles(self):
        self.doc["events"].append({"id": "done", "trigger": "signal", "target": "finished", "actions": [], "repeat": "always"})
        line = self.doc["scenes"][0]["lines"][0]
        line.update(kind="stage", duration=1, waitFor={"event": "done", "timeout": 3})
        save_project(self.root, self.doc, 1)
        result = generate_project(self.root, self.base / "build")
        script = (Path(result["output"]) / "game/generated/creator_story.rpy").read_text(encoding="utf-8")
        self.assertIn("call screen creator_stage_wait", script)
        line["waitFor"]["event"] = "unknown"
        self.assertTrue(any("等待的事件不存在" in d["message"] for d in validate_project(self.doc)))
        line["waitFor"] = {"event": "done", "timeout": -1}
        self.assertTrue(any("事件等待超时" in d["message"] for d in validate_project(self.doc)))
        line.update(kind="dialogue", waitFor={"event": "done"})
        self.assertTrue(any("只有纯演出" in d["message"] for d in validate_project(self.doc)))

    def test_approval_hash_invalidates_text_edits_not_revision(self):
        digest = review_digest(self.doc)
        self.doc["review"] = {"required": True, "confirmedHash": digest}
        self.doc["revision"] = 99
        self.assertEqual(review_digest(self.doc), digest)
        self.doc["scenes"][0]["lines"][0]["text"] += "变动"
        atomic_json(self.root / "project.json", self.doc)
        with self.assertRaisesRegex(ValueError, "确认"): generate_project(self.root, self.base / "build")

    def test_path_escape_rejected(self):
        for path in ("../outside.png", "C:/outside.png", "/tmp/outside.png"):
            with self.assertRaises(ValueError): safe_path(self.root, path)

    def test_unicode_labels_do_not_collide(self):
        self.assertNotEqual(line_label("中文"), line_label("汉字"))
        self.assertNotEqual(label("main", "line-1"), label("main", "line_1"))

    def test_generated_label_collision_is_reported(self):
        self.doc["graphs"].append({"id": "scene", "title": "冲突", "parent": None, "entry": "meet", "nodes": [{"id": "meet", "type": "end", "title": "冲突"}]})
        save_project(self.root, self.doc, 1)
        with self.assertRaisesRegex(ValueError, "标签重复"):
            generate_project(self.root, self.base / "build")

    def test_duplicate_lines_invalid(self):
        self.doc["scenes"][1]["lines"][0]["id"] = "meet_1"
        self.assertTrue(any("节点 ID" in d["message"] for d in validate_project(self.doc)))

    def test_migration_preserves_original_and_clicks(self):
        legacy = {"id": "legacy", "title": "原稿", "timeline_version": 2, "is_demo": True, "nodes": [{"id": "n1", "kind": "chat", "speaker": "甲", "text": "历史", "original": "[甲] 历史", "source_paragraph": 3, "advance": False, "visual": {"background": "bg", "sprites": [], "cg": "", "transition": "none"}, "audio": None, "auto_wait": None}, {"id": "n2", "kind": "chat", "speaker": "乙", "text": "现在", "visual": None, "audio": None, "auto_wait": 2}], "assets": [{"id": "bg", "kind": "scene", "name": "背景", "mapping": "bg.png", "status": "mapped"}]}
        source = self.base / "legacy.json"
        source.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
        game = self.base / "legacy-game"
        game.mkdir()
        (game / "bg.png").write_bytes(b"test image")
        before = source.read_bytes()
        migrated = import_timeline(self.base / "migrated", source, game)
        self.assertEqual(before, source.read_bytes())
        self.assertEqual(migrated["legacySource"], legacy)
        lines = migrated["scenes"][0]["lines"]
        self.assertFalse(lines[0]["advance"])
        self.assertIsNone(lines[1]["visual"])
        self.assertEqual(lines[1]["autoWait"], 2)
        self.assertEqual(lines[0]["source"]["source_paragraph"], 3)

    def test_real_chapter_migration_remains_unconfirmed(self):
        source = self.base / "real.json"
        source.write_text(json.dumps({"timeline_version": 2, "title": "真稿", "nodes": [], "assets": []}), encoding="utf-8")
        result = import_timeline(self.base / "imported-real", source, self.base)
        self.assertTrue(result["review"]["required"])
        self.assertIsNone(result["review"]["confirmedHash"])
        with self.assertRaisesRegex(ValueError, "确认"): generate_project(self.base / "imported-real", self.base / "build")


if __name__ == "__main__": unittest.main()
