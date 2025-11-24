from app.repositories.categories import CategoryRepository
from app.schemas.category import CategoryBase, CategorySchema


class CategoryService:
    """Сервис для работы с категориями"""

    def __init__(self, category_repo: CategoryRepository):
        """Инициализация сервиса с репозиторием категорий"""
        self.category_repo = category_repo

    async def get_all_categories(self, skip: int = 0, limit: int = 100) -> list[CategorySchema]:
        """Получить все категории с поддержкой пагинации"""
        db_categories = await self.category_repo.get_all(skip=skip, limit=limit)
        return [CategorySchema.model_validate(obj) for obj in db_categories]

    async def get_category_by_id(self, category_id: int) -> CategorySchema | None:
        """Получить категорию по ID"""
        db_category = await self.category_repo.get_by_id(category_id)
        if db_category is None:
            return None
        return CategorySchema.model_validate(db_category)

    async def create_category(self, category: CategoryBase) -> CategorySchema | None:
        """Создать новую категорию"""
        existing_category = await self.category_repo.get_by_name(category.name)
        if existing_category:
            return None
        db_category = await self.category_repo.create(name=category.name)
        return CategorySchema.model_validate(db_category)