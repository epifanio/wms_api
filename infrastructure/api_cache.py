import redis
import json


def get_data(transaction_id, redishost="redis", password=None):
    r = redis.StrictRedis(host=redishost, password=password)
    reply = json.loads(r.execute_command("JSON.GET", transaction_id))
    return reply


def set_data(transaction_id, data, redishost="redis", password=None):
    r = redis.StrictRedis(host=redishost, password=password)
    r.execute_command("JSON.SET", transaction_id, ".", json.dumps(data))
    return transaction_id