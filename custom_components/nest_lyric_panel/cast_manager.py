"""Lifecycle and Cast controls for configured zones."""
import asyncio
import logging
import time
from datetime import timedelta

from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from .cast_policy import CastPolicy

_LOGGER = logging.getLogger(__name__)
APP_ID = 'A078F6B0'


class CastZone:
    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.display = config['display']
        self.policy = CastPolicy(tuple(dict.fromkeys([config['primary_player'], *config.get('additional_players', [])])))
        self.lock = asyncio.Lock()
        self.unsubscribers = []
        self.status = 'idle'
        self.reason = 'waiting_for_playback'
        self.listeners = set()

    def start(self):
        now = time.monotonic()
        for entity in self.policy.sources:
            state = self.hass.states.get(entity)
            if state and state.state == 'playing':
                self.policy.update_source(entity, True, now)
        self.unsubscribers.append(async_track_state_change_event(self.hass, [*self.policy.sources, self.display], self.changed))
        self.unsubscribers.append(async_track_time_interval(self.hass, self.tick, timedelta(seconds=5)))
        self.hass.async_create_task(self.evaluate())

    def stop(self):
        self.config['enabled'] = False
        for unsubscribe in self.unsubscribers:
            unsubscribe()
        self.unsubscribers.clear()

    async def changed(self, event):
        entity = event.data['entity_id']
        if entity in self.policy.sources:
            state = event.data.get('new_state')
            self.policy.update_source(entity, bool(state and state.state == 'playing'), time.monotonic())
        await self.evaluate()
        self.notify()

    def notify(self):
        for listener in tuple(self.listeners):
            listener()

    async def tick(self, _now):
        await self.evaluate()
        self.notify()

    def owned(self, state):
        if not state or state.state != 'playing' or state.attributes.get('app_id') != APP_ID:
            return False
        title = str(state.attributes.get('media_title') or '')
        dashboard_title = self.config.get('dashboard_title')
        if dashboard_title:
            return title == f"{dashboard_title}: {self.config['view_title']}"
        return title.endswith(': ' + self.config['view_title'])

    async def evaluate(self):
        if not self.config.get('enabled', True) or self.lock.locked():
            return
        async with self.lock:
            state = self.hass.states.get(self.display)
            decision = self.policy.decision(time.monotonic(), self.owned(state), bool(state and state.state not in ('unknown', 'unavailable')))
            self.status = decision
            self.reason = {'idle':'waiting_for_playback','unavailable':'display_unavailable','cast':'starting_cast','waiting_retry':'waiting_to_retry','showing':'panel_showing','close':'closing_panel'}.get(decision, decision)
            if decision == 'cast':
                self.policy.attempted(time.monotonic())
                was_muted = state.attributes.get('is_volume_muted')
                muted_by_us = False
                try:
                    if self.config.get('mute_before_cast', True):
                        if was_muted is None:
                            self.status, self.reason = 'error', 'mute_unconfirmed'
                            return
                        if was_muted is False:
                            muted_by_us = True
                            await self.hass.services.async_call('media_player', 'volume_mute', {'entity_id': self.display, 'is_volume_muted': True}, blocking=True)
                            for _ in range(30):
                                current = self.hass.states.get(self.display)
                                if current and current.attributes.get('is_volume_muted') is True:
                                    break
                                await asyncio.sleep(0.1)
                            else:
                                self.status, self.reason = 'error', 'mute_unconfirmed'
                                return
                    if not self.config.get('enabled', True) or not self.policy.playing:
                        return
                    await self.hass.services.async_call('cast', 'show_lovelace_view', {'entity_id': self.display, 'dashboard_path': self.config['dashboard_path'], 'view_path': self.config['view_path']}, blocking=True)
                    await asyncio.sleep(3)
                    if self.owned(self.hass.states.get(self.display)):
                        self.status = 'showing'
                        self.reason = 'panel_showing'
                except Exception:
                    self.status = 'error'
                    self.reason = 'cast_request_failed'
                    _LOGGER.exception('Cast failed for zone %s', self.config['name'])
                finally:
                    current = self.hass.states.get(self.display)
                    if muted_by_us and current and current.attributes.get('is_volume_muted') is True:
                        try:
                            await self.hass.services.async_call('media_player', 'volume_mute', {'entity_id': self.display, 'is_volume_muted': False}, blocking=True)
                        except Exception:
                            _LOGGER.exception('Could not restore display mute state')
            elif decision == 'close':
                # Recheck immediately before stopping: never stop another app.
                if self.owned(self.hass.states.get(self.display)):
                    try:
                        await self.hass.services.async_call('media_player', 'turn_off', {'entity_id': self.display}, blocking=True)
                    except Exception:
                        self.status = 'error'
                        self.reason = 'close_failed'
                        _LOGGER.exception('Could not stop Cast zone %s', self.config['name'])
