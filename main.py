import os
import math
import json
import time
import mido
import shutil
import random
import pygame
import hashlib
import requests
import threading
import traceback
import subprocess
import webbrowser
from tkinter import filedialog

# 加载资源函数
def asset_load():
    try:
        with open("Asset/text/setting.json", "rb") as _io:
            _buffer = json.loads(_io.read())
            for _k in _buffer:
                global_info["setting"][_k] = _buffer[_k]

        if global_info["setting"]["id"] <= 0:
            global_info["setting"]["id"] = 1

        global_asset["loading"] = pygame.transform.smoothscale(pygame.image.load("Asset/image/loading.png"), global_info["display_size"]).convert_alpha()
        add_page(overlay_page, [loading_screen, {}], 1)

        global_asset["error"] = pygame.transform.smoothscale(pygame.image.load("Asset/image/error_background.png"), global_info["display_size"]).convert_alpha()

        if os.path.isdir("Cache/extracted/Updater"):
            _n = 0
            while _n <= 16:
                try:
                    if os.path.isdir("Updater"):
                        shutil.rmtree("Updater")
                    break
                except:
                    _n += 1
            shutil.copytree("Cache/extracted/Updater", "Updater")
            shutil.rmtree("Cache")

        pygame.font.init()
        global_asset["font"] = pygame.font.Font("Asset/font/font.ttf", 28)
        global_asset["menu"] = pygame.transform.smoothscale(pygame.image.load("Asset/image/menu_background.png"), global_info["display_size"]).convert_alpha()
        global_asset["blur"] = pygame.transform.smoothscale(pygame.image.load("Asset/image/blur_background.png"), global_info["display_size"]).convert_alpha()
        global_asset["config"] = pygame.transform.smoothscale(pygame.image.load("Asset/image/config_background.png"), (760, 40)).convert_alpha()
        global_asset["logo"] = pygame.transform.smoothscale(pygame.image.load("Asset/image/logo.png"), (560, 64)).convert_alpha()
        global_asset["message_mask"] = pygame.transform.smoothscale(pygame.image.load("Asset/image/mask.png"), (800, 40)).convert_alpha()

        global_asset["structure"] = []
        for _n in os.listdir("Asset/mcstructure"):
            if os.path.splitext(_n)[1] == ".mcstructure":
                if "推荐" in _n:
                    global_asset["structure"].insert(0, _n)
                else:
                    global_asset["structure"].append(_n)

        with open("Asset/text/mapping.json", "rb") as _io:
            _mapping = json.loads(_io.read())

        with open("Asset/text/profile.json", "rb") as _io:
            global_asset["profile"] = json.loads(_io.read())

        for _k in ("new_bedrock", "old_bedrock", "new_java", "old_java"):
            global_asset["profile"][_k]["sound_list"] = translate_mapping_profile(_mapping, global_asset["profile"][_k]["sound_list"])

        threading.Thread(target=get_version_list).start()

        time.sleep(1)

        global_info["message"].append("小提示：使用鼠标左右键来进入或返回页面！")

        add_page(overlay_page, [menu_screen, {"config": [["转换文件", 0, start_to_game], ["设置", 0, ask_software_setting], ["关于MIDI-MCSTRUCTURE", 0, show_about]]}], 0, False)
    except:
        global_info["exit"] = 3
        global_info["log"].extend(("[E] " + line for line in traceback.format_exc().splitlines()))

def translate_mapping_profile(_mapping: dict, _sound: dict) -> dict:
    _sound_list = {}

    for _k in _mapping:
        if isinstance(_mapping[_k], dict):
            _sound_list[_k] = translate_mapping_profile(_mapping[_k], _sound)
        else:
            if _mapping[_k] in _sound:
                _sound_list[_k] = _sound[_mapping[_k]]
            else:
                _sound_list[_k] = _sound[_mapping["undefined"]]

    return _sound_list

# MIDI转换函数
def convertor(_setting, _task_id):
    # 添加正在处理页面
    add_page(overlay_page, [processing_screen, {}])

    try:
        # 加载MIDI文件，clip参数用于阻止出现不合法数值时报错
        _midi_file = mido.MidiFile(_setting["file"], charset="utf-8" if _setting["lyrics"] else "latin1", clip=True)

        # 根据设置的游戏版本选择合适的配置文件
        if global_info["convertor"]["edition"] == 0:
            if global_info["convertor"]["version"] == 0:
                _profile = global_asset["profile"]["old_bedrock"]
            elif global_info["convertor"]["version"] == 1:
                _profile = global_asset["profile"]["new_bedrock"]
        elif global_info["convertor"]["edition"] == 1:
            if global_info["convertor"]["version"] == 0:
                _profile = global_asset["profile"]["old_java"]
            elif global_info["convertor"]["version"] == 1:
                _profile = global_asset["profile"]["new_java"]

        # 存储MIDI通道信息
        _info_list = {}
        # 存储tempo信息
        _tempo_list = [(0, 500000), (float("INF"), 0)]
        # 存储临时音符数据
        _note_buffer = {}
        # 存储临时歌词数据
        _lyrics_buffer = {}
        # 存储音量数据，用于平均音量的计算
        _average_volume = [0, 0]

        # 遍历每个轨道
        for _track in _midi_file.tracks:
            # 设置轨道初始时间
            _time = 0

            # 遍历每个音符
            for _message in _track:
                # 累加时间，将时间差表示转为时间轴表示
                _time += _message.time

                # 判断该事件是否有通道数据，如果有并且通道没有初始化数据就初始化该通道
                if hasattr(_message, "channel"):
                    if _message.channel not in _info_list:
                        _info_list[_message.channel] = {
                            "program": [(0, _profile["sound_list"]["default"]), (float("INF"), 0)],
                            "volume": [(0, 1), (float("INF"), 0)], "pan": [(0, [0, 0]), (float("INF"), [0, 0])]}

                # 获取tempo信息，并按时间顺序添加到列表中
                if _message.type == "set_tempo":
                    for _n, _value in enumerate(_tempo_list):
                        if _value[0] > _time:
                            _tempo_list.insert(_n, (_time, _message.tempo))
                            break

                # 获取MIDI控制事件
                if _message.type == "control_change":
                    _channel = _message.channel

                    # 通道音量控制器，调整某个通道音量
                    if _message.control == 7:
                        for _n, _value in enumerate(_info_list[_channel]["volume"]):
                            if _value[0] > _time:
                                _info_list[_channel]["volume"].insert(_n, (_time, _message.value / 127))
                                break

                    # 通道声像控制器
                    elif _message.control == 10:
                        _radian = math.radians(_message.value * 1.40625)
                        for _n, _value in enumerate(_info_list[_channel]["pan"]):
                            if _value[0] > _time:
                                _info_list[_channel]["pan"].insert(_n, (_time, [round_45(math.cos(_radian), 2), round_45(math.sin(_radian), 2)]))
                                break

                    # 清除通道效果控制器
                    elif _message.control == 121:
                        for _n, _value in enumerate(_info_list[_channel]["volume"]):
                            if _value[0] > _time:
                                _info_list[_channel]["volume"].insert(_n, (_time, 1))
                                break
                        for _n, _value in enumerate(_info_list[_channel]["pan"]):
                            if _value[0] > _time:
                                _info_list[_channel]["pan"].insert(_n, (_time, [0, 1]))
                                break

                # 获取通道音色事件
                if _message.type == "program_change":
                    # 先把乐器代号从int类型转为str类型，方便使用
                    _program = str(_message.program)
                    _channel = _message.channel

                    # 判断是否是打击乐器专属的轨道，如果是就不添加音色信息，因为打击乐器用note来表示音色
                    if _channel != 9:
                        for _n, _value in enumerate(_info_list[_channel]["program"]):
                            if _value[0] > _time:
                                if _program in _profile["sound_list"]:
                                    _info_list[_channel]["program"].insert(_n, (_time, _profile["sound_list"][_program]))
                                else:
                                    _info_list[_channel]["program"].insert(_n, (_time, _profile["sound_list"]["undefined"]))
                                break

                if _message.type == "lyrics":
                    # 将音符时间转为游戏tick时间并根据速度设置调整
                    _tick_time = int(round_45(time_convertor(_time, _tempo_list, _midi_file.ticks_per_beat) / _setting["speed"]))

                    # 判断歌词缓存中是否有改时间，如果没有就创建该时间
                    if _tick_time not in _lyrics_buffer:
                        _lyrics_buffer[_tick_time] = []
                    # 向该时间中添加歌词数据
                    _lyrics_buffer[_tick_time].append({"text": _message.text})

                # 获取音符信息
                if _message.type == "note_on" and _message.velocity != 0:
                    # 对音符力度（音量）进行归一化处理
                    _velocity = _message.velocity / 127
                    _channel = _message.channel
                    # 一般音符用于表示音调，打击乐器（第十轨道上的音符）用于表示音色
                    _pitch = _message.note

                    # 判断是否禁用了打击乐器，如果禁用并且当前是打击乐器音符就跳过
                    if _channel == 9 and not _setting["percussion"]:
                        continue

                    # 读取该音符所在通道的通道音量
                    for _value in _info_list[_channel]["volume"]:
                        if _value[0] > _time:
                            break
                        else:
                            _volume = _value[1]

                    # 读取该音符所在通道的通道声像
                    for _value in _info_list[_channel]["pan"]:
                        if _value[0] > _time:
                            break
                        else:
                            _pan = _value[1]

                    # 如果是打击乐器就获取配置文件中对应的乐器，否则获取音调和该音符所在通道的通道音色
                    if _channel == 9:
                        if str(_pitch) in _profile["sound_list"]["percussion"]:
                            _program = _profile["sound_list"]["percussion"][str(_pitch)]
                        else:
                            _program = _profile["sound_list"]["percussion"]["undefined"]
                        _pitch = 1
                    else:
                        for _value in _info_list[_channel]["program"]:
                            if _value[0] > _time:
                                break
                            else:
                                _program = _value[1]
                        if 21 <= _pitch <= 108:
                            _pitch = global_asset["profile"]["note_list"][_pitch - 21]
                        else:
                            continue

                    # 检查配置文件中是否禁用了该乐器，是就跳过
                    if _program == "disable":
                        continue

                    # 音符力度（音量）乘以音符所在的通道音量
                    _velocity *= _volume

                    # 将音符时间转为游戏tick时间并根据速度设置调整
                    _tick_time = int(round_45(time_convertor(_time, _tempo_list, _midi_file.ticks_per_beat) / _setting["speed"]))

                    # 一个音符可以对应多个我的世界乐器，因此这里遍历一下从配置文件中获取的数据
                    for _n, _note in enumerate(_program):
                        # 如果禁用单音符对应多个我的世界乐器的功能，仅循环一次就退出
                        if _n > 0 and not _setting["adjustment"]:
                            break

                        # 累加配置文件中我的世界乐器之间的时间间隔
                        _tick_time += _note[3]

                        _note_pitch = _pitch
                        _note_velocity = _velocity

                        # 如果启用调整音符功能，则会根据配置文件对音量和音调进行调整
                        if _setting["adjustment"]:
                            _note_velocity *= _note[1]
                            _note_pitch = round_45(_note_pitch * _note[2], 2)

                        # Java版不允许音调范围超出0.5~2.0之间，否则会报错
                        if _setting["edition"] == 1 and not 0.5 <= _note_pitch <= 2:
                            continue

                        # 将音量限制在100%下
                        if _note_velocity >= 1:
                            _note_velocity = 1
                        else:
                            _note_velocity = round_45(_velocity, 2)

                        # 如果启用控制平均音量功能，就记录音量信息
                        if _setting["volume"]:
                            _average_volume[0] += 1
                            _average_volume[1] += _note_velocity

                        # 判断音符缓存中是否有改时间，如果没有就创建该时间
                        if _tick_time not in _note_buffer:
                            _note_buffer[_tick_time] = []

                        # 向该时间中添加音符数据
                        _note_buffer[_tick_time].append({"program": _note[0], "pitch": _note_pitch, "velocity": _note_velocity, "pan": _pan})

        # 调整音量，用于控制平均音量功能
        if _average_volume[0]:
            _average_volume = _average_volume[1] / _average_volume[0]
            for _k in _note_buffer:
                for _i in _note_buffer[_k]:
                    _i["velocity"] *= (_setting["volume"] / 100) / _average_volume
                    if _i["velocity"] >= 1:
                        _i["velocity"] = 1
                    else:
                        _i["velocity"] = round_45(_i["velocity"], 2)

        # 存放音符和歌词字幕合并后的最终结果
        _result = {}

        # 歌词数据处理
        if _setting["lyrics"]:
            # 计算平均间隔时间
            _last_time = 0
            _average_delay_time = [0, 0]
            for _k in sorted(list(_lyrics_buffer)):
                _average_delay_time[1] += _k - _last_time
                _average_delay_time[0] += 1
                _last_time = _k

            if _average_delay_time[0]:
                _average_delay_time = _average_delay_time[1] / _average_delay_time[0]

                # 根据间隔时间断句
                _last_time = 0
                _head_sign = True
                _lyrics_text = []
                _lyrics_list = []
                _lyrics_length = 0
                for _k in sorted(list(_lyrics_buffer)):
                    for _i in _lyrics_buffer[_k]:
                        if _lyrics_length > 20 or (_average_delay_time <= _k - _last_time and not _head_sign):
                            _lyrics_list.append(_lyrics_text)
                            _lyrics_length = 0
                            _lyrics_text = []
                        _lyrics_text.append(_i["text"])

                        for _char in _i["text"]:
                            if _char in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz()[]{},.!?;:'\"~+-*/":
                                _lyrics_length += 0.5
                            else:
                                _lyrics_length += 1
                    _last_time = _k
                    _head_sign = False
                if _lyrics_text:
                    _lyrics_list.append(_lyrics_text)

                # 渲染歌词字幕
                _lyrics_mask = 0
                for _k in sorted(list(_lyrics_buffer)):
                    _lyrics_progress = 0
                    _lyrics_mask += len(_lyrics_buffer[_k])
                    for _i in range(len(_lyrics_list)):
                        if _lyrics_mask - _lyrics_progress <= len(_lyrics_list[_i]):
                            _text_f = ""
                            _text_s = ""
                            for _n, _t in enumerate(_lyrics_list[_i]):
                                if _lyrics_mask - _lyrics_progress == _n:
                                    _text_f = _text_s
                                    _text_s = ""
                                _text_s += _t

                            if not _text_f:
                                _text_f = _text_s
                                _text_s = ""

                            _last_lyrics = ""
                            if _i - 1 >= 0:
                                for _t in _lyrics_list[_i - 1]:
                                    _last_lyrics += _t

                            _next_lyrics = ""
                            if _i + 1 < len(_lyrics_list):
                                for _t in _lyrics_list[_i + 1]:
                                    _next_lyrics += _t

                            # 将歌词数据合并到结果中
                            if _k not in _result:
                                _result[_k] = []
                            _result[_k].append({"type": "lyrics", "last": _last_lyrics, "real_f": _text_f, "real_s": _text_s, "next": _next_lyrics})
                            break

                        _lyrics_progress += len(_lyrics_list[_i])

        # 将音符数据合并到结果中
        for _k in _note_buffer:
            for _i in _note_buffer[_k]:
                _i["type"] = "note"

                if _k not in _result:
                    _result[_k] = []

                _result[_k].append(_i)

        # 获取最早的数据的时间，用于跳过静音功能
        if _setting["skip"]:
            _time_offset = min(list(_result))
        else:
            _time_offset = 0

        # 根据需要将音符数据转为各种文件
        if os.path.exists("Cache/convertor"):
            shutil.rmtree("Cache/convertor")
        os.makedirs("Cache/convertor")

        _music_name = os.path.splitext(os.path.basename(_setting["file"]))[0]

        if _setting["output_format"] == 0:
            with open("Cache/convertor/raw_command.txt", "w", encoding="utf-8") as _io:
                _io.write("# music_name=" + _music_name + "\n")
                _io.write("# structure_id=" + str(_task_id) + "\n")
                _io.write("# length_of_time=" + str(max(list(_result))) + "\n")
                _io.write("# structure_path=Asset/mcstructure/" + global_asset["structure"][_setting["structure"]] + "\n")

                for _cmd in cmd_convertor(_setting, _profile, _result, _task_id, _time_offset, (True if _setting["command_type"] == 0 else False)):
                    _io.write(_cmd + "\n")

            subprocess.Popen("Writer/writer.exe").wait()

            if not os.path.exists("Cache/convertor/structure.mcstructure"):
                return

            if _save_path := filedialog.asksaveasfilename(title="MIDI-MCSTRUCTURE NEXT", initialfile=_music_name,
                                                          filetypes=[("Structure Files", ".mcstructure")],
                                                          defaultextension=".mcstructure"):
                if os.path.exists(_save_path):
                    os.remove(_save_path)
                shutil.copyfile("Cache/convertor/structure.mcstructure", _save_path)
        elif _setting["output_format"] == 1:
            if _setting["command_type"] == 0:
                return
            with open("Cache/convertor/function.mcfunction", "w", encoding="utf-8") as _io:
                for _cmd in cmd_convertor(_setting, _profile, _result, _task_id, _time_offset, False):
                    _io.write(_cmd + "\n")

            if _setting["edition"] == 0:
                os.makedirs("Cache/convertor/function_pack/functions")

                with open("Asset/text/manifest.json", "rb") as _io:
                    _manifest_file = json.loads(_io.read())

                _manifest_file["header"]["name"] = _music_name
                _manifest_file["header"]["uuid"] = uuid(8) + "-" + uuid(4) + "-" + uuid(4) + "-" + uuid(4) + "-" + uuid(
                    12)
                _manifest_file["modules"][0]["uuid"] = uuid(8) + "-" + uuid(4) + "-" + uuid(4) + "-" + uuid(
                    4) + "-" + uuid(12)

                _behavior_file = [
                    {"pack_id": _manifest_file["header"]["uuid"], "version": _manifest_file["header"]["version"]}]

                shutil.copyfile("Cache/convertor/function.mcfunction",
                                "Cache/convertor/function_pack/functions/midi_player.mcfunction")

                with open("Cache/convertor/function_pack/manifest.json", "w") as _io:
                    _io.write(json.dumps(_manifest_file))

                with open("Cache/convertor/function_pack/world_behavior_packs.json", "w") as _io:
                    _io.write(json.dumps(_behavior_file))
            elif _setting["edition"] == 1:
                os.makedirs("Cache/convertor/function_pack/data/mms/functions")

                _behavior_file = {"pack": {"pack_format": 1, "description": "§bby §dMIDI-MCSTRUCTURE"}}

                shutil.copyfile("Cache/convertor/function.mcfunction",
                                "Cache/convertor/function_pack/data/mms/functions/midi_player.mcfunction")

                with open("Cache/convertor/function_pack/pack.mcmeta", "w") as _io:
                    _io.write(json.dumps(_behavior_file))

            if _setting["version"] == 0 and _setting["edition"] == 1:
                if _save_path := filedialog.asksaveasfilename(title="MIDI-MCSTRUCTURE NEXT",
                                                              initialfile=_music_name,
                                                              filetypes=[("Function Files", ".mcfunction")],
                                                              defaultextension=".mcfunction"):
                    if os.path.exists(_save_path):
                        os.remove(_save_path)
                    shutil.copyfile("Cache/convertor/function.mcfunction", _save_path)
            else:
                if _save_path := filedialog.askdirectory(title="MIDI-MCSTRUCTURE NEXT"):
                    _save_path += "/" + _music_name
                    _n = 0
                    while True:
                        if os.path.exists(_save_path + ("-" + str(_n) if _n else "")):
                            _n += 1
                        else:
                            shutil.copytree("Cache/convertor/function_pack", _save_path + ("-" + str(_n) if _n else ""))
                            break
    except:
        global_info["message"].append("转换失败，请将log.txt发送给开发者以修复问题！")
        global_info["log"].extend(("[E] " + line for line in traceback.format_exc().splitlines()))
    finally:
        remove_page(overlay_page)

def cmd_convertor(_setting: dict, _profile: str, _result: list, _task_id: int, _time_offset: int, _delay_info: bool) -> list:
    if _setting["command_type"] == 0:
        _raw_cmd = _profile["command"]["delay"]
    elif _setting["command_type"] == 1:
        _raw_cmd = _profile["command"]["clock"][0]
    elif _setting["command_type"] == 2:
        _raw_cmd = _profile["command"]["address"][0]
    else:
        raise ValueError("Unknown Command Type: " + str(_setting["command_type"]))

    _cmd_list = []
    if _setting["compression"]:
        _data_pool = {}
        for _k in sorted(list(_result)):
            for _n, _i in enumerate(_result[_k]):
                if _i["type"] == "note":
                    _data = ("note",
                             _i["program"],
                             ("^" + str(_i["pan"][0]) + " ^ ^" + str(_i["pan"][1]) if _setting["panning"] else "~ ~ ~"),
                             str(_i["velocity"]),
                             str(_i["pitch"]))
                elif _i["type"] == "lyrics":
                    _data = ("lyrics",
                             _i["last"],
                             _i["real_f"],
                             _i["real_s"],
                             _i["next"])
                else:
                    raise TypeError("Unknown Data Type: " + str(_i["type"]))

                if _data not in _data_pool:
                    _data_pool[_data] = []
                _data_pool[_data].append(_k - _time_offset)

        for _data in _data_pool:
            _selector = ""
            _time_list = _data_pool[_data]
            _list_length = len(_time_list)

            if _list_length == 1:
                _selector = _profile["command"]["timer_target_selector"]["regular"].replace("{VALUE}", str(_time_list[0]))
            else:
                for _i in range(_list_length + 1):
                    if _i > 0:
                        _start_time = _time_list[_i - 1] + 1
                    else:
                        _start_time = ""

                    if _i < _list_length:
                        _end_time = _time_list[_i] - 1
                    else:
                        _end_time = ""

                    if _selector:
                        _selector += ","

                    if _start_time != "" and _end_time != "":
                        if _start_time == _end_time:
                            _selector += _profile["command"]["timer_target_selector"]["compressed"][0].replace(
                                "{VALUE}", str(_end_time)
                            )
                        elif _start_time > _end_time:
                            _selector = _selector[:-1]
                        else:
                            _selector += _profile["command"]["timer_target_selector"]["compressed"][0].replace(
                                "{VALUE}", _profile["command"]["timer_target_selector"]["compressed"][1].replace(
                                    "{START}", str(_start_time)).replace(
                                    "{END}", str(_end_time))
                            )
                    else:
                        _selector += _profile["command"]["timer_target_selector"]["compressed"][0].replace(
                            "{VALUE}", _profile["command"]["timer_target_selector"]["compressed"][1].replace(
                                "{START}", str(_start_time)).replace(
                                "{END}", str(_end_time))
                        )

            if _data[0] == "note":
                _cmd = _raw_cmd.replace(
                    "{SOUND}", _data[1]).replace(
                    "{POSITION}", _data[2]).replace(
                    "{VOLUME}", _data[3]).replace(
                    "{PITCH}", _data[4]).replace(
                    "{TTS}", _selector).replace(
                    "{ADDRESS}", str(_task_id))
            elif _data[0] == "lyrics":
                _cmd = _profile["command"]["lyrics"][_setting["command_type"]].replace(
                    "{LAST}", _data[1]).replace(
                    "{REAL_F}", _data[2]).replace(
                    "{REAL_S}", _data[3]).replace(
                    "{NEXT}", _data[4]).replace(
                    "{TTS}", _selector).replace(
                    "{ADDRESS}", str(_task_id))
            else:
                raise TypeError("Unknown Data Type: " + str(_i["type"]))

            _cmd_list.append(_cmd[1:] if _cmd[0] == "/" else _cmd)
    else:
        _last_time = _time_offset
        for _k in sorted(list(_result)):
            for _n, _i in enumerate(_result[_k]):
                if _i["type"] == "note":
                    _cmd = _raw_cmd.replace(
                        "{SOUND}", _i["program"]).replace(
                        "{POSITION}", ("^" + str(_i["pan"][0]) + " ^ ^" + str(_i["pan"][1]) if _setting[
                            "panning"] else "~ ~ ~")).replace(
                        "{VOLUME}", str(_i["velocity"])).replace(
                        "{PITCH}", str(_i["pitch"])).replace(
                        "{TIME}", str(_k - _time_offset)).replace(
                        "{TTS}", _profile["command"]["timer_target_selector"]["regular"].replace("{VALUE}", str(_k - _time_offset))).replace(
                        "{ADDRESS}", str(_task_id))
                elif _i["type"] == "lyrics":
                    _cmd = _profile["command"]["lyrics"][_setting["command_type"]].replace(
                        "{LAST}", _i["last"]).replace(
                        "{REAL_F}", _i["real_f"]).replace(
                        "{REAL_S}", _i["real_s"]).replace(
                        "{NEXT}", _i["next"]).replace(
                        "{TIME}", str(_k - _time_offset)).replace(
                        "{TTS}", _profile["command"]["timer_target_selector"]["regular"].replace("{VALUE}", str(_k - _time_offset))).replace(
                        "{ADDRESS}", str(_task_id))
                else:
                    raise TypeError("Unknown Data Type: " + str(_i["type"]))
                if _delay_info:
                    _cmd_list.append("# tick_delay=" + str(_k - _last_time))
                _cmd_list.append(_cmd[1:] if _cmd[0] == "/" else _cmd)
                _last_time = _k

    if _setting["command_type"] == 1:
        _raw_cmd = _profile["command"]["clock"][1:]
    elif _setting["command_type"] == 2:
        _raw_cmd = _profile["command"]["address"][1:]
    else:
        _raw_cmd = []

    for _cmd in _raw_cmd:
        _cmd_list.append(_cmd.replace(
            "{TIME}", str(max(list(_result)))).replace(
            "{ADDRESS}", str(_task_id)))

    return _cmd_list

# 页面渲染函数
def render_page(_root: pygame.Surface, _overlay: list, _event: dict):

    _pages_num = len(_overlay)

    for _n in range(_pages_num):
        if _n + 1 == _pages_num or _overlay[_n + 1][2] != 1:
            _root.blit(to_alpha(_overlay[_n][0](_overlay[_n][1], _event if _overlay[_n][3] else {}), (255, 255, 255, 255 * _overlay[_n][2])), (0, 0))
        if _overlay[_n][3]:
            _overlay[_n][2] += (1.01 - _overlay[_n][2]) * global_info["animation_speed"]
            if _overlay[_n][2] >= 1:
                _overlay[_n][2] = 1
        else:
            _overlay[_n][2] += (-0.01 - _overlay[_n][2]) * global_info["animation_speed"]
            if _overlay[_n][2] <= 0:
                _overlay[_n][2] = 0

    for _n in range(_pages_num - 1, -1, -1):
        if _overlay[_n][2] == 0:
            del _overlay[_n]

    if global_info["message"]:
        global_info["message_info"][1] += timer.get_time()

        _root.blit(global_asset["message_mask"], (0, 450 - global_info["message_info"][0] * 40))
        _text_surface = to_alpha(global_asset["font"].render(global_info["message"][0], True, (255, 255, 255)), (255, 255, 255, 255 * global_info["message_info"][0]))
        _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, 470 - global_info["message_info"][0] * 40 - _text_surface.get_size()[1] / 2))

        if global_info["message_info"][1] <= 3000:
            global_info["message_info"][0] += (1 - global_info["message_info"][0]) * global_info["animation_speed"]
        else:
            global_info["message_info"][0] -= global_info["message_info"][0] * global_info["animation_speed"]

            if global_info["message_info"][0] < 0.01:
                del global_info["message"][0]
                global_info["message_info"] = [0, 0]

# 功能函数
def to_alpha(_origin_surf: pygame.Surface, _color_value, _surf_size=None, _surf_position=(0, 0)) -> pygame.Surface:
    if _surf_size is None:
        _surf_size = _origin_surf.get_size()
    _alpha_surf = pygame.Surface(_surf_size, pygame.SRCALPHA)
    _alpha_surf.fill(_color_value)
    _origin_surf.blit(_alpha_surf, _surf_position, special_flags=pygame.BLEND_RGBA_MULT)
    return _origin_surf

def round_45(_i: float, _n=0) -> float:
    _i = int(_i * 10 ** int(_n + 1))
    if _i % 10 >= 5:
        _i += 10
    _i = int(_i / 10)
    return _i / (10 ** int(_n))

def uuid(_n: int) -> str:
    _uuid = ""
    while _n:
        _uuid += str(hex(random.randint(0, 15)))[2:]
        _n -= 1
    return _uuid

def time_convertor(_time: int, _tempo_list: list, _ticks_per_beat: int) -> float:
    _tick_time = 0

    for _n in range(1, len(_tempo_list)):
        if _tempo_list[_n][0] <= _time:
            _tick_time += mido.tick2second(_tempo_list[_n][0] - _tempo_list[_n - 1][0], _ticks_per_beat, _tempo_list[_n - 1][1]) * 2000
        else:
            _tick_time += mido.tick2second(_time - _tempo_list[_n - 1][0], _ticks_per_beat, _tempo_list[_n - 1][1]) * 2000
            break

    return _tick_time

# GUI页面管理函数
def add_page(_overlay, _page, _position=0, _back=True):
    _overlay.append(_page + [_position, True, _back])

def remove_page(_overlay):
    _pages_num = len(_overlay)
    for _n in range(_pages_num - 1, -1, -1):
        if _overlay[_n][3] and _overlay[_n][4]:
            _overlay[_n][3] = False
            break

# 版本更新函数
def get_version_list():
    try:
        _update_log = json.loads(requests.get("https://gitee.com/mrdxhmagic/midi-mcstructure_next/raw/master/update.json").content)

        global_info["update_list"] = []
        for _i in _update_log:
            if _i["API"] == 0:
                global_info["update_list"].append(_i)

        _length = len(global_info["update_list"])

        for _x in range(_length):
            for _y in range(_length - _x - 1):
                if global_info["update_list"][_y]["version"] < global_info["update_list"][_y + 1]["version"]:
                    global_info["update_list"][_y], global_info["update_list"][_y + 1] = global_info["update_list"][_y + 1], global_info["update_list"][_y]

        global_info["new_version"] = global_info["update_list"][0]["version"] > global_info["setting"]["version"]
    except:
        global_info["log"].extend(("[E] " + line for line in traceback.format_exc().splitlines()))

def download(_url, _state, _target_hash="", _file_name="package.7z"):
    try:
        _state["state"] = 0

        if os.path.exists("Cache/download"):
            shutil.rmtree("Cache/download")
        os.makedirs("Cache/download")

        _real_hash = hashlib.md5()
        _response = requests.get(_url, stream=True)

        _response.raise_for_status()

        _state["total"] = int(_response.headers['content-length'])

        with open("Cache/download/" + _file_name, 'ab') as _io:
            for _data_chunk in _response.iter_content(chunk_size=1024):
                _state["downloaded"] += len(_data_chunk)
                _real_hash.update(_data_chunk)
                _io.write(_data_chunk)

        if _target_hash and _target_hash != str(_real_hash.hexdigest()):
            raise IOError("Broken Package, Please Try Again.")
    except:
        _state["state"] = -1
        global_info["log"].extend(("[E] " + line for line in traceback.format_exc().splitlines()))
    finally:
        if _state["state"] != -1:
            _state["state"] = 1

# 各种回调函数（用于GUI）
def start_to_game():
    add_page(overlay_page, [convertor_screen, {"config": [["选择文件", 0, ask_file], ["游戏版本", 0, ask_edition], ["常用设置", 0, ask_setting], ["其他设置", 0, ask_other_setting], ["开始", 0, start_task]]}])

def convertor_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root = pygame.Surface(global_info["display_size"]).convert_alpha()
    _mask = global_asset["menu"].copy()
    _root.blit(global_asset["blur"], (0, 0))

    mouse_position = pygame.mouse.get_pos()

    for _n, _i in enumerate(_info["config"]):
        _text = _i[0]
        _y = 20 + _n * 60
        if _y <= mouse_position[1] <= _y + 40 and 20 <= mouse_position[0] <= 780:
            if _n == 4:
                if not global_info["convertor"]["file"]:
                    _text = "请选择文件"
                elif global_info["convertor"]["edition"] == -1:
                    _text = "请选择游戏版本"
                elif global_info["convertor"]["output_format"] == -1:
                    _text = "请完成常用设置"
                elif global_info["convertor"]["speed"] == -1:
                    _text = "请完成其他设置"
            _i[1] += (255 - _i[1]) * global_info["animation_speed"]
            if "mouse_left" in _input and not _input["mouse_left"]:
                _i[2]()
        else:
            _i[1] += (127 - _i[1]) * global_info["animation_speed"]
        _root.blit(global_asset["config"], (20, _y))
        _mask = to_alpha(_mask, (0, 0, 0, 0), (760, 40), (20, _y))
        if _n == 0:
            if global_info["convertor"]["file"]:
                _text = os.path.splitext(os.path.basename(global_info["convertor"]["file"]))[0]
        elif _n == 1:
            if global_info["convertor"]["edition"] == 0:
                _text = "基岩版"
                if global_info["convertor"]["version"] == 0:
                    _text += "（1.19.50以下）"
                elif global_info["convertor"]["version"] == 1:
                    _text += "（1.19.50以上）"
            elif global_info["convertor"]["edition"] == 1:
                _text = "Java版"
                if global_info["convertor"]["version"] == 0:
                    _text += "（1.13以下）"
                elif global_info["convertor"]["version"] == 1:
                    _text += "（1.13以上）"
        elif _n == 2 and global_info["convertor"]["output_format"] != -1:
            if global_info["convertor"]["output_format"] == 0:
                _text = "mcstructure"
            elif global_info["convertor"]["output_format"] == 1:
                _text = "mcfunction"
            else:
                _text = ""
            if global_info["convertor"]["command_type"] == 0:
                _text += "/命令链延迟"
            elif global_info["convertor"]["command_type"] == 1:
                _text += "/计分板时钟"
            elif global_info["convertor"]["command_type"] == 2:
                _text += "/时钟与编号"
            if global_info["convertor"]["volume"]:
                _text += "/" + str(global_info["convertor"]["volume"]) + "%"
            if global_asset["structure"]:
                _text += "/" + os.path.splitext(global_asset["structure"][global_info["convertor"]["structure"]])[0]
        elif _n == 3 and global_info["convertor"]["speed"] != -1:
            _text = str(global_info["convertor"]["speed"] / 100)
            if global_info["convertor"]["speed"] % 10 == 0:
                _text += "0"
            _text += "倍"
            if global_info["convertor"]["panning"]:
                _text += "/声相偏移"
            if global_info["convertor"]["skip"]:
                _text += "/静音跳过"
            if global_info["convertor"]["percussion"]:
                _text += "/打击乐器"
            if global_info["convertor"]["adjustment"]:
                _text += "/乐器调整"
            if global_info["convertor"]["lyrics"]:
                _text += "/歌词"
            if global_info["convertor"]["compression"]:
                _text += "/压缩"
        _text_surface = to_alpha(global_asset["font"].render(_text, True, (255, 255, 255)), (255, 255, 255, _i[1]))
        _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, _y + 20 - _text_surface.get_size()[1] / 2))

    _root.blit(_mask, (0, 0))

    return _root

def loading_screen(_info, _input):
    return global_asset["loading"].copy()

def menu_screen(_info, _input):
    _root = pygame.Surface(global_info["display_size"]).convert_alpha()
    _mask = global_asset["menu"].copy()
    _root.blit(global_asset["blur"], (0, 0))

    mouse_position = pygame.mouse.get_pos()

    for _n, _i in enumerate(_info["config"]):
        _y = 20 + _n * 60
        if _y <= mouse_position[1] <= _y + 40 and 20 <= mouse_position[0] <= 780:
            _i[1] += (255 - _i[1]) * global_info["animation_speed"]
            if "mouse_left" in _input and not _input["mouse_left"]:
                _i[2]()
        else:
            _i[1] += (127 - _i[1]) * global_info["animation_speed"]
        _root.blit(global_asset["config"], (20, _y))
        _mask = to_alpha(_mask, (0, 0, 0, 0), (760, 40), (20, _y))
        _text_surface = to_alpha(global_asset["font"].render(_i[0] + ("（发现新版本）" if global_info["new_version"] and _n == 1 else ""), True, (255, 255, 255)), (255, 255, 255, _i[1]))
        _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, _y + 20 - _text_surface.get_size()[1] / 2))

    _root.blit(_mask, (0, 0))

    return _root

def ask_software_setting():
    add_page(overlay_page, [software_setting_screen, {"config": [["查看更新", 0], ["重置结构ID", 0], ["界面刷新率 ", 0], ["动画速度 ", 0], ["日志等级 ", 0]]}])

def software_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        global_info["new_version"] = False
        remove_page(overlay_page)

    _root = pygame.Surface(global_info["display_size"]).convert_alpha()
    _mask = global_asset["menu"].copy()
    _root.blit(global_asset["blur"], (0, 0))

    mouse_position = pygame.mouse.get_pos()

    for _n, _i in enumerate(_info["config"]):
        _text = _i[0]
        _y = 20 + _n * 60
        if _y <= mouse_position[1] <= _y + 40 and 20 <= mouse_position[0] <= 780:
            _i[1] += (255 - _i[1]) * global_info["animation_speed"]
            if "mouse_left" in _input and not _input["mouse_left"]:
                if _n == 0:
                    show_version_list()
                elif _n == 1:
                    global_info["setting"]["id"] = 1
                    global_info["message"].append("已重置结构ID！")
                elif _n == 2:
                    global_info["setting"]["fps"] += 30
                    if global_info["setting"]["fps"] > 120:
                        global_info["setting"]["fps"] = 0
                elif _n == 3:
                    global_info["setting"]["animation_speed"] += 1
                    if global_info["setting"]["animation_speed"] >= 16:
                        global_info["setting"]["animation_speed"] = 0
                elif _n == 4:
                    global_info["setting"]["log_level"] += 1
                    if global_info["setting"]["log_level"] == 2:
                        global_info["setting"]["log_level"] = 0
        else:
            _i[1] += (127 - _i[1]) * global_info["animation_speed"]
        if _n == 0:
            _text += "（发现新版本）" if global_info["new_version"] else ""
        elif _n == 2:
            _text += str(global_info["setting"]["fps"]) + "Hz" if global_info["setting"]["fps"] else "无限制"
        elif _n == 3:
            _text += str(global_info["setting"]["animation_speed"]) if global_info["setting"]["animation_speed"] else "关"
        elif _n == 4:
            if global_info["setting"]["log_level"] == 0:
                _text += "Disable"
            elif global_info["setting"]["log_level"] == 1:
                _text += "Error"
        _root.blit(global_asset["config"], (20, _y))
        _mask = to_alpha(_mask, (0, 0, 0, 0), (760, 40), (20, _y))
        _text_surface = to_alpha(global_asset["font"].render(_text, True, (255, 255, 255)), (255, 255, 255, _i[1]))
        _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, _y + 20 - _text_surface.get_size()[1] / 2))

    _root.blit(_mask, (0, 0))

    return _root

def show_version_list():
    add_page(overlay_page, [version_list_screen, {"index": 0, "state": [], "config": [["", 0], ["◀                                                                                                                    ", 0], ["                                                                                                                    ▶", 0], ["查看该版本详情", 0], ["下载并安装该版本", 0]]}])

def version_list_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    if global_info["update_list"]:
        _root = pygame.Surface(global_info["display_size"]).convert_alpha()
        _mask = global_asset["menu"].copy()
        _root.blit(global_asset["blur"], (0, 0))

        mouse_position = pygame.mouse.get_pos()

        _y = 20

        for _n, _i in enumerate(_info["config"]):
            if _n > 2:
                _y += 60
            if _y <= mouse_position[1] <= _y + 40 and (((80 <= mouse_position[0] <= 720 and _n == 0) or (20 <= mouse_position[0] <= 780 and _n > 2)) or ((20 <= mouse_position[0] <= 80 and _n == 1) or (720 <= mouse_position[0] <= 780 and _n == 2))):
                _i[1] += (255 - _i[1]) * global_info["animation_speed"]
                if "mouse_left" in _input and not _input["mouse_left"]:
                    if _n == 1:
                        _info["index"] -= 1
                        if _info["index"] < 0:
                            _info["index"] = len(global_info["update_list"]) - 1
                    elif _n == 2:
                        _info["index"] += 1
                        if _info["index"] >= len(global_info["update_list"]):
                            _info["index"] = 0
                    elif _n == 3 and global_info["update_list"][_info["index"]]["description_url"]:
                        webbrowser.open(global_info["update_list"][_info["index"]]["description_url"])
                    elif _n == 4:
                        show_download(global_info["update_list"][_info["index"]])
            else:
                _i[1] += (127 - _i[1]) * global_info["animation_speed"]
            if _n == 0:
                _i[1] = 255
                _i[0] = "V" + str(global_info["update_list"][_info["index"]]["version"]) + ("-" + str(global_info["update_list"][_info["index"]]["edition"]) if global_info["update_list"][_info["index"]]["edition"] else "")
            if _n >= 2:
                _root.blit(global_asset["config"], (20, _y))
            _mask = to_alpha(_mask, (0, 0, 0, 0), (760, 40), (20, _y))
            _text_surface = to_alpha(global_asset["font"].render(_i[0], True, (255, 255, 255)), (255, 255, 255, _i[1]))
            _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, _y + 20 - _text_surface.get_size()[1] / 2))

        _root.blit(_mask, (0, 0))
    else:
        _root = global_asset["blur"].copy()
        _text_surface = global_asset["font"].render("无法获取版本信息", True, (255, 255, 255))
        _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, (global_info["display_size"][1] - _text_surface.get_size()[1]) / 2))

    return _root

def show_download(_info):
    _state = {"state": 0, "downloaded": 0, "total": 0}
    threading.Thread(target=download, args=(_info["download_url"], _state, _info["hash"])).start()
    add_page(overlay_page, [download_screen, {"state": _state, "version": _info["version"], "time": 0}])

def download_screen(_info, _input):
    if _info["state"]["state"] == -1 and _info["time"] != -1:
        _info["time"] += timer.get_time()
    if _info["time"] >= 3000:
        remove_page(overlay_page)
        _info["time"] = -1

    _root = pygame.Surface(global_info["display_size"]).convert_alpha()
    _mask = global_asset["menu"].copy()
    _root.blit(global_asset["blur"], (0, 0))

    _y = 20

    for _n in range(2):
        if _n == 0:
            _text = ("V" + str(global_info["setting"]["version"]) + "  ➡  " if global_info["setting"]["version"] else "") + "V" + str(_info["version"])
        else:
            if _info["state"]["state"] == 0:
                _text = str(round_45((_info["state"]["downloaded"] / _info["state"]["total"]) * 100, 2)) + "%" if _info["state"]["total"] else "等待中"
            elif _info["state"]["state"] == 1:
                _text = "下载完成"
                global_info["exit"] = 2
            elif _info["state"]["state"] == -1:
                _text = "下载失败，请重试"
            else:
                _text = ""
        _root.blit(global_asset["config"], (20, _y))
        _mask = to_alpha(_mask, (0, 0, 0, 0), (760, 40), (20, _y))
        _text_surface = global_asset["font"].render(_text, True, (255, 255, 255))
        _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, _y + 20 - _text_surface.get_size()[1] / 2))
        _y += 60

    _root.blit(_mask, (0, 0))

    return _root

def show_about():
    if global_info["setting"]["version"]:
        _edition = "V" + str(global_info["setting"]["version"])
    else:
        _edition = "Unknown"
    if global_info["setting"]["edition"]:
        _edition += "-" + str(global_info["setting"]["edition"])
    add_page(overlay_page, [about_screen, {"text": [["", 0, 0], ["", 0, 0], [_edition, 0, 0], ["交流群(密码14890357)", 0, 20], ["MMS-NEXT 开源仓库", 0, 20], ["MMS 开源仓库", 0, 20]]}])

def about_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root = pygame.Surface(global_info["display_size"]).convert_alpha()
    _mask = global_asset["menu"].copy()
    _root.blit(global_asset["blur"], (0, 0))

    mouse_position = pygame.mouse.get_pos()

    _y = 20
    for _n, _i in enumerate(_info["text"]):
        _y += _i[2]
        if _i[2]:
            if _y <= mouse_position[1] <= _y + 40 and 20 <= mouse_position[0] <= 780:
                _i[1] += (255 - _i[1]) * global_info["animation_speed"]
                if "mouse_left" in _input and not _input["mouse_left"]:
                    if _n == 3:
                        webbrowser.open("qm.qq.com/q/9oBhTyDN8k")
                    elif _n == 4:
                        webbrowser.open("gitee.com/mrdxhmagic/midi-mcstructure_next")
                    elif _n == 5:
                        webbrowser.open("gitee.com/mrdxhmagic/midi-mcstructure")
            else:
                _i[1] += (127 - _i[1]) * global_info["animation_speed"]
        else:
            _i[1] = 255
        _root.blit(global_asset["config"], (20, _y))
        _mask = to_alpha(_mask, (0, 0, 0, 0), (760, 40), (20, _y))
        _text_surface = to_alpha(global_asset["font"].render(_i[0], True, (255, 255, 255)), (255, 255, 255, _i[1]))
        _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, _y + 20 - _text_surface.get_size()[1] / 2))
        _y += 40

    _root.blit(global_asset["logo"], (120, 28))

    _root.blit(_mask, (0, 0))

    return _root

def ask_file():
    if _path := filedialog.askopenfilename(title="MIDI-MCSTRUCTURE NEXT", filetypes=[("MIDI Files", ".mid")]):
        global_info["convertor"]["file"] = _path

def ask_setting():
    if global_info["convertor"]["output_format"] == -1:
        global_info["convertor"]["output_format"] = 0
    add_page(overlay_page, [setting_screen, {"config": [["输出格式 ", 0], ["播放模式 ", 0], ["平均音量 ", 0], ["结构模板 ", 0]]}])

def setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root = pygame.Surface(global_info["display_size"]).convert_alpha()
    _mask = global_asset["menu"].copy()
    _root.blit(global_asset["blur"], (0, 0))

    mouse_position = pygame.mouse.get_pos()

    for _n, _i in enumerate(_info["config"]):
        _y = 20 + _n * 60
        if _y <= mouse_position[1] <= _y + 40 and 20 <= mouse_position[0] <= 780:
            _i[1] += (255 - _i[1]) * global_info["animation_speed"]
            if "mouse_left" in _input and not _input["mouse_left"]:
                if _n == 0:
                    if global_info["convertor"]["output_format"] == 0 or global_info["convertor"]["edition"] == 1:
                        global_info["convertor"]["output_format"] = 1
                        if global_info["convertor"]["command_type"] == 0:
                            global_info["convertor"]["command_type"] = 1
                    else:
                        global_info["convertor"]["output_format"] = 0
                elif _n == 1:
                    global_info["convertor"]["command_type"] += 1
                    if global_info["convertor"]["command_type"] >= 3:
                        if global_info["convertor"]["output_format"] == 0:
                            global_info["convertor"]["command_type"] = 0
                        else:
                            global_info["convertor"]["command_type"] = 1
                elif _n == 2:
                    global_info["convertor"]["volume"] += 10
                    if global_info["convertor"]["volume"] >= 110:
                        global_info["convertor"]["volume"] = 0
                elif _n == 3:
                    global_info["convertor"]["structure"] += 1
                    if global_info["convertor"]["structure"] >= len(global_asset["structure"]):
                        global_info["convertor"]["structure"] = 0

                if global_info["convertor"]["output_format"] == 0:
                    global_info["convertor"]["compression"] = False
        else:
            _i[1] += (127 - _i[1]) * global_info["animation_speed"]
        _root.blit(global_asset["config"], (20, _y))
        _mask = to_alpha(_mask, (0, 0, 0, 0), (760, 40), (20, _y))
        _text = _i[0]
        if _n == 0:
            if global_info["convertor"]["output_format"] == 0:
                _text += "mcstructure"
            elif global_info["convertor"]["output_format"] == 1:
                _text += "mcfunction"
        elif _n == 1:
            if global_info["convertor"]["command_type"] == 0:
                _text += "命令链延迟"
            elif global_info["convertor"]["command_type"] == 1:
                _text += "计分板时钟"
            elif global_info["convertor"]["command_type"] == 2:
                _text += "时钟与编号"
        elif _n == 2:
            if global_info["convertor"]["volume"]:
                _text += str(global_info["convertor"]["volume"]) + "%"
            else:
                _text += "保持原始音量"
        elif _n == 3:
            if global_asset["structure"]:
                _text += os.path.splitext(global_asset["structure"][global_info["convertor"]["structure"]])[0]
            else:
                _text += "无"
        _text_surface = to_alpha(global_asset["font"].render(_text, True, (255, 255, 255)), (255, 255, 255, _i[1]))
        _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, _y + 20 - _text_surface.get_size()[1] / 2))

    _root.blit(_mask, (0, 0))

    return _root

def ask_other_setting():
    if global_info["convertor"]["speed"] == -1:
        global_info["convertor"]["speed"] = 100
    add_page(overlay_page, [other_setting_screen, {"config": [["播放速度 ", 0], ["声相偏移 ", 0], ["静音跳过 ", 0], ["打击乐器 ", 0], ["乐器调整 ", 0], ["歌词显示 ", 0], ["指令压缩  ", 0]]}])

def other_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root = pygame.Surface(global_info["display_size"]).convert_alpha()
    _mask = global_asset["menu"].copy()
    _root.blit(global_asset["blur"], (0, 0))

    mouse_position = pygame.mouse.get_pos()

    for _n, _i in enumerate(_info["config"]):
        _y = 20 + _n * 60
        if _y <= mouse_position[1] <= _y + 40 and 20 <= mouse_position[0] <= 780:
            _i[1] += (255 - _i[1]) * global_info["animation_speed"]
            if "mouse_left" in _input and not _input["mouse_left"]:
                if _n == 0:
                    global_info["convertor"]["speed"] += 5
                    if global_info["convertor"]["speed"] >= 130:
                        global_info["convertor"]["speed"] = 75
                elif _n == 1:
                    if global_info["convertor"]["panning"]:
                        global_info["convertor"]["panning"] = False
                    else:
                        global_info["convertor"]["panning"] = True
                elif _n == 2:
                    if global_info["convertor"]["skip"]:
                        global_info["convertor"]["skip"] = False
                    else:
                        global_info["convertor"]["skip"] = True
                elif _n == 3:
                    if global_info["convertor"]["percussion"]:
                        global_info["convertor"]["percussion"] = False
                    else:
                        global_info["convertor"]["percussion"] = True
                elif _n == 4:
                    if global_info["convertor"]["adjustment"]:
                        global_info["convertor"]["adjustment"] = False
                    else:
                        global_info["convertor"]["adjustment"] = True
                elif _n == 5:
                    if global_info["convertor"]["lyrics"]:
                        global_info["convertor"]["lyrics"] = False
                    else:
                        global_info["convertor"]["lyrics"] = True
                elif _n == 6:
                    if global_info["convertor"]["compression"] or (global_info["convertor"]["command_type"] == 0 or (global_info["convertor"]["edition"] == 1 and global_info["convertor"]["version"] == 0)):
                        global_info["convertor"]["compression"] = False
                    else:
                        global_info["convertor"]["compression"] = True
        else:
            _i[1] += (127 - _i[1]) * global_info["animation_speed"]
        _root.blit(global_asset["config"], (20, _y))
        _mask = to_alpha(_mask, (0, 0, 0, 0), (760, 40), (20, _y))
        _text = _i[0]
        if _n == 0:
            _text += str(global_info["convertor"]["speed"] / 100)
            if global_info["convertor"]["speed"] % 10 == 0:
                _text += "0"
            _text += "倍"
        elif _n == 1:
            if global_info["convertor"]["panning"]:
                _text += "启用"
            else:
                _text += "关闭"
        elif _n == 2:
            if global_info["convertor"]["skip"]:
                _text += "启用"
            else:
                _text += "关闭"
        elif _n == 3:
            if global_info["convertor"]["percussion"]:
                _text += "启用"
            else:
                _text += "关闭"
        elif _n == 4:
            if global_info["convertor"]["adjustment"]:
                _text += "启用"
            else:
                _text += "关闭"
        elif _n == 5:
            if global_info["convertor"]["lyrics"]:
                _text += "启用"
            else:
                _text += "关闭"
        elif _n == 6:
            if global_info["convertor"]["compression"]:
                _text += "启用"
            elif global_info["convertor"]["command_type"] == 0 or (global_info["convertor"]["edition"] == 1 and global_info["convertor"]["version"] == 0):
                _text += "不可用"
            else:
                _text += "关闭"
        _text_surface = to_alpha(global_asset["font"].render(_text, True, (255, 255, 255)), (255, 255, 255, _i[1]))
        _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, _y + 20 - _text_surface.get_size()[1] / 2))

    _root.blit(_mask, (0, 0))

    return _root

def ask_edition():
    if global_info["convertor"]["edition"] == -1:
        global_info["convertor"]["edition"] = 0
    add_page(overlay_page, [game_edition_screen, {"config": [[0], [0]]}])

def game_edition_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root = pygame.Surface(global_info["display_size"]).convert_alpha()
    _mask = global_asset["menu"].copy()
    _root.blit(global_asset["blur"], (0, 0))

    mouse_position = pygame.mouse.get_pos()

    for _n, _i in enumerate(_info["config"]):
        _y = 20 + _n * 60
        if _y <= mouse_position[1] <= _y + 40 and 20 <= mouse_position[0] <= 780:
            _i[0] += (255 - _i[0]) * global_info["animation_speed"]
            if "mouse_left" in _input and not _input["mouse_left"]:
                if _n == 0:
                    if global_info["convertor"]["edition"] == 0:
                        global_info["convertor"]["edition"] = 1
                        global_info["convertor"]["output_format"] = 1
                        if global_info["convertor"]["command_type"] == 0:
                            global_info["convertor"]["command_type"] = 1
                    else:
                        global_info["convertor"]["edition"] = 0
                elif _n == 1:
                    if global_info["convertor"]["version"] == 0:
                        global_info["convertor"]["version"] = 1
                    else:
                        global_info["convertor"]["version"] = 0

                if global_info["convertor"]["version"] == 0 and global_info["convertor"]["edition"] == 1:
                    global_info["convertor"]["compression"] = False
        else:
            _i[0] += (127 - _i[0]) * global_info["animation_speed"]
        _root.blit(global_asset["config"], (20, _y))
        _mask = to_alpha(_mask, (0, 0, 0, 0), (760, 40), (20, _y))
        _text = ""
        if _n == 0:
            if global_info["convertor"]["edition"] == 0:
                _text = "基岩版"
            elif global_info["convertor"]["edition"] == 1:
                _text = "Java版"
        elif _n == 1:
            if global_info["convertor"]["version"] == 0:
                _text = "1.19.50/1.13以下"
            elif global_info["convertor"]["version"] == 1:
                _text = "1.19.50/1.13以上"
        _text_surface = to_alpha(global_asset["font"].render(_text, True, (255, 255, 255)), (255, 255, 255, _i[0]))
        _root.blit(_text_surface, ((global_info["display_size"][0] - _text_surface.get_size()[0]) / 2, _y + 20 - _text_surface.get_size()[1] / 2))

    _root.blit(_mask, (0, 0))

    return _root

def start_task():
    if not global_info["convertor"]["file"]:
        return
    if global_info["convertor"]["edition"] == -1:
        return
    if global_info["convertor"]["output_format"] == -1:
        return
    if global_info["convertor"]["speed"] == -1:
        return
    threading.Thread(target=convertor, args=(global_info["convertor"].copy(), global_info["setting"]["id"])).start()
    if global_info["convertor"]["command_type"] == 2:
        global_info["setting"]["id"] += 1

def processing_screen(_info, _input):
    return global_asset["blur"].copy()

global_info = {"exit": 0, "log": [], "message": [], "message_info": [0, 0], "new_version": False, "update_list": [], "downloader": [{"state": "waiting", "downloaded": 0, "total": 0}], "setting": {"id": 1, "fps": 60, "log_level": 1, "version": 0, "edition": "", "animation_speed": 10}, "profile": {}, "convertor": {"file": "", "edition": -1, "version": 1, "command_type": 0, "output_format": -1, "volume": 30, "structure": 0, "skip": True, "speed": -1, "adjustment": True, "percussion": True, "panning": False, "lyrics": False, "compression": False}}
overlay_page = []
global_asset = {}

pygame.display.init()

global_info["display_size"] = (800, 450)

pygame.display.set_caption("MIDI-MCSTRUCTURE NEXT  GUI")

try:
    pygame.display.set_icon(pygame.image.load("Asset/image/icon.ico"))
except:
    global_info["log"].extend(("[E] " + line for line in traceback.format_exc().splitlines()))

window = pygame.display.set_mode(global_info["display_size"])

try:
    timer = pygame.time.Clock()

    threading.Thread(target=asset_load).start()

    while True:
        window.fill((0, 0, 0, 255))
        env_list = {}
        for env in pygame.event.get():
            if env.type == pygame.QUIT:
                global_info["exit"] = 1
            if env.type == pygame.MOUSEBUTTONDOWN:
                if env.button == 1:
                    env_list["mouse_left"] = True
                if env.button == 3:
                    env_list["mouse_right"] = True
            if env.type == pygame.MOUSEBUTTONUP:
                if env.button == 1:
                    env_list["mouse_left"] = False
                if env.button == 3:
                    env_list["mouse_right"] = False
        if global_info["exit"]:
            break
        global_info["animation_speed"] = timer.get_fps()
        if 0 < global_info["setting"]["animation_speed"] < global_info["animation_speed"]:
            global_info["animation_speed"] = global_info["setting"]["animation_speed"] / global_info["animation_speed"]
        else:
            global_info["animation_speed"] = 1
        if overlay_page:
            render_page(window, overlay_page, env_list)
        pygame.display.flip()
        timer.tick(global_info["setting"]["fps"])
except KeyboardInterrupt:
    global_info["exit"] = 1
except:
    global_info["exit"] = 3
    global_info["log"].extend(("[E] " + line for line in traceback.format_exc().splitlines()))
finally:
    if global_info["log"] and global_info["setting"]["log_level"]:
        with open("log.txt", "a") as io:
            io.write("[" + ("V" + str(global_info["setting"]["version"]) if global_info["setting"]["version"] else "Unknown") + "] " + time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()) + ":\n")
            io.writelines("  " + line + "\n" for line in global_info["log"])

    if not os.path.exists("Asset/text"):
        os.makedirs("Asset/text")

    with open("Asset/text/setting.json", "w") as io:
        io.write(json.dumps(global_info["setting"], indent=2))

    if global_info["exit"] == 2:
        subprocess.Popen("Updater/updater.exe")
    elif global_info["exit"] == 3:
        window.blit(pygame.transform.scale(global_asset["error"], (800, 450)), (0, 0))
        pygame.display.flip()
        time.sleep(3)

    os._exit(0)