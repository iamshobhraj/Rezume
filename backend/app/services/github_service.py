"""GitHub service – fetches user's merged PRs and creates OSS WorkEntries."""

import logging
import uuid
import httpx
from datetime import datetime
import json

from sqlalchemy.orm import Session

from app.config import settings
from app.models.work_entry import WorkEntry, EntryType
from app.models.github_user import GithubUser
from app.services.ingestion import ingestion_service
from app.providers.manager import ProviderManager

logger = logging.getLogger(__name__)


class GithubService:
    """Fetches merged PRs from GitHub and converts them into OSS WorkEntries."""

    def __init__(self):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.github_token:
            self.headers["Authorization"] = f"Bearer {settings.github_token}"

    async def fetch_oss_contributions(self, db: Session, username: str) -> dict:
        """Fetch merged PRs for a user and save them as OSS WorkEntries."""
        
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
                start_year = org_data["start_date"][:7] if org_data["start_date"] else ""  # YYYY-MM
                end_year = org_data["end_date"][:7] if org_data["end_date"] else "present"
                
                oss_profile_entry = {
                    "org": org_data["org"],
                    "ecosystem": org_data["ecosystem"],
                    "org_github": org_data["org_github"],
                    "duration": f"{start_year} – {end_year}",
                    "repos": list(org_data["repos"]),
                    "contributions": org_data["prs"]
                }
                
                entry_id = f"oss-{org_name}"
                existing = db.query(WorkEntry).filter(WorkEntry.id == entry_id).first()
                if not existing:
                    entry = WorkEntry(
                        id=entry_id,
                        title=f"{org_name.capitalize()} OSS Contributions",
                        entry_type=EntryType.OSS,
                        company=org_name,
                        role="Open Source Contributor",
                        start_date=start_year,
                        end_date=end_year,
                        raw_text=json.dumps(oss_profile_entry, indent=2),
                        priority=4,
                        github_url=f"https://{org_data['org_github']}"
                    )
                    db.add(entry)
                    db.flush()
                    try:
                        ingestion_service.ingest_project(entry.id)
                        created_count += 1
                    except Exception as e:
                        logger.error(f"Failed to ingest OSS entry {entry_id}: {e}")
                else:
                    existing.raw_text = json.dumps(oss_profile_entry, indent=2)
                    existing.start_date = start_year
                    existing.end_date = end_year
                    db.flush()
                    # Re-ingest the updated entry
                    try:
                        ingestion_service.ingest_project(entry_id)
                    except Exception as e:
                        logger.error(f"Failed to re-ingest OSS entry {entry_id}: {e}")
            
            github_user.last_fetch_stamp = datetime.utcnow()
            db.commit()
            
            return {
                "success": True, 
                "message": f"Fetched {len(items)} PRs, created {created_count} new OSS entries.",
                "created_count": created_count
            }

github_service = GithubService()
