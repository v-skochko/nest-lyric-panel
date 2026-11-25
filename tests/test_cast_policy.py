"""Tests for Cast zone timing and source arbitration without HA dependencies."""
import importlib.util
import sys
import unittest
from pathlib import Path

path = Path(__file__).parents[1] / 'custom_components/nest_lyric_panel/cast_policy.py'
spec = importlib.util.spec_from_file_location('cast_policy', path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class PolicyTest(unittest.TestCase):
    def test_idle_updates_do_not_schedule_closing(self):
        p = module.CastPolicy(('main',))
        p.update_source('main', False, 1)
        self.assertEqual(p.decision(500, True, True), 'idle')

    def test_retry_and_independent_sources(self):
        p = module.CastPolicy(('main', 'extra'))
        p.update_source('main', True, 0)
        self.assertEqual(p.decision(0, False, True), 'cast')
        p.attempted(0)
        self.assertEqual(p.decision(29, False, True), 'waiting_retry')
        self.assertEqual(p.decision(30, False, True), 'cast')
        p.update_source('extra', True, 31)
        p.update_source('main', True, 32)
        self.assertEqual(p.active_source, 'extra')
        p.update_source('extra', False, 33)
        self.assertEqual(p.active_source, 'main')
        self.assertEqual(p.decision(34, True, True), 'showing')
        self.assertEqual(p.decision(34, False, False), 'unavailable')

    def test_stop_only_owned_panel_and_resume(self):
        p = module.CastPolicy(('main',))
        p.update_source('main', True, 1)
        p.update_source('main', False, 10)
        self.assertEqual(p.decision(129, True, True), 'idle')
        self.assertEqual(p.decision(130, False, True), 'idle')
        self.assertEqual(p.decision(130, True, True), 'close')
        p.update_source('main', True, 131)
        self.assertEqual(p.decision(132, True, True), 'showing')

    def test_new_playback_starts_without_old_retry_delay(self):
        p = module.CastPolicy(('main',))
        p.update_source('main', True, 1)
        p.attempted(1)
        p.update_source('main', False, 2)
        p.update_source('main', True, 3)
        self.assertEqual(p.decision(3, False, True), 'cast')


if __name__ == '__main__':
    unittest.main()
