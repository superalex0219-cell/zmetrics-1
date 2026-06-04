from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models here so Alembic can detect them during autogenerate.
# Order matters: base tables before dependent ones.
from app.db.models.user import QuarryUserAccess, Role, UserProfile  # noqa: E402, F401
from app.db.models.quarry import Quarry, SiteSection  # noqa: E402, F401
from app.db.models.passport import BlastPassport  # noqa: E402, F401
from app.db.models.blast import BlastEvent, Calibration, Device  # noqa: E402, F401
from app.db.models.capture import CaptureSession  # noqa: E402, F401
from app.db.models.artifact import Artifact  # noqa: E402, F401
from app.db.models.analysis import AnalysisJob, AnalysisResult, ModelVersion  # noqa: E402, F401
from app.db.models.report import Comment, Recommendation, Report  # noqa: E402, F401
from app.db.models.audit import AuditLog  # noqa: E402, F401
