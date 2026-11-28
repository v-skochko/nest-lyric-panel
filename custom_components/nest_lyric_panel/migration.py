"""Move newly created Cast subentries into the shared integration entry."""
from homeassistant.helpers import device_registry as dr, entity_registry as er
from . import DOMAIN


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
