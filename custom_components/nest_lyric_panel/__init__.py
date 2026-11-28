"""Lyrics lookup and translation bridge for Music Plus."""
import asyncio
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)
DOMAIN = 'nest_lyric_panel'

if TYPE_CHECKING:
    from .cast_manager import CastZone


@dataclass
class PanelRuntimeData:
    """Objects owned by one loaded configuration entry."""

    zones: dict[str, 'CastZone'] = field(default_factory=dict)


PanelConfigEntry = ConfigEntry[PanelRuntimeData]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
from .lyrics import lrclib, is_english, lyrics_mode

@websocket_api.websocket_command({vol.Required('type'):'nest_lyric_panel/mode',vol.Required('status'):vol.In(['found','not_found']),vol.Optional('text',default=''):vol.All(str,vol.Length(max=50000)),vol.Optional('has_timed',default=False):bool,vol.Optional('track_duration',default=0):vol.All(vol.Coerce(float),vol.Range(min=0)),vol.Optional('lyrics_duration',default=0):vol.All(vol.Coerce(float),vol.Range(min=0))})
@websocket_api.async_response
async def mode(hass,connection,msg):
    settings=hass.data[DOMAIN]['settings']; connection.send_result(msg['id'],int(lyrics_mode(msg['status'],msg['text'],msg['has_timed'],msg['track_duration'],msg['lyrics_duration'],bool(settings.get('translation_url')),settings.get('sync_tolerance',2))))

@websocket_api.websocket_command({vol.Required('type'): 'nest_lyric_panel/settings'})
@websocket_api.async_response
async def card_settings(hass, connection, msg):
    """Expose only the settings needed by cards."""
    connection.send_result(msg['id'], {'sync_offset': hass.data[DOMAIN]['settings'].get('sync_offset')})

@websocket_api.websocket_command({vol.Required('type'):'nest_lyric_panel/lookup',vol.Required('artist'):vol.All(str,vol.Length(min=1,max=300)),vol.Required('title'):vol.All(str,vol.Length(min=1,max=300)),vol.Optional('album',default=''):vol.All(str,vol.Length(max=300)),vol.Optional('duration',default=0):vol.Coerce(float)})
@websocket_api.async_response
async def lookup(hass,connection,msg):
    artist,title,album=msg['artist'].strip(),msg['title'].strip(),msg['album'].strip();duration=max(0,msg['duration']);key=(artist,title,album,round(duration));cache=hass.data[DOMAIN]['cache'];entry=cache.get(key)
    if entry and time.monotonic()-entry[0]<hass.data[DOMAIN]['settings'].get('cache_minutes',60)*60:connection.send_result(msg['id'],entry[1]);return
    errors=[];result=None
    try:result=await lrclib(hass,artist,title,album,duration)
    except Exception as exc:errors.append('LRCLIB');_LOGGER.warning('LRCLIB lookup failed: %s',type(exc).__name__)
    if result:result={'plainLyrics':result.get('plainLyrics'),'syncedLyrics':result.get('syncedLyrics'),'duration':result.get('duration'),'source':'LRCLIB'}
    if result:result['status']='found'
    else:result={'status':'incomplete' if errors else 'not_found','failed_sources':errors}
    if not errors:
        if len(cache)>=128:cache.pop(next(iter(cache)))
        cache[key]=(time.monotonic(),result)
    connection.send_result(msg['id'],result)

@websocket_api.websocket_command({vol.Required('type'):'nest_lyric_panel/translate',vol.Required('text'):vol.All([str],vol.Length(min=1,max=4)),vol.Required('full_text'):vol.All(str,vol.Length(max=50000))})
@websocket_api.async_response
async def translate(hass,connection,msg):
    if not is_english(msg['full_text']):connection.send_result(msg['id'],{'status':'skipped','translatedText':[]});return
    url=hass.data[DOMAIN]['settings'].get('translation_url','')
    if not url:connection.send_result(msg['id'],{'status':'skipped','translatedText':[]});return
    try:
        shared=hass.data[DOMAIN]
        lock_key=(url,msg['full_text'])
        locks=shared['translation_locks']
        item=locks.setdefault(lock_key, [asyncio.Lock(), 0])
        item[1]+=1
        try:
          async with item[0]:
            cache=shared['translation_cache']; ttl=shared['settings'].get('cache_minutes',60)*60
            now=time.monotonic(); keys=[(url,msg['full_text'],line) for line in msg['text']]
            missing=list(dict.fromkeys(key for key in keys if key not in cache or now-cache[key][0]>=ttl))
            results={key:cache[key][1] for key in keys if key not in missing}
            if missing:
                session=async_get_clientsession(hass)
                async with asyncio.timeout(60):
                    async with session.post(url,json={'q':[key[2] for key in missing],'source':'en','target':'uk','format':'text'},allow_redirects=False) as resp:
                        resp.raise_for_status(); content=await resp.json(content_type=None)
                translated=content.get('translatedText') if isinstance(content,dict) else None
                if not isinstance(translated,list) or len(translated)!=len(missing) or not all(isinstance(x,str) for x in translated):raise ValueError('Invalid translation response')
                for key,value in zip(missing,translated):
                    if len(cache)>=4096:cache.pop(next(iter(cache)))
                    cache[key]=(time.monotonic(),value)
                    results[key]=value
            vals=[results[key] for key in keys]
        finally:
            item[1]-=1
            if not item[1]:locks.pop(lock_key,None)
        connection.send_result(msg['id'],{'status':'ok','translatedText':vals})
    except Exception as exc:
        _LOGGER.warning('Translation unavailable: %s',type(exc).__name__);connection.send_error(msg['id'],'translation_failed','Translation unavailable')

async def async_setup(hass:HomeAssistant,config):
    store = Store(hass, 1, 'nest_lyric_panel.shared_settings')
    saved = await store.async_load()
    hass.data[DOMAIN]={'cache':{},'translation_cache':{},'translation_locks':{},'settings':saved or {}, 'settings_store':store, 'settings_initialized': saved is not None}
    frontend=Path(__file__).parent/'frontend'
    await hass.http.async_register_static_paths([
        StaticPathConfig('/nest_lyric_panel/nest-lyric-editor.js',str(frontend/'nest-lyric-editor.js'),True),
        StaticPathConfig('/nest_lyric_panel/nest-lyric-panel.js',str(frontend/'nest-lyric-panel.js'),True),
        StaticPathConfig('/nest_lyric_panel/nest-lyric-display.js',str(frontend/'nest-lyric-display.js'),True),
    ])
    websocket_api.async_register_command(hass,card_settings)
    websocket_api.async_register_command(hass,lookup)
    websocket_api.async_register_command(hass,translate)
    websocket_api.async_register_command(hass,mode)
    return True

async def async_setup_entry(hass:HomeAssistant,entry:PanelConfigEntry):
    from .cast_manager import CastZone
    data = hass.data[DOMAIN]
    entry.runtime_data = PanelRuntimeData()
    if not data['settings_initialized']:
        legacy = next((item for item in hass.config_entries.async_entries(DOMAIN) if item.unique_id == DOMAIN), entry)
        data['settings'] = dict(legacy.options)
        data['settings_initialized'] = True
        await data['settings_store'].async_save(data['settings'])
    if entry.unique_id != DOMAIN:
        # Legacy zone entries are migrated only after the parent is ready.
        return True
    from .migration import flatten_zones
    from .zones import zones
    flatten_zones(hass, entry)
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    dashboards = hass.data.get(LOVELACE_DATA)
    for subentry in zones(entry):
        zone_config = dict(subentry.data)
        if dashboards:
            path = zone_config.get('dashboard_path')
            dashboard = dashboards.dashboards.get(path) or (dashboards.dashboards.get(None) if path == 'lovelace' else None)
            title = (dashboard.config or {}).get('title') if dashboard else None
            if title:
                zone_config['dashboard_title'] = title
        zone = CastZone(hass, zone_config)
        entry.runtime_data.zones[subentry.subentry_id] = zone
        zone.start()
    entry.async_on_unload(entry.add_update_listener(_reload_zones))
    await hass.config_entries.async_forward_entry_setups(entry, ['number', 'text', 'sensor', 'select', 'switch'])
    return True

async def _reload_zones(hass:HomeAssistant, entry:ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass:HomeAssistant,entry:PanelConfigEntry):
    if entry.unique_id != DOMAIN:
        return True
    if not await hass.config_entries.async_unload_platforms(entry, ['number', 'text', 'sensor', 'select', 'switch']):
        return False
    live_zones = entry.runtime_data.zones
    for zone in live_zones.values():
        zone.stop()
    live_zones.clear()
    return True


async def async_remove_config_entry_device(hass, entry, device_entry):
    """Remove a Cast zone when its device is removed in Home Assistant."""
    all_zones = dict(entry.data.get('zones', {}))
    for zone_id, data in all_zones.items():
        if (DOMAIN, data.get('legacy_entry_id', zone_id)) in device_entry.identifiers:
            del all_zones[zone_id]
            hass.config_entries.async_update_entry(entry, data={**entry.data, 'zones': all_zones})
            return True
    return False
