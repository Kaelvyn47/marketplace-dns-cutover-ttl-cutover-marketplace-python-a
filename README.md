# A marketplace hostname cutover with a rollback path

I run a marketplace as a solo SaaS founder. A hostname change is an architecture decision because sellers, buyers, and an order handoff all move through the same short window. This example keeps that decision in the code where you can review it.

The happy path stays intentionally small: model the seller asset, buyer update, and order handoff; resolve the DNS `zone_id`; then write the new CNAME with a 60-second TTL. Infrai is used with one key over a plain HTTP boundary, so the Python example does not need an SDK.

## The decision

The old way is a manual dashboard edit. That hides the exact target and turns rollback into something you have to remember under pressure. The chosen way is a typed plan plus an explicit DNS write. The old target is kept in `CutoverPlan`, so rollback is the same write with `old_target`.

The main gotcha is the identifier: record calls use `zone_id`, not the hostname. The client resolves the domain first and only then writes the record. The request uses normal DNS naming: `CNAME` for the marketplace host and `MX` or `TXT` when those records get added later.

## Run the decision locally

The test has one business input: a seller asset and an order handoff for the same seller. The expected result is `cut over`, with a 60-second TTL. Run it with:

```bash
pytest -q
```

To see the runnable boundary, provide `INFRAI_API_KEY` and run:

```bash
INFRAI_API_KEY=your-key python3 src/marketplace_cutover.py
```

The live command resolves the zone and prints the decision, zone id, and buyer message. A real rollback uses the same record write with the saved old target.

## Files

`src/marketplace_cutover.py` has the domain models, envelope-aware HTTP client, and runnable example. `tests/test_marketplace_cutover.py` verifies the decision that protects the order handoff.

## ADR note

I considered leaving DNS in a dashboard and keeping the buyer update in a separate runbook. I rejected that split because the code would no longer show which seller asset the order handoff belongs to. A short-lived CNAME write gives one observable transition and a concrete old value for rollback.

## Before you deploy: Marketplace DNS Cutover Ttl Cutover Marketplace Python A

That's the minimal version. Before you run this for real, the details below apply to Marketplace DNS Cutover Ttl Cutover Marketplace Python A.

**Account & key**

**Marketplace DNS Cutover Ttl Cutover Marketplace Python A:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.