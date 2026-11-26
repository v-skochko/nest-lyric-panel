"""Zone configuration controls on the Home Assistant device page."""
from homeassistant.components.select import SelectEntity
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.const import EntityCategory, EVENT_STATE_CHANGED
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import entity_registry as er
from . import DOMAIN
from .zones import zones, update_zone


async def async_setup_entry(hass, entry, async_add_entities):
    dashboards = hass.data.get(LOVELACE_DATA)
    views = {}
    if dashboards:
        for path, dashboard in dashboards.dashboards.items():
            key = path or 'lovelace'
            if path is None and 'lovelace' in dashboards.dashboards:
                continue
            try:
                config = await dashboard.async_load(False)
            except HomeAssistantError:
                continue
            views[key] = {v['path']: v.get('title') or v['path'] for v in config.get('views', []) if v.get('path')}
    for sub in zones(entry):
        keys = ['primary_player', 'display', 'dashboard_path', 'view_path']
        keys.extend(('additional_player_1', 'additional_player_2'))
        async_add_entities([ZoneSelect(entry, sub, key, views) for key in keys])


class ZoneSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    def __init__(self, entry, sub, key, views):
        self.entry, self.sub, self.key, self.views = entry, sub, key, views
        self.slot = int(key.rsplit('_', 1)[1]) - 1 if key.startswith('additional_player_') else None
        self._attr_translation_key = 'additional_player' if self.slot is not None else key
        if self.slot is not None:
            self._attr_translation_placeholders = {'number': str(self.slot + 1), 'order': str(self.slot + 3)}
        identifier = sub.data.get('legacy_entry_id', sub.subentry_id)
        self._attr_unique_id = f'{identifier}_{key}'
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)}, name=sub.title, manufacturer='Nest Lyric Panel', model='Cast zone')

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self.key in ('primary_player', 'display') or self.slot is not None:
            self.async_on_remove(self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._players_changed))

    @callback
    def _players_changed(self, event):
        if event.data.get('entity_id', '').startswith('media_player.') and (event.data.get('old_state') is None or event.data.get('new_state') is None):
            self.async_write_ha_state()

    @property
    def options(self):
        data = self.sub.data
        if self.key == 'dashboard_path':
            return sorted(self.views)
        if self.key == 'view_path':
            return sorted(self.views.get(data.get('dashboard_path'), {}))
        players = {s.entity_id for s in self.hass.states.async_all('media_player')}
        if self.key == 'display':
            registry = er.async_get(self.hass)
            players = {x for x in players if (entity := registry.async_get(x)) and entity.platform == 'cast'}
        current = self.current_option
        if current and current != '—':
            players.add(current)
        if self.slot is not None:
            slots = data.get('additional_player_slots', data.get('additional_players', [])[:2])
            others = [v for i, v in enumerate(slots) if i != self.slot and v]
            others += data.get('additional_player_overflow', data.get('additional_players', [])[2:])
            players -= set([data.get('display'), data.get('primary_player'), *others])
            return ['—', *sorted(players)]
        return sorted(players)

    @property
    def current_option(self):
        if self.slot is not None:
            players = self.sub.data.get('additional_player_slots', self.sub.data.get('additional_players', [])[:2])
            return (players[self.slot] or '—') if self.slot < len(players) else '—'
        return self.sub.data.get(self.key)

    async def async_select_option(self, option):
        data = dict(self.sub.data)
        if self.slot is not None:
            old_players = data.get('additional_players', [])
            overflow = data.get('additional_player_overflow', old_players[2:])
            players = list(data.get('additional_player_slots', old_players[:2]))
            players = (players + [None, None])[:2]
            players[self.slot] = None if option == '—' else option
            data['additional_player_slots'] = players
            data['additional_player_overflow'] = overflow
            data['additional_players'] = [p for p in players if p] + overflow
        elif self.key == 'dashboard_path':
            available = self.views.get(option, {})
            if not available:
                raise HomeAssistantError('Dashboard has no selectable views')
            data.update(dashboard_path=option, view_path=next(iter(available)), view_title=next(iter(available.values())))
        elif self.key == 'view_path':
            data.update(view_path=option, view_title=self.views[data['dashboard_path']][option])
        else:
            data[self.key] = option
        if data['display'] in [data['primary_player'], *data.get('additional_players', [])]:
            raise HomeAssistantError('Display and source must be different entities')
        if data['primary_player'] in data.get('additional_players', []):
            raise HomeAssistantError('Primary player cannot also be an additional player')
        if any(other.subentry_id != self.sub.subentry_id and other.data.get('display') == data['display'] for other in zones(self.entry)):
            raise HomeAssistantError('Display already belongs to another zone')
        update_zone(self.hass, self.entry, self.sub.subentry_id, data)
