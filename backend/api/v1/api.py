from fastapi import APIRouter

from api.v1 import completions, auth, chat, users, documents, pipelines, stats

api_router = APIRouter()

api_router.include_router(
    completions.router,
    prefix="/completions",
    tags=["completions"]
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"]
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"]
)

api_router.include_router(
    pipelines.router,
    prefix="/pipelines",
    tags=["pipelines"]
)

api_router.include_router(
    stats.router,
    prefix="/stats",
    tags=["stats"]
)