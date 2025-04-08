import redis
import time
import uuid
import pytest

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

def test_leader_election():
    node_id = str(uuid.uuid4())
    result = r.set("leader_lock", node_id, nx=True, ex=5)
    assert result is True, "Should become leader"
    assert r.get("leader_lock") == node_id, "Should remain leader"

def test_queue_push_and_pop():
    r.delete("order_queue")  # Clear any leftover orders before test
    order = '{"order_id": "test-100", "type": "fraud_check"}'
    r.rpush("order_queue", order)
    fetched = r.lpop("order_queue")
    assert fetched == order, "Popped order should match pushed order"

@pytest.fixture(autouse=True)
def clean_redis_queue():
    r.delete("order_queue")
    yield
    r.delete("order_queue")