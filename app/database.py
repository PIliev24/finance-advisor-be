import aiosqlite
import structlog

from app.config import settings

logger = structlog.get_logger()

_db: aiosqlite.Connection | None = None

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        aggregate_type TEXT NOT NULL,
        aggregate_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_data TEXT NOT NULL,
        metadata TEXT,
        version INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(aggregate_id, version)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions_projection (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'EUR',
        category TEXT NOT NULL,
        description TEXT,
        date TEXT NOT NULL,
        import_batch_id TEXT,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS monthly_summary_projection (
        year_month TEXT NOT NULL,
        category TEXT NOT NULL,
        total_income REAL NOT NULL DEFAULT 0,
        total_expenses REAL NOT NULL DEFAULT 0,
        transaction_count INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (year_month, category)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS budgets_projection (
        id TEXT PRIMARY KEY,
        category TEXT NOT NULL UNIQUE,
        monthly_limit REAL NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS life_events_projection (
        id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        description TEXT,
        date TEXT NOT NULL,
        impact TEXT,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
]


async def init_database() -> None:
    global _db
    _db = await aiosqlite.connect(settings.db_path)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")

    for ddl in DDL_STATEMENTS:
        await _db.execute(ddl)
    await _db.commit()

    logger.info("database_initialized", path=settings.db_path)


async def close_database() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("database_closed")


def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


async def check_health() -> None:
    db = get_db()
    cursor = await db.execute("SELECT 1")
    await cursor.close()
