import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketplace_cutover import CutoverPlan, OrderHandoff, SellerAsset, choose_cutover


def test_cutover_decision_keeps_short_ttl_and_matches_seller_handoff():
    plan = CutoverPlan("market.example", "new.example.net", "old.example.net", ttl=60)
    asset = SellerAsset("seller-42", "catalog", "new.example.net")
    handoff = OrderHandoff("order-1001", "seller-42", "buyer-7")

    assert choose_cutover(plan, asset, handoff) == "cut over"
    assert plan.ttl == 60
