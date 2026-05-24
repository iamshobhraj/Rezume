"""UserProfile router – manages candidate profile details."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileResponse, UserProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserProfileResponse)
def get_profile(db: Session = Depends(get_db)):
    """Fetch the candidate profile (auto-seeding a default one if missing)."""
    profile = db.query(UserProfile).first()
    if not profile:
        profile = UserProfile(
            id=1,
            name="Candidate Name",
            email="email@example.com",
            phone="",
            github="",
            linkedin="",
            location="",
            college="",
            degree="",
            graduation_year="",
            coursework="",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put("", response_model=UserProfileResponse)
def update_profile(body: UserProfileUpdate, db: Session = Depends(get_db)):
    """Update candidate profile details."""
    profile = db.query(UserProfile).first()
    if not profile:
        profile = UserProfile(id=1)
        db.add(profile)

    for key, value in body.model_dump().items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile
