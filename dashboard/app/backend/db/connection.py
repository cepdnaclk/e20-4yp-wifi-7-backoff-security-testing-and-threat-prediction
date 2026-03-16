import asyncpg


async def init_pool(config: dict) -> asyncpg.Pool:
    return await asyncpg.create_pool(**config, min_size=2, max_size=10)


async def close_pool(pool: asyncpg.Pool):
    await pool.close()
