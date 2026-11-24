"""Set up Nest Lyric Panel."""
from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from . import DOMAIN


def _options_schema(options):
    return vol.Schema({
        vol.Optional("translation_url", default=options.get("translation_url", "")): str,
        vol.Optional("sync_tolerance", default=options.get("sync_tolerance", 2)): vol.All(vol.Coerce(float), vol.Range(min=0, max=60)),
        vol.Optional("cache_minutes", default=options.get("cache_minutes", 60)): vol.All(vol.Coerce(int), vol.Range(min=0, max=1440)),
    })


def _valid_url(url):
    if not url:
        return True
    try:
        parts = urlsplit(url)
        return parts.scheme in ("http", "https") and bool(parts.hostname) and not parts.username and not parts.password and not parts.fragment
    except ValueError:
        return False


class NestLyricPanelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Nest Lyric Panel", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NestLyricPanelOptionsFlow()


class NestLyricPanelOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input["translation_url"] = user_input["translation_url"].strip()
            if _valid_url(user_input["translation_url"]):
                return self.async_create_entry(title="", data=user_input)
            errors["translation_url"] = "invalid_url"
        return self.async_show_form(step_id="init", data_schema=_options_schema(user_input or self.config_entry.options), errors=errors)
