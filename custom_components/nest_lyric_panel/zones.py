"""Persistent Cast zones belonging directly to the integration entry."""
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class ZoneConfig:
    subentry_id: str
    title: str
    data: dict


def zones(entry):
    return [ZoneConfig(key, data.get('name', key), data) for key, data in entry.data.get('zones', {}).items()]


def update_zone(hass, entry, zone_id, data):
    all_zones = dict(entry.data.get('zones', {}))
    all_zones[zone_id] = dict(data)
    hass.config_entries.async_update_entry(entry, data={**entry.data, 'zones': all_zones})
