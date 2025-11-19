import time

def test_cache_ttl():
    from cache import cache_set, cache_get

    cache_set("key123", "hello", 1)
    assert cache_get("key123") == "hello"

    time.sleep(1.1)
    assert cache_get("key123") is None
