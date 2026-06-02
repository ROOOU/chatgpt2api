from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from api.support import require_identity
from services.image_conversation_service import image_conversation_service


class ImageConversationListRequest(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)


class ImageConversationItemRequest(BaseModel):
    item: dict[str, Any] = Field(default_factory=dict)


class ImageConversationRenameRequest(BaseModel):
    title: str = ""


def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/image-conversations")
    async def list_image_conversations(authorization: str | None = Header(default=None)):
        identity = require_identity(authorization)
        return await run_in_threadpool(image_conversation_service.list, identity)

    @router.put("/api/image-conversations")
    async def save_image_conversations(
        body: ImageConversationListRequest,
        authorization: str | None = Header(default=None),
    ):
        identity = require_identity(authorization)
        return await run_in_threadpool(image_conversation_service.save_many, identity, body.items)

    @router.put("/api/image-conversations/{conversation_id}")
    async def save_image_conversation(
        conversation_id: str,
        body: ImageConversationItemRequest,
        authorization: str | None = Header(default=None),
    ):
        identity = require_identity(authorization)
        item = {**body.item, "id": conversation_id}
        return await run_in_threadpool(image_conversation_service.save_one, identity, item)

    @router.patch("/api/image-conversations/{conversation_id}")
    async def rename_image_conversation(
        conversation_id: str,
        body: ImageConversationRenameRequest,
        authorization: str | None = Header(default=None),
    ):
        identity = require_identity(authorization)
        return await run_in_threadpool(image_conversation_service.rename, identity, conversation_id, body.title)

    @router.delete("/api/image-conversations/{conversation_id}")
    async def delete_image_conversation(
        conversation_id: str,
        authorization: str | None = Header(default=None),
    ):
        identity = require_identity(authorization)
        return await run_in_threadpool(image_conversation_service.delete, identity, conversation_id)

    @router.delete("/api/image-conversations")
    async def clear_image_conversations(authorization: str | None = Header(default=None)):
        identity = require_identity(authorization)
        return await run_in_threadpool(image_conversation_service.clear, identity)

    return router
