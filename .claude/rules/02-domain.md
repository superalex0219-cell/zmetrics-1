---
# Domain Model Rules
---

## Entity Naming
Use these English names consistently in code:
- `quarry` — карьер
- `site_section` — участок/блок
- `blast_passport` — паспорт БВР
- `blast_event` — взрыв (the actual explosion event)
- `capture_session` — сессия съемки
- `artifact` — файл/артефакт (left_frame, right_frame, depth_map, point_cloud, mask, particle_list, report_file)
- `device` — устройство (ZED 2 camera)
- `calibration` — калибровка стереокамеры
- `analysis_job` — задача анализа (Celery job)
- `analysis_result` — результат анализа (P10/P50/P80, Rosin-Rammler)
- `model_version` — версия ML-модели
- `report` — отчет
- `recommendation` — рекомендация по БВР
- `comment` — комментарий
- `user_profile` — профиль пользователя (keycloak sub → local profile)
- `quarry_user_access` — доступ пользователя к карьеру (role is per-quarry)
- `audit_log` — журнал аудита

## Relationships (cardinality)
- `Quarry 1 → M SiteSection`
- `SiteSection 1 → M BlastPassport`
- `BlastPassport 1 → 0..1 BlastEvent` (passport can exist without blast)
- `BlastEvent 1 → M CaptureSession`
- `Device 1 → M Calibration`
- `Device 1 → M CaptureSession`
- `Calibration 1 → M CaptureSession` (one calibration per session)
- `CaptureSession 1 → M Artifact`
- `CaptureSession 1 → M AnalysisJob`
- `AnalysisJob M → 1 ModelVersion`
- `AnalysisJob 1 → 0..1 AnalysisResult`
- `AnalysisResult 1 → 1 Report`
- `Report 1 → M Recommendation`
- `Recommendation 1 → M Comment`

## BlastPassport Versioning
- When a passport is revised: create new record with `revision_number = old.revision_number + 1`
- Set old passport `superseded_by_id = new.id` and `status = SUPERSEDED`
- Write AuditLog entry for the revision event

## Units
- Sizes (P10/P50/P80, hole_diameter, etc.) are always stored in **millimeters**
- Explosive amounts in **kilograms**
- Distances (burden, spacing, depth, stemming) in **meters**
- Volumes in **cubic meters (m³)**
- confidence_score is **0.0–1.0** (dimensionless)
