"""Executa a suíte contra PostgreSQL real: DB_NAME/DB_USER/DB_PASSWORD/DB_HOST no ambiente."""
import os

from .settings_test import *  # noqa

DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": os.environ.get("DB_NAME", "loja"),
                         "USER": os.environ.get("DB_USER", "loja"), "PASSWORD": os.environ.get("DB_PASSWORD", ""),
                         "HOST": os.environ.get("DB_HOST", "localhost"), "PORT": os.environ.get("DB_PORT", "5432")}}
