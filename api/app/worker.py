from __future__ import annotations

import os

from celery import Celery

from app.core.config import settings


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def create_celery_app() -> Celery:
    app = Celery(
        "sentinelkit",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["app.tasks"],
    )
    app.conf.update(
        task_always_eager=_env_flag("CELERY_TASK_ALWAYS_EAGER"),
        task_eager_propagates=True,
        task_track_started=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
    )
    return app


celery_app = create_celery_app()
