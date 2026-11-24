"""Translation endpoint configuration entity."""
from homeassistant.components.text import TextEntity, TextMode
from homeassistant.exceptions import HomeAssistantError
from .config_flow import _valid_url
from .entity import SettingsEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([TranslationEndpoint(entry)])


class TranslationEndpoint(SettingsEntity, TextEntity):
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 255

    def __init__(self, entry):
        super().__init__(entry, "translation_url", "Адреса перекладача")

    @property
    def native_value(self):
        return self.entry.options.get(self.key, "")

    async def async_set_value(self, value):
        value = value.strip()
        if not _valid_url(value):
            raise HomeAssistantError("Invalid translation URL")
        self.update_option(value)
