from fastapi import APIRouter

from app.api.routes import activity, admin, audit, auth, compare, exports, games, health, management, stats, system, users

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(system.router)
api_router.include_router(stats.router)
api_router.include_router(activity.router)
api_router.include_router(compare.router)
api_router.include_router(users.router)
api_router.include_router(games.router)
api_router.include_router(management.router)
api_router.include_router(audit.router)
api_router.include_router(exports.router)
api_router.include_router(admin.router)
