import time
import redis

class RateLimiter:

    def __init__(self, redis_host, redis_port, time_window):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        self.time_window = time_window

    def is_request_allowed(self, identifier, max_requests):
        current_time = int(time.time())

        # Remove expired entries from the sorted set
        self.redis_client.zremrangebyscore(identifier, 0, current_time - self.time_window)

        # Get the count of requests within the time window
        request_count = self.redis_client.zcard(identifier)

        if request_count >= max_requests:
            return False

        # Add current timestamp to the sorted set
        self.redis_client.zadd(identifier, {current_time: current_time})
        
        # Set expiration time for the sorted set
        self.redis_client.expire(identifier, self.time_window)

        return True