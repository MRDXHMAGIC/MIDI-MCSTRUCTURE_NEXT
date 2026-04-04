from tools import limit, round_45, get_str_pos

class AverageNumber:
    def __init__(self) -> None:
        self.__num = 0
        self.__sum = 0

    def __bool__(self) -> bool:
        return bool(self.__num)

    def get(self) -> float:
        if self.__num == 0:
            return 0
        else:
            return self.__sum / self.__num

    def put(self, _num: float) -> None:
        self.__num += 1
        self.__sum += _num

class Eval:
    def __init__(self, _cmd: str):
        _offset = 0
        _content = []

        try:
            while True:
                _stack = 1
                _start = _cmd.index("{EVAL:", _offset)

                for _n, _i in enumerate(_cmd[_start + 6:]):
                    if _i == "{":
                        _stack += 1
                    elif _i == "}":
                        _stack -= 1

                    if _stack == 0:
                        _end = _n + _start + 6
                        break
                else:
                    raise SyntaxError("\"{EVAL:\" was never closed!")

                _content.extend((_cmd[:_start], compile(_cmd[_start + 6:_end], "<string>", "eval", optimize=2)))
                _cmd = _cmd[_end + 1:]
        except ValueError:
            pass

        self.__content = tuple(_i for _i in _content if _i) + (_cmd,)

    def eval(self, _globals=None, _locals=None) -> str:
        return "".join((_i if isinstance(_i, str) else str(eval(_i, _globals, _locals))) for _i in self.__content)

class Note:
    __slots__ = (
        "__id",
        "__program",
        "__pitch",
        "__volume",
        "__panning"
    )

    master_volume = 1
    def __init__(self, _program: str, _volume: float, _pitch: float, _panning: tuple[float], _id = None):
        if not isinstance(_panning, (tuple, list)): raise TypeError("Panning must be tuple!")
        if not isinstance(_program, str): raise TypeError("Program must be string!")
        if not isinstance(_volume, (float, int)): raise TypeError("Volume must be float!")
        if not isinstance(_pitch, (float, int)): raise TypeError("Pitch must be float!")

        self.__program = _program

        self.__id = _id
        self.__pitch = round_45(_pitch, 5)
        self.__volume = round_45(_volume, 2)
        self.__panning = (round_45(_panning[0], 2), round_45(_panning[1], 2))

    def dump(self, _origin: bool = True) -> dict[str, float | tuple[float]]:
        return {
            "type": "note",
            "pitch": self.__pitch,
            "program": self.__program,
            "panning": self.__panning,
            "volume": round_45(self.__volume * (1 if _origin else self.master_volume), 2)
        }

    def format(self, _text: str) -> str:
        if not isinstance(_text, str): raise TypeError("Text must be string!")
        
        return _text.replace(
            "{SOUND}", self.__program).replace(
            "{PANNING}", "^" + str(self.__panning[0]) + " ^ ^" + str(self.__panning[1])).replace(
            "{VOLUME}", str(round_45(limit(0, self.__volume * self.master_volume, 1), 2))).replace(
            "{PITCH}", str(self.__pitch)
        )

    def __eq__(self, _other: Note) -> bool:
        return isinstance(_other, Note) and hash(_other) == hash(self)

    def __hash__(self) -> int:
        return hash(
            (
                self.__id,
                self.__pitch,
                self.__volume,
                self.__program,
                self.__panning
            )
        )

    def __repr__(self) -> str:
        return f"Note<pg={self.__program}, pt={self.__pitch}, vl={round_45(self.__volume * self.master_volume, 2)}, pn=({self.__panning[0]}, {self.__panning[1]})>"

class Lyrics:
    __slots__ = (
        "__last",
        "__head",
        "__tail",
        "__next"
    )

    def __init__(self, _last: str, _head: str, _tail: str, _next: str) -> None:
        if not isinstance(_last, str): raise TypeError("Lyrics must be string!")
        if not isinstance(_head, str): raise TypeError("Lyrics must be string!")
        if not isinstance(_tail, str): raise TypeError("Lyrics must be string!")
        if not isinstance(_next, str): raise TypeError("Lyrics must be string!")

        self.__last = _last
        self.__head = _head
        self.__tail = _tail
        self.__next = _next

    def format(self, _text: str) -> str:
        if not isinstance(_text, str): raise TypeError("Text must be string!")

        return _text.replace(
            "{LAST}", self.__last).replace(
            "{REAL_F}", self.__head).replace(
            "{REAL_S}", self.__tail).replace(
            "{NEXT}", self.__next
        )

    def dump(self, _) -> dict[str, str]:
        return {
            "type": "lyrics",
            "last": self.__last,
            "real_f": self.__head,
            "real_s": self.__tail,
            "next": self.__next
        }

    def __eq__(self, _other: Lyrics) -> bool:
        return isinstance(_other, Lyrics) and hash(_other) == hash(self)

    def __hash__(self) -> int:
        return hash(
            (
                self.__last,
                self.__head,
                self.__tail,
                self.__next
            )
        )

    def __repr__(self) -> str:
        return f"Lyrics<{self.__last} | {self.__head} {self.__tail} | {self.__next}>"

class NoteData:
    __slots__ = (
        "source_program",
        "percussion",
        "velocity",
        "panning",
        "program",
        "pitch",
        "time",
        "type"
    )

    def __init__(self, _time: float, _pitch: float, _program: tuple[int], _panning: tuple[float], _velocity: float):
        self.type = "note"
        self.time = _time
        self.pitch = _pitch
        self.program = _program[0]
        self.panning = _panning
        self.velocity = _velocity
        self.percussion = False
        self.source_program = _program[1]

class LyricsData:
    __slots__ = (
        "type",
        "value"
    )

    def __init__(self, _text: str):
        self.type = "lyrics"
        self.value = _text

class InfoList:
    def __init__(self, _init_value) -> None:
        self.list_info = {0: _init_value}

    def __iter__(self) -> tuple:
        for _k in sorted(self.list_info.keys()):
            yield _k, self.list_info[_k]

    def add_info(self, _time: int | float | str, _value) -> None:
        if not isinstance(_time, (int, float, str)):
            raise ValueError("Time Must be int, float or str!")
        self.list_info[float(_time)] = _value

    def match_info(self, _time: int | float | str):
        if not isinstance(_time, (int, float, str)):
            raise ValueError("Time Must be int, float or str!")

        _time = float(_time)
        _time_list = sorted(self.list_info.keys(), reverse=True)
        for _i in _time_list:
            if _i <= _time:
                return self.list_info[_i]

        raise ValueError("Couldn't find a Matched Value!")

class LyricsList:
    def __init__(self, _lyrics_list: dict[int, str], _smooth: bool=True, _join: bool=False) -> None:
        if not all(isinstance(_i, int) and isinstance(_lyrics_list[_i], str) for _i in _lyrics_list):
            raise TypeError("Unsupported Lyrics Struct!")

        self.lyrics_list = []
        _time_list = sorted(_lyrics_list.keys())

        # 处理歌词文本
        if _join:
            # 计算平均间隔时间
            _time_num = 0
            _last_time = min(_time_list)
            _average_delay_time = [0, 0]
            for _k in _time_list:
                _average_delay_time[0] += _k - _last_time
                _average_delay_time[1] += 1
                _last_time = _k
            # 判断除数是否为0
            if _average_delay_time[1]:
                _average_delay_time = _average_delay_time[0] / _average_delay_time[1]
                _step = _average_delay_time * 0.001
                # 微调合并的间隔时间，避免出现太长的歌词
                _scores = []
                while _average_delay_time > 0:
                    # 迭代最佳结果
                    _num = 0
                    _result = []
                    _last_time = min(_time_list)
                    for _k in _time_list:
                        _lyrics_length = len(_lyrics_list[_k])
                        if _k - _last_time <= _average_delay_time and _lyrics_length < 16:
                            _num += _lyrics_length
                        else:
                            _result.append(_num)
                            _num = 0
                        _last_time = _k
                    if _num: _result.append(_num)
                    # 计算得分
                    _scores.append((_average_delay_time, sum(map(lambda _x: 0.209 * (_x ** 2) - 3.56 * _x, _result))))
                    # 减去一个单位的时间
                    _average_delay_time -= _step
                # 取最好的结果
                _average_delay_time = min(_scores, key=lambda _x: _x[1])[0]
                # 合并歌词
                _lyrics_text_buffer = ""
                _last_time = min(_time_list)
                for _k in _time_list:
                    if any((len(_lyrics_text_buffer) > 16, len(_lyrics_list[_k]) > 16 and _k != _time_list[0], _average_delay_time <= _k - _last_time)):
                        self.lyrics_list.append(_lyrics_text_buffer)
                        _lyrics_text_buffer = ""
                    _lyrics_text_buffer += _lyrics_list[_k]
                    _last_time = _k
                # 处理剩余的一句歌词
                if _lyrics_text_buffer: self.lyrics_list.append(_lyrics_text_buffer)
        else:
            self.lyrics_list = tuple(_lyrics_list[_i] for _i in _time_list)

        # 移除空行
        self.lyrics_list = tuple(filter(lambda _i: bool(_i), self.lyrics_list))

        # 生成时间点信息
        _node_list = []
        if _smooth:
            _num = 0
            _time_list_length = len(_time_list)
            for _i in range(1, _time_list_length):
                _text_length = len(_lyrics_list[_time_list[_i - 1]])
                _delta_time = _time_list[_i] - _time_list[_i - 1]
                for _n in range(_delta_time):
                    _node_list.append((_n + _time_list[_i - 1], int(round_45(_text_length * ((_n + 1) / _delta_time))) + _num))
                _num += _text_length
            _node_list.append((max(_time_list), sum(len(_lyrics_list[_k]) for _k in _time_list)))
        else:
            _num = 0
            for _k in _time_list:
                _num += len(_lyrics_list[_k])
                _node_list.append((_k, _num))
        self.node_list = _node_list

    def __iter__(self) -> tuple[Lyrics]:
        # 渲染歌词
        _lyrics_list_length = len(self.lyrics_list)
        for _k, _i in self.node_list:
            _lyrics_position = 0
            for _n in range(_lyrics_list_length):
                _text_length = len(self.lyrics_list[_n])
                if _lyrics_position + _text_length >= _i:
                    yield _k, Lyrics(self.lyrics_list[_n - 1] if _n > 0 else "", self.lyrics_list[_n][:_i - _lyrics_position], self.lyrics_list[_n][_i - _lyrics_position:], self.lyrics_list[_n + 1] if _n < _lyrics_list_length - 1 else "")
                    break
                _lyrics_position += _text_length

class Stack:
    __slots__ = (
        "__data",
    )

    def __init__(self):
        self.__data: dict[int, dict[int, list[NoteData]]] = {}

    def put(self, _channel: int, _data: NoteData):
        _data.percussion = _channel == 9

        if _channel not in self.__data:
            self.__data[_channel] = {_data.pitch: [_data]}
        elif _data.pitch not in self.__data[_channel]:
            self.__data[_channel][_data.pitch] = [_data]
        else:
            self.__data[_channel][_data.pitch].append(_data)

    def get(self, _channel: int, _pitch: int) -> NoteData:
        try:
            return self.__data[_channel][_pitch].pop()
        except:
            return None

    def __iter__(self):
        for _channel in self.__data.values():
            for _notes in _channel.values():
                for _note in _notes:
                    yield _note