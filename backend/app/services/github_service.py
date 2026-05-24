"""GitHub service – fetches user's merged PRs and creates OSS Projects."""

import logging
import uuid
import httpx
from datetime import datetime
import json

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
            
            # Group items by organization to build the requested OSS data model
            orgs = {}
            for item in items:
                repo_url = item.get("repository_url", "")
                parts = repo_url.split("/")
                repo_name = parts[-1] if len(parts) > 0 else "Unknown"
                org_name = parts[-2] if len(parts) > 1 else "Unknown"
                
                if org_name not in orgs:
                    orgs[org_name] = {
                        "org": org_name,
                        "ecosystem": f"{org_name.capitalize()} Ecosystem",
                        "org_github": f"github.com/{org_name}",
                        "repos": set(),
                        "prs": [],
                        "start_date": item.get("created_at", ""),
                        "end_date": item.get("closed_at", "")
                    }
                orgs[org_name]["repos"].add(repo_name)
                
                title = item.get("title", "")
                html_url = item.get("html_url", "")
                orgs[org_name]["prs"].append(f"{title} ({html_url})")
                
                created_at = item.get("created_at", "")
                closed_at = item.get("closed_at", "")
                if created_at and created_at < orgs[org_name]["start_date"]:
                    orgs[org_name]["start_date"] = created_at
                if closed_at and closed_at > orgs[org_name]["end_date"]:
                    orgs[org_name]["end_date"] = closed_at

            created_count = 0
            for org_name, org_data in orgs.items():
                start_year = org_data["start_date"][:4] if org_data["start_date"] else ""
                end_year = org_data["end_date"][:4] if org_data["end_date"] else "Present"
                duration = f"{start_year} - {end_year}" if start_year != end_year else start_year
                
                oss_profile_entry = {
                    "org": org_data["org"],
                    "ecosystem": org_data["ecosystem"],
                    "org_github": org_data["org_github"],
                    "duration": duration,
                    "repos": list(org_data["repos"]),
                    "contributions": org_data["prs"]
                }
                
                project_id = f"oss-{org_name}"
                existing = db.query(Project).filter(Project.id == project_id).first()
                if not existing:
                    project = Project(
                        id=project_id,
                        title=f"{org_name.capitalize()} OSS Contributions",
                        company=org_name,
                        role="Open Source Contributor",
                        date_range=duration,
                        raw_text=json.dumps(oss_profile_entry, indent=2),
                        project_type="oss",
                        priority=4,
                        github_url=f"https://{org_data['org_github']}"
                    )
                    db.add(project)
                    db.flush()
                    try:
                        ingestion_service.ingest_project(project.id)
                        created_count += 1
                    except Exception as e:
                        logger.error(f"Failed to ingest OSS project {project_id}: {e}")
                else:
                    existing.raw_text = json.dumps(oss_profile_entry, indent=2)
                    existing.date_range = duration
                    db.flush()
                    # Re-ingest the updated project
                    try:
                        ingestion_service.ingest_project(project_id)
                    except Exception as e:
                        logger.error(f"Failed to re-ingest OSS project {project_id}: {e}")
            
            github_user.last_fetch_stamp = datetime.utcnow()
            db.commit()
            
            return {
                "success": True, 
                "message": f"Fetched {len(items)} PRs, created {created_count} new OSS projects.",
                "created_count": created_count
            }

github_service = GithubService()
