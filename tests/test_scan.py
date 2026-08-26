"""What the hardware will actually run, and what it costs to run it there.

A scan that lists hardware is a report. What is wanted is the arithmetic:
whether this fits, what to do when it does not, and which optimisations the
silicon in front of you actually supports -- recommending one it does not is
worse than recommending nothing, because somebody spends a day finding out.
"""

import pytest

from fde.costing import STALE_AFTER_DAYS, compare_hosting, size_for
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.scan import (
    GPU,
    Hardware,
    finetune_feasible,
    fits,
    scan_facts,
    suggest,
)

# Ampere: no hardware fp8. Hopper: yes. That difference decides real advice.
A100 = Hardware(gpus=[GPU("A100", vram_gb=80, sm="8.0")], ram_gb=256)
TWO_A100 = Hardware(gpus=[GPU("A100", 80, "8.0"), GPU("A100", 80, "8.0")], ram_gb=512)
H100 = Hardware(gpus=[GPU("H100", vram_gb=80, sm="9.0")], ram_gb=512)
LAPTOP = Hardware(gpus=[], ram_gb=32)


# --- does it fit ---------------------------------------------------------


def test_a_mid_sized_model_fits_with_room_for_the_cache(reg=None):
    result = fits(A100, params_b=27, precision="bf16", max_num_seqs=16)
    assert result.ok
    assert result.kv_cache_gb > 0


def test_a_large_model_does_not_fit_and_says_by_how_much(reg=None):
    result = fits(A100, params_b=70, precision="bf16", max_num_seqs=16)
    assert not result.ok
    assert result.shortfall_gb > 0


def test_the_cache_is_counted_rather_than_forgotten(reg=None):
    """Naive sizing counts weights and runs out of memory under exactly the
    load it was sized for."""
    small = fits(A100, params_b=8, precision="bf16", max_num_seqs=8)
    large = fits(A100, params_b=8, precision="bf16", max_num_seqs=128)
    assert large.kv_cache_gb > small.kv_cache_gb


def test_the_card_is_not_filled_to_the_brim(reg=None):
    """Activations and fragmentation need room. Filling it exactly works in
    testing and fails under load."""
    assert fits(A100, params_b=8, precision="bf16").available_gb < 80


# --- optimisations the silicon actually supports -------------------------


def test_hardware_fp8_is_not_suggested_on_ampere(reg=None):
    """Recommending it here costs somebody a day finding out it is not there."""
    assert "fp8_kv_cache" not in {o.id for o in suggest(A100)}


def test_hardware_fp8_is_suggested_on_hopper(reg=None):
    assert "fp8_kv_cache" in {o.id for o in suggest(H100)}


def test_tensor_parallelism_needs_more_than_one_card(reg=None):
    assert "tensor_parallel" not in {o.id for o in suggest(A100)}
    assert "tensor_parallel" in {o.id for o in suggest(TWO_A100)}


def test_prefix_caching_is_always_suggested(reg=None):
    """The highest-value flag for nearly any workload, and free."""
    for hardware in (A100, H100, TWO_A100):
        assert "prefix_caching" in {o.id for o in suggest(hardware)}


def test_every_suggestion_states_what_it_costs(reg=None):
    """An optimisation with no stated cost reads as free, and none of them are."""
    for option in suggest(H100):
        assert option.reason and option.cost


def test_a_machine_with_no_accelerator_says_so_rather_than_failing(reg=None):
    """CPU-only is a real answer, and frequently the right one."""
    options = suggest(LAPTOP)
    assert options
    assert any("cpu" in o.id for o in options)


# --- adaptation ----------------------------------------------------------


def test_a_full_finetune_of_a_small_model_does_not_fit_one_card(reg=None):
    """Optimiser state and gradients are several times the weights, which is
    the part people are surprised by."""
    assert not finetune_feasible(A100, params_b=7, method="full").ok


def test_a_parameter_efficient_finetune_of_a_larger_model_does(reg=None):
    assert finetune_feasible(A100, params_b=12, method="qlora").ok


def test_the_infeasible_case_names_the_cheaper_method(reg=None):
    result = finetune_feasible(A100, params_b=7, method="full")
    assert "qlora" in result.reason.lower() or "parameter" in result.reason.lower()


# --- facts ---------------------------------------------------------------


def test_a_scan_produces_detected_facts(reg=None):
    """Measured, so they outrank anything anybody says about the environment."""
    from fde.models.base import Provenance

    facts = {f.dimension: f for f in scan_facts(A100)}
    assert facts["available_vram_gb"].value == 80
    assert facts["available_vram_gb"].provenance is Provenance.DETECTED


def test_a_machine_with_no_gpu_reports_zero_rather_than_nothing(reg=None):
    facts = {f.dimension: f.value for f in scan_facts(LAPTOP)}
    assert facts["available_vram_gb"] == 0


def test_the_scan_reports_capacity_class_not_only_numbers(reg=None):
    """A measurement nothing keys on decides nothing. The class is the part
    an approach can be gated on."""
    for hardware, expected in ((LAPTOP, "none"), (A100, "single"), (TWO_A100, "multi")):
        facts = {f.dimension: f.value for f in scan_facts(hardware)}
        assert facts["accelerator"] == expected


def test_a_detected_accelerator_reaches_the_architecture(reg=None):
    """The whole point of scanning. A machine with nothing local, and somebody
    waiting, must not be handed a design that serves open weights on it."""
    from fde.predicate import holds
    from fde.registry import load_registry

    registry = load_registry("framework")
    profile = Profile()
    profile.ingest(scan_facts(LAPTOP))
    profile.ingest([Fact("human_waiting", "yes", Provenance.INTERVIEW)])

    self_hosted = registry.approaches["self-hosted"]
    assert any(holds(p, profile, registry) for p in self_hosted.avoid_when)


def test_a_detected_accelerator_does_not_rule_it_out_when_present(reg=None):
    from fde.predicate import holds
    from fde.registry import load_registry

    registry = load_registry("framework")
    profile = Profile()
    profile.ingest(scan_facts(TWO_A100))
    profile.ingest([Fact("human_waiting", "yes", Provenance.INTERVIEW)])

    self_hosted = registry.approaches["self-hosted"]
    assert not any(holds(p, profile, registry) for p in self_hosted.avoid_when)


# --- costing -------------------------------------------------------------


def test_sizing_counts_redundancy_and_peak_not_only_average(reg=None):
    """Naive sizing from average throughput understates the fleet, and the
    understatement is discovered in production."""
    plan = size_for(requests_per_day=500_000, params_b=70)
    assert plan["replicas"] > plan["naive_replicas"]
    assert {"redundancy", "peak", "prefill"} <= set(plan["factors"])


def test_the_worked_example_reaches_the_documented_conclusion(reg=None):
    """At sustained interactive volume, self-hosting loses. The framework has
    to be able to reach that answer as well as the opposite one."""
    comparison = compare_hosting(requests_per_day=500_000, params_b=70)
    assert comparison["recommendation"] == "managed"
    assert comparison["self_hosted_monthly"] > comparison["managed_monthly"]


def test_low_volume_batch_reaches_the_opposite_conclusion(reg=None):
    """Both answers are correct for their workload, and a framework that only
    knows one of them is wrong half the time."""
    comparison = compare_hosting(requests_per_day=2_000, params_b=8, human_waiting=False)
    assert comparison["recommendation"] == "self-hosted"


def test_every_figure_carries_a_date_and_a_way_to_re_derive_it(reg=None):
    """An absolute with no date ages silently, and somebody quotes it a year
    later in a proposal."""
    plan = size_for(requests_per_day=500_000, params_b=70)
    assert plan["as_of"] and plan["rederive"]


def test_a_stale_figure_is_flagged_rather_than_used_quietly(reg=None):
    with pytest.warns(UserWarning, match="as of"):
        size_for(requests_per_day=1_000, params_b=8, today="2030-01-01")


def test_a_current_figure_produces_no_warning(reg=None):
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        size_for(requests_per_day=1_000, params_b=8, today="2026-09-01")


def test_the_staleness_window_is_stated_rather_than_implied(reg=None):
    assert STALE_AFTER_DAYS > 0


def test_a_replica_of_a_large_model_is_more_than_one_card(reg=None):
    """Pricing every replica as one GPU quotes a 70B fleet at a third of its
    cost. A replica is however many cards the weights and cache need."""
    from fde.costing import gpus_per_replica

    assert gpus_per_replica(8) == 1
    assert gpus_per_replica(70) > 1


def test_quantisation_changes_how_many_cards_a_replica_takes(reg=None):
    from fde.costing import gpus_per_replica

    assert gpus_per_replica(70, precision="int8") < gpus_per_replica(70, precision="bf16")


# --- as an FDE runs it ----------------------------------------------------


def test_scan_reports_the_shortfall_rather_than_only_refusing(reg=None):
    """'Does not fit' sends somebody guessing. 'Short 13GB' tells them whether
    quantising is enough or the model has to change."""
    from typer.testing import CliRunner

    from fde.cli import app

    result = CliRunner().invoke(app, ["scan", "--model-b", "70", "--vram", "80"])
    assert "does not fit" in result.output
    assert "short" in result.output


def test_stated_hardware_is_not_recorded_as_a_detected_fact(tmp_path):
    """An FDE sizing a client's box from their own laptop is reasoning, not
    measuring. Recording it as detected would let a quoted number outrank a
    measurement, which is the one thing provenance exists to prevent."""
    from typer.testing import CliRunner

    from fde.cli import app

    runner = CliRunner()
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path)])
    result = runner.invoke(
        app, ["scan", str(tmp_path / "acme"), "--vram", "80", "--model-b", "8"]
    )
    assert "not recorded" in result.output
    assert not list((tmp_path / "acme" / "facts").glob("*scan*"))
