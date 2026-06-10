"""
SAM3 segmentation step — real instance segmentation using facebook/sam3.

Replaces MockSegmentationStep when a left_frame artifact is available.
Falls back to synthetic mask generation if no frame is found in MinIO,
so the pipeline remains runnable without ZED 2 hardware.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import threading
import time
from typing import TYPE_CHECKING, Any

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult

if TYPE_CHECKING:
    from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level model singleton — loaded once per worker process, never twice
# ---------------------------------------------------------------------------

_model_lock = threading.Lock()
_sam3_processor: Any = None
_sam3_model: Any = None
_sam3_device: str | None = None

_SAM3_REQUIRED_TORCH_ATTR = "float8_e8m0fnu"


def _validate_sam3_runtime(torch_module: Any) -> None:
    """Fail early with a clear message for torch/transformers version mismatches."""
    if hasattr(torch_module, _SAM3_REQUIRED_TORCH_ATTR):
        return

    version = getattr(torch_module, "__version__", "unknown")
    raise RuntimeError(
        "SAM3 requires a newer PyTorch runtime: torch."
        f"{_SAM3_REQUIRED_TORCH_ATTR} is missing in torch {version}. "
        "Rebuild the worker image with the pinned SAM3 dependencies."
    )


def _ensure_model_loaded(model_path: str) -> tuple[Any, Any, str]:
    global _sam3_processor, _sam3_model, _sam3_device

    if _sam3_model is not None:
        return _sam3_processor, _sam3_model, _sam3_device

    with _model_lock:
        if _sam3_model is not None:  # re-check inside lock
            return _sam3_processor, _sam3_model, _sam3_device

        import torch

        _validate_sam3_runtime(torch)

        from transformers import Sam3Model, Sam3Processor

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("sam3_load_start", extra={"model_path": model_path, "device": device})

        processor = Sam3Processor.from_pretrained(model_path)
        model = Sam3Model.from_pretrained(model_path).to(device)
        model.eval()

        _sam3_processor = processor
        _sam3_model = model
        _sam3_device = device

        logger.info("sam3_load_done", extra={"device": device})
        return processor, model, device


# ---------------------------------------------------------------------------
# DB + MinIO helpers (async, run on the event loop)
# ---------------------------------------------------------------------------

async def _fetch_left_frame(ctx: PipelineContext) -> "PILImage.Image | None":
    """Download the first left_frame artifact for this capture session."""
    from PIL import Image
    from sqlalchemy import select

    from app.db_models import Artifact, ArtifactType

    stmt = (
        select(Artifact)
        .where(
            Artifact.capture_session_id == ctx.capture_session_id,
            Artifact.artifact_type == ArtifactType.LEFT_FRAME,
        )
        .order_by(Artifact.frame_index)
        .limit(1)
    )
    result = await ctx.db_session.execute(stmt)
    artifact = result.scalar_one_or_none()

    if artifact is None:
        logger.warning(
            "sam3_no_left_frame_artifact",
            extra={"capture_session_id": str(ctx.capture_session_id)},
        )
        return None

    try:
        resp = ctx.storage_client.get_object(
            Bucket=artifact.storage_bucket, Key=artifact.storage_key
        )
        image_bytes = resp["Body"].read()
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        logger.warning(
            "sam3_frame_download_failed",
            extra={"storage_key": artifact.storage_key, "error": str(exc)},
        )
        return None


# ---------------------------------------------------------------------------
# CPU-bound inference (runs in executor so event loop stays unblocked)
# ---------------------------------------------------------------------------

def _run_inference(
    image: "PILImage.Image",
    processor: Any,
    model: Any,
    device: str,
    text_prompt: str,
    threshold: float,
) -> dict:
    import torch

    inputs = processor(images=image, text=text_prompt, return_tensors="pt")

    # Extract original_sizes before moving tensors to device (needed for post-processing)
    if "original_sizes" in inputs:
        original_sizes = inputs["original_sizes"].tolist()
    else:
        original_sizes = [[image.height, image.width]]

    inputs = {k: v.to(device) if hasattr(v, "to") else v for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    results = processor.post_process_instance_segmentation(
        outputs,
        threshold=threshold,
        mask_threshold=threshold,
        target_sizes=original_sizes,
    )[0]

    masks_list = _convert_to_mask_format(results, image.width, image.height)
    return {"n_masks": len(masks_list), "masks": masks_list, "source": "sam3"}


def _convert_to_mask_format(results: dict, width: int, height: int) -> list[dict]:
    """Convert SAM3 output tensors to our masks.json schema."""
    import cv2

    masks_out = []
    for idx, (mask_tensor, score) in enumerate(
        zip(results.get("masks", []), results.get("scores", []))
    ):
        mask_np = mask_tensor.cpu().numpy().astype(np.uint8)

        # Bounding box from non-zero pixels
        rows = np.any(mask_np, axis=1)
        cols = np.any(mask_np, axis=0)
        if not rows.any():
            continue
        y1, y2 = int(np.where(rows)[0][[0, -1]].tolist()[0]), int(np.where(rows)[0][[0, -1]].tolist()[1])
        x1, x2 = int(np.where(cols)[0][[0, -1]].tolist()[0]), int(np.where(cols)[0][[0, -1]].tolist()[1])

        bbox_norm = [
            float(x1) / width,
            float(y1) / height,
            float(x2) / width,
            float(y2) / height,
        ]

        # Polygon approximation via Douglas-Peucker on the largest contour
        contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            eps = 0.005 * cv2.arcLength(largest, closed=True)
            approx = cv2.approxPolyDP(largest, eps, closed=True)
            polygon = [
                [float(pt[0][0]) / width, float(pt[0][1]) / height]
                for pt in approx
            ]
        else:
            polygon = [
                [bbox_norm[0], bbox_norm[1]],
                [bbox_norm[2], bbox_norm[1]],
                [bbox_norm[2], bbox_norm[3]],
                [bbox_norm[0], bbox_norm[3]],
            ]

        masks_out.append({
            "id": idx,
            "bbox_normalized": bbox_norm,
            "polygon_normalized": polygon,
            "confidence": float(score),
        })

    return masks_out


# ---------------------------------------------------------------------------
# Synthetic fallback (no image available — keeps pipeline runnable)
# ---------------------------------------------------------------------------

def _synthetic_fallback(capture_session_id: Any) -> dict:
    rng = np.random.default_rng(seed=int(str(capture_session_id).replace("-", "")[:8], 16))
    n = int(rng.integers(80, 200))
    masks = []
    for i in range(n):
        cx, cy = float(rng.uniform(0.05, 0.95)), float(rng.uniform(0.05, 0.95))
        rx, ry = float(rng.uniform(0.01, 0.08)), float(rng.uniform(0.01, 0.06))
        angles = [k * 3.14159 / 4 for k in range(8)]
        polygon = [[cx + rx * float(np.cos(a)), cy + ry * float(np.sin(a))] for a in angles]
        masks.append({
            "id": i,
            "bbox_normalized": [cx - rx, cy - ry, cx + rx, cy + ry],
            "polygon_normalized": polygon,
            "confidence": float(rng.uniform(0.70, 0.99)),
        })
    return {"n_masks": len(masks), "masks": masks, "source": "synthetic_fallback"}


# ---------------------------------------------------------------------------
# PipelineStep implementation
# ---------------------------------------------------------------------------

class Sam3SegmentationStep(PipelineStep):
    """
    Instance segmentation of rock particles using SAM3.

    If a left_frame artifact exists in MinIO → runs real SAM3 inference.
    If no frame is available → falls back to synthetic masks (same as mock),
    so downstream steps (particle_volumes, granulometry) still have data.
    """

    step_name = "segmentation"

    def __init__(
        self,
        model_path: str = "facebook/sam3",
        text_prompt: str = "rock fragment",
        threshold: float = 0.5,
    ) -> None:
        self._model_path = model_path
        self._text_prompt = text_prompt
        self._threshold = threshold

    async def execute(
        self, ctx: PipelineContext, previous_results: list[StepResult]
    ) -> StepResult:
        t0 = time.monotonic()
        output_key = f"sessions/{ctx.capture_session_id}/pipeline/segmentation/masks.json"

        # Idempotency: skip if artifact already written
        try:
            ctx.storage_client.head_object(Bucket=ctx.bucket_artifacts, Key=output_key)
            logger.info("sam3_cached", extra={"key": output_key})
            return StepResult(
                step_name=self.step_name,
                success=True,
                output_artifact_keys=[output_key],
                duration_seconds=time.monotonic() - t0,
                metadata={"cached": True},
            )
        except Exception:
            pass

        # Try to get a real frame
        image = await _fetch_left_frame(ctx)

        if image is not None:
            # Run heavy inference in a thread pool so we don't block the event loop
            try:
                processor, model, device = _ensure_model_loaded(self._model_path)
                loop = asyncio.get_event_loop()
                masks_data = await loop.run_in_executor(
                    None,
                    _run_inference,
                    image,
                    processor,
                    model,
                    device,
                    self._text_prompt,
                    self._threshold,
                )
                source = "sam3"
            except Exception as exc:
                logger.error("sam3_inference_failed", extra={"error": str(exc)})
                return StepResult(
                    step_name=self.step_name,
                    success=False,
                    output_artifact_keys=[],
                    duration_seconds=time.monotonic() - t0,
                    error=f"SAM3 inference error: {exc}",
                )
        else:
            # No frame → synthetic fallback, pipeline keeps running
            logger.warning(
                "sam3_using_synthetic_fallback",
                extra={"capture_session_id": str(ctx.capture_session_id)},
            )
            masks_data = _synthetic_fallback(ctx.capture_session_id)
            source = "synthetic_fallback"

        ctx.storage_client.put_object(
            Bucket=ctx.bucket_artifacts,
            Key=output_key,
            Body=json.dumps(masks_data).encode(),
            ContentType="application/json",
        )

        return StepResult(
            step_name=self.step_name,
            success=True,
            output_artifact_keys=[output_key],
            duration_seconds=time.monotonic() - t0,
            metadata={
                "n_particles_detected": masks_data["n_masks"],
                "source": source,
            },
        )
