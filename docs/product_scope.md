# ZMetrics — Product Scope

## Purpose
ZMetrics is a field-to-report platform for analyzing rock fragmentation (гранулометрический состав) after blast events at quarry operations. It helps blast engineers plan blast work parameters, capture stereo images of the muck pile (развал), process them through an automated CV/ML pipeline, generate granulometric distribution reports, and receive AI-assisted recommendations for future blast parameter optimization.

## Target Users

| Role | Permissions | Primary Actions |
|------|-------------|-----------------|
| **User** | Read only | View reports for assigned quarries |
| **Surveyor (маркшейдер)** | User + capture | Upload stereo frames, trigger analysis |
| **Blaster (Взрывник)** | Surveyor + planning | Manage blast passports, view recommendations, export reports, comment |
| **Admin** | All | User/role management, quarry creation, system administration |

Roles are assigned **per quarry** — a person may be `blaster` at Quarry A and `surveyor` at Quarry B.

## Key User Journeys

### Before Blast
1. Admin creates a `Quarry` and `SiteSection` (blast block).
2. Blaster creates a `BlastPassport` with blast design parameters (burden, spacing, explosive type, hole depth, etc.).
3. Blaster submits the passport; Admin approves it.
4. Passport moves to `ACTIVE` status once blast is authorized.

### After Blast
1. Surveyor creates a `BlastEvent` linked to the passport.
2. Surveyor captures stereo images using ZED 2 → Android app, creating a `CaptureSession`.
3. Images are uploaded (online or offline sync) to the backend.
4. Surveyor or Blaster triggers `AnalysisJob`.
5. Worker processes the pipeline: calibration → rectification → depth → point cloud → segmentation → particle volumes → granulometry.
6. `AnalysisResult` is stored: P10/P50/P80 (mm), Rosin-Rammler parameters, confidence score.
7. A `Report` is generated with a `Recommendation` (always `requires_human_review` status).
8. Blaster reviews the report, reads the recommendation, and decides to accept/reject.

### Recommendation Review
- All AI recommendations start as `requires_human_review`.
- Blaster reads the recommendation and marks it `reviewed → accepted | rejected`.
- Accepted recommendations may inform the next blast passport (manually, by the blaster).
- **System never auto-applies any blast parameters.**

## Out of Scope (current phase)
- Detonator control or blast firing systems
- Integration with drilling/blasting equipment
- Regulatory reporting compliance automation
- Automatic acceptance of any blast parameters

## Regulatory Context
This system is decision-support only. All parameter recommendations are advisory and require explicit human review. Final blast design decisions remain with the licensed blast engineer (Взрывник).
