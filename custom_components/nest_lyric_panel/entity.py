"""Shared configuration entities for the integration's virtual device."""
from homeassistant.helpers.entity import DeviceInfo
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
        self.async_on_remove(self.entry.add_update_listener(self._options_changed))

    async def _options_changed(self, hass, entry):
        self.async_write_ha_state()

    def update_option(self, value):
        options = dict(self.entry.options)
        options[self.key] = value
        self.hass.config_entries.async_update_entry(self.entry, options=options)
