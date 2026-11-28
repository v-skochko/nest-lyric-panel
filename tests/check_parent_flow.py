"""Exercise duplicate setup through Home Assistant's config entry manager."""
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from homeassistant import loader
from homeassistant.config_entries import SOURCE_USER, ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


class ParentFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_second_setup_keeps_original_entry(self):
        with tempfile.TemporaryDirectory() as config_dir:
            hass = HomeAssistant(config_dir)
            loader.async_setup(hass)
            hass.config_entries = ConfigEntries(hass, {})
            await hass.config_entries.async_initialize()
            domain = "nest_lyric_panel"
            flows = hass.config_entries.flow
            try:
                # Exercise entry creation and duplicate detection without starting HTTP or Cast.
                with (
                    patch("homeassistant.config_entries.async_process_deps_reqs"),
                    patch.object(ConfigEntries, "async_setup", new_callable=AsyncMock),
                ):
                    form = await flows.async_init(domain, context={"source": SOURCE_USER})
                    self.assertEqual(form["type"], FlowResultType.FORM)
                    created = await flows.async_configure(form["flow_id"], {})
                    self.assertEqual(created["type"], FlowResultType.CREATE_ENTRY)
                    original = created["result"]
                    self.assertEqual(original.unique_id, domain)

                    duplicate = await flows.async_init(domain, context={"source": SOURCE_USER})
                    self.assertEqual(duplicate["type"], FlowResultType.ABORT)
                    self.assertIn(duplicate["reason"], ("single_instance_allowed", "already_configured"))
                    self.assertEqual(hass.config_entries.async_entries(domain), [original])
            finally:
                await hass.async_stop(force=True)


if __name__ == "__main__":
    unittest.main()
