import math
import mido
from tools import round_45
from database import InfoList, TempoList

class MIDIReader:
    def __init__(self, _path: str):
        self.midi_file = None
        self.__instruments_mapping = {}
        # 尝试使用UTF-8编码解码MIDI文件
        for _charset in ("utf-8", "latin1"):
            try:
                # 加载MIDI文件，clip参数用于阻止出现不合法数值时报错
                self.midi_file = mido.MidiFile(_path, charset=_charset, clip=True)
                break
            except:
                pass

        if self.midi_file is None:
            raise IOError("Can't Load MIDI File: " + str(_path))

    def scan_instruments(self):
        _channel_info = {}
        _program_info = {}
        _tempo_info = TempoList(self.midi_file.ticks_per_beat)
        # 遍历每个轨道
        for _track in self.midi_file.tracks:
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
                    _channel_info[_channel].add_info(_time, _message.program)
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
                    _abs_time = int(round_45(_tempo_info.compute_tick_time(_time) / 1000))
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

    def override_mapping(self, _mapping: dict[int, dict[int, int]]) -> None:
        self.__instruments_mapping = _mapping

    def __iter__(self):
        _channel_info = {}
        _tempo_info = TempoList(self.midi_file.ticks_per_beat)
        # 遍历每个轨道
        for _track in self.midi_file.tracks:
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
                        _channel_info[_channel]["volume"].add_info(_time, _value)
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
                    _channel_info[_channel]["program"].add_info(_time, _mapping.get(_message.program, _message.program))
                # 获取歌词事件
                elif _message.type == "lyrics":
                    # 获取歌词数据
                    _data = {
                        "type": "text",
                        "text": _message.text
                    }
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
                        _note_pitch = 45
                        _note_program = _mapping.get(_message.note, _message.note)
                    else:
                        _note_pitch = _message.note - 21
                        _note_program = _channel_info[_channel]["program"].match_info(_time)
                    # 打包数据
                    _data = {
                        "type": "note",
                        "percussion": _channel == 9,
                        "velocity": _note_velocity,
                        "panning": _note_panning,
                        "program": _note_program,
                        "pitch": _note_pitch
                    }

                # 将音符时间转为游戏tick时间并返回结果
                if _data is not None: yield _tempo_info.compute_tick_time(_time), _data
