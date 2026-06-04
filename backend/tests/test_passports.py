"""Tests: blast passport CRUD and revision logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from app.db.models.passport import BlastPassport, PassportStatus
from app.db.models.quarry import Quarry, SiteSection
from app.db.models.user import QuarryUserAccess, Role, UserProfile
from app.services.passport import create_revision


@pytest_asyncio.fixture
async def setup_quarry(db_session):
    """Create a quarry, section, user, and role for tests."""
    quarry = Quarry(name="Test Quarry")
    db_session.add(quarry)
    await db_session.flush()

    section = SiteSection(quarry_id=quarry.id, name="Block A", block_number="A1")
    db_session.add(section)
    await db_session.flush()

    role = Role(name="blaster", level=3)
    db_session.add(role)
    await db_session.flush()

    user = UserProfile(
        keycloak_sub="blaster-sub-001",
        email="blaster@zmetrics.local",
        full_name="Test Blaster",
    )
    db_session.add(user)
    await db_session.flush()

    access = QuarryUserAccess(
        user_id=user.id,
        quarry_id=quarry.id,
        role_id=role.id,
    )
    db_session.add(access)
    await db_session.flush()

    return {"quarry": quarry, "section": section, "user": user, "role": role}


@pytest.mark.asyncio
async def test_create_passport_defaults_to_draft(db_session, setup_quarry):
    data = setup_quarry
    passport = BlastPassport(
        site_section_id=data["section"].id,
        created_by_id=data["user"].id,
        explosive_type="ANFO",
        total_explosive_kg=500.0,
    )
    db_session.add(passport)
    await db_session.flush()

    assert passport.status == PassportStatus.DRAFT
    assert passport.revision_number == 1
    assert passport.superseded_by_id is None


@pytest.mark.asyncio
async def test_passport_revision_supersedes_original(db_session, setup_quarry):
    data = setup_quarry
    original = BlastPassport(
        site_section_id=data["section"].id,
        created_by_id=data["user"].id,
        explosive_type="ANFO",
        total_explosive_kg=500.0,
        burden_m=3.0,
    )
    db_session.add(original)
    await db_session.flush()

    new_revision = await create_revision(
        db_session,
        original,
        {"burden_m": 3.5, "total_explosive_kg": 550.0},
        data["user"].id,
    )

    assert new_revision.revision_number == 2
    assert new_revision.status == PassportStatus.DRAFT
    assert new_revision.burden_m == 3.5
    assert new_revision.total_explosive_kg == 550.0

    assert original.status == PassportStatus.SUPERSEDED
    assert original.superseded_by_id == new_revision.id


@pytest.mark.asyncio
async def test_passport_recommendation_status_safety(db_session):
    """Recommendations must always start as requires_human_review."""
    from app.db.models.report import Recommendation, RecommendationStatus

    rec = Recommendation(
        report_id=uuid.uuid4(),  # FK not enforced in SQLite test
        recommendation_text="Reduce burden by 0.3m",
    )
    assert rec.status == RecommendationStatus.REQUIRES_HUMAN_REVIEW
