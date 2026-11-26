"""Build a conservative, repeatable plan for consolidating legacy Cast entries."""
from dataclasses import dataclass


@dataclass(frozen=True)
class LegacyZone:
    entry_id: str
    title: str
    data: dict
    disabled: bool


def plan_legacy_zones(entries, existing_displays):
    """Return only unambiguous entries; keep legacy IDs for stable entity IDs.

    Refuse duplicate displays instead of silently discarding user settings.
    """
    displays = set(existing_displays)
    result = []
    for entry in entries:
        data = dict(entry.data)
        display = data.get('display')
        if not display:
            continue
        if display in displays:
            raise ValueError(f'Duplicate Cast display: {display}')
        displays.add(display)
        data['legacy_entry_id'] = entry.entry_id
        if entry.disabled_by is not None:
            data['enabled'] = False
        result.append(LegacyZone(entry.entry_id, entry.title, data, entry.disabled_by is not None))
    return result
