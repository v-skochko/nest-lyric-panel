"""Migrate legacy top-level zones without changing entity or device IDs."""
from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers import device_registry as dr, entity_registry as er
from . import DOMAIN
from .migration_plan import plan_legacy_zones


async def migrate_zones(hass, parent):
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != parent.entry_id and e.data.get('display')]
    existing = {sub.data.get('display'): sub for sub in parent.get_subentries_of_type('cast_zone')}
    planned = plan_legacy_zones(entries, [])
    registry = er.async_get(hass)
    devices = dr.async_get(hass)
    for item in planned:
        legacy = hass.config_entries.async_get_entry(item.entry_id)
        if not legacy:
            continue
        sub = existing.get(item.data['display'])
        if sub and sub.subentry_id != item.entry_id:
            raise ValueError(f"Display is already configured: {item.data['display']}")
        if not await hass.config_entries.async_unload(item.entry_id):
            raise RuntimeError(f'Could not unload legacy zone {item.title}')
        if not sub:
            sub = ConfigSubentry(subentry_id=item.entry_id, subentry_type='cast_zone', title=item.title, unique_id=item.data['display'], data=MappingProxyType(item.data))
            hass.config_entries.async_add_subentry(parent, sub)
        matches = devices.async_get_devices(identifiers={(DOMAIN, item.entry_id)}, config_entry_id=item.entry_id)
        device = matches[0] if len(matches) == 1 else None
        if device:
            devices.async_update_device(device.id, new_config_entry_id=parent.entry_id, new_config_subentry_id=sub.subentry_id)
        for entity in er.async_entries_for_config_entry(registry, item.entry_id):
            registry.async_update_entity(entity.entity_id, config_entry_id=parent.entry_id, config_subentry_id=sub.subentry_id)
        await hass.config_entries.async_remove(item.entry_id)


def detach_legacy_settings_device(hass, parent):
    """Keep the three settings entities while removing their obsolete device."""
    registry = er.async_get(hass)
    devices = dr.async_get(hass)
    matches = devices.async_get_devices(identifiers={(DOMAIN, parent.entry_id)}, config_entry_id=parent.entry_id)
    device = matches[0] if len(matches) == 1 else None
    if not device:
        return
    attached = er.async_entries_for_device(registry, device.id, include_disabled_entities=True)
    expected = {f"{parent.entry_id}_{key}" for key in ("translation_url", "sync_tolerance", "cache_minutes")}
    if any(entity.platform != DOMAIN or entity.unique_id not in expected for entity in attached):
        return
    for entity in attached:
        registry.async_update_entity(entity.entity_id, device_id=None)
    devices.async_remove_device(device.id)


def flatten_zones(hass, parent):
    """Move zones to the parent while keeping device and sensor identities."""
    pending = parent.get_subentries_of_type('cast_zone')
    all_zones = dict(parent.data.get('zones', {}))
    devices = dr.async_get(hass)
    registry = er.async_get(hass)
    for sub in pending:
        all_zones[sub.subentry_id] = {**sub.data, 'enabled': True}
        for device in dr.async_entries_for_config_entry(devices, parent.entry_id):
            if device.config_subentry_id == sub.subentry_id:
                devices.async_update_device(device.id, new_config_subentry_id=None)
        for entity in er.async_entries_for_config_entry(registry, parent.entry_id):
            if entity.config_subentry_id == sub.subentry_id:
                registry.async_update_entity(entity.entity_id, config_subentry_id=None)
    if pending:
        hass.config_entries.async_update_entry(parent, data={**parent.data, 'zones': all_zones})
    for entity in er.async_entries_for_config_entry(registry, parent.entry_id):
        for zone_id, data in all_zones.items():
            identity = data.get('legacy_entry_id', zone_id)
            obsolete = {f'{identity}_{key}' for key in ('enabled', 'add_player', 'remove_player')}
            prefix = f'{identity}_additional_player_'
            old_slot = entity.unique_id.startswith(prefix) and entity.unique_id[len(prefix):].isdigit() and int(entity.unique_id[len(prefix):]) > 2
            if entity.platform == DOMAIN and (entity.unique_id in obsolete or old_slot):
                registry.async_remove(entity.entity_id)
                break
    for sub in pending:
        hass.config_entries.async_remove_subentry(parent, sub.subentry_id)
