from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_post_service
from app.schemas.posts import Post, PostBase
from app.services.posts import PostService

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/", response_model=list[Post])
async def read_posts(
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        post_service: PostService = Depends(get_post_service)
):
    """Получить список всех постов или постов по ID категории."""

    if category_id is not None:
        posts = await post_service.get_posts_by_category(
            category_id=category_id,
            skip=skip,
            limit=limit
            )
        if posts is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")
    else:
        posts = await post_service.get_all_posts(skip=skip, limit=limit)
    return posts


@router.post("/", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_post(
        post: PostBase,
        post_service: PostService = Depends(get_post_service)
):
    """Создать новый пост"""
    db_post = await post_service.create_post(post=post)
    if db_post is None:
        raise HTTPException(status_code=400, detail="Не удалось создать пост. Проверьте данные")
    return db_post


@router.get("/{post_id}", response_model=Post)
async def read_post(
        post_id: int,
        post_service: PostService = Depends(get_post_service)
):
    """Получить пост по ID"""
    db_post = await post_service.get_post_by_id(post_id=post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Пост не найден")
    return db_post
