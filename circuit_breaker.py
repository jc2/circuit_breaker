from abc import ABC, abstractclassmethod
from functools import wraps

import redis


class State(ABC):

    def __init__(self):
        self._redis = redis.Redis(host="localhost", password="1234", db=0)
        self._context = None

    def set_context(self, context):
        self._context = context


    @abstractclassmethod
    def handle(self, successful_call=True):
        pass


class Open(State):

    NAME = "Open"
    MAX_ERRORS = 5
    ERROR_KEY = f"{NAME}_error_count"

    def __init__(self):
        super().__init__()
        self._redis.set(self.ERROR_KEY, 0)

    def handle(self, successful_call=True):
        if successful_call:
            self._redis.set(self.ERROR_KEY, 0)
        else:
            if self._redis.incr(self.ERROR_KEY, 1) >= self.MAX_ERRORS:
                self._context.move_to(Close())


class Close(State):

    NAME = "Close"
    MAX_TIME = 60  # 1 min
    MAX_CALLS = 5
    COUNT_KEY = f"{NAME}_count"
    LOCK_KEY = f"{NAME}_lock"

    def __init__(self):
        super().__init__()
        self._redis.set(self.LOCK_KEY, 1, ex=self.MAX_TIME)
        self._redis.set(self.COUNT_KEY, 0)

    def handle(self, successful_call=True):
        if not self._redis.get(self.LOCK_KEY):
            self._context.move_to(HalfOpen())
        else:
            if self._redis.incr(self.COUNT_KEY, 1) >= self.MAX_CALLS:
                self._context.move_to(HalfOpen())


class HalfOpen(State):

    NAME = "HalfOpen"
    MAX_SUCCESSFUL = 2
    MAX_ERRORS = 1
    ERROR_KEY = f"{NAME}_error_count"
    SUCCESS_KEY = f"{NAME}_success_count"

    def __init__(self):
        super().__init__()
        self._redis.set(self.ERROR_KEY, 0)
        self._redis.set(self.SUCCESS_KEY, 0)

    def handle(self, successful_call=True):
        if successful_call:
            if self._redis.incr(self.SUCCESS_KEY, 1) >= self.MAX_SUCCESSFUL:
                self._context.move_to(Open())
        else:
            if self._redis.incr(self.ERROR_KEY, 1) >= self.MAX_ERRORS:
                self._context.move_to(Close())


class CircuitBreaker():

    def __init__(self):
        self.move_to(Open())

    def call(self, successful_call=True):
        self._state.handle(successful_call)

    def get_state_name(self):
        return self._state.NAME

    def move_to(self, new_state):
        self._state = new_state
        self._state.set_context(self)


cb = CircuitBreaker()


class CircuitBreakerClosed(Exception):
    pass


def breaker(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if cb.get_state_name() == "Close":
            cb.call()
            raise CircuitBreakerClosed()
        else:
            try:
                r = f(*args, **kwargs)
            except Exception as e:
                cb.call(successful_call=False)
                raise e
            cb.call(successful_call=True)
            return r
    return wrapper
