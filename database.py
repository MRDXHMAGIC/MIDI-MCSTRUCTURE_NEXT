import mido
from tools import round_45

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

class TempoList:
    def __init__(self, _ticks_per_beat: int) -> None:
        self.ticks_per_beat = _ticks_per_beat
        self.tempo_list = [[0, 500000]]
        self.is_revised = False

    def add_tempo(self, _time: int | float | str, _tempo: int) -> None:
        if not isinstance(_time, (int, float, str)):
            raise ValueError("Time Must be int, float or str!")
        if not isinstance(_tempo, int):
            raise ValueError("Tempo Must be int!")
        for _i in self.tempo_list:
            if _i[0] == _time:
                _i[1] = _tempo
                break
        else:
            self.tempo_list.append([_time, _tempo])
        self.is_revised = True

    def compute_tick_time(self, _time: int | float | str) -> float:
        if not isinstance(_time, (int, float, str)):
            raise ValueError("Time Must be int, float or str!")

        if self.is_revised:
            self.tempo_list.sort(key=lambda _i: _i[0])
            self.is_revised = False

        _tempo_list = self.tempo_list + [(float("INF"), self.tempo_list[-1][1])]

        _abs_time = 0
        for _n in range(1, len(_tempo_list)):
            if _tempo_list[_n][0] <= _time:
                _abs_time += mido.tick2second(_tempo_list[_n][0] - _tempo_list[_n - 1][0], self.ticks_per_beat, _tempo_list[_n - 1][1]) * 1000
            else:
                _abs_time += mido.tick2second(_time - _tempo_list[_n - 1][0], self.ticks_per_beat, _tempo_list[_n - 1][1]) * 1000
                break

        return _abs_time

class LyricsList:
    def __init__(self, _lyrics_list: dict[int, str], _smooth: bool=True, _join: bool=False):
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
            self.lyrics_list = list(_lyrics_list[_i] for _i in _time_list)

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

    def __iter__(self):
        # 渲染歌词
        _lyrics_list_length = len(self.lyrics_list)
        for _k, _i in self.node_list:
            _lyrics_position = 0
            for _n in range(_lyrics_list_length):
                _text_length = len(self.lyrics_list[_n])
                if _lyrics_position + _text_length >= _i:
                    yield _k, (self.lyrics_list[_n - 1] if _n > 0 else "", (self.lyrics_list[_n][:_i - _lyrics_position], self.lyrics_list[_n][_i - _lyrics_position:]), self.lyrics_list[_n + 1] if _n < _lyrics_list_length - 1 else "")
                    break
                _lyrics_position += _text_length