# ZMetrics — Domain Model

## Entity Hierarchy

```
Quarry (карьер)
  └── SiteSection (участок/блок)
        └── BlastPassport (паспорт БВР)
              └── BlastEvent (взрыв)  [0..1]
                    └── CaptureSession (сессия съемки)
                          ├── Artifact (артефакт: кадры, маски, облако точек, отчет)
                          └── AnalysisJob (задача анализа)
                                └── AnalysisResult (результат: P10/P50/P80, RR)
                                      └── Report (отчет)
                                            ├── Recommendation (рекомендация)
                                            │     └── Comment (комментарий)
                                            └── Artifact (report_file)

Device (устройство) ──── Calibration (калибровка)
     └─────────────────────────────────┘
                  └── CaptureSession

UserProfile ──── QuarryUserAccess ──── Role
                       └── Quarry

AuditLog (only append; tracks passport/role/recommendation changes)
ModelVersion (ML model registry)
```

## BlastPassport State Machine

```
[created]
    ↓
DRAFT ──────────────────────────────────────────────────────── CANCELLED
  │  (blaster submits)
  ↓
SUBMITTED ─────────────────────────────── (admin returns) → DRAFT
  │  (admin approves)
  ↓
APPROVED ──────────────────────────────── (new revision) → SUPERSEDED
  │  (blast authorized)
  ↓
ACTIVE
  │  (blast executed + captured)
  ↓
COMPLETED
```

## Recommendation Status Machine

```
[created by AI system]
          ↓
REQUIRES_HUMAN_REVIEW  ←  Always the initial status (enforced by DB default)
          ↓ (blaster reads)
       REVIEWED
       ↙        ↘
   ACCEPTED    REJECTED
```

**Note**: The system never transitions a recommendation past `requires_human_review` automatically.

## Key Entities

### Quarry
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | PK |
| name | str | Quarry name |
| latitude/longitude | Numeric | Geographic coordinates (optional) |
| deleted_at | DateTime | Soft delete |

### SiteSection (блок/участок)
| Field | Type | Description |
|-------|------|-------------|
| quarry_id | UUID FK | Parent quarry |
| name | str | Section name |
| block_number | str | Blast block designation (e.g., "A1") |

### BlastPassport (паспорт БВР)
| Field | Type | Description |
|-------|------|-------------|
| site_section_id | UUID FK | Target section |
| revision_number | int | Starts at 1, increments on revision |
| superseded_by_id | UUID FK | Points to new revision when SUPERSEDED |
| status | PassportStatus | State machine |
| explosive_type | str | e.g., "ANFO", "Emulite" |
| total_explosive_kg | Numeric(10,3) | Total explosive load |
| hole_diameter_mm | Numeric(8,2) | mm |
| hole_depth_m | Numeric(8,2) | m |
| burden_m | Numeric(8,2) | m |
| spacing_m | Numeric(8,2) | m |
| stemming_m | Numeric(8,2) | m |
| target_p80_mm | Numeric(8,2) | Design target P80 in mm |

### Calibration
Stores stereo camera calibration parameters as JSONB:
- `left_camera_matrix`, `right_camera_matrix`: `{"fx", "fy", "cx", "cy"}`
- `left_dist_coeffs`, `right_dist_coeffs`: `{"k1", "k2", "p1", "p2", "k3"}`
- `rotation_matrix`, `translation_vector`: stereo extrinsics
- `baseline_mm`: camera separation in mm

Using JSONB for flexibility across ZED 2 model variants.

### Artifact Types (ArtifactType enum)
- `left_frame` — raw left stereo image
- `right_frame` — raw right stereo image
- `depth_map` — disparity/depth output (numpy .npy)
- `point_cloud` — 3D point cloud (.ply)
- `mask` — segmentation masks (.json polygon list)
- `particle_list` — per-particle volumes and diameters (.json)
- `report_file` — generated report (PDF/HTML)

### AnalysisResult (metrics stored in mm)
| Field | Type | Description |
|-------|------|-------------|
| p10_mm | Numeric(10,3) | 10th percentile size (mm) |
| p50_mm | Numeric(10,3) | Median size (mm) |
| p80_mm | Numeric(10,3) | 80th percentile size (mm) |
| rosin_rammler_n | Numeric(10,6) | Uniformity index |
| rosin_rammler_xc | Numeric(10,3) | Characteristic size (mm) |
| oversize_percent | Numeric(6,3) | % particles > 500mm |
| fines_percent | Numeric(6,3) | % particles < 25mm |
| confidence_score | Numeric(5,4) | 0.0–1.0 |
| size_distribution | JSONB | `[{size_mm, cumulative_passing_pct}]` |

### QuarryUserAccess
Role is per-quarry. Unique constraint: one active (non-revoked) access per (user, quarry).
Role levels: `user=1`, `surveyor=2`, `blaster=3`, `admin=4`
