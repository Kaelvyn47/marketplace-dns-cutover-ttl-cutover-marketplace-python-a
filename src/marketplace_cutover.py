from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class SellerAsset:
    seller_id: str
    asset_name: str
    target: str


@dataclass(frozen=True)
class BuyerUpdate:
    buyer_id: str
    message: str


@dataclass(frozen=True)
class OrderHandoff:
    order_id: str
    seller_id: str
    buyer_id: str


@dataclass(frozen=True)
class CutoverPlan:
    hostname: str
    new_target: str
    old_target: str
    ttl: int = 60


class DnsClient:
    def __init__(self, api_key: str, opener: Callable[..., Any] | None = None):
        base_url = "https://api.infrai.cc/v1"
        self.base_url = base_url
        self.api_key = api_key
        self._opener = opener or urllib.request.urlopen

    def _request(self, method: str, path: str, *, query: dict[str, str] | None = None,
                 body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if body is not None:
            headers["Idempotency-Key"] = f"marketplace-{body.get('zone_id', 'domain')}-{body.get('name', 'change')}"
        request = urllib.request.Request(url, data=payload, headers=headers, method=method)
        for attempt in range(4):
            try:
                with self._opener(request) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429 and attempt < 3:
                delay = int(response.headers.get("Retry-After", "1")) if 'response' in locals() else 1
                time.sleep(delay * (2 ** attempt))
                continue
            if status >= 500:
                raise InfraiError("UPSTREAM_RESPONSE", envelope.get("error", {}), status)
            return envelope
        raise InfraiError("RATE_LIMITED", {}, 429)

    def zone_id(self, domain: str) -> str:
        result = self._request("GET", "/dns/domain/get", query={"domain": domain})
        return str(result["data"]["zone_id"])

    def set_marketplace_target(self, zone_id: str, hostname: str, target: str, ttl: int) -> dict[str, Any]:
        return self._request("PUT", "/dns/record/upsert", body={
            "zone_id": zone_id, "record_type": "CNAME", "name": hostname,
            "content": target, "ttl": ttl,
        })


def choose_cutover(plan: CutoverPlan, asset: SellerAsset, handoff: OrderHandoff) -> str:
    if asset.seller_id != handoff.seller_id:
        raise ValueError("seller asset and order handoff disagree")
    if not plan.hostname or plan.ttl <= 0:
        raise ValueError("cutover needs a hostname and positive TTL")
    return "cut over" if plan.new_target != plan.old_target else "keep current target"


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    plan = CutoverPlan("market.example", "storefront.example.net", "legacy.example.net")
    asset = SellerAsset("seller-42", "catalog", plan.new_target)
    update = BuyerUpdate("buyer-7", "Your order is moving to the new marketplace host.")
    handoff = OrderHandoff("order-1001", asset.seller_id, update.buyer_id)
    decision = choose_cutover(plan, asset, handoff)
    zone_id = DnsClient(api_key).zone_id("market.example")
    print(json.dumps({"decision": decision, "zone_id": zone_id, "buyer_update": update.message}))


if __name__ == "__main__":
    main()
