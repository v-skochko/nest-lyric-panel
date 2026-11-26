"""Zone configuration controls on the Home Assistant device page."""
from homeassistant.components.select import SelectEntity
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.const import EntityCategory, EVENT_STATE_CHANGED
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import entity_registry as er
from . import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    dashboards = hass.data.get(LOVELACE_DATA)
    for sub in entry.get_subentries_of_type('cast_zone'):
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
        async_add_entities([ZoneSelect(entry, sub, key, views) for key in ('primary_player','display','add_player','remove_player','dashboard_path','view_path')], config_subentry_id=sub.subentry_id)


class ZoneSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    def __init__(self, entry, sub, key, views):
        self.entry, self.sub, self.key, self.views = entry, sub, key, views
        self._attr_translation_key = key
        identifier = sub.data.get('legacy_entry_id', sub.subentry_id)
        self._attr_unique_id = f'{identifier}_{key}'
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)}, name=sub.title, manufacturer='Nest Lyric Panel', model='Cast zone')

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self.key in ('primary_player', 'display', 'add_player'):
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
        if self.key == 'remove_player':
            return ['—', *data.get('additional_players', [])]
        players = {s.entity_id for s in self.hass.states.async_all('media_player')}
        if self.key == 'display':
            registry = er.async_get(self.hass)
            players = {x for x in players if (entity := registry.async_get(x)) and entity.platform == 'cast'}
        if self.key in ('display', 'primary_player') and data.get(self.key):
            players.add(data[self.key])
        players = sorted(players)
        if self.key == 'add_player':
            return ['—', *[x for x in players if x not in [data.get('display'), data.get('primary_player'), *data.get('additional_players', [])]]]
        return players

    @property
    def current_option(self):
        if self.key in ('add_player', 'remove_player'):
            return '—'
        return self.sub.data.get(self.key)

    async def async_select_option(self, option):
        if option == '—':
            return
        data = dict(self.sub.data)
        if self.key == 'add_player':
            data['additional_players'] = [*data.get('additional_players', []), option]
        elif self.key == 'remove_player':
            data['additional_players'] = [x for x in data.get('additional_players', []) if x != option]
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
        if any(other.subentry_id != self.sub.subentry_id and other.data.get('display') == data['display'] for other in self.entry.get_subentries_of_type('cast_zone')):
            raise HomeAssistantError('Display already belongs to another zone')
        self.hass.config_entries.async_update_subentry(self.entry, self.sub, data=data, unique_id=data['display'])
