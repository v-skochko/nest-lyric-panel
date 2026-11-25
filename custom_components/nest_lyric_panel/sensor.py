"""State and active player for a Cast zone."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from . import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    zone = hass.data[DOMAIN]['zones'].get(entry.entry_id)
    if zone:
        async_add_entities([ZoneSensor(entry, zone)])


class ZoneSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = 'Cast status'
    def __init__(self, entry, zone):
        self.zone = zone
        self._attr_unique_id = f'{entry.entry_id}_cast_status'
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.title, manufacturer='Nest Lyric Panel', model='Cast zone')

    @property
    def native_value(self):
        return self.zone.status if self.zone.config.get('enabled', True) else 'disabled'

    @property
    def extra_state_attributes(self):
        return {'active_player': self.zone.policy.active_source or self.zone.config['primary_player'], 'display': self.zone.display}

    async def async_added_to_hass(self):
        self.zone.listeners.add(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self.zone.listeners.discard(self.async_write_ha_state)
