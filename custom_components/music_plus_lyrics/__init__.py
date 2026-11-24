"""Lyrics lookup and translation bridge for Music Plus."""
import asyncio
import json
import logging
import re
import time
import unicodedata
from enum import IntEnum
from pathlib import Path
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
DOMAIN = 'music_plus_lyrics'
HEADERS = {'User-Agent': 'MusicPlusLyrics/0.1 (https://github.com/v-skochko/music-plus-lyrics)', 'Accept': 'application/json,text/html'}

def normalize(value):
    value = unicodedata.normalize('NFKC', value or '').casefold()
    return ' '.join(re.findall(r'[^\W_]+', value, re.UNICODE))

async def fetch(hass,url,params=None):
    session=async_get_clientsession(hass)
    async with asyncio.timeout(10):
        async with session.get(url,params=params,headers=HEADERS,allow_redirects=True) as resp:
            if resp.status==404:return None
            resp.raise_for_status()
            return await resp.text()

async def lrclib(hass,artist,title,album,duration):
    q={'artist_name':artist,'track_name':title}
    if album:q['album_name']=album
    if duration:q['duration']=round(duration)
    if album and duration:
        body=await fetch(hass,'https://lrclib.net/api/get',q)
        if body:
            obj=json.loads(body)
            if obj.get('syncedLyrics') or obj.get('plainLyrics'):return obj
    body=await fetch(hass,'https://lrclib.net/api/search',{'artist_name':artist,'track_name':title})
    results=json.loads(body) if body else []
    exact=[x for x in results if normalize(x.get('artistName'))==normalize(artist) and normalize(x.get('trackName'))==normalize(title) and (x.get('syncedLyrics') or x.get('plainLyrics'))]
    def rank(x):
        d=x.get('duration'); diff=abs(float(d)-duration) if duration and isinstance(d,(int,float)) and d>0 else float('inf')
        return (diff>2,not bool(x.get('syncedLyrics')),diff)
    return min(exact,key=rank) if exact else None

def is_english(text):
    return bool(re.search('[A-Za-z]',text)) and not any(unicodedata.category(c).startswith(('L','M')) and not ('a'<=c.lower()<='z') for c in text)

class LyricsMode(IntEnum):
    NOT_FOUND = 0
    SYNCED_TRANSLATED = 1
    SYNCED_ORIGINAL = 2
    UNSYNCED_TRANSLATED = 3
    UNSYNCED_ORIGINAL = 4

def lyrics_mode(status, text, has_timed, track_duration, lyrics_duration, translation_enabled=True, sync_tolerance=2):
    """Derive one consistent mode for a particular track, without shared mutable state."""
    if status == 'not_found':
        return LyricsMode.NOT_FOUND
    synced = bool(has_timed and track_duration > 0 and lyrics_duration > 0 and abs(track_duration - lyrics_duration) <= sync_tolerance)
    if translation_enabled and is_english(text):
        return LyricsMode.SYNCED_TRANSLATED if synced else LyricsMode.UNSYNCED_TRANSLATED
    return LyricsMode.SYNCED_ORIGINAL if synced else LyricsMode.UNSYNCED_ORIGINAL

@websocket_api.websocket_command({vol.Required('type'):'music_plus_lyrics/mode',vol.Required('status'):vol.In(['found','not_found']),vol.Optional('text',default=''):vol.All(str,vol.Length(max=50000)),vol.Optional('has_timed',default=False):bool,vol.Optional('track_duration',default=0):vol.All(vol.Coerce(float),vol.Range(min=0)),vol.Optional('lyrics_duration',default=0):vol.All(vol.Coerce(float),vol.Range(min=0))})
@websocket_api.async_response
async def mode(hass,connection,msg):
    settings=hass.data[DOMAIN]['settings']; connection.send_result(msg['id'],int(lyrics_mode(msg['status'],msg['text'],msg['has_timed'],msg['track_duration'],msg['lyrics_duration'],bool(settings.get('translation_url')),settings.get('sync_tolerance',2))))

@websocket_api.websocket_command({vol.Required('type'):'music_plus_lyrics/lookup',vol.Required('artist'):vol.All(str,vol.Length(min=1,max=300)),vol.Required('title'):vol.All(str,vol.Length(min=1,max=300)),vol.Optional('album',default=''):vol.All(str,vol.Length(max=300)),vol.Optional('duration',default=0):vol.Coerce(float)})
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

@websocket_api.websocket_command({vol.Required('type'):'music_plus_lyrics/translate',vol.Required('text'):vol.All([str],vol.Length(min=1,max=4)),vol.Required('full_text'):vol.All(str,vol.Length(max=50000))})
@websocket_api.async_response
async def translate(hass,connection,msg):
    if not is_english(msg['full_text']):connection.send_result(msg['id'],{'status':'skipped','translatedText':[]});return
    url=hass.data[DOMAIN]['settings'].get('translation_url','')
    if not url:connection.send_result(msg['id'],{'status':'skipped','translatedText':[]});return
    try:
        session=async_get_clientsession(hass)
        async with asyncio.timeout(60):
            async with session.post(url,json={'q':msg['text'],'source':'en','target':'uk','format':'text'},allow_redirects=False) as resp:
                resp.raise_for_status(); content=await resp.json(content_type=None)
        vals=content.get('translatedText') if isinstance(content,dict) else None
        if not isinstance(vals,list) or len(vals)!=len(msg['text']) or not all(isinstance(x,str) for x in vals):raise ValueError('Invalid translation response')
        connection.send_result(msg['id'],{'status':'ok','translatedText':vals})
    except Exception as exc:
        _LOGGER.warning('Translation unavailable: %s',type(exc).__name__);connection.send_error(msg['id'],'translation_failed','Translation unavailable')

async def async_setup(hass:HomeAssistant,config):
    hass.data[DOMAIN]={'cache':{},'settings':{}}
    await hass.http.async_register_static_paths([StaticPathConfig('/music_plus_lyrics/music-plus-lyrics.js',str(Path(__file__).parent/'frontend'/'music-plus-lyrics.js'),True)])
    websocket_api.async_register_command(hass,lookup)
    websocket_api.async_register_command(hass,translate)
    websocket_api.async_register_command(hass,mode)
    return True

async def async_setup_entry(hass:HomeAssistant,entry:ConfigEntry):
    hass.data[DOMAIN]['settings']=dict(entry.options)
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True

async def _options_updated(hass:HomeAssistant,entry:ConfigEntry):
    hass.data[DOMAIN]['settings']=dict(entry.options)
    hass.data[DOMAIN]['cache'].clear()

async def async_unload_entry(hass:HomeAssistant,entry:ConfigEntry):
    hass.data[DOMAIN]['settings']={}
    hass.data[DOMAIN]['cache'].clear()
    return True
