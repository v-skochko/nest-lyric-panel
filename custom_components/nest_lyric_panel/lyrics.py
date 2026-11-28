"""Lyrics lookup, language detection and track mode."""
import asyncio
import json
import re
import unicodedata
from enum import IntEnum
from homeassistant.helpers.aiohttp_client import async_get_clientsession

HEADERS = {'User-Agent': 'NestLyricPanel/0.1 (https://github.com/v-skochko/nest-lyric-panel)', 'Accept': 'application/json,text/html'}

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

