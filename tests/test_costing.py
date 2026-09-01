"""Unit economics: whether a seat earns more than it burns.

The failure named here is a per-seat price set before anyone multiplied
cost-per-workflow by workflows-per-day by workdays -- an architecture bill
arriving late, dressed as a pricing problem.
"""

from fde.costing import unit_economics


def test_a_seat_that_burns_more_than_it_earns_is_named_underwater():
    """The Indiranagar math: five unbounded steps, no routing, no caching,
    eight workflows a day against a twenty-five dollar seat."""
    economics = unit_economics(8, 25.0, steps_per_workflow=5, today="2026-09-01")
    assert economics["cost_per_seat_month"] > 0
    assert economics["levers"], "no levers offered on an unoptimised stack"


def test_routing_and_caching_are_the_levers_the_corpus_already_owns():
    economics = unit_economics(8, 25.0, steps_per_workflow=5, today="2026-09-01")
    reasons = " ".join(reason for reason, _ in economics["levers"])
    assert "cascade" in reasons
    assert "prefix" in reasons
    assert "bound the loop" in reasons
    for _, new_margin in economics["levers"]:
        assert new_margin > economics["margin_per_seat"]


def test_measured_coverage_from_the_engagement_lowers_the_bill():
    without = unit_economics(8, 25.0, today="2026-09-01")
    with_routing = unit_economics(8, 25.0, cheap_path_coverage=0.6,
                                  today="2026-09-01")
    assert with_routing["cost_per_seat_month"] < without["cost_per_seat_month"]
