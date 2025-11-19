from cache import redis_client

def test_cache_basic():
    redis_client.set("x", "123")
    assert redis_client.get("x") == "123"
