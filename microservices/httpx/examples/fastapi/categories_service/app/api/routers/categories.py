from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_category_service
from app.schemas.category import CategorySchema, CategoryBase
from app.services.categories import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategorySchema])
async def read_categories(
        skip: int = 0,
        limit: int = 100,
        category_service: CategoryService = Depends(get_category_service)
):
    """Получить список всех категорий"""
    categories = await category_service.get_all_categories(skip=skip, limit=limit)
    return categories


@router.post("/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(
        category: CategoryBase,
        category_service: CategoryService = Depends(get_category_service)
):
    """Создать новую категорию"""
    db_category = await category_service.create_category(category=category)
    if db_category is None:
        raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")
    return db_category


@router.get("/{category_id}", response_model=CategorySchema)
async def read_category(
        category_id: int,
        category_service: CategoryService = Depends(get_category_service)
):
    """Получить категорию по ID"""
    db_category = await category_service.get_category_by_id(category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return db_category
