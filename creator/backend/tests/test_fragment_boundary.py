from pathlib import Path
import textwrap
import unittest


class FragmentBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=Path(__file__).resolve().parents[1].joinpath('creator_native_preview.rpy').read_text('utf-8')
        start=source.index('    def _cn_fragment_should_stop(')
        end=source.index('    def _cn_finish_fragment(',start)
        namespace={}
        exec(textwrap.dedent(source[start:end]),namespace)
        cls.stop=staticmethod(namespace['_cn_fragment_should_stop'])

    def test_scene_boundary_stops_on_jump_or_fallthrough(self):
        self.assertTrue(self.stop('C1b3','C1b2',['_cn_fragment_return'],0,0,['C1b2']))

    def test_nested_call_and_other_context_do_not_end_parent(self):
        self.assertFalse(self.stop('phone','C1b2',['_cn_fragment_return','_call_phone'],0,0,[]))
        self.assertFalse(self.stop('phone','C1b2',['_cn_fragment_return'],1,0,[]))

    def test_local_labels_return_sites_and_self_loops_remain_in_scene(self):
        for label in ('C1b2','C1b2.branch','_call_phone'):
            self.assertFalse(self.stop(label,'C1b2',['_cn_fragment_return'],0,0,['_call_phone']))
        self.assertTrue(self.stop('C1b20','C1b2',['_cn_fragment_return'],0,0,[]))

    def test_no_fragment_frame_and_editor_labels_are_not_boundaries(self):
        self.assertFalse(self.stop('other','C1b2',[],0,0,[]))
        self.assertFalse(self.stop('_cn_fragment_return','C1b2',['_cn_fragment_return'],0,0,[]))
