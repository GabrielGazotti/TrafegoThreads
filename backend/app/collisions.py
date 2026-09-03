"""
Detecção de colisões por cluster: cada grupo de veículos próximos
conta uma vez, somando todos os veículos envolvidos (não pares).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from . import config

if TYPE_CHECKING:
    from .city import City


def _in_collision_range(a, b) -> bool:
    dist = ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5
    same_zone = (
        a.current_intersection is not None
        and b.current_intersection is not None
        and a.current_intersection[0] == b.current_intersection[0]
    ) or dist < config.COLLISION_DISTANCE
    return same_zone and dist < config.COLLISION_DISTANCE


def _find_clusters(active: list) -> list[list]:
    n = len(active)
    if n < 2:
        return []

    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if _in_collision_range(active[i], active[j]):
                union(i, j)

    groups: dict[int, list] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(active[i])

    return [cluster for cluster in groups.values() if len(cluster) >= 2]


def process_collision_clusters(active: list, city: City, metrics, event_log) -> None:
    """Marca veículos colididos e incrementa veículos envolvidos por cluster."""
    for cluster in _find_clusters(active):
        involved = [v for v in cluster if not v.crashed]
        if len(involved) < 2:
            continue

        for v in involved:
            v.mark_crashed()

        metrics.inc_vehicles_involved(len(involved))

        ref = involved[0]
        inter_desc = (
            city.intersections[ref.current_intersection[0]].id
            if ref.current_intersection
            else "via"
        )
        ids = "+".join(v.id for v in involved)
        event_log.append(
            {
                "t": round(time.time(), 3),
                "vehicle": ids,
                "type": "colisao",
                "level": "crash",
                "message": f"💥 COLISÃO ({len(involved)} veículos) perto de {inter_desc}",
            }
        )
        metrics.inc_events()
