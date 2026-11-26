"""Set up Nest Lyric Panel."""
from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.exceptions import HomeAssistantError

from . import DOMAIN
from .zones import zones


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

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry):
        return {"cast_zone": CastZoneFlow}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NestLyricPanelOptionsFlow()


class CastZoneFlow(config_entries.ConfigSubentryFlow):
    def _dashboards(self):
        data = self.hass.data.get(LOVELACE_DATA)
        if not data:
            return {}
        return {path or "lovelace": item for path, item in data.dashboards.items() if path is not None or "lovelace" not in data.dashboards}

    async def async_step_user(self, user_input=None):
        return await self._zone_step("user", user_input)

    async def _zone_step(self, step, user_input):
        entry = self._get_reconfigure_subentry() if step == "reconfigure" else None
        dashboards = self._dashboards()
        choices = [selector.SelectOptionDict(value=path, label=(item.config or {}).get("title", path)) for path, item in dashboards.items()]
        schema = _zone_schema(choices)
        errors = {}
        if user_input is not None:
            if user_input["display"] in [user_input["primary_player"], *user_input.get("additional_players", [])]:
                errors["display"] = "source_is_display"
            elif any((not entry or other.subentry_id != entry.subentry_id) and other.data.get("display") == user_input["display"] for other in zones(self._get_entry())):
                errors["display"] = "display_in_use"
            else:
                self._zone_values = user_input
                self._zone_entry = entry
                return await self.async_step_view()
        suggested = user_input or (dict(entry.data) if entry else {})
        return self.async_show_form(step_id=step, data_schema=self.add_suggested_values_to_schema(schema, suggested), errors=errors)

    async def async_step_view(self, user_input=None):
        dashboard = self._dashboards().get(self._zone_values["dashboard_path"])
        try:
            config = await dashboard.async_load(False) if dashboard else {}
        except HomeAssistantError:
            config = {}
        views = {view.get("path"): view.get("title") or view.get("path") for view in config.get("views", []) if view.get("path")}
        if not views:
            return self.async_abort(reason="no_views")
        if user_input is not None:
            path = user_input["view_path"]
            if path not in views:
                return self.async_show_form(step_id="view", data_schema=_view_schema(views), errors={"base": "invalid_view"})
            values = {**self._zone_values, "view_path": path, "view_title": views[path]}
            if self._zone_entry:
                return self.async_update_and_abort(self._get_entry(), self._zone_entry, data_updates=values, title=values["name"], unique_id=values["display"])
            return self.async_create_entry(title=values["name"], data=values, unique_id=values["display"])
        return self.async_show_form(step_id="view", data_schema=self.add_suggested_values_to_schema(_view_schema(views), self._zone_entry.data if self._zone_entry else {}))



class NestLyricPanelOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        shared = self.hass.data[DOMAIN]
        if user_input is not None:
            user_input["translation_url"] = user_input["translation_url"].strip()
            if _valid_url(user_input["translation_url"]):
                shared["settings"] = dict(user_input)
                shared["cache"].clear()
                await shared["settings_store"].async_save(shared["settings"])
                self.hass.bus.async_fire("nest_lyric_panel_settings_changed")
                return self.async_create_entry(title="", data=user_input)
            errors["translation_url"] = "invalid_url"
        return self.async_show_form(step_id="init", data_schema=_options_schema(user_input or shared["settings"]), errors=errors)


def _zone_schema(dashboards):
    return vol.Schema({
        vol.Required("name"): str,
        vol.Required("primary_player"): selector.EntitySelector(selector.EntitySelectorConfig(domain="media_player")),
        vol.Optional("additional_players", default=[]): selector.EntitySelector(selector.EntitySelectorConfig(domain="media_player", multiple=True)),
        vol.Required("display"): selector.EntitySelector(selector.EntitySelectorConfig(domain="media_player", integration="cast")),
        vol.Required("dashboard_path"): selector.SelectSelector(selector.SelectSelectorConfig(options=dashboards, mode="dropdown")),
    })


def _view_schema(views):
    options = [selector.SelectOptionDict(value=path, label=title) for path, title in views.items()]
    return vol.Schema({vol.Required("view_path"): selector.SelectSelector(selector.SelectSelectorConfig(options=options, mode="dropdown"))})
