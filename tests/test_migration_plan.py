"""Tests of the non-mutating migration planner."""
import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

path=Path(__file__).resolve().parents[1]/'custom_components/nest_lyric_panel/migration_plan.py'
spec=importlib.util.spec_from_file_location('migration_plan',path)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

class MigrationPlanTests(unittest.TestCase):
    def test_preserves_settings_and_disabled_state(self):
        entry=SimpleNamespace(entry_id='old-id',title='Kitchen',data={'display':'media_player.screen','enabled':True,'primary_player':'media_player.music'},disabled_by='user')
        zone=m.plan_legacy_zones([entry],[])[0]
        self.assertEqual(zone.data['legacy_entry_id'],'old-id')
        self.assertFalse(zone.data['enabled'])
        self.assertTrue(entry.data['enabled'])
    def test_duplicate_screen_refused(self):
        entry=SimpleNamespace(entry_id='old',title='TV',data={'display':'media_player.screen'},disabled_by=None)
        with self.assertRaises(ValueError):m.plan_legacy_zones([entry],['media_player.screen'])
if __name__=='__main__':unittest.main()
