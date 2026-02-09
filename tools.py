import random

def uuid(_n: int) -> str:
    _uuid = ""
    while _n:
        _uuid += str(hex(random.randint(0, 15)))[2:]
        _n -= 1
    return _uuid

def limit(_min: float, _real: float, _max: float) -> float:
    return max(_min, min(_max, _real))

def round_int(_i: float) -> int:
    return int(_i + (0.5 if _i >= 0 else -0.5))

def round_45(_i: float, _n: int = 0) -> float:
    return int(_i * (10 ** _n) + (0.5 if _i >= 0 else -0.5)) / (10 ** _n)

def is_number(_str: str) -> bool:
    _length = len(_str)
    return all(_str[_i] in "0123456789" or (_str[_i] == "." and 1 < _i + 1 < _length) for _i in range(_length)) and _str.count(".") <= 1

def get_time_text(_time: int) -> str:
    return str(_time // 60).rjust(2, "0") + ":" + str(_time % 60).rjust(2, "0")
