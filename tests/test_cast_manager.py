"""Exercise Cast orchestration using a fake Home Assistant service registry."""
import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'custom_components/nest_lyric_panel'
for name in ('homeassistant', 'homeassistant.helpers', 'homeassistant.helpers.event', 'fake_nlp'):
    sys.modules[name] = types.ModuleType(name)
sys.modules['fake_nlp'].__path__ = [str(root)]
events = sys.modules['homeassistant.helpers.event']
events.async_track_state_change_event = lambda *args: lambda: None
events.async_track_time_interval = lambda *args: lambda: None
spec = importlib.util.spec_from_file_location('fake_nlp.cast_policy', root / 'cast_policy.py')
policy = importlib.util.module_from_spec(spec); sys.modules[spec.name] = policy; spec.loader.exec_module(policy)
spec = importlib.util.spec_from_file_location('fake_nlp.cast_manager', root / 'cast_manager.py')
manager = importlib.util.module_from_spec(spec); sys.modules[spec.name] = manager; spec.loader.exec_module(manager)

class States:
    def __init__(self): self.values = {}
    def get(self, key): return self.values.get(key)
class State:
    def __init__(self, state, **attrs): self.state = state; self.attributes = attrs
class Services:
    def __init__(self, states): self.calls = []; self.states = states
    async def async_call(self, domain, service, data, blocking=True):
        self.calls.append((domain, service, dict(data)))
        if service == 'volume_mute': self.states.get(data['entity_id']).attributes['is_volume_muted'] = data['is_volume_muted']
class Hass:
    def __init__(self): self.states = States(); self.services = Services(self.states)

class CastTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.h = Hass()
        self.h.states.values['screen'] = State('idle', is_volume_muted=False)
        self.z = manager.CastZone(self.h, {'name':'Kitchen', 'display':'screen', 'primary_player':'music', 'dashboard_path':'lovelace', 'view_path':'nest', 'view_title':'Nest'})

    async def test_cast_and_restore_mute(self):
        self.z.policy.update_source('music', True, 1)
        original = manager.asyncio.sleep
        async def no_sleep(_): pass
        manager.asyncio.sleep = no_sleep
        try: await self.z.evaluate()
        finally: manager.asyncio.sleep = original
        self.assertEqual([(x[0],x[1]) for x in self.h.services.calls], [('media_player','volume_mute'), ('cast','show_lovelace_view'), ('media_player','volume_mute')])
        self.assertFalse(self.h.states.get('screen').attributes['is_volume_muted'])

    async def test_unavailable_source_stops_being_active(self):
        self.z.policy.update_source('music', True, 1)
        event = types.SimpleNamespace(data={'entity_id':'music', 'new_state':State('unavailable')})
        await self.z.changed(event)
        self.assertIsNone(self.z.policy.active_source)
        self.assertIsNotNone(self.z.policy.stopped_at)

    async def test_never_closes_other_app(self):
        self.h.states.values['screen'] = State('playing', app_id='other', media_title='Video')
        self.z.policy.update_source('music', True, 1); self.z.policy.update_source('music', False, 2)
        self.z.policy.stopped_at = manager.time.monotonic() - 121
        await self.z.evaluate()
        self.assertEqual(self.h.services.calls, [])

    async def test_close_only_owned_view(self):
        self.h.states.values['screen'] = State('playing', app_id=manager.APP_ID, media_title='Home Assistant: Nest')
        self.z.policy.update_source('music', True, 1); self.z.policy.update_source('music', False, 2)
        self.z.policy.stopped_at = manager.time.monotonic() - 121
        await self.z.evaluate()
        self.assertEqual(self.h.services.calls[0][1], 'turn_off')

if __name__ == '__main__': unittest.main()
