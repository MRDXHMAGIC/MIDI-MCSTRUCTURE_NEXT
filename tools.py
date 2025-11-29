import random

def uuid(_n: int) -> str:
    _uuid = ""
    while _n:
        _uuid += str(hex(random.randint(0, 15)))[2:]
        _n -= 1
    return _uuid

def round_45(_i: float, _n=0) -> float:
    _i = int(_i * 10 ** int(_n + 1))
    if _i % 10 >= 5:
        _i += 10
    _i = int(_i / 10)
    return _i / (10 ** int(_n))

def is_number(_str: str) -> bool:
    _length = len(_str)
    return all(_str[_i] in "0123456789" or (_str[_i] == "." and 1 < _i + 1 < _length) for _i in range(_length)) and _str.count(".") <= 1