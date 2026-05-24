"""User Profile ORM model – stores personal candidate details."""

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class UserProfile(Base):
    """UserProfile model storing candidate details."""

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, default=1)
    name = Column(String, nullable=False, default="")
    email = Column(String, nullable=False, default="")
    phone = Column(String, nullable=True, default="")
    github = Column(String, nullable=True, default="")
    linkedin = Column(String, nullable=True, default="")
    location = Column(String, nullable=True, default="")
    college = Column(String, nullable=True, default="")
    degree = Column(String, nullable=True, default="")
    graduation_year = Column(String, nullable=True, default="")
    coursework = Column(Text, nullable=True, default="")
