import math
import mido
from tools import round_int, round_45
from database import InfoList, Stack, NoteData, LyricsData

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

    def compute_time(self, _time: int | float | str) -> float:
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

class MIDIReader:
    def __init__(self, _path: str):
        self.__midi_file = None
        self.__nodes_cache = []
        self.__instruments_mapping = {}
        # 尝试使用UTF-8编码解码MIDI文件
        for _charset in ("utf-8", "latin1"):
            try:
                # 加载MIDI文件，clip参数用于阻止出现不合法数值时报错
                self.__midi_file = mido.MidiFile(_path, charset=_charset, clip=True)
                break
            except UnicodeDecodeError:
                pass

    def __scan_time_nodes(self):
        _tempo_info = TempoList(self.__midi_file.ticks_per_beat)
        # 遍历每个轨道
        for _track in self.__midi_file.tracks:
            # 设置轨道初始时间
            _time = 0
            # 遍历每个音符
            for _message in _track:
                # 累加时间，将时间差表示转为时间轴表示
                _time += _message.time
                # 获取tempo信息
                if _message.type == "set_tempo":
                    _tempo_info.add_tempo(_time, _message.tempo)
                # 获取音符时间信息
                elif _message.type == "note_on":
                    yield _tempo_info.compute_time(_message.time)

    def scan_instruments(self):
        _channel_info = {}
        _program_info = {}
        _tempo_info = TempoList(self.__midi_file.ticks_per_beat)
        # 遍历每个轨道
        for _track in self.__midi_file.tracks:
            # 设置轨道初始时间
            _time = 0
            # 遍历每个音符
            for _message in _track:
                # 初始化数据值
                _data = None
                # 累加时间，将时间差表示转为时间轴表示
                _time += _message.time
                # 判断该事件是否有通道数据并初始化值
                if hasattr(_message, "channel"):
                    _channel = _message.channel
                    if _channel not in _channel_info: _channel_info[_channel] = InfoList(-1)
                else:
                    _channel = -1
                # 获取tempo信息
                if _message.type == "set_tempo":
                    _tempo_info.add_tempo(_time, _message.tempo)
                # 获取通道音色事件【跳过打击乐器（第十轨道上的音符）】
                elif _message.type == "program_change":
                    if _channel != 9: _channel_info[_channel].add_info(_time, _message.program)
                # 获取打击乐器信息
                elif _message.type == "note_on":
                    if _channel == 9:
                        _data = _message.note
                    else:
                        _data = _channel_info[_channel].match_info(_time)
                # 记录信息
                if _data is not None:
                    # 初始化
                    if _channel not in _program_info: _program_info[_channel] = []
                    # 转换时间
                    _abs_time = int(round_45(_tempo_info.compute_time(_time) / 1000))
                    # 记录出现的时间范围
                    for _i in _program_info[_channel]:
                        if _i[1] == _data:
                            if _abs_time < _i[0][0]:
                                _i[0][0] = _abs_time
                            elif _abs_time > _i[0][1]:
                                _i[0][1] = _abs_time
                            break
                    else:
                        _program_info[_channel].append(([_abs_time, _abs_time], _data))
        # 给每个通道的数据按时间排序
        for _k in _program_info.keys():
            _program_info[_k].sort(key=lambda _i: _i[0][0])

        return _program_info

    def get_time_accuracy(self, _time_per_tick: float) -> float:
        return sum(map(lambda _i: (round_int(_i / _time_per_tick) - _i / _time_per_tick) ** 2, self.__scan_time_nodes()))

    def override_mapping(self, _mapping: dict[int, dict[int, int]]) -> None:
        self.__instruments_mapping = _mapping

    def __iter__(self):
        _stack = Stack()
        _tempo_info = TempoList(self.__midi_file.ticks_per_beat)
        _channel_info = {}
        # 遍历每个轨道
        for _track in self.__midi_file.tracks:
            # 设置轨道初始时间
            _time = 0
            # 遍历每个音符
            for _message in _track:
                # 初始化返回值
                _data = None
                # 累加时间，将时间差表示转为时间轴表示
                _time += _message.time
                # 判断该事件是否有通道数据，如果有并且通道没有初始化数据就初始化该通道
                if hasattr(_message, "channel"):
                    _channel = _message.channel
                    _mapping: dict[int, int] = self.__instruments_mapping.get(_channel, {})
                    if _channel not in _channel_info:
                        _channel_info[_channel] = {
                            "program": InfoList(-1),
                            "volume": InfoList(1),
                            "panning": InfoList((0, 1))}
                else:
                    _mapping = {}
                    _channel = -1
                # 获取tempo信息
                if _message.type == "set_tempo":
                    _tempo_info.add_tempo(_time, _message.tempo)
                # 获取MIDI控制事件
                elif _message.type == "control_change":
                    _value = _message.value
                    # 通道音量控制器，调整某个通道音量
                    if _message.control == 7:
                        _channel_info[_channel]["volume"].add_info(_time, _value / 127)
                    # 通道声像控制器
                    elif _message.control == 10:
                        _radian = math.radians(_value * 1.40625)
                        _channel_info[_channel]["panning"].add_info(_time, (round_45(math.cos(_radian), 2), round_45(math.sin(_radian), 2)))
                    # 清除通道效果控制器
                    elif _message.control == 121:
                        _channel_info[_channel]["volume"].add_info(_time, 1)
                        _channel_info[_channel]["panning"].add_info(_time, (0, 1))
                # 获取通道音色事件
                elif _message.type == "program_change":
                    # 记录乐器代号
                    _channel_info[_channel]["program"].add_info(_time, _message.program)
                # 获取歌词事件
                elif _message.type == "lyrics":
                    # 获取歌词数据
                    _data = LyricsData(_message.text)
                # 获取音符信息
                elif _message.type == "note_on" and _message.velocity != 0:
                    # 对音符力度（音量）进行归一化处理
                    _note_velocity = _message.velocity / 127
                    # 音符音量再乘以音符所在的通道的音量
                    _note_velocity *= _channel_info[_channel]["volume"].match_info(_time)
                    # 获取声相偏移数据
                    _note_panning = _channel_info[_channel]["panning"].match_info(_time)
                    # 一般音符用于表示音调，打击乐器（第十轨道上的音符）用于表示音色
                    if _channel == 9:
                        # 打击乐器保持原声
                        _note_pitch = 66
                        _note_program = _message.note
                    else:
                        _note_pitch = _message.note
                        _note_program = _channel_info[_channel]["program"].match_info(_time)

                    # 打包数据
                    _stack.put(_channel, NoteData(_tempo_info.compute_time(_time), _note_pitch, (_mapping.get(_note_program, _note_program), _note_program), _note_panning, _note_velocity))

                elif _message.type == "note_off" or (_message.type == "note_on" and _message.velocity == 0):
                    _data = _stack.get(_channel, _message.note)

                # 将音符时间转为游戏tick时间并返回结果
                if _data is not None: yield _tempo_info.compute_time(_time), _data

        for _data in _stack: yield _data.time + 0.00001, _data
