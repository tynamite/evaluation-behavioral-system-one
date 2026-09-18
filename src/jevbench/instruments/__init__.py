"""The full battery."""

from __future__ import annotations

from . import (
    cognitive,
    dark_triad,
    decision,
    followup,
    games,
    personality,
    reasoning,
    risk_time,
    strategic,
)
from .base import PERSONAS, Persona, Probe, apply_persona, permute_options

MODULES = {
    "crt": cognitive,
    "games": games,
    "decision": decision,
    "risk_time": risk_time,
    "strategic": strategic,
    "personality": personality,
    "reasoning": reasoning,
    "dark_triad": dark_triad,
    "followup": followup,
}


def all_probes(only: list[str] | None = None) -> list[Probe]:
    """Every probe in the battery, optionally filtered to named modules."""
    selected = MODULES if not only else {k: v for k, v in MODULES.items() if k in only}
    if only:
        unknown = set(only) - set(MODULES)
        if unknown:
            raise ValueError(f"Unknown module(s): {sorted(unknown)}. Known: {sorted(MODULES)}")
    out: list[Probe] = []
    for mod in selected.values():
        out.extend(mod.probes())
    ids = [p.probe_id for p in out]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"Duplicate probe ids: {sorted(dupes)}")
    return out


__all__ = [
    "PERSONAS",
    "Persona",
    "Probe",
    "all_probes",
    "apply_persona",
    "permute_options",
]
