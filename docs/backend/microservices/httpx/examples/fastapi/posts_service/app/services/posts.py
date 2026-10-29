from app.repositories.posts import PostRepository
from app.schemas.posts import Post as PostSchema, PostBase
from app.clients.category import CategoryServiceClient


class PostService:
    """Сервис для работы с постами"""

    def __init__(self, post_repo: PostRepository, category_client: CategoryServiceClient):
        """Инициализация сервиса с репозиторием постов"""
        self.post_repo = post_repo
        self.category_client = category_client

    async def get_all_posts(self, skip: int = 0, limit: int = 100) -> list[PostSchema]:
        """Получить все посты с поддержкой пагинации"""
        db_posts = await self.post_repo.get_all(skip=skip, limit=limit)
        return [PostSchema.model_validate(post) for post in db_posts]

    async def get_post_by_id(self, post_id: int) -> PostSchema | None:
        """Получить пост по ID"""
        db_post = await self.post_repo.get_by_id(post_id)
        if db_post is None:
            return None
        return PostSchema.model_validate(db_post)

    async def get_posts_by_category(
        self, category_id: int, skip: int = 0, limit: int = 100
    ) -> list[PostSchema] | None:
        """Получить посты по ID категории"""
        await self.category_client.validate(category_id)

        db_posts = await self.post_repo.get_by_category_id(category_id, skip=skip, limit=limit)
        return [PostSchema.model_validate(post) for post in db_posts]

    async def create_post(self, post: PostBase) -> PostSchema | None:
        """Создать новый пост"""
        await self.category_client.validate(post.category_id)

        db_post = await self.post_repo.create(
            title=post.title,
            content=post.content,
            category_id=post.category_id,
        )
        return PostSchema.model_validate(db_post)
