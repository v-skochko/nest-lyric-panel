"""Configuration flow behavior with fake HA and real voluptuous."""
import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path

for name in ('fake_flow', 'homeassistant', 'homeassistant.config_entries', 'homeassistant.core', 'homeassistant.helpers', 'homeassistant.helpers.selector', 'homeassistant.components', 'homeassistant.components.lovelace', 'homeassistant.components.lovelace.const', 'homeassistant.exceptions'):
    sys.modules[name] = types.ModuleType(name)
sys.modules['fake_flow'].DOMAIN = 'nest_lyric_panel'
sys.modules['homeassistant.core'].callback = lambda fn: fn
sys.modules['homeassistant.components.lovelace.const'].LOVELACE_DATA = 'lovelace'
sys.modules['homeassistant.exceptions'].HomeAssistantError = Exception
class Flow:
    def __init_subclass__(cls, **kwargs): pass
    def _async_current_entries(self): return []
    async def async_set_unique_id(self, value): self.unique_id = value
    def _abort_if_unique_id_configured(self): pass
    def async_show_form(self, **kw): return {'type':'form', **kw}
    def async_abort(self, **kw): return {'type':'abort', **kw}
    def async_create_entry(self, **kw): return {'type':'create_entry', **kw}
    def add_suggested_values_to_schema(self, schema, values): return schema
class OptionsFlow: pass
sys.modules['homeassistant.config_entries'].ConfigFlow = Flow
sys.modules['homeassistant.config_entries'].OptionsFlow = OptionsFlow
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
    def setUp(self): self.f=mod.NestLyricPanelConfigFlow();self.f.hass=Hass()
    async def test_create_and_derive_title(self):
        data={'name':'Kitchen','primary_player':'media_player.a','additional_players':[],'display':'media_player.screen','dashboard_path':'lovelace','enabled':True}
        step=await self.f.async_step_user(data);self.assertEqual(step['step_id'],'view')
        result=await self.f.async_step_view({'view_path':'nest-hub'})
        self.assertEqual(result['data']['view_title'],'Nest Hub');self.assertEqual(result['title'],'Kitchen')
    async def test_missing_or_unknown_view_is_not_created(self):
        data={'name':'Kitchen','primary_player':'media_player.a','additional_players':[],'display':'media_player.screen','dashboard_path':'lovelace','enabled':True}
        await self.f.async_step_user(data)
        result=await self.f.async_step_view({'view_path':'missing'})
        self.assertEqual(result['errors']['base'],'invalid_view')

    async def test_reject_same_source_and_screen(self):
        data={'name':'Kitchen','primary_player':'media_player.a','additional_players':[],'display':'media_player.a','dashboard_path':'lovelace','enabled':True}
        result=await self.f.async_step_user(data);self.assertEqual(result['errors']['display'],'source_is_display')
if __name__=='__main__': unittest.main()
