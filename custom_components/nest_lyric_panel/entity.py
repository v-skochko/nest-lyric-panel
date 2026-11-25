"""Shared configuration entities for the integration's virtual device."""
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import callback
from homeassistant.const import EntityCategory
from . import DOMAIN


class SettingsEntity:
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry, key, name):
        self.entry = entry
        self.key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Nest Lyric Panel",
            manufacturer="Nest Lyric Panel", model="Lyrics service",
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.hass.bus.async_listen("nest_lyric_panel_settings_changed", self._settings_changed))

    @callback
    def _settings_changed(self, event):
        self.async_write_ha_state()

    async def update_option(self, value):
        shared = self.hass.data[DOMAIN]
        shared['settings'][self.key] = value
        shared['cache'].clear()
        await shared['settings_store'].async_save(shared['settings'])
        self.hass.bus.async_fire('nest_lyric_panel_settings_changed')
