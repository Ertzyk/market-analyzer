import redis
import json

# Połączenie z Redis w Dockerze
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,  # zwracaj stringi zamiast bajtów
)

def cache_get(key: str):
    value = redis_client.get(key)
    if value:
        return json.loads(value)
    return None

def cache_set(key: str, value, ttl_seconds=300):
    redis_client.set(
        key,
        json.dumps(value, default=str),
        ex=ttl_seconds
    )

def clear_cache():
    global CACHE
    CACHE = {}  # szybkie wyczyszczenie wszystkiego