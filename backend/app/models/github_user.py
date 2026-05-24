"""GitHub User ORM model – stores the fetch timestamp for a user."""

import datetime

from sqlalchemy import Column, DateTime, String

from app.database import Base


class GithubUser(Base):
    """A GitHub user and their last fetched timestamp."""

    __tablename__ = "github_users"

    username = Column(String, primary_key=True)
    last_fetch_stamp = Column(DateTime, default=datetime.datetime.utcnow)
