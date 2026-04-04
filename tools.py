import os
import random
import shutil
import subprocess

def where_ffmpeg() -> str:
    try:
        if _path := shutil.which("ffmpeg"):
            _result = subprocess.run((_path, "-version"), capture_output=True, text=True, timeout=8, check=True)

            if _result.stdout.startswith("ffmpeg version"):
                return _path
    except:
        pass

    if os.path.exists("FFmpeg/ffmpeg.exe"):
        return os.path.abspath("Ffmpeg/ffmpeg.exe")
    else:
        return None

def get_str_pos(_text: str, _subtext: str) -> tuple[int]:
    _offset = 0
    _result = []

    try:
        while True:
            _position = _text.index(_subtext, _offset)
            _offset = _position + len(_subtext)
            _result.append(_position)
    except ValueError:
        pass

    return tuple(_result)

def get_color(_surf) -> tuple[int]:
    _colors = []
    for _x in range(_surf.size[0]):
        for _y in range(_surf.size[1]):
            _colors.append(_surf.get_at((_x, _y))[:3])

    _colors.sort(key=lambda _i: sum(_i) / len(_i))

    _num = 0
    _average_color = [0, 0, 0]
    for _color in _colors[round_int(len(_colors) * (1 / 3)):round_int(len(_colors) * (2 / 3))]:
        _average_color = tuple(_a + _b for _a, _b in zip(_average_color, _color))
        _num += 1

    _average_color = tuple(_i / _num for _i in _average_color)

    _color_list = (
        (255, 255, 255),
        (255, 178, 186),
        (255, 180, 169),
        (255, 178, 190),
        (249, 171, 255),
        (211, 187, 255),
        (186, 195, 255),
        (158, 202, 255),
        (141, 205, 255),
        (168, 216, 241),
        (83, 219, 201),
        (122, 220, 119),
        (112, 219, 167),
        (193, 208, 44),
        (219, 201, 10),
        (250, 189, 0),
        (255, 184, 112),
        (255, 181, 160),
        (255, 181, 154),
        (123, 208, 255)
    )

    return min(((sum((_a - _b + (min(_average_color) - min(_color))) ** 2 for _a, _b in zip(_color, _average_color)), _color) for _color in _color_list), key=lambda _i: _i[0])[1]

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
