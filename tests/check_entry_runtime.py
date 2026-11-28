"""Run against real Home Assistant libraries in an isolated Python process."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.sensor import SensorEntity
from custom_components.nest_lyric_panel import DOMAIN, async_setup_entry, async_unload_entry
from custom_components.nest_lyric_panel.sensor import ZoneSensor


async def main():
    zone_config = {'display': 'media_player.screen', 'primary_player': 'media_player.music'}
    item = SimpleNamespace(subentry_id='zone-1', data=zone_config, title='Kitchen')
    zone = MagicMock()
    zone.listeners = set()
    hass = SimpleNamespace(
        data={DOMAIN: {'settings_initialized': True}},
        config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock(), async_unload_platforms=AsyncMock(return_value=True)),
    )
    entry = SimpleNamespace(unique_id=DOMAIN, async_on_unload=MagicMock(), add_update_listener=MagicMock())
    with patch('custom_components.nest_lyric_panel.cast_manager.CastZone', return_value=zone), \
         patch('custom_components.nest_lyric_panel.migration.flatten_zones'), \
         patch('custom_components.nest_lyric_panel.zones.zones', return_value=[item]):
        assert await async_setup_entry(hass, entry)
        assert entry.runtime_data.zones == {'zone-1': zone}
        assert 'zones' not in hass.data[DOMAIN]
        zone.start.assert_called_once()
        assert await async_unload_entry(hass, entry)
        zone.stop.assert_called_once()
        assert entry.runtime_data.zones == {}

    sensor = ZoneSensor(entry, item, zone)
    with patch.object(SensorEntity, 'async_added_to_hass', new_callable=AsyncMock) as added, \
         patch.object(SensorEntity, 'async_will_remove_from_hass', new_callable=AsyncMock) as removed:
        await sensor.async_added_to_hass()
        assert sensor.async_write_ha_state in zone.listeners
        await sensor.async_will_remove_from_hass()
        assert not zone.listeners
        added.assert_awaited_once()
        removed.assert_awaited_once()
    print('Entry runtime and sensor lifecycle checks passed')


if __name__ == '__main__':
    asyncio.run(main())
