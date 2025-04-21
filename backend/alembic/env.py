import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from core.config import settings
from database.models.base import BaseModel

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = BaseModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Configurar la conexión a la base de datos
db_url_from_settings = str(settings.DATABASE_URL)
config.set_main_option("sqlalchemy.url", db_url_from_settings)
#print(f"DEBUG [env.py]: DATABASE_URL from settings: {db_url_from_settings}")
#print(f"DEBUG [env.py]: sqlalchemy.url in config: {config.get_main_option('sqlalchemy.url')}")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    print(f"DEBUG [env.py]: Running run_migrations_online()")
    alembic_config_section = config.get_section(config.config_ini_section)
    print(f"DEBUG [env.py]: Alembic config section for engine: {alembic_config_section}")

    connectable = async_engine_from_config(
        alembic_config_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
