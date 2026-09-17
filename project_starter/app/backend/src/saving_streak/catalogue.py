"""The reward catalogue: versioned data, not hardcoded config (spec D12).

A catalogue is one published version — a version number and the items it
priced. Changing a price publishes a *new* version rather than editing the old
one, because a claim records the price it was claimed at and a later price
change must never rewrite it.

Prices are points, and points are integers everywhere (spec D4).

This module is data plus the lookup over it. It reads no clock and touches no
storage; the application service takes a `Catalogue` as an injected
collaborator, so a test can hand it a later version and watch history stay put.
"""

from __future__ import annotations

from dataclasses import dataclass

from .events import DomainError


@dataclass(frozen=True)
class CatalogueItem:
    """One reward and what it costs, in points."""

    item_id: str
    name: str
    price_points: int

    def __post_init__(self) -> None:
        if not self.item_id or not self.name:
            raise ValueError("a catalogue item needs an id and a name")
        if not isinstance(self.price_points, int) or isinstance(self.price_points, bool):
            raise TypeError(f"a price must be a whole number of points, got {self.price_points!r}")
        if self.price_points <= 0:
            raise ValueError(f"a price must be above zero, got {self.price_points}")


@dataclass(frozen=True)
class Catalogue:
    """One published version of the catalogue."""

    version: int
    items: tuple[CatalogueItem, ...]

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError(f"a catalogue version starts at 1, got {self.version}")
        if not self.items:
            raise ValueError("a catalogue with nothing in it cannot be published")
        ids = [item.item_id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("two catalogue items share an id")

    def item(self, item_id: str) -> CatalogueItem:
        """The item with this id, or a refusal the adapter maps to 400.

        Not `None`: a claim for something the catalogue does not sell is a
        command the domain refuses, not an empty answer.
        """
        for item in self.items:
            if item.item_id == item_id:
                return item
        raise DomainError(
            f"no catalogue item {item_id!r} in catalogue version {self.version}"
        )


#: Every published version, oldest first. Adding a version is how a price
#: changes; the earlier versions stay exactly as they were claimed against.
CATALOGUE_VERSIONS: tuple[Catalogue, ...] = (
    Catalogue(
        version=1,
        items=(
            CatalogueItem("cinema-ticket", "Cinema ticket", 100),
            CatalogueItem("coffee-or-snack-voucher", "Coffee or snack voucher", 40),
            CatalogueItem("charity-donation", "Charity donation", 10),
            CatalogueItem("family-cinema-pack", "Family cinema pack (two tickets + a snack)", 180),
        ),
    ),
)


def current_catalogue() -> Catalogue:
    """The version customers are shopping from right now."""
    return CATALOGUE_VERSIONS[-1]
