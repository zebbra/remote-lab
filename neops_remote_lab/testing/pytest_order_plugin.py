from __future__ import annotations

import logging
from _pytest.nodes import Item
import pytest
from .fixture import REMOTE_LAB_ORDER, REMOTE_LAB_FIXTURE_META

_log = logging.getLogger("remote-lab-plugin")

__all__ = [
    "REMOTE_LAB_ORDER",
    "REMOTE_LAB_FIXTURE_META",
]


def _format_execution_order(items: list[Item]) -> str:
    """Format the test execution order as a structured string."""
    lines = [
        "",
        "=" * 80,
        "REMOTE LAB TEST EXECUTION ORDER",
        "=" * 80,
        "",
        "Tests are ordered by their Remote Lab fixture rank (lower rank = earlier execution).",
        "Within each fixture group, tests maintain their original collection order.",
    ]

    # Group by fixture rank
    fixture_order = 1
    for rank in sorted(set(REMOTE_LAB_ORDER.values())):
        for fx_name in [fx for fx, fx_rank in REMOTE_LAB_ORDER.items() if fx_rank == rank]:
            # Find tests using this fixture
            fixture_tests = [item for item in items if fx_name in getattr(item, "fixturenames", ())]
            if not fixture_tests:
                continue

            meta = REMOTE_LAB_FIXTURE_META[fx_name]
            lines.extend(
                [
                    "",
                    f"Fixture #{fixture_order}: {fx_name}",
                    f"  topology: {meta['topology']}",
                    f"  reuse: {meta['reuse']}",
                    f"  rank: {meta['rank']}",
                    "  tests:",
                ]
            )
            lines.extend(f"    {i}. {item.nodeid}" for i, item in enumerate(fixture_tests, 1))
            fixture_order += 1

    # Non-Remote Lab tests
    non_remote_lab_tests = [
        item for item in items if not any(fx in getattr(item, "fixturenames", ()) for fx in REMOTE_LAB_FIXTURE_META)
    ]
    if non_remote_lab_tests:
        lines.extend(
            [
                "",
                "Non-Remote Lab tests:",
            ]
        )
        lines.extend(f"{i}. {item.nodeid}" for i, item in enumerate(non_remote_lab_tests, 1))

    lines.append("=" * 80)
    return "\n".join(lines)


def pytest_collection_modifyitems(config: pytest.Config, items: list[Item]) -> None:
    """Reorder collected tests so that those sharing the same Remote Lab lab run consecutively.

    The function logs (at DEBUG level) the computed rank for every item and
    the final execution order.  INFO level summarises the grouping.
    """

    indexed_items: list[tuple[int, Item]] = list(enumerate(items))

    detailed: list[tuple[int, str, list[str]]] = []  # (rank, nodeid, fixtures)

    for original_pos, item in indexed_items:
        fixture_names = getattr(item, "fixturenames", ()) or []
        remote_lab_fxs = [fx for fx in fixture_names if fx in REMOTE_LAB_ORDER]

        # Validate: only one Remote Lab fixture per test
        if len(remote_lab_fxs) > 1:
            fixture_list = ", ".join(remote_lab_fxs)
            raise ValueError(
                f"Test {item.nodeid} uses multiple Remote Lab fixtures: {fixture_list}. "
                "Only one Remote Lab fixture per test is allowed."
            )

        # build readable meta info
        meta_parts = []
        for fx in remote_lab_fxs:
            m = REMOTE_LAB_FIXTURE_META.get(fx, {})
            meta_parts.append(f"{fx}(reuse={m.get('reuse')},scope={m.get('scope')})")

        rank = min(REMOTE_LAB_ORDER[fx] for fx in remote_lab_fxs) if remote_lab_fxs else 999

        detailed.append((rank, item.nodeid, remote_lab_fxs))
        _log.debug(
            "Collected %s – rank=%s (fixtures=%s)",
            item.nodeid,
            rank,
            ", ".join(meta_parts) or "-",
        )

        # Stash rank & original index for the actual sort step
        item._remote_lab_rank = rank  # type: ignore[attr-defined]
        item._orig_idx = original_pos  # type: ignore[attr-defined]

    # Stable ordering: first by rank, then by original collection order
    items.sort(key=lambda it: (it._remote_lab_rank, it._orig_idx))  # type: ignore[attr-defined]

    # Log the structured order in one or two calls
    formatted_order = _format_execution_order(items)
    _log.info(formatted_order)
