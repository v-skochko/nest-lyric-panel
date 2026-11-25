"""Pure decision logic for a single automatic Cast zone.

The caller owns subscriptions, timers and device actions.  Monotonic seconds are
used so that clock adjustments do not alter retry and stop intervals.
"""
from __future__ import annotations

from dataclasses import dataclass, field

RETRY_SECONDS = 30
STOP_SECONDS = 120


@dataclass
class CastPolicy:
    sources: tuple[str, ...]
    playing: dict[str, float] = field(default_factory=dict)
    last_attempt: float | None = None
    stopped_at: float | None = None

    def update_source(self, entity: str, is_playing: bool, now: float) -> None:
        if entity not in self.sources:
            return
        if is_playing:
            if not self.playing:
                self.last_attempt = None
            if entity not in self.playing:
                self.playing[entity] = now
            self.stopped_at = None
        else:
            was_playing = entity in self.playing
            self.playing.pop(entity, None)
            if was_playing and not self.playing and self.stopped_at is None:
                self.stopped_at = now

    @property
    def active_source(self) -> str | None:
        return max(self.playing, key=self.playing.get) if self.playing else None

    def decision(self, now: float, panel_active: bool, display_available: bool) -> str:
        if self.playing:
            if not display_available:
                return 'unavailable'
            if panel_active:
                return 'showing'
            if self.last_attempt is None or now - self.last_attempt >= RETRY_SECONDS:
                return 'cast'
            return 'waiting_retry'
        if self.stopped_at is not None and now - self.stopped_at >= STOP_SECONDS and panel_active:
            return 'close'
        return 'idle'

    def attempted(self, now: float) -> None:
        self.last_attempt = now
