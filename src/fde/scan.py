"""What the hardware in front of you will actually run.

A scan that lists devices is a report. What is useful is the arithmetic --
whether this fits, by how much it does not, and which optimisations this silicon
supports.

That last one is the part worth being careful about. **Recommending an
optimisation the hardware cannot do is worse than recommending nothing**,
because it costs somebody a day of finding out, and it costs the framework the
benefit of the doubt on everything else it said.

Detected facts outrank anything stated. A person's recollection of how much
memory a box has is a guess with confidence attached; the box knows.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from fde.models.base import DimensionKind, Provenance
from fde.models.fact import Fact

BYTES_PER_PARAM = {"fp32": 4.0, "bf16": 2.0, "fp16": 2.0, "int8": 1.0, "int4": 0.5}

# Leave room for activations and fragmentation. Filling the card exactly works
# in testing and fails under load.
UTILISATION = 0.90

# Hardware fp8 arrives at compute capability 8.9 (Ada) and above. Below that it
# is emulated at best, and suggesting it is an instruction to waste an afternoon.
FP8_FROM_SM = 8.9

# Training outright costs roughly sixteen bytes a parameter, and only two of
# them are the weights: bf16 weights (2) plus bf16 gradients (2) plus fp32
# master weights (4) plus Adam's two moments in fp32 (8). The optimiser state
# is the largest term and the one nobody budgets for.
FULL_FINETUNE_BYTES_PER_PARAM = 16.0

# Quantised weights plus a small adapter, its gradients and its optimiser
# state. The adapter is a fraction of a percent of the parameters, which is
# the entire point of doing it this way.
PEFT_BYTES_PER_PARAM = 0.65


@dataclass
class GPU:
    model: str
    vram_gb: float
    sm: str = "8.0"

    @property
    def compute_capability(self) -> float:
        try:
            return float(self.sm)
        except ValueError:
            return 0.0


@dataclass
class Hardware:
    gpus: list[GPU] = field(default_factory=list)
    ram_gb: float = 0.0

    @property
    def total_vram_gb(self) -> float:
        return sum(g.vram_gb for g in self.gpus)

    @property
    def largest_vram_gb(self) -> float:
        return max((g.vram_gb for g in self.gpus), default=0.0)


@dataclass
class Fit:
    ok: bool
    weights_gb: float
    kv_cache_gb: float
    required_gb: float
    available_gb: float
    shortfall_gb: float


@dataclass
class Option:
    id: str
    reason: str
    cost: str


@dataclass
class Feasible:
    ok: bool
    required_gb: float
    available_gb: float
    reason: str = ""


@dataclass
class Detection:
    """What was found, and whether that counts as a measurement.

    The distinction is the point. "Measured: no accelerator" and "could not
    measure" are different facts, and only the first may ever be recorded as
    DETECTED -- detected outranks what people say about the environment, so a
    non-measurement recorded as one lets a false reading beat a true
    statement, which is the single thing provenance exists to prevent.
    """

    hardware: Hardware
    measured: bool
    note: str = ""


def detect() -> Detection:
    """What is actually here.

    Probes what it can and says what it cannot. A machine whose accelerator
    this scan has no probe for -- unified-memory silicon, a ROCm device --
    reports an unmeasured detection rather than a confident zero.
    """
    ram = _ram_gb()

    if shutil.which("nvidia-smi"):
        try:
            output = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=name,memory.total,compute_cap",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10, check=True,
            ).stdout
        except (subprocess.SubprocessError, OSError) as exc:
            return Detection(
                Hardware(gpus=[], ram_gb=ram), measured=False,
                note=f"nvidia-smi is present and failed ({exc}); nothing recorded",
            )
        gpus, skipped = [], 0
        for line in output.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            try:
                gpus.append(
                    GPU(model=parts[0], vram_gb=float(parts[1]) / 1024, sm=parts[2])
                )
            except (IndexError, ValueError):
                # MIG slices and some drivers report [N/A] for memory. A card
                # that cannot be read is not a card that is not there.
                skipped += 1
        if skipped and not gpus:
            return Detection(
                Hardware(gpus=[], ram_gb=ram), measured=False,
                note=f"{skipped} device(s) reported unreadable memory; "
                     f"nothing recorded",
            )
        return Detection(Hardware(gpus=gpus, ram_gb=ram), measured=True)

    unmeasurable = _unmeasurable_accelerator()
    if unmeasurable:
        return Detection(
            Hardware(gpus=[], ram_gb=ram), measured=False, note=unmeasurable
        )
    return Detection(Hardware(gpus=[], ram_gb=ram), measured=True)


def _unmeasurable_accelerator() -> str:
    """Evidence of an accelerator this scan has no probe for.

    Not exhaustive and not trying to be: the job is to avoid recording
    "no accelerator" on a machine that visibly has one.
    """
    import platform
    from pathlib import Path

    if platform.system() == "Darwin" and _darwin_is_arm():
        return (
            "unified-memory accelerator present (Apple silicon); per-card "
            "arithmetic does not apply and nothing is recorded as measured"
        )
    if Path("/dev/kfd").exists():
        return (
            "a ROCm device is present and this scan has no probe for it; "
            "nothing is recorded as measured"
        )
    return ""


def _darwin_is_arm() -> bool:
    """Ask the kernel, not the process.

    Under Rosetta, platform.machine() reports the interpreter's architecture
    -- x86_64 on an arm machine -- so the probe meant to prevent a false
    measurement would itself be deceived. sysctl answers for the hardware.
    """
    import platform

    try:
        out = subprocess.run(
            ["sysctl", "-n", "hw.optional.arm64"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        out = ""
    if out in ("0", "1"):
        return out == "1"
    # The kernel gave no answer -- a non-Darwin sysctl exists and errors with
    # empty output rather than raising, which is not the same as saying no.
    # The process architecture is the only signal left.
    return platform.machine() == "arm64"


def fits(
    hardware: Hardware,
    params_b: float,
    precision: str = "bf16",
    max_num_seqs: int = 16,
    max_model_len: int = 8192,
    layers: int = 32,
    kv_heads: int = 8,
    head_dim: int = 128,
) -> Fit:
    """Whether this model runs here, counting the cache as well as the weights."""
    weights = params_b * BYTES_PER_PARAM[precision]
    cache = (max_num_seqs * max_model_len * layers * 2 * kv_heads * head_dim * 2) / 1e9
    required = weights + cache
    available = hardware.total_vram_gb * UTILISATION

    return Fit(
        ok=required <= available,
        weights_gb=round(weights, 2),
        kv_cache_gb=round(cache, 2),
        required_gb=round(required, 2),
        available_gb=round(available, 2),
        shortfall_gb=round(max(0.0, required - available), 2),
    )


def suggest(hardware: Hardware) -> list[Option]:
    """Optimisations this hardware can actually do.

    Each gated on what is present rather than on what is usually present. Every
    one states its cost, because an optimisation with no stated cost reads as
    free and none of them are.
    """
    if not hardware.gpus:
        return [
            Option(
                "cpu_inference",
                "No accelerator here. A small quantised model on CPU is a real "
                "answer and often the right one for low volume.",
                "An order of magnitude slower than a GPU. Fine when nobody is "
                "waiting; not fine when somebody is.",
            ),
            Option(
                "prefix_caching",
                "Requests sharing a prompt prefix reuse the computed cache.",
                "Memory for the cache. Free in every other sense.",
            ),
        ]

    options = [
        Option(
            "prefix_caching",
            "The highest-value flag for nearly any workload where requests share "
            "a system prompt, which is nearly all of them.",
            "Some memory held for the cache. Nothing else.",
        ),
        Option(
            "continuous_batching",
            "New requests join the running batch each step rather than waiting "
            "for it to drain.",
            "None worth stating; this is the default worth keeping.",
        ),
        Option(
            "int8_quantisation",
            "Halves the weight footprint against bf16, and runs everywhere.",
            "A small and measurable quality cost. Measure it rather than assume it.",
        ),
    ]

    best = max(g.compute_capability for g in hardware.gpus)
    if best >= FP8_FROM_SM:
        options.append(Option(
            "fp8_kv_cache",
            f"This silicon supports fp8 in hardware (compute capability {best}), "
            f"so the cache halves without emulation.",
            "A quality cost on long contexts. Measure before committing to it.",
        ))

    if len(hardware.gpus) > 1:
        options.append(Option(
            "tensor_parallel",
            f"{len(hardware.gpus)} cards, so a model too large for one can be "
            f"split across them.",
            "Interconnect becomes the bottleneck. Worth it for a model that "
            "otherwise does not fit; not worth it for one that does.",
        ))

    return options


def finetune_feasible(hardware: Hardware, params_b: float, method: str = "qlora") -> Feasible:
    """Whether this can be adapted here.

    Sized from the weights, a 7B finetune looks like it fits on one card. It
    does not: gradients, fp32 master weights and Adam's moments together cost
    seven times what the weights do, and that is the arithmetic people skip.
    """
    per_param = (
        FULL_FINETUNE_BYTES_PER_PARAM if method == "full" else PEFT_BYTES_PER_PARAM
    )
    required = params_b * per_param
    available = hardware.total_vram_gb * UTILISATION

    if required <= available:
        return Feasible(True, round(required, 2), round(available, 2))

    return Feasible(
        False,
        round(required, 2),
        round(available, 2),
        reason=(
            f"a full finetune needs roughly {required:.0f}GB against "
            f"{available:.0f}GB available -- optimiser state and gradients, not "
            f"the weights. Parameter-efficient adaptation (qlora) is the cheaper "
            f"lever and usually the right one anyway."
            if method == "full" else
            f"needs roughly {required:.0f}GB against {available:.0f}GB available."
        ),
    )


def accelerator_class(hardware: Hardware) -> str:
    """Capacity class rather than hardware.

    Three values because three things change: nothing local, one device, or
    enough devices to split a model that fits on none of them alone.
    """
    if not hardware.gpus:
        return "none"
    return "single" if len(hardware.gpus) == 1 else "multi"


def scan_facts(hardware: Hardware) -> list[Fact]:
    """What the machine says about itself.

    Detected, so these outrank anything anybody recalls about the environment.
    The class is the one that reaches a decision; the measurements are what
    the sizing arithmetic is done against, and what makes the class checkable.
    """
    return [
        Fact("accelerator", accelerator_class(hardware), Provenance.DETECTED,
             kind=DimensionKind.ENVIRONMENT, source="scan"),
        Fact("available_vram_gb", round(hardware.total_vram_gb), Provenance.DETECTED,
             kind=DimensionKind.ENVIRONMENT, source="scan"),
        Fact("gpu_count", len(hardware.gpus), Provenance.DETECTED,
             kind=DimensionKind.ENVIRONMENT, source="scan"),
        Fact("host_ram_gb", round(hardware.ram_gb), Provenance.DETECTED,
             kind=DimensionKind.ENVIRONMENT, source="scan"),
    ]


def _ram_gb() -> float:
    try:
        import os

        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
    except (ValueError, AttributeError, OSError):  # pragma: no cover - platform dependent
        return 0.0


# --- which local model, on this box ---------------------------------------

# Dated deliberately, like every figure in costing: model releases move
# monthly, and an undated recommendation is a stale one wearing a fresh
# tool's authority. Sizes are quantized on-disk footprints, roughly Q4.
MODEL_GUIDANCE_AS_OF = "2026-09"


@dataclass
class LocalModelPlan:
    runtime: str            # ollama | vllm | none
    runtime_reason: str
    endpoint: str
    serve_hint: str
    judge_model: str        # also the frame-reader model; small on purpose
    coder_model: str
    budget_gb: float
    notes: list[str] = field(default_factory=list)


def _judge_model(budget_gb: float) -> str:
    # Judging and schema-bound extraction are the easy jobs; the calibration
    # gate, not the leaderboard, decides if the size is enough.
    if budget_gb >= 12:
        return "qwen3.5:9b"
    if budget_gb >= 6:
        return "qwen3.5:4b"
    return "qwen3.5:2b"


def _coder_model(budget_gb: float) -> str:
    if budget_gb >= 28:
        return "qwen3-coder:30b-a3b"   # MoE, ~19GB, best coder per GB
    if budget_gb >= 20:
        return "devstral:24b"          # agent-tuned, ~16GB, Apache-2.0
    if budget_gb >= 12:
        return "gpt-oss:20b"           # MoE, ~14GB native MXFP4
    if budget_gb >= 6:
        return "qwen2.5-coder:7b"      # ~4.7GB, strongest 7B-class coder
    return "qwen3.5:4b"                # below coder territory; say so


def recommend_local_models(
    hardware: Hardware, platform_system: str | None = None,
    is_arm_mac: bool | None = None,
) -> LocalModelPlan:
    """Runtime and models this box can actually serve, sized from what was
    measured -- never from what somebody remembered about the machine.

    Detection defaults to the scanner's own probes: platform.machine() under
    a Rosetta-translated Python says x86_64 on Apple silicon, which is the
    exact lie _darwin_is_arm() exists to see through."""
    import platform as _platform

    if platform_system is None:
        platform_system = _platform.system()
    if is_arm_mac is None:
        is_arm_mac = platform_system == "Darwin" and _darwin_is_arm()
    unified = is_arm_mac and not hardware.gpus
    budget = (
        hardware.ram_gb * 0.66 if unified          # shared with everything else
        else hardware.largest_vram_gb * UTILISATION if hardware.gpus
        else hardware.ram_gb * 0.5                 # CPU-only: llama.cpp-class
    )

    notes = []
    if unified:
        runtime, reason = "ollama", (
            "Apple silicon: Ollama runs on the MLX backend (0.19+); "
            "vllm-metal exists for the same box when concurrency arrives"
        )
        endpoint, serve = "http://localhost:11434", "ollama pull {model}"
        if hardware.ram_gb < 32:
            notes.append(
                "the MLX backend previews at 32GB unified memory and above; "
                "below that Ollama still serves, on the default backend"
            )
    elif hardware.gpus:
        runtime, reason = "vllm", (
            "a CUDA-class card: vLLM for one box; SGLang where many requests "
            "share long prefixes (agents, RAG) -- roughly a quarter more "
            "throughput there"
        )
        endpoint, serve = "http://localhost:8000", "vllm serve {model}"
    else:
        runtime, reason = "ollama", (
            "no accelerator measured: Ollama (llama.cpp backend) serves "
            "small models on CPU; expect seconds per reply, not tokens "
            "per breath"
        )
        endpoint, serve = "http://localhost:11434", "ollama pull {model}"

    if budget < 6:
        notes.append(
            f"{budget:.0f}GB of usable memory is below coder territory -- "
            f"the judge and reader fit, `fde implement` wants a hosted or "
            f"remote agent"
        )

    return LocalModelPlan(
        runtime=runtime,
        runtime_reason=reason,
        endpoint=endpoint,
        serve_hint=serve,
        judge_model=_judge_model(budget),
        coder_model=_coder_model(budget),
        budget_gb=round(budget, 1),
        notes=notes,
    )
