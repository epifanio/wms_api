import aioredis
from fastapi import Request, APIRouter, Query, HTTPException

router = APIRouter()

# Connect to Redis
async def connect_to_redis():
    global redis
    redis = aioredis.from_url(
        "redis://redis", encoding="utf-8", decode_responses=True
    )

# Store a key-value pair
@router.post('/store/{key}/{value}')
async def store_key_value_pair(key: str, value: str):
    async with redis.client() as conn:
        await conn.set(key, value)
        val = await conn.get(key)
    return {'message': f'Key-value pair stored successfullyfor val: {val}'}

# Retrieve a value by key
@router.get('/retrieve/{key}')
async def retrieve_value_by_key(key: str):
    value = await redis.get(key)
    if value is None:
        return {'message': 'Key not found.'}
    return {'key': key, 'value': value}

# Retrieve the content of a value by key
@router.get('/content/{key}')
async def retrieve_content_by_key(key: str):
    value = await redis.get(key)
    if value is None:
        return {'message': 'Key not found.'}
    return value

# Startup event
@router.on_event('startup')
async def startup_event():
    await connect_to_redis()

@router.get("/keys")
async def get_keys():
    keys = await redis.keys("*")
    return {"keys": keys}
# Shutdown event
@router.on_event('shutdown')
async def shutdown_event():
    redis.close()
    await redis.wait_closed()