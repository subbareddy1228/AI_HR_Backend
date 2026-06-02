from fastapi import APIRouter
from . import Applications, Profile, JobSearch, SavedJobs, RecentApplications, RecommendedJobSections, Notifications

# Main router for candidates
router = APIRouter(prefix="/api/candidates", tags=["candidates"])

# Sub-routers (⚠️ no prefix here, only tags)
router.include_router(Applications.router, prefix="/applications")
router.include_router(Profile.router, prefix="/profile")
router.include_router(JobSearch.router, prefix="/jobsearch")
router.include_router(SavedJobs.router, prefix="/savedjobs")
router.include_router(RecentApplications.router, prefix="/recentapplications")
router.include_router(RecommendedJobSections.router, prefix="/recommendedjobs")
router.include_router(Notifications.router, prefix="/notifications")
