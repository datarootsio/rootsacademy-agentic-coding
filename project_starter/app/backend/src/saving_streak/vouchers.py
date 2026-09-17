"""The outbound voucher-issuance port (spec D16).

Claiming is instant and final: the voucher or ticket is issued immediately and
there is no reversal path. Issuance itself belongs to a supplier, which is out
of scope for this system — all Saving Streak owns is the port, and the rule
that a claim is a unit: if issuance fails, the points are not deducted.

The port takes no clock and no ledger. It is handed what the supplier needs to
print a voucher, including the caller's idempotency key so a supplier that can
deduplicate has something to deduplicate on.
"""

from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass


class VoucherIssuanceFailed(RuntimeError):
    """The supplier did not issue a voucher.

    Not a `DomainError`: nothing the customer sent is wrong. The claim fails as
    a unit, nothing is deducted, and the caller may try again.
    """


@dataclass(frozen=True)
class IssuanceRequest:
    """What the supplier is asked for."""

    customer_id: str
    item_id: str
    item_name: str
    price_points: int
    idempotency_key: str


@dataclass(frozen=True)
class Voucher:
    """What came back: the code the customer redeems at the counter."""

    code: str


class VoucherIssuer(ABC):
    """The port. Implementations may fail; none of them may half-succeed."""

    @abstractmethod
    def issue(self, request: IssuanceRequest) -> Voucher:
        """Issue one voucher, or raise `VoucherIssuanceFailed`."""


class LocalVoucherIssuer(VoucherIssuer):
    """The demo's stand-in for a supplier integration.

    It mints a code and nothing else. Supplier integration is out of scope for
    this spec; what matters here is that the seam calls a port it does not own
    and survives that port saying no.
    """

    def issue(self, request: IssuanceRequest) -> Voucher:
        return Voucher(code=f"SS-{secrets.token_hex(5).upper()}")
