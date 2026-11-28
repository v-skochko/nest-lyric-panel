"""Per-zone Cast settings."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from . import DOMAIN
from .zones import zones, update_zone


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([MuteBeforeCast(entry, zone) for zone in zones(entry)])


class MuteBeforeCast(SwitchEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = 'mute_before_cast'
    _attr_icon = 'mdi:volume-mute'

    def __init__(self, entry, zone):
        self.entry, self.zone = entry, zone
        identifier = zone.data.get('legacy_entry_id', zone.subentry_id)
        self._attr_unique_id = f'{identifier}_mute_before_cast'
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)}, name=zone.title, manufacturer='Nest Lyric Panel', model='Cast zone')

    @property
    def is_on(self):
        return self.zone.data.get('mute_before_cast', True)

    async def async_turn_on(self, **kwargs):
        update_zone(self.hass, self.entry, self.zone.subentry_id, {**self.zone.data, 'mute_before_cast': True})

    async def async_turn_off(self, **kwargs):
        update_zone(self.hass, self.entry, self.zone.subentry_id, {**self.zone.data, 'mute_before_cast': False})
