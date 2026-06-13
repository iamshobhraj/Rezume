"""UserSkill CRUD endpoints – manage the candidate's skill inventory."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_skill import UserSkill
from app.schemas.project import UserSkillCreate, UserSkillResponse, UserSkillUpdate

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[UserSkillResponse])
def list_skills(db: Session = Depends(get_db)):
    """List all user skills, ordered by category then name."""
    skills = db.query(UserSkill).order_by(UserSkill.category, UserSkill.skill_name).all()
    return skills


@router.post("", response_model=UserSkillResponse, status_code=201)
def create_skill(body: UserSkillCreate, db: Session = Depends(get_db)):
    """Add a new skill to the inventory."""
    # Check for duplicates
    existing = (
        db.query(UserSkill)
        .filter(UserSkill.skill_name == body.skill_name, UserSkill.category == body.category)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Skill '{body.skill_name}' already exists in category '{body.category}'",
        )

    skill = UserSkill(
        skill_name=body.skill_name,
        category=body.category,
        proficiency=body.proficiency,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.post("/bulk", response_model=list[UserSkillResponse], status_code=201)
def create_skills_bulk(body: list[UserSkillCreate], db: Session = Depends(get_db)):
    """Add multiple skills at once, skipping duplicates."""
    created = []
    for item in body:
        existing = (
            db.query(UserSkill)
            .filter(UserSkill.skill_name == item.skill_name, UserSkill.category == item.category)
            .first()
        )
        if existing:
            continue
        skill = UserSkill(
            skill_name=item.skill_name,
            category=item.category,
            proficiency=item.proficiency,
        )
        db.add(skill)
        created.append(skill)

    db.commit()
    for s in created:
        db.refresh(s)
    return created


@router.put("/{skill_id}", response_model=UserSkillResponse)
def update_skill(skill_id: int, body: UserSkillUpdate, db: Session = Depends(get_db)):
    """Update an existing skill."""
    skill = db.query(UserSkill).get(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(skill, key, value)

    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/{skill_id}")
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    """Delete a skill from the inventory."""
    skill = db.query(UserSkill).get(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    name = skill.skill_name
    db.delete(skill)
    db.commit()
    return {"detail": f"Skill '{name}' deleted"}
