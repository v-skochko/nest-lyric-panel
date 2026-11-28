"""Configuration flow behavior with fake HA and real voluptuous."""
import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path

for name in ('fake_flow', 'fake_flow.zones', 'homeassistant', 'homeassistant.config_entries', 'homeassistant.core', 'homeassistant.helpers', 'homeassistant.helpers.selector', 'homeassistant.components', 'homeassistant.components.lovelace', 'homeassistant.components.lovelace.const', 'homeassistant.exceptions'):
    sys.modules[name] = types.ModuleType(name)
sys.modules['fake_flow'].DOMAIN = 'nest_lyric_panel'
sys.modules['fake_flow.zones'].zones = lambda entry: []
sys.modules['homeassistant.core'].callback = lambda fn: fn
sys.modules['homeassistant.components.lovelace.const'].LOVELACE_DATA = 'lovelace'
sys.modules['homeassistant.exceptions'].HomeAssistantError = Exception
class Flow:
    def __init_subclass__(cls, **kwargs): pass
    def _get_entry(self): return types.SimpleNamespace(subentries={})
    async def async_set_unique_id(self, value): self.unique_id = value
    def _abort_if_unique_id_configured(self): pass
    def async_show_form(self, **kw): return {'type':'form', **kw}
    def async_abort(self, **kw): return {'type':'abort', **kw}
    def async_create_entry(self, **kw): return {'type':'create_entry', **kw}
    def add_suggested_values_to_schema(self, schema, values): return schema
class OptionsFlow(Flow): pass
sys.modules['homeassistant.config_entries'].ConfigFlow = Flow
sys.modules['homeassistant.config_entries'].OptionsFlow = OptionsFlow
sys.modules['homeassistant.config_entries'].ConfigSubentryFlow = Flow
sel=sys.modules['homeassistant.helpers.selector']
sel.EntitySelectorConfig=lambda **kw:kw
sel.SelectSelectorConfig=lambda **kw:kw
sel.SelectOptionDict=lambda **kw:kw
sel.EntitySelector=lambda config: str if not config.get('multiple') else list
sel.SelectSelector=lambda config: str
spec=importlib.util.spec_from_file_location('fake_flow.config_flow', Path(__file__).resolve().parents[1]/'custom_components/nest_lyric_panel/config_flow.py')
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
class Dashboard:
    config={'title':'Home'}
    async def async_load(self, force): return {'views':[{'path':'nest-hub','title':'Nest Hub'}]}
class Hass:
    data={'lovelace':types.SimpleNamespace(dashboards={'lovelace':Dashboard()})}

class FlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self): self.f=mod.CastZoneFlow();self.f.hass=Hass()
    async def test_initial_zone_form(self):
        self.assertEqual((await self.f.async_step_user())['type'], 'form')

    async def test_create_and_derive_title(self):
        data={'name':'Kitchen','primary_player':'media_player.a','additional_players':[],'display':'media_player.screen','dashboard_path':'lovelace','enabled':True}
        step=await self.f.async_step_user(data);self.assertEqual(step['step_id'],'view')
        result=await self.f.async_step_view({'view_path':'nest-hub'})
        self.assertEqual(result['data']['view_title'],'Nest Hub');self.assertEqual(result['title'],'Kitchen')
    async def test_fixed_slots_keep_second_when_first_is_empty(self):
        data={'name':'TV','primary_player':'media_player.a','additional_player_2':'media_player.b','display':'media_player.screen','dashboard_path':'lovelace'}
        await self.f.async_step_user(data)
        result=await self.f.async_step_view({'view_path':'nest-hub'})
        self.assertEqual(result['data']['additional_player_slots'], [None, 'media_player.b'])
        self.assertEqual(result['data']['additional_players'], ['media_player.b'])

    async def test_reject_duplicate_sources(self):
        data={'name':'TV','primary_player':'media_player.a','additional_player_1':'media_player.a','display':'media_player.screen','dashboard_path':'lovelace'}
        result=await self.f.async_step_user(data)
        self.assertEqual(result['errors']['base'], 'duplicate_player')
        data['additional_player_1'] = 'media_player.b'
        self.assertEqual((await self.f.async_step_user(data))['step_id'], 'view')
        self.assertEqual((await self.f.async_step_view({'view_path': 'nest-hub'}))['type'], 'create_entry')

    async def test_missing_or_unknown_view_is_not_created(self):
        data={'name':'Kitchen','primary_player':'media_player.a','additional_players':[],'display':'media_player.screen','dashboard_path':'lovelace','enabled':True}
        await self.f.async_step_user(data)
        result=await self.f.async_step_view({'view_path':'missing'})
        self.assertEqual(result['errors']['base'],'invalid_view')
        self.assertEqual((await self.f.async_step_view({'view_path':'nest-hub'}))['type'], 'create_entry')

    async def test_reject_same_source_and_screen(self):
        data={'name':'Kitchen','primary_player':'media_player.a','additional_players':[],'display':'media_player.a','dashboard_path':'lovelace','enabled':True}
        result=await self.f.async_step_user(data);self.assertEqual(result['errors']['display'],'source_is_display')
        data['display'] = 'media_player.screen'
        self.assertEqual((await self.f.async_step_user(data))['step_id'], 'view')
        self.assertEqual((await self.f.async_step_view({'view_path':'nest-hub'}))['type'], 'create_entry')
class MainFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_parent_flow_and_hooks(self):
        flow = mod.NestLyricPanelConfigFlow()
        self.assertEqual((await flow.async_step_user())['type'], 'form')
        result = await flow.async_step_user({})
        self.assertEqual(result['type'], 'create_entry')
        self.assertEqual(flow.unique_id, 'nest_lyric_panel')
        self.assertEqual(result['data'], {})
        self.assertEqual(flow.async_get_supported_subentry_types(None)['cast_zone'], mod.CastZoneFlow)
        self.assertIsInstance(flow.async_get_options_flow(None), mod.NestLyricPanelOptionsFlow)

    async def test_existing_entry_is_rejected(self):
        flow = mod.NestLyricPanelConfigFlow()
        def abort(): raise RuntimeError('already_configured')
        flow._abort_if_unique_id_configured = abort
        with self.assertRaisesRegex(RuntimeError, 'already_configured'):
            await flow.async_step_user({})

    async def test_zone_missing_views_and_duplicate_display(self):
        flow = mod.CastZoneFlow(); flow.hass = Hass()
        data = {'name':'Zone', 'primary_player':'media_player.a', 'display':'media_player.screen', 'dashboard_path':'lovelace'}
        previous = mod.zones
        try:
            mod.zones = lambda entry: [types.SimpleNamespace(data={'display':'media_player.screen'})]
            self.assertEqual((await flow.async_step_user(data))['errors']['display'], 'display_in_use')
            mod.zones = lambda entry: []
            self.assertEqual((await flow.async_step_user(data))['step_id'], 'view')
            self.assertEqual((await flow.async_step_view({'view_path':'nest-hub'}))['type'], 'create_entry')
            flow.hass = types.SimpleNamespace(data={})
            self.assertEqual((await flow.async_step_user(data))['reason'], 'no_views')
            class BrokenDashboard:
                config = {}
                async def async_load(self, force): raise Exception('failed')
            flow.hass = types.SimpleNamespace(data={'lovelace':types.SimpleNamespace(dashboards={'lovelace':BrokenDashboard()})})
            self.assertEqual((await flow.async_step_user(data))['reason'], 'no_views')
        finally:
            mod.zones = previous

    async def test_options_validation_and_recovery(self):
        class Store:
            async def async_save(self, data): self.saved = dict(data)
        class Bus:
            def async_fire(self, name): self.name = name
        store, bus = Store(), Bus()
        shared = {'settings':{}, 'cache':{'x':1}, 'translation_cache':{'x':1}, 'settings_store':store}
        flow = mod.NestLyricPanelOptionsFlow(); flow.hass = types.SimpleNamespace(data={'nest_lyric_panel':shared}, bus=bus)
        self.assertEqual((await flow.async_step_init())['type'], 'form')
        data = {'translation_url':'not a url', 'sync_offset':0, 'sync_tolerance':2, 'cache_minutes':60}
        self.assertEqual((await flow.async_step_init(data))['errors']['translation_url'], 'invalid_url')
        data['translation_url'] = ' https://example.com/translate '
        self.assertEqual((await flow.async_step_init(data))['type'], 'create_entry')
        self.assertEqual(store.saved['translation_url'], 'https://example.com/translate')
        self.assertEqual(shared['cache'], {})
        self.assertEqual(shared['translation_cache'], {})
        self.assertEqual(bus.name, 'nest_lyric_panel_settings_changed')

    def test_url_validation(self):
        for url in ('', 'http://example.com', 'https://example.com/path'):
            self.assertTrue(mod._valid_url(url), url)
        for url in ('ftp://example.com', 'http://user:pass@example.com', 'http://example.com/#fragment', 'http://[bad'):
            self.assertFalse(mod._valid_url(url), url)


if __name__=='__main__': unittest.main()
