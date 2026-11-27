"""Numeric settings for Nest Lyric Panel."""
from homeassistant.components.number import NumberEntity, NumberMode
from .entity import SettingsEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([
        SettingsNumber(entry, "sync_offset", "Зміщення синхронізації", 0, -30, 30, 0.1, "s"),
        SettingsNumber(entry, "sync_tolerance", "Допустима різниця тривалості", 2, 0, 60, 0.5, "s"),
        SettingsNumber(entry, "cache_minutes", "Тривалість кешу лірики", 60, 0, 1440, 1, "min"),
    ])


class SettingsNumber(SettingsEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, key, name, default, minimum, maximum, step, unit):
        super().__init__(entry, key, name)
        self.default = default
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return self.hass.data["nest_lyric_panel"]["settings"].get(self.key, self.default)

    async def async_set_native_value(self, value):
        await self.update_option(int(value) if self.key == "cache_minutes" else float(value))
