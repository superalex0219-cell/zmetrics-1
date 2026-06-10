"""
Pipeline step interface. All CV/ML processing steps implement PipelineStep.

Real implementations replace mock_*.py files without changing task orchestration code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class PipelineContext:
    """Shared context passed to every pipeline step."""
    job_id: UUID
    capture_session_id: UUID
    storage_client: Any        # boto3 S3 client
    db_session: Any            # AsyncSession
    config: dict = field(default_factory=dict)
    # Resolved MinIO bucket names
    bucket_frames: str = "zmetrics-frames"
    bucket_artifacts: str = "zmetrics-artifacts"


@dataclass
class StepResult:
    """Result returned by each pipeline step."""
    step_name: str
    success: bool
    output_artifact_keys: list[str]  # MinIO keys written by this step
    duration_seconds: float
    metadata: dict = field(default_factory=dict)
    error: str | None = None


class PipelineStep(ABC):
    """Abstract base for all pipeline stages."""

    @property
    @abstractmethod
    def step_name(self) -> str:
        """Unique identifier for this step."""
        ...

    @abstractmethod
    async def execute(
        self,
        ctx: PipelineContext,
        previous_results: list[StepResult],
    ) -> StepResult:
        """
        Execute this step.

        Rules:
        - Read inputs from MinIO via ctx.storage_client.
        - Write outputs to MinIO under sessions/{capture_session_id}/pipeline/{step_name}/.
        - Must be idempotent: check if output artifact exists before recomputing.
        - Return StepResult. Set success=False on failure; never raise — caller handles it.
        """
        ...


def ctx_frame_index(ctx: PipelineContext) -> int:
    """Frame pair index this job analyzes (CAP-MULTI series; 0 for legacy jobs)."""
    return int(ctx.config.get("frame_index") or 0)


def pipeline_prefix(ctx: PipelineContext) -> str:
    """MinIO prefix for this job's pipeline artifacts.

    Frame 0 keeps the historical ``sessions/{id}/pipeline`` prefix (idempotency
    with pre-CAP-MULTI artifacts); other frame pairs get their own subtree so
    that per-pair jobs of one session never collide.
    """
    base = f"sessions/{ctx.capture_session_id}/pipeline"
    idx = ctx_frame_index(ctx)
    return base if idx == 0 else f"{base}/f{idx:04d}"


class PipelineStepError(Exception):
    def __init__(self, step_name: str, result: StepResult) -> None:
        self.step_name = step_name
        self.result = result
        super().__init__(f"Pipeline step '{step_name}' failed: {result.error}")


class Pipeline:
    """Runs a sequence of PipelineStep instances, collecting results."""

    def __init__(self, steps: list[PipelineStep]) -> None:
        self.steps = steps

    async def run(self, ctx: PipelineContext) -> list[StepResult]:
        results: list[StepResult] = []
        for step in self.steps:
            result = await step.execute(ctx, results)
            results.append(result)
            if not result.success:
                raise PipelineStepError(step.step_name, result)
        return results
