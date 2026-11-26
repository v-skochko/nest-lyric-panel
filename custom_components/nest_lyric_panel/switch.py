"""Device-page control for a Cast zone."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from . import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    for sub in entry.get_subentries_of_type('cast_zone'):
        async_add_entities([ZoneEnabled(entry, sub)], config_subentry_id=sub.subentry_id)


class ZoneEnabled(SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = 'zone_enabled'
    _attr_entity_category = EntityCategory.CONFIG
    def __init__(self, entry, sub):
        self.entry, self.sub = entry, sub
        key = sub.data.get('legacy_entry_id', sub.subentry_id)
        self._attr_unique_id = f'{key}_enabled'
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, key)}, name=sub.title, manufacturer='Nest Lyric Panel', model='Cast zone')

    @property
    def is_on(self):
        return self.sub.data.get('enabled', True)

    async def async_turn_on(self, **kwargs):
        self._set_enabled(True)

    async def async_turn_off(self, **kwargs):
        self._set_enabled(False)

    def _set_enabled(self, value):
        data = {**self.sub.data, 'enabled': value}
        self.hass.config_entries.async_update_subentry(self.entry, self.sub, data=data)
