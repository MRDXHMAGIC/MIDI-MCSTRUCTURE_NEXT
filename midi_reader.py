import math
import mido
from tools import round_45
from database import InfoList, TempoList

class MIDIReader:
    def __init__(self, _path: str):
        self.midi_file = None
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
                    if _channel not in _channel_info:
                        _channel_info[_channel] = {
                            "program": InfoList(-1),
                            "volume": InfoList(1),
                            "panning": InfoList((0, 1))}
                else:
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
                if _message.type == "program_change":
                    # 获取乐器代号
                    _program = _message.program
                    # 判断是否是打击乐器专属的轨道，如果是就不添加音色信息，因为打击乐器用note来表示音色
                    if _channel != 9:
                        _channel_info[_channel]["program"].add_info(_time, _program)
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
                        _note_program = _message.note
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

                if _data is not None:
                    # 将音符时间转为游戏tick时间并返回结果
                    yield _tempo_info.compute_tick_time(_time), _data
