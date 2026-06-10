"""Tests: CVParticleVolumeStep and CVGranulometryStep (real granulometry path)."""

from __future__ import annotations

import io
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from app.pipeline.cv_granulometry import CVGranulometryStep, _confidence
from app.pipeline.cv_particles import CVParticleVolumeStep
from app.pipeline.interfaces import PipelineContext, StepResult

# ---------------------------------------------------------------------------
# Fixtures: in-memory S3 + a distortion-free synthetic calibration
# ---------------------------------------------------------------------------

W, H = 200, 150
FX = 100.0
BASELINE_MM = 120.0
DEPTH_MM = 2000.0


def make_s3():
    storage: dict[str, bytes] = {}
    mock = MagicMock()

    def put_object(Bucket, Key, Body, **kwargs):
        storage[f"{Bucket}/{Key}"] = Body if isinstance(Body, bytes) else Body.read()

    def get_object(Bucket, Key):
        if f"{Bucket}/{Key}" not in storage:
            raise KeyError(Key)
        data = storage[f"{Bucket}/{Key}"]
        return {"Body": MagicMock(read=lambda: data)}

    mock.put_object.side_effect = put_object
    mock.get_object.side_effect = get_object
    mock.head_object.side_effect = Exception("404")  # force recompute
    mock._storage = storage
    return mock


def make_db(calibration_id=None):
    db = MagicMock()
    row = None
    if calibration_id is not None:
        row = MagicMock()
        row.calibration_id = calibration_id
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    return db


def make_ctx(s3, db=None) -> PipelineContext:
    return PipelineContext(
        job_id=uuid.uuid4(),
        capture_session_id=uuid.uuid4(),
        storage_client=s3,
        db_session=db or make_db(),
    )


def seed_session_artifacts(s3, ctx, masks: list[dict], mask_source: str = "sam3") -> None:
    """Write calibration_params.json, depth_map.npy and masks.json."""
    base = f"sessions/{ctx.capture_session_id}/pipeline"
    cam = {"fx": FX, "fy": FX, "cx": W / 2, "cy": H / 2}
    dist = {"k1": 0.0, "k2": 0.0, "p1": 0.0, "p2": 0.0, "k3": 0.0}
    cal = {
        "baseline_mm": BASELINE_MM,
        "image_width_px": W,
        "image_height_px": H,
        "left_camera_matrix": cam,
        "right_camera_matrix": cam,
        "left_dist_coeffs": dist,
        "right_dist_coeffs": dist,
        "rotation_matrix": {"data": np.eye(3).tolist()},
        # mm units → unit_to_mm == 1.0
        "translation_vector": {"data": [[-BASELINE_MM], [0.0], [0.0]]},
    }
    s3.put_object(
        Bucket=ctx.bucket_artifacts,
        Key=f"{base}/calibration_params.json",
        Body=json.dumps(cal).encode(),
    )

    depth = np.full((H, W), DEPTH_MM, dtype=np.float32)
    buf = io.BytesIO()
    np.save(buf, depth)
    s3.put_object(
        Bucket=ctx.bucket_artifacts,
        Key=f"{base}/depth_estimation/depth_map.npy",
        Body=buf.getvalue(),
    )

    s3.put_object(
        Bucket=ctx.bucket_artifacts,
        Key=f"{base}/segmentation/masks.json",
        Body=json.dumps(
            {"n_masks": len(masks), "masks": masks, "source": mask_source}
        ).encode(),
    )


def square_mask(mask_id: int, x1: float, y1: float, x2: float, y2: float, conf: float = 0.9) -> dict:
    return {
        "id": mask_id,
        "bbox_normalized": [x1, y1, x2, y2],
        "polygon_normalized": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
        "confidence": conf,
    }


def depth_step_result(backend: str = "igev_plusplus", ckpt: str = "sceneflow.pth") -> StepResult:
    return StepResult(
        step_name="depth_estimation",
        success=True,
        output_artifact_keys=[],
        duration_seconds=0.0,
        metadata={"backend": backend, "checkpoint": ckpt},
    )


# ---------------------------------------------------------------------------
# CVParticleVolumeStep
# ---------------------------------------------------------------------------

async def test_cv_particles_metric_size_from_depth():
    s3 = make_s3()
    cal_id = uuid.uuid4()
    ctx = make_ctx(s3, make_db(calibration_id=cal_id))
    # 40x60 px square at constant 2000mm depth
    seed_session_artifacts(s3, ctx, [square_mask(0, 0.2, 0.2, 0.4, 0.6)])

    result = await CVParticleVolumeStep().execute(ctx, [depth_step_result()])

    assert result.success, result.error
    assert result.metadata["n_particles"] == 1
    assert result.metadata["mask_source"] == "sam3"

    payload = json.loads(s3._storage[f"{ctx.bucket_artifacts}/{result.output_artifact_keys[0]}"])
    assert payload["source"] == "cv"
    assert payload["depth_backend"] == "igev_plusplus/sceneflow.pth"
    assert payload["calibration_id"] == str(cal_id)

    p = payload["particles"][0]
    # Analytic expectation with the original focal (rectified focal is close
    # for an identity-R, distortion-free rig): 40x60px @ 20mm/px →
    # area ≈ 0.96e6 mm², d_eq ≈ 1105 mm. Allow 20% for rectification scaling.
    assert p["equivalent_diameter_mm"] == pytest.approx(1105.0, rel=0.2)
    assert p["median_depth_mm"] == pytest.approx(DEPTH_MM, rel=0.05)
    assert p["major_axis_mm"] > p["minor_axis_mm"] > 0
    assert p["volume_m3"] > 0
    assert 0.99 <= p["depth_coverage"] <= 1.0


async def test_cv_particles_skips_unreliable_masks():
    s3 = make_s3()
    ctx = make_ctx(s3)
    masks = [
        square_mask(0, 0.2, 0.2, 0.4, 0.6),       # good
        square_mask(1, 0.5, 0.5, 0.51, 0.51),     # tiny → too_small
        {"id": 2, "bbox_normalized": [0, 0, 0, 0], "polygon_normalized": [[0.1, 0.1]], "confidence": 0.5},
    ]
    seed_session_artifacts(s3, ctx, masks)

    # Poke a hole in the depth under a third region to exercise coverage skip
    base = f"sessions/{ctx.capture_session_id}/pipeline"
    depth = np.full((H, W), DEPTH_MM, dtype=np.float32)
    depth[100:140, 120:180] = np.nan
    buf = io.BytesIO()
    np.save(buf, depth)
    s3.put_object(Bucket=ctx.bucket_artifacts, Key=f"{base}/depth_estimation/depth_map.npy", Body=buf.getvalue())
    masks.append(square_mask(3, 0.6, 0.67, 0.9, 0.93))  # over the NaN hole
    s3.put_object(
        Bucket=ctx.bucket_artifacts,
        Key=f"{base}/segmentation/masks.json",
        Body=json.dumps({"n_masks": len(masks), "masks": masks, "source": "sam3"}).encode(),
    )

    result = await CVParticleVolumeStep().execute(ctx, [depth_step_result()])

    assert result.success, result.error
    assert result.metadata["n_particles"] == 1
    skipped = result.metadata["n_skipped"]
    assert skipped["too_small"] >= 1
    assert skipped["degenerate_polygon"] == 1
    assert skipped["low_depth_coverage"] >= 1


async def test_cv_particles_empty_masks_is_honest_empty_result():
    s3 = make_s3()
    ctx = make_ctx(s3)
    seed_session_artifacts(s3, ctx, [])

    result = await CVParticleVolumeStep().execute(ctx, [depth_step_result()])

    assert result.success, result.error
    assert result.metadata["n_particles"] == 0
    payload = json.loads(s3._storage[f"{ctx.bucket_artifacts}/{result.output_artifact_keys[0]}"])
    assert payload["particles"] == []
    assert payload["total_volume_m3"] == 0.0


# ---------------------------------------------------------------------------
# CVGranulometryStep
# ---------------------------------------------------------------------------

def seed_particle_list(s3, ctx, particles: list[dict], **overrides) -> None:
    payload = {
        "source": "cv",
        "mask_source": "sam3",
        "depth_backend": "igev_plusplus/sceneflow.pth",
        "calibration_id": str(uuid.uuid4()),
        "n_particles": len(particles),
        "n_masks_input": len(particles),
        "n_skipped": {"too_small": 0, "low_depth_coverage": 0, "degenerate_polygon": 0},
        "total_volume_m3": sum(p["volume_m3"] for p in particles),
        "mean_depth_coverage": 0.95,
        "mean_segmentation_confidence": 0.9,
        "particles": particles,
    }
    payload.update(overrides)
    s3.put_object(
        Bucket=ctx.bucket_artifacts,
        Key=f"sessions/{ctx.capture_session_id}/pipeline/particles/particle_list.json",
        Body=json.dumps(payload).encode(),
    )


async def test_cv_granulometry_is_volume_weighted():
    s3 = make_s3()
    ctx = make_ctx(s3)
    # Two particles: d=100mm with 10% of volume, d=200mm with 90%.
    seed_particle_list(s3, ctx, [
        {"equivalent_diameter_mm": 100.0, "volume_m3": 0.001},
        {"equivalent_diameter_mm": 200.0, "volume_m3": 0.009},
    ])

    result = await CVGranulometryStep().execute(ctx, [])

    assert result.success, result.error
    payload = json.loads(s3._storage[f"{ctx.bucket_artifacts}/{result.output_artifact_keys[0]}"])
    assert payload["analysis_method"] == "cv"
    # Volume-weighted: cum passing is 10% at 100mm, 100% at 200mm
    # → P50 = 100 + (50-10)/(100-10)*100 ≈ 144.444 (count-weighted would be 150)
    assert payload["p10_mm"] == pytest.approx(100.0, abs=0.01)
    assert payload["p50_mm"] == pytest.approx(144.444, abs=0.01)
    assert payload["p80_mm"] == pytest.approx(177.778, abs=0.01)
    assert payload["total_particles_counted"] == 2
    assert "calibration_id=" in payload["confidence_notes"]
    assert "segmentation=sam3" in payload["confidence_notes"]
    # AnalysisResult row was created
    ctx.db_session.add.assert_called_once()
    ctx.db_session.flush.assert_awaited()


async def test_cv_granulometry_empty_particles_writes_null_result():
    s3 = make_s3()
    ctx = make_ctx(s3)
    seed_particle_list(s3, ctx, [])

    result = await CVGranulometryStep().execute(ctx, [])

    assert result.success, result.error
    payload = json.loads(s3._storage[f"{ctx.bucket_artifacts}/{result.output_artifact_keys[0]}"])
    assert payload["p10_mm"] is None
    assert payload["p80_mm"] is None
    assert payload["total_particles_counted"] == 0
    assert payload["confidence_score"] == 0.0
    assert payload["confidence_notes"].startswith("⚠ No particles measured")


def test_confidence_scales_with_sample_size_and_coverage():
    base = {
        "mask_source": "sam3",
        "depth_backend": "igev_plusplus/sceneflow.pth",
        "calibration_id": "cal-1",
        "n_skipped": {},
    }
    score_big, notes_big = _confidence({
        **base, "n_particles": 60,
        "mean_segmentation_confidence": 0.9, "mean_depth_coverage": 0.95,
    })
    assert score_big == pytest.approx(0.9 * 0.95)
    assert "Real CV pipeline" in notes_big

    score_small, notes_small = _confidence({
        **base, "n_particles": 3,
        "mean_segmentation_confidence": 0.9, "mean_depth_coverage": 0.95,
    })
    assert score_small < score_big
    assert "Low confidence" in notes_small


def test_confidence_capped_for_synthetic_fallback_masks():
    score, notes = _confidence({
        "mask_source": "synthetic_fallback",
        "depth_backend": "igev_plusplus/sceneflow.pth",
        "calibration_id": "cal-1",
        "n_particles": 100,
        "mean_segmentation_confidence": 0.95,
        "mean_depth_coverage": 0.99,
        "n_skipped": {},
    })
    assert score <= 0.2
    assert notes.startswith("⚠ Synthetic fallback masks")
