import random

def get_list_position(_size: tuple[int], _position: tuple[int]) -> int:
    _n = _position[2]
    _n += _position[1] * _size[2]
    _n += _position[0] * (_size[1] * _size[2])
    return _n

def check_position(_size: tuple[int], _position: tuple[[int]]) -> bool:
    if _position[0] >= _size[0] or _position[0] < 0:
        return False
    elif _position[1] >= _size[1] or _position[1] < 0:
        return False
    elif _position[2] >= _size[2] or _position[2] < 0:
        return False
    return True

def uuid(_n: int) -> str:
    _uuid = ""
    while _n:
        _uuid += str(hex(random.randint(0, 15)))[2:]
        _n -= 1
    return _uuid

def round_45(_i: float, _n: int = 0) -> float:
    _i = int(_i * 10 ** int(_n + 1))
    if _i % 10 >= 5:
        _i += 10
    _i = int(_i / 10)
    return _i / (10 ** int(_n))

def round_01(_i: float, _n: int = 3) -> int:
    if _i % 1 >= 10 ** -_n:
        _i += 1
    return int(_i)

def is_number(_str: str) -> bool:
    _length = len(_str)
    return all(_str[_i] in "0123456789" or (_str[_i] == "." and 1 < _i + 1 < _length) for _i in range(_length)) and _str.count(".") <= 1

def get_time_text(_time: int) -> str:
    return str(_time // 60).rjust(2, "0") + ":" + str(_time % 60).rjust(2, "0")
