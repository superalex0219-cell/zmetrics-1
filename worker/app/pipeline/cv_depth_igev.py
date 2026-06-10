"""Real step: stereo depth estimation via IGEV++ (neural stereo matching).

Drop-in replacement for CVStereoDepthStep (same step_name, same output keys):
reads the rectified pair + Q matrix produced by CVRectificationStep, predicts
disparity with IGEV++ on CUDA, reprojects to metric depth via Q.

Selected with DEPTH_BACKEND=igev; the checkpoint comes from IGEV_CKPT_PATH
(mounted into the container, see infra/docker-compose.gpu.yml).
"""
import io
import json
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult, pipeline_prefix

# Architecture hyperparameters of the published igev_plusplus checkpoints
# (defaults of demo_imgs.py in the upstream repo) — must match the weights.
_IGEV_ARGS = dict(
    hidden_dims=[128, 128, 128],
    corr_levels=2,
    corr_radius=4,
    n_downsample=2,
    n_gru_layers=3,
    max_disp=768,
    s_disp_range=48,
    m_disp_range=96,
    l_disp_range=192,
    s_disp_interval=1,
    m_disp_interval=2,
    l_disp_interval=4,
)

_model_cache: dict[str, object] = {}


def _load_model(ckpt_path: str, device: str):
    """Build IGEVStereo and load weights once per worker process."""
    import torch
    from app.pipeline.igev.igev_stereo import IGEVStereo

    cached = _model_cache.get(ckpt_path)
    if cached is not None:
        return cached

    args = SimpleNamespace(
        **_IGEV_ARGS,
        mixed_precision=(device == "cuda"),
        precision_dtype="float16" if device == "cuda" else "float32",
    )
    model = IGEVStereo(args)
    state = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    # Upstream checkpoints were saved from nn.DataParallel → strip "module."
    state = {k.removeprefix("module."): v for k, v in state.items()}
    model.load_state_dict(state, strict=True)
    model.to(device)
    model.eval()
    _model_cache[ckpt_path] = model
    return model


class IGEVDepthStep(PipelineStep):
    step_name = "depth_estimation"

    def __init__(
        self,
        ckpt_path: str,
        *,
        valid_iters: int = 16,
        max_inference_width: int = 1536,
    ) -> None:
        self._ckpt_path = ckpt_path
        self._valid_iters = valid_iters
        # Frames wider than this are downscaled for inference (VRAM/latency);
        # the disparity map is upsampled back and rescaled, so depth stays metric
        # at the calibration resolution.
        self._max_inference_width = max_inference_width

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        import cv2
        import torch

        t0 = time.monotonic()
        base = f"{pipeline_prefix(ctx)}/depth_estimation"
        depth_key = f"{base}/depth_map.npy"
        disp_key = f"{base}/disparity.npy"

        # Idempotency
        try:
            ctx.storage_client.head_object(Bucket=ctx.bucket_artifacts, Key=depth_key)
            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[depth_key, disp_key],
                duration_seconds=time.monotonic() - t0,
                metadata={"cached": True},
            )
        except Exception:
            pass

        try:
            if not Path(self._ckpt_path).is_file():
                raise FileNotFoundError(f"IGEV checkpoint not found: {self._ckpt_path}")

            rect_base = f"{pipeline_prefix(ctx)}/rectification"

            def _read_image(key: str) -> np.ndarray:
                resp = ctx.storage_client.get_object(Bucket=ctx.bucket_artifacts, Key=key)
                arr = np.frombuffer(resp["Body"].read(), dtype=np.uint8)
                return cv2.imdecode(arr, cv2.IMREAD_COLOR)

            img_l = _read_image(f"{rect_base}/rectified_left.jpg")
            img_r = _read_image(f"{rect_base}/rectified_right.jpg")
            full_h, full_w = img_l.shape[:2]

            scale = min(1.0, self._max_inference_width / full_w)
            if scale < 1.0:
                size = (round(full_w * scale), round(full_h * scale))
                img_l = cv2.resize(img_l, size, interpolation=cv2.INTER_AREA)
                img_r = cv2.resize(img_r, size, interpolation=cv2.INTER_AREA)

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = _load_model(self._ckpt_path, device)

            def _to_tensor(img_bgr: np.ndarray) -> torch.Tensor:
                rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                t = torch.from_numpy(rgb).permute(2, 0, 1).float()
                return t[None].to(device)

            from app.pipeline.igev.utils import InputPadder

            t_infer = time.monotonic()
            with torch.inference_mode():
                left_t, right_t = _to_tensor(img_l), _to_tensor(img_r)
                padder = InputPadder(left_t.shape, divis_by=32)
                left_t, right_t = padder.pad(left_t, right_t)
                disp_t = model(left_t, right_t, iters=self._valid_iters, test_mode=True)
                disp_t = padder.unpad(disp_t)
            infer_s = time.monotonic() - t_infer

            disparity = disp_t.cpu().numpy().squeeze().astype(np.float32)
            if scale < 1.0:
                # Disparity is measured in pixels → rescale values with the size.
                disparity = cv2.resize(
                    disparity, (full_w, full_h), interpolation=cv2.INTER_LINEAR
                ) / scale

            # Load Q matrix from rectification step (same as the SGBM path)
            q_resp = ctx.storage_client.get_object(
                Bucket=ctx.bucket_artifacts,
                Key=f"{rect_base}/Q_matrix.json",
            )
            Q = np.array(json.loads(q_resp["Body"].read())["Q"], dtype=np.float64)

            points_3d = cv2.reprojectImageTo3D(disparity, Q)
            depth_map = points_3d[:, :, 2]
            depth_map = np.where(
                (disparity <= 0) | (~np.isfinite(depth_map)) | (depth_map <= 0),
                np.nan,
                depth_map,
            ).astype(np.float32)

            def _upload_npy(key: str, arr: np.ndarray) -> None:
                buf = io.BytesIO()
                np.save(buf, arr)
                buf.seek(0)
                ctx.storage_client.put_object(
                    Bucket=ctx.bucket_artifacts, Key=key,
                    Body=buf.getvalue(), ContentType="application/octet-stream",
                )

            _upload_npy(depth_key, depth_map)
            _upload_npy(disp_key, disparity)

            valid_pixels = int(np.sum(np.isfinite(depth_map)))
            median_depth = float(np.nanmedian(depth_map)) if valid_pixels > 0 else 0.0

            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[depth_key, disp_key],
                duration_seconds=time.monotonic() - t0,
                metadata={
                    "backend": "igev_plusplus",
                    "checkpoint": Path(self._ckpt_path).name,
                    "device": device,
                    "valid_iters": self._valid_iters,
                    "inference_size": f"{img_l.shape[1]}x{img_l.shape[0]}",
                    "inference_seconds": round(infer_s, 3),
                    "valid_pixels": valid_pixels,
                    # depth units follow the calibration translation units (mm for
                    # ZED factory calibration, baseline_mm)
                    "median_depth_mm": round(median_depth, 3),
                },
            )

        except Exception as exc:
            return StepResult(
                step_name=self.step_name, success=False,
                output_artifact_keys=[],
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )
