from elasticsearch import AsyncElasticsearch
from fastapi import Request

from src.core.config import settings


def create_elastic() -> AsyncElasticsearch:
    return AsyncElasticsearch(settings.elastic_url)


def get_elastic(request: Request) -> AsyncElasticsearch:
    return request.app.state.elastic
