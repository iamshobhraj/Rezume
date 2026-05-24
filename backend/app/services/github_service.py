"""GitHub service – fetches user's merged PRs and creates OSS Projects."""

import logging
import uuid
import httpx
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models.project import Project
from app.models.github_user import GithubUser
from app.services.ingestion import ingestion_service
from app.providers.manager import ProviderManager

logger = logging.getLogger(__name__)


class GithubService:
    """Fetches merged PRs from GitHub and converts them into OSS Projects."""

    def __init__(self):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.github_token:
            self.headers["Authorization"] = f"Bearer {settings.github_token}"

    async def fetch_oss_contributions(self, db: Session, username: str) -> dict:
        """Fetch merged PRs for a user and save them as OSS Projects."""
        
        # Initialize/configure ingestion service
        ingestion_service.db = db
        ingestion_service.pm = ProviderManager(db)

        # Check if we fetched recently (simple rate limiting logic could go here)
        github_user = db.query(GithubUser).filter(GithubUser.username == username).first()
        if not github_user:
            github_user = GithubUser(username=username)
            db.add(github_user)

        # Query merged PRs
        query = f"author:{username} type:pr is:merged"
        url = "https://api.github.com/search/issues"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params={"q": query, "per_page": 10}, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"GitHub API error: {response.text}")
                return {"success": False, "error": f"GitHub API error: {response.status_code}"}
                
            data = response.json()
            items = data.get("items", [])
            
            created_count = 0
            for item in items:
                pr_url = item.get("html_url")
                
                # Check if this PR already exists based on github_url
                existing = db.query(Project).filter(Project.github_url == pr_url).first()
                if existing:
                    continue
                
                title = item.get("title", "OSS Contribution")
                repo_url = item.get("repository_url", "")
                repo_name = repo_url.split("/")[-1] if repo_url else "Open Source"
                body = item.get("body", "")
                
                # Fetch diff or files if we want a richer snapshot
                # For now, using the PR body and title as the raw text
                raw_text = f"Repository: {repo_name}\nPull Request: {title}\nURL: {pr_url}\n\nDescription:\n{body}"
                
                project = Project(
                    id=str(uuid.uuid4()),
                    title=f"PR: {title}",
                    company=repo_name,
                    role="Open Source Contributor",
                    date_range=item.get("closed_at", "").split("T")[0],
                    raw_text=raw_text,
                    project_type="oss",
                    priority=4,  # Give OSS a slightly higher default priority
                    github_url=pr_url,
                )
                db.add(project)
                db.flush()
                
                # Ingest it
                try:
                    ingestion_service.ingest_project(project.id)
                    created_count += 1
                except Exception as e:
                    logger.error(f"Failed to ingest OSS project {project.id}: {e}")
            
            github_user.last_fetch_stamp = datetime.utcnow()
            db.commit()
            
            return {
                "success": True, 
                "message": f"Fetched {len(items)} PRs, created {created_count} new OSS projects.",
                "created_count": created_count
            }

github_service = GithubService()
