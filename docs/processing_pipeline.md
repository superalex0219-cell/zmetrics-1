# ZMetrics — CV/ML Processing Pipeline

## Overview

The analysis pipeline is triggered by an `AnalysisJob`. Each step implements `PipelineStep` from `worker/app/pipeline/interfaces.py`. Steps read/write artifacts in MinIO under `sessions/{capture_session_id}/pipeline/{step_name}/`.

## Pipeline Steps

| Step | Class | Input | Output | Mock / Real |
|------|-------|-------|--------|-------------|
| `calibration_load` | `MockCalibrationStep` | DB `Calibration` record | `calibration_params.json` | Mock: returns fixed ZED 2-like params |
| `rectification` | `MockRectificationStep` | Left/right frames + calibration | `rectified_left.jpg`, `rectified_right.jpg` | Mock: writes placeholder JPEG |
| `depth_estimation` | `MockDepthStep` | Rectified frames | `depth_map.npy` | Mock: random float32 array 2m–8m |
| `point_cloud` | `MockPointCloudStep` | Depth map + calibration | `point_cloud.ply` | Mock: random 5000-point cloud |
| `segmentation` | `MockSegmentationStep` | Left frame | `masks.json` | Mock: random ellipse polygons |
| `particle_volumes` | `MockParticleVolumeStep` | Point cloud + masks | `particle_list.json` | Mock: log-normal distribution |
| `granulometry` | `MockGranulometryStep` | Particle list | `result.json` + DB `AnalysisResult` | Mock: computes real P/RR from synthetic data |

## Artifact Storage Paths

```
MinIO bucket: zmetrics-artifacts
  sessions/{capture_session_id}/
    pipeline/
      calibration_params.json
      rectification/
        rectified_left.jpg
        rectified_right.jpg
      depth/
        depth_map.npy
        depth_stats.json
      pointcloud/
        point_cloud.ply
        meta.json
      segmentation/
        masks.json
      particles/
        particle_list.json
      granulometry/
        result.json

MinIO bucket: zmetrics-frames
  sessions/{capture_session_id}/
    frames/
      left_{frame_index:04d}.jpg
      right_{frame_index:04d}.jpg
```

## Granulometric Distribution

**P-values**: Cumulative passing sizes computed from sorted particle diameter array.
- P10: size at which 10% of material passes (small end)
- P50: median size
- P80: size at which 80% passes (key design target)

**Rosin-Rammler fit**: `R(x) = exp(-(x/xc)^n)`
- `n`: uniformity index (larger = more uniform fragmentation)
- `xc`: characteristic size (mm)
- Fit via linear regression on `ln(-ln(1-F)) = n*ln(x) - n*ln(xc)`

## Real Implementation Notes (future milestones)

### Calibration (M2)
- Read calibration from DB, validate matrix shapes
- OpenCV `stereoRectify()` + `initUndistortRectifyMap()` to compute rectification maps

### Rectification (M2)
- Load left/right frames from MinIO
- Apply `cv2.remap()` with cached rectification maps
- Save rectified pair back to MinIO

### Depth Estimation (M2)
- OpenCV `StereoSGBM` or `StereoBM` disparity computation
- Convert disparity to depth: `Z = f * B / d` (focal length × baseline / disparity)

### Point Cloud (M2)
- `cv2.reprojectImageTo3D(disparity, Q_matrix)`
- Filter out invalid points (disparity = 0 or negative depth)
- Save as Open3D PointCloud, write `.ply` to MinIO

### Segmentation (M3)
- Adapter pattern: `SegmentationAdapter` with implementations for YOLO-seg and SAM
- Input: rectified left frame
- Output: list of instance masks (polygons + bounding boxes)

### Particle Volumes (M3)
- Project 2D masks onto 3D point cloud using depth map
- Compute convex hull volume for each particle cluster
- Fall back to ellipsoid approximation for small clusters

## Step Idempotency Contract

Each step MUST:
1. Check if its output artifact already exists in MinIO before recomputing
2. Return early with `success=True` if artifact exists (avoid duplicate processing)
3. On failure: set `success=False`, fill `error` field, do NOT raise
