import os
import log
import math
import json
import time
import pickle
import shutil
import pygame
import tarfile
import hashlib
import requests
import threading
import traceback
import subprocess
import webbrowser
from tools import round_01, round_45, uuid, is_number, get_time_text
from tkinter import filedialog
from database import LyricsList
from ui_manager import UIManager
from midi_reader import MIDIReader


class NetStream:
    def __init__(self, _url: str):
        self.size = 0
        self.__buffer = b""
        self.__stream = None
        self.__position = 0
        self.__response = requests.get(_url, stream=True)

        self.__response.raise_for_status()

        self.size = int(self.__response.headers["content-length"])
    def __enter__(self):
        self.__stream = self.__response.__enter__().iter_content(5120)
        return self
    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.__response.__exit__(_exc_type, _exc_val, _exc_tb)
    def __bool__(self):
        return True
    def seekable(self):
        return False
    def readable(self):
        return self.__stream is not None
    def tell(self):
        return self.__position
    def read(self, _size: int = -1):
        if _size == -1:
            _data, self.__buffer = self.__buffer, b""
            for _chunk in self.__stream:
                _data += _chunk
        else:
            while len(self.__buffer) < _size:
                try:
                    self.__buffer += next(self.__stream)
                except StopIteration:
                    self.__stream = None
                    break
            _data, self.__buffer = self.__buffer[:_size], self.__buffer[_size:]

        self.__position += len(_data)

        return _data

# 加载资源函数
def asset_load() -> None:
    try:
        logger.debug("Loading Setting Files...")
        if os.path.exists("Asset/text/setting.json"):
            with open("Asset/text/setting.json", "rb") as _io:
                _buffer = json.loads(_io.read())
                for _k in _buffer:
                    global_info["setting"][_k] = _buffer[_k]
        else:
            logger.warn("setting.json is Not Existing!")

        if not global_info["setting"]["disable_update_check"]:
            threading.Thread(target=get_version_list, daemon=True).start()
        else:
            logger.info("Disable Update Check")

        logger.set_log_level(global_info["setting"]["log_level"])

        logger.debug("Pygame Font Module Initializing...")
        pygame.font.init()

        logger.debug("UI Renderer Initializing...")
        global_asset["res_logo"] = pygame.image.load("Asset/image/logo.png").convert_alpha()
        global_asset["res_error"] = pygame.image.load("Asset/image/error_background.png").convert_alpha()
        global_asset["res_message"] = pygame.image.load("Asset/image/mask.png").convert_alpha()
        global_asset["res_load_mask"] = pygame.image.load("Asset/image/loading_mask.png").convert_alpha()
        if os.path.exists("Asset/image/custom_menu_background.png"):
            global_asset["menu"] = pygame.image.load("Asset/image/custom_menu_background.png").convert_alpha()
        else:
            global_asset["menu"] = pygame.image.load("Asset/image/default_menu_background.png").convert_alpha()

        if os.path.exists("Cache/image/blur.png"):
            global_asset["blur"] = pygame.image.load("Cache/image/blur.png").convert_alpha()
            _progress = None
        else:
            global_asset["blur"] = pygame.Surface(global_asset["menu"].get_size()).convert_alpha()
            _progress = [0, global_asset["menu"].get_size()[0]]

        change_size((800, 450), False, _progress)
        if _progress is not None:
            global_asset["blur"] = blur_picture(global_asset["menu"], _progress)
            if not os.path.exists("Cache/image"):
                os.makedirs("Cache/image")
            pygame.image.save(global_asset["blur"], "Cache/image/blur.png")
        ui_manager.add_resource(_font_path="Asset/font/font.ttf", _corner_surf=pygame.image.load("Asset/image/corner_mask.png"), _blur_surf=global_asset["blur"], _background_surf=global_asset["menu"])

        logger.debug("Pygame Modules Initializing...")
        pygame.init()

        logger.debug("Loading Mapping Files...")
        with open("Asset/text/mapping.json", "rb") as _io:
            global_asset["mapping"] = json.loads(_io.read())

        logger.debug("Producing Mapping...")
        global_asset["instruments"] = {"other": {}, "percussion": {}}
        for _k, _v in global_asset["mapping"].items():
            if _k not in ("undefined", "default", "percussion"): global_asset["instruments"]["other"][_v] = int(_k)
        for _k, _v in global_asset["mapping"]["percussion"].items():
            if _k != "undefined": global_asset["instruments"]["percussion"][_v] = int(_k)

        if not os.path.exists("Asset/text/default_profile.json"):
            logger.info("Copy Backup Profile")
            shutil.copy("Asset/text/profile.json", "Asset/text/default_profile.json")

        if os.path.isdir("Cache/extracted/Updater"):
            logger.info("Replacing Updater Files...")
            _n = 0
            while _n <= 16:
                try:
                    if os.path.isdir("Updater"):
                        shutil.rmtree("Updater")
                    break
                except:
                    logger.error(traceback.format_exc())
                    _n += 1
            shutil.copytree("Cache/extracted/Updater", "Updater")
            shutil.rmtree("Cache/extracted")

        logger.debug("Scanning .mcstructure Files...")
        global_asset["structure"] = []
        for _n in os.listdir("Asset/mcstructure"):
            if os.path.splitext(_n)[1] == ".mcstructure":
                if "推荐" in _n:
                    global_asset["structure"].insert(0, _n)
                else:
                    global_asset["structure"].append(_n)
        if not global_asset["structure"]:
            logger.warn("No Structure File!")

        logger.debug("Loading Profile...")
        if load_profile():
            global_info["message"].insert(0, "小提示：使用鼠标左右键来进入或返回页面！")
        else:
            global_info["message"].append("无法加载配置文件，已加载默认配置文件！")

        logger.debug("Initialized Successfully!")
        time.sleep(1)

        remove_page(overlay_page)
        global_info["message_info"][2] = True
        add_page(overlay_page, [menu_screen, {"button_state": [0, 0, 0]}], 0, False)
    except:
        global_info["exit"] = 3
        logger.error(traceback.format_exc())

def change_size(_size: tuple[int], _exit: bool, _progress: list | None = None) -> tuple[list[int] | None, pygame.Surface]:
    try:
        # 添加资源
        ui_manager.add_resource(_font_path="Asset/font/font.ttf", _corner_surf=pygame.image.load("Asset/image/corner_mask.png"), _blur_surf=global_asset["blur"], _background_surf=global_asset["menu"])
        # 设置尺寸
        ui_manager.change_size(_size)
        # 加载错误界面
        global_asset["error"] = pygame.transform.smoothscale(global_asset["res_error"], ui_manager.get_abs_position((1, 1)))
        # 加载logo
        global_asset["logo"] = pygame.transform.smoothscale(global_asset["res_logo"], ui_manager.get_abs_position((0.7, 0.142))).convert_alpha()
        # 加载启动遮罩背景
        global_asset["loading_mask"] = pygame.transform.smoothscale(global_asset["res_load_mask"], ui_manager.get_abs_position((1, 1))).convert_alpha()
        # 添加启动页面
        add_page(overlay_page, [loading_screen, {"progress": _progress, "alpha": 0}], 1)
        # 加载字体
        global_asset["font"] = pygame.font.Font("Asset/font/font.ttf", ui_manager.get_abs_position((0, 0.062))[1])
        # 加载消息背景
        global_asset["message_mask"] = pygame.transform.scale(global_asset["res_message"], ui_manager.get_abs_position((1, 0.089))).convert_alpha()
        # 移除页面
        if _exit:
            time.sleep(0.3)
            remove_page(overlay_page)
    except:
        logger.fatal(traceback.format_exc())
        global_info["exit"] = 3

def blur_picture(_surf: pygame.Surface, _progress: list[int], _kernel_size: int=33, _sigma: float=2) -> pygame.Surface:
    _kernel = []
    _radius = _kernel_size // 2

    _max_kernel_var = 0
    for _x in range(_radius * -1, _radius + 1):
        _buffer = []
        for _y in range(_radius * -1, _radius + 1):
            _value = 1 / (2 * math.pi * _sigma ** 2) * math.exp(-(_x ** 2 + _y ** 2) / (2 * _sigma ** 2))
            _buffer.append(_value)
            if _max_kernel_var < _value: _max_kernel_var = _value
        _kernel.append(_buffer)

    _mask_size = (_radius * 2 + 1, _radius * 2 + 1)
    _blur_mask = pygame.Surface(_mask_size).convert_alpha()
    for _x in range(_mask_size[0]):
        for _y in range(_mask_size[1]):
            _blur_mask.set_at((_x, _y), (255, 255, 255, round_45(255 * (1 / _max_kernel_var) * _kernel[_x][_y])))

    _surf_size = _surf.get_size()
    _mask = pygame.Surface(_mask_size).convert_alpha()
    _result = pygame.Surface(_surf_size).convert_alpha()

    _mask.set_alpha(255 * _max_kernel_var)
    for _x in range(_surf_size[0]):
        _progress[0] = _x + 1
        for _y in range(_surf_size[1]):
            _mask.fill(_surf.get_at((_x, _y)))
            _mask.blit(_blur_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            _result.blit(_mask, (_x - _radius, _y - _radius))

    return _result

def load_profile(*, _path: str = "Asset/text/profile.json", _backup_path: str = "Asset/text/default_profile.json") -> bool:
    _result = False
    try:
        with open(_path, "rb") as _io:
            global_asset["profile"] = json.loads(_io.read())
        _result = True
    except:
        logger.error(traceback.format_exc())
        if not _backup_path:
            raise IOError("Can not Load Profile!")
        else:
            load_profile(_path=_backup_path, _backup_path="")

    return _result

def translate_mapping_profile(_mapping: dict, _sound: dict) -> dict:
    _sound_list = {}

    for _k in _mapping:
        if isinstance(_mapping[_k], dict):
            _sound_list[_k] = translate_mapping_profile(_mapping[_k], _sound)
        else:
            if _mapping[_k] in _sound:
                _sound_list[int(_k) if _k not in ("undefined", "default") else _k] = _sound[_mapping[_k]]
            else:
                _sound_list[int(_k) if _k not in ("undefined", "default") else _k] = _sound[_mapping["undefined"]]

    return _sound_list

# MIDI转换
def convertor(_setting, _task_id):
    # 添加正在处理页面
    add_page(overlay_page, [processing_screen, {}])

    try:
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

        with open(_setting["file"], "rb") as _io:
            _path_hash = str(hashlib.file_digest(_io, "md5").hexdigest())

        _midi_reader = MIDIReader(_setting["file"])

        if not os.path.exists("Cache/mapping"): os.makedirs("Cache/mapping")

        try:
            with open("Cache/mapping/" + _path_hash + ".pkl", "rb") as _io:
                _mapping = pickle.load(_io)
            global_info["message"].append("请调整乐器音色映射方案（已加载缓存方案）")
        except:
            logger.warn(traceback.format_exc())
            _mapping = {}
            global_info["message"].append("请调整乐器音色映射方案")

        _instruments = _midi_reader.scan_instruments()

        _info = {"button_state": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], "index": 0, "channel_index": 0, "channels": sorted(_instruments.keys()), "data": _instruments, "mapping": _mapping, "done": [False]}
        add_page(overlay_page, [adj_mapping_screen, _info])

        while not _info["done"][0]:
            time.sleep(0.2)

        try:
            with open("Cache/mapping/" + _path_hash + ".pkl", "wb") as _io:
                pickle.dump(_mapping, _io, protocol=5)
        except:
            logger.warn(traceback.format_exc())

        _midi_reader.override_mapping(_mapping)

        _note_buffer = {}
        _lyrics_buffer = {}
        _average_volume = [0, 0]
        for _time, _data in _midi_reader:
            if _data["type"] == "text":
                # 计算游戏刻数
                _tick_time = int(round_45(_time / _setting["time_per_tick"]))
                # 添加数据到音符缓存中
                if _tick_time not in _lyrics_buffer:
                    _lyrics_buffer[_tick_time] = ""
                _lyrics_buffer[_tick_time] += _data["text"]

            elif _data["type"] == "note":
                # 获取游戏中的音调值
                if 0 <= _data["pitch"] < len(global_asset["profile"]["note_list"]):
                    _pitch = global_asset["profile"]["note_list"][_data["pitch"]]
                else:
                    logger.warn("Pitch " + str(_data["pitch"]) + " Out of Range!")
                    continue

                # 获取游戏中的乐器名称
                if _data["percussion"]:
                    _program = _profile["sound_list"].get(global_asset["mapping"]["percussion"].get(str(_data["program"]), global_asset["mapping"]["percussion"]["undefined"]), _profile["sound_list"][global_asset["mapping"]["percussion"]["undefined"]])
                else:
                    if _data["program"] == -1:
                        _program = _profile["sound_list"][global_asset["mapping"]["default"]]
                    else:
                        _program = _profile["sound_list"].get(global_asset["mapping"].get(str(_data["program"]), global_asset["mapping"]["undefined"]), _profile["sound_list"][global_asset["mapping"]["undefined"]])

                _delay_time = 0
                # 一个音符可以对应多个我的世界乐器，因此这里遍历一下从配置文件中获取的数据
                for _n, _note in enumerate(_program):
                    # 如果禁用单音符对应多个我的世界乐器的功能，仅循环一次就退出
                    if not _setting["adjustment"] and _n > 0:
                        break

                    # 累加配置文件中我的世界乐器之间的时间间隔
                    _delay_time += _note[3]

                    # 如果启用调整音符功能，则会根据配置文件对音量和音调进行调整
                    _note_pitch = _pitch
                    _note_velocity = _data["velocity"]
                    if _setting["adjustment"]:
                        _note_pitch *= _note[2]
                        _note_velocity *= _note[1]

                    # Java版不允许音调范围超出0.5~2.0之间
                    if _setting["edition"] == 1 and not 0.5 <= _note_pitch <= 2:
                        continue

                    # 将音量限制在100%下
                    if _note_velocity >= 1:
                        _note_velocity = 1

                    # 如果启用控制平均音量功能，就记录音量信息
                    if _setting["volume"]:
                        _average_volume[0] += 1
                        _average_volume[1] += _note_velocity

                    _tick_time = int(round_45((_time + _delay_time) / _setting["time_per_tick"]))

                    # 判断音符缓存中是否有改时间，如果没有就创建该时间
                    if _tick_time not in _note_buffer:
                        _note_buffer[_tick_time] = []

                    # 向该时间中添加音符数据
                    _note_buffer[_tick_time].append(
                        {
                            "program": _note[0],
                            "pitch": _note_pitch,
                            "velocity": _note_velocity,
                            "panning": _data["panning"]
                        }
                    )
            else:
                raise TypeError("Unknown Data Type: " + str(_data["type"]))

        # 存放音符和歌词字幕合并后的最终结果
        _result = {}

        # 调整平均音量，音符数据取整，最终合并到结果中
        if _average_volume[0]:
            _average_volume = (_setting["volume"] / 100) / (_average_volume[1] / _average_volume[0])
        else:
            _average_volume = 1

        for _k in _note_buffer:
            for _i in _note_buffer[_k]:
                _note = {
                    "type": "note",
                    "program": _i["program"],
                    "pitch": round_45(_i["pitch"], 2),
                    "velocity": round_45(_i["velocity"] * _average_volume, 2),
                    "panning": list(map(lambda _n: round_45(_n, 2), _i["panning"]))}

                if _k not in _result:
                    _result[_k] = []
                # 去除重复的音符
                if _note not in _result[_k]:
                    _result[_k].append(_note)

        # 歌词数据处理
        if _setting["lyrics"]["enable"]:
            _lyrics_file: bool = os.path.exists(os.path.splitext(_setting["file"])[0] + ".lrc")
            if _lyrics_file:
                logger.info("Find LRC File")

                for _charset in ("utf-8", "ANSI"):
                    try:
                        with open(os.path.splitext(_setting["file"])[0] + ".lrc", "r", encoding=_charset) as _io:
                            _lyrics_buffer = load_lrc(_io.read().splitlines(), _setting["time_per_tick"])
                        break
                    except:
                        pass
            # 渲染歌词字幕
            if _lyrics_buffer:
                _last_l = None
                for _k, _l in LyricsList(_lyrics_buffer, _setting["lyrics"]["smooth"], _setting["lyrics"]["joining"]):
                    # 判断与上个歌词显示内容是否不同
                    if _last_l == _l and _setting["compression"] == 1:
                        continue
                    # 将歌词数据合并到结果中
                    if _k not in _result:
                        _result[_k] = []
                    _result[_k].append({
                        "type": "lyrics",
                        "last": _l[0],
                        "real_f": _l[1][0],
                        "real_s": _l[1][1],
                        "next": _l[2]})
                    _last_l = _l

        # 获取最早的数据的时间，用于跳过静音功能
        if _setting["skip"]:
            _time_offset = min(list(_result))
        else:
            _time_offset = 0

        # 根据需要将音符数据转为各种文件
        if os.path.exists("Cache/convertor"):shutil.rmtree("Cache/convertor")
        os.makedirs("Cache/convertor")
        if os.path.exists("Cache/output"):shutil.rmtree("Cache/output")
        os.makedirs("Cache/output")

        _music_name = os.path.splitext(os.path.basename(_setting["file"]))[0]

        if _setting["output_format"] == 0:
            with open("Cache/convertor/raw_command.txt", "w", encoding="utf-8") as _io:
                _io.write("# music_name=" + _music_name + "\n")
                _io.write("# length_of_time=" + str(max(list(_result))) + "\n")

                for _cmd in cmd_convertor(_setting, _profile, _result, _task_id, _time_offset, (True if _setting["command_type"] == 0 else False)):
                    _io.write(_cmd + "\n")

            subprocess.Popen(" ".join(
                (
                    "Writer/writer.exe",
                    "-l " + str(global_info["setting"]["log_level"]),
                    "-s Asset/mcstructure/" + global_asset["structure"][_setting["structure"]],
                    "-c Cache/convertor/raw_command.txt",
                    "-id " + ("0" if _task_id is None else str(_task_id)),
                    "Cache/output/structure.mcstructure"
                )
            )).wait()

            if not os.path.exists("Cache/output/structure.mcstructure"):
                raise IOError("structure.mcstructure Not in Cache!")

            if _save_path := filedialog.asksaveasfilename(title="MIDI-MCSTRUCTURE NEXT",
                                                          initialfile=_music_name + "-" + uuid(6).upper(),
                                                          filetypes=[("Structure Files", ".mcstructure")],
                                                          defaultextension=".mcstructure"):
                if os.path.exists(_save_path): os.remove(_save_path)
                shutil.copyfile("Cache/output/structure.mcstructure", _save_path)
        elif _setting["output_format"] == 1:
            if _setting["command_type"] == 0: raise ValueError("Unsupported Command Type!")

            with open("Cache/convertor/function.mcfunction", "w", encoding="utf-8") as _io:
                for _cmd in cmd_convertor(_setting, _profile, _result, _task_id, _time_offset, False):
                    _io.write(_cmd + "\n")

            if _setting["edition"] == 0:
                if not os.path.exists("Cache/output/functions") :os.makedirs("Cache/output/functions")

                with open("Asset/text/manifest.json", "rb") as _io:
                    _manifest_file = json.loads(_io.read())

                _manifest_file["header"]["name"] = _music_name
                if _setting["version"] == 1: _manifest_file["header"]["min_engine_version"] = [1, 19, 50]
                _manifest_file["header"]["uuid"] = "-".join((uuid(8), uuid(4), uuid(4), uuid(4), uuid(12)))
                _manifest_file["modules"][0]["uuid"] = "-".join((uuid(8), uuid(4), uuid(4), uuid(4), uuid(12)))

                _behavior_file = [
                    {
                        "pack_id": _manifest_file["header"]["uuid"],
                        "version": _manifest_file["header"]["version"]
                    }
                ]

                shutil.copyfile(
                    "Cache/convertor/function.mcfunction",
                    "Cache/output/functions/midi_player.mcfunction"
                )

                with open("Cache/output/manifest.json", "w", encoding="utf-8") as _io:
                    _io.write(json.dumps(_manifest_file))

                with open("Cache/output/world_behavior_packs.json", "w", encoding="utf-8") as _io:
                    _io.write(json.dumps(_behavior_file))

                shutil.copyfile(
                    "Asset/image/icon.png",
                    "Cache/output/pack_icon.png"
                )
            elif _setting["edition"] == 1:
                os.makedirs("Cache/output/data/mms/functions")

                _behavior_file = {"pack": {"pack_format": 1, "description": "§r§fBy §dMIDI-MCSTRUCTURE §bNEXT"}}

                shutil.copyfile(
                    "Cache/convertor/function.mcfunction",
                    "Cache/output/data/mms/functions/midi_player.mcfunction"
                )

                with open("Cache/output/pack.mcmeta", "w", encoding="utf-8") as _io:
                    _io.write(json.dumps(_behavior_file))

            if _setting["version"] == 0 and _setting["edition"] == 1:
                if _save_path := filedialog.asksaveasfilename(title="MIDI-MCSTRUCTURE NEXT",
                                                              initialfile=_music_name,
                                                              filetypes=[("Function Files", ".mcfunction")],
                                                              defaultextension=".mcfunction"):
                    if os.path.exists(_save_path): os.remove(_save_path)
                    shutil.copyfile("Cache/convertor/function.mcfunction", _save_path)
            else:
                if _save_path := filedialog.asksaveasfilename(title="MIDI-MCSTRUCTURE NEXT",
                                                              filetypes=[("ZIP Files", ".zip")],
                                                              initialfile=_music_name,
                                                              defaultextension=".zip"):
                    if os.path.exists(_save_path): os.remove(_save_path)
                    shutil.make_archive(os.path.splitext(_save_path)[0], "zip", "Cache/output")
        elif _setting["output_format"] == 2:
            _last = _time_offset
            _buffer = []
            for _k in sorted(_result.keys()):
                for _n, _note in enumerate(_result[_k]):
                    if _n == 0:
                        _delay = _k - _last
                    else:
                        _delay = 0
                    match _note:
                        case {"type": "note", "program": _sound, "pitch": _pitch, "velocity": _volume, "panning": (_x, _y)}:
                            _buffer.append([_delay, "n", _sound, _pitch, _volume, _x, _y])
                        case {"type": "lyrics", "last": _last, "real_f": _rf, "real_s": _rs, "next": _next}:
                            _buffer.append([_delay, "l", _last, _rf, _rs, _next])
                        case _:
                            raise TypeError("Unknown Data Type: " + _note["type"])
                _last = _k

            shutil.unpack_archive("Cache/mcpack/" + os.listdir("Cache/mcpack")[0], "Cache/convertor")

            with open("Cache/convertor/scripts/main.js", "r", encoding="utf-8") as _io:
                _code = _io.read()

            with open("Cache/convertor/scripts/main.js", "w", encoding="utf-8") as _io:
                _io.write(_code.replace("{SOUND_NAME}", _music_name, 1).replace("{SOUND_DATA}", json.dumps(_buffer, indent=2), 1))

            with open("Cache/convertor/manifest.json", "rb") as _io:
                _manifest_file = json.loads(_io.read())

            _manifest_file["header"]["name"] = _music_name
            _manifest_file["header"]["uuid"] = "-".join((uuid(8), uuid(4), uuid(4), uuid(4), uuid(12)))
            _manifest_file["modules"][0]["uuid"] = "-".join((uuid(8), uuid(4), uuid(4), uuid(4), uuid(12)))

            with open("Cache/convertor/manifest.json", "w", encoding="utf-8") as _io:
                _io.write(json.dumps(_manifest_file))

            shutil.make_archive("Cache/output/package", "zip", "Cache/convertor")
            if _save_path := filedialog.asksaveasfilename(title="MIDI-MCSTRUCTURE NEXT",
                                                          filetypes=[("MCPACK Files", ".mcpack")],
                                                          initialfile=_music_name,
                                                          defaultextension=".mcpack"):
                if os.path.exists(_save_path): os.remove(_save_path)
                shutil.copyfile("Cache/output/package.zip", _save_path)
    except:
        global_info["message"].append("转换失败，请将log.txt发送给开发者以修复问题！")
        logger.error(traceback.format_exc())
    finally:
        remove_page(overlay_page)

def cmd_convertor(_setting: dict, _profile: dict, _result: list, _task_id: int, _time_offset: int, _delay_info: bool) -> list[str]:
    if _setting["command_type"] == 0:
        _raw_cmd = _profile["command"]["delay"][0]
    elif _setting["command_type"] == 1:
        _raw_cmd = _profile["command"]["clock"][0]
    elif _setting["command_type"] == 2:
        _raw_cmd = _profile["command"]["address"][0]
    else:
        raise ValueError("Unknown Command Type: " + str(_setting["command_type"]))

    _cmd_list = []
    if _setting["command_type"] == 0:
        _last_time = _time_offset
        for _k in sorted(list(_result)):
            for _n, _i in enumerate(_result[_k]):
                if _i["type"] == "note":
                    _cmd = _raw_cmd.replace(
                        "{SOUND}", _i["program"]).replace(
                        "{POSITION}", ("^" + str(_i["panning"][0]) + " ^ ^" + str(_i["panning"][1]) if _setting["panning"] else "~ ~ ~")).replace(
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
    else:
        _data_buffer = {}
        for _k in sorted(list(_result)):
            for _n, _i in enumerate(_result[_k]):
                if _i["type"] == "note":
                    _data = ("note",
                             _i["program"],
                             ("^" + str(_i["panning"][0]) + " ^ ^" + str(_i["panning"][1]) if _setting["panning"] else "~ ~ ~"),
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

                if _data not in _data_buffer:
                    _data_buffer[_data] = []

                _time_object = _k - _time_offset
                if _time_object not in _data_buffer[_data]:
                    _data_buffer[_data].append(_time_object)

        _data_pool = {}
        for _k in _data_buffer:
            _data_num = 0
            _label_id = 0
            for _i in _data_buffer[_k]:
                if _data_num >= _setting["compression"]:
                    _label_id += 1
                    _data_num = 0

                _key = _k + tuple([_label_id])

                if _key not in _data_pool:
                    _data_pool[_key] = []

                _data_pool[_key].append(_i)
                _data_num += 1

        for _data in _data_pool:
            _selector = ""
            _time_list = _data_pool[_data]
            _list_length = len(_time_list)

            if _list_length == 1:
                _selector = _profile["command"]["timer_target_selector"]["regular"].replace("{VALUE}", str(_time_list[0]))
            else:
                _str_length = len(_profile["command"]["timer_target_selector"]["compressed"][2])
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
                        _selector += _profile["command"]["timer_target_selector"]["compressed"][2]

                    if _start_time != "" and _end_time != "":
                        if _start_time == _end_time:
                            _selector += _profile["command"]["timer_target_selector"]["compressed"][0].replace(
                                "{VALUE}", str(_end_time)
                            )
                        elif _start_time > _end_time:
                            _selector = _selector[:-_str_length]
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
                raise TypeError("Unknown Data Type: " + str(_data[0]))

            _cmd_list.append(_cmd[1:] if _cmd[0] == "/" else _cmd)

    if _setting["command_type"] == 0:
        _raw_cmd = _profile["command"]["delay"][1:]
    elif _setting["command_type"] == 1:
        _raw_cmd = _profile["command"]["clock"][1:]
    elif _setting["command_type"] == 2:
        _raw_cmd = _profile["command"]["address"][1:]
    else:
        _raw_cmd = []

    if _raw_cmd:
        if _delay_info:
            _cmd_list.append("# tick_delay=0")

        for _i in _raw_cmd:
            _cmd = _i.replace(
                "{TIME}", str(max(list(_result)))).replace(
                "{ADDRESS}", str(_task_id))
            _cmd_list.append(_cmd[1:] if _cmd[0] == "/" else _cmd)

    return _cmd_list

def load_lrc(_str: list[str], _time_per_tick: int=50) -> dict[int, str]:
    _offset = 0
    _buffer = {}
    for _line in _str:
        if _length := len(_line):
            _tags = []
            _start = None
            _argument = ""
            for _i in range(_length):
                if _line[_i] == "[" and _start is None:
                    _start = _i
                elif _line[_i] == "]" and _start is not None:
                    _tags.append(_line[_start + 1:_i])
                    _start = None
                elif _start is None:
                    _argument = _line[_i:]
                    break

            for _tag in _tags:
                _tag_type, _value = _tag.split(":", 1)
                if is_number(_tag_type):
                    _time = (float(_tag_type) * 60 + float(_value)) * 1000
                    if _time not in _buffer:
                        _buffer[_time] = ""
                    _buffer[_time] += _argument

                elif _tag_type == "offset":
                    _offset = int(_value)

    _result = {}
    for _i in _buffer:
        _tick_time = int(round_45((_i - _offset) / _time_per_tick))
        if _tick_time >= 0:
            _result[_tick_time] = _buffer[_i]

    return _result

# 页面渲染函数
def render_page(_root: pygame.Surface, _overlay: list, _event: dict):
    _pages_num = len(_overlay)
    for _n in range(_pages_num):
        if _n + 1 == _pages_num or _overlay[_n + 1][2] != 1:
            _window = _overlay[_n][0](_overlay[_n][1], _event if _overlay[_n][3] else {})
            _window.set_alpha(_overlay[_n][2] * 255)
            _root.blit(_window, (0, 0))
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

    if global_info["message"] and global_info["message_info"][2]:
        global_info["message_info"][1] += timer.get_time()

        _root.blit(global_asset["message_mask"], ui_manager.get_abs_position((0, 1 - global_info["message_info"][0] * 0.089), True))

        _text_surface = global_asset["font"].render(global_info["message"][0], True, (255, 255, 255))
        _text_surface.set_alpha(255 * global_info["message_info"][0])

        _text_position = ui_manager.get_abs_position((0.5, 1.044 - global_info["message_info"][0] * 0.089), True)
        _root.blit(_text_surface, (_text_position[0] - _text_surface.get_size()[0] / 2, _text_position[1] - global_asset["font"].get_height() / 2))

        if global_info["message_info"][1] <= 3000:
            global_info["message_info"][0] += (1 - global_info["message_info"][0]) * global_info["animation_speed"]
        else:
            global_info["message_info"][0] -= global_info["message_info"][0] * global_info["animation_speed"]

            if global_info["message_info"][0] < 0.01:
                del global_info["message"][0]
                global_info["message_info"] = [0, 0, True]

# 功能函数
def watchdog():
    try:
        while True:
            if global_info["watch_dog"] >= 30:
                logger.fatal("Run Timed Out of 3000ms Exceeded!\nProcess is Killed by Watchdog!")
                logger.done()
                break
            global_info["watch_dog"] += 1
            time.sleep(0.1)
    finally:
        os._exit(1)

def change_button_alpha(_state: list[float], _index: int) -> None:
    for _n in range(len(_state)):
        if _n == _index:
            _state[_n] += (255 - _state[_n]) * global_info["animation_speed"]
        else:
            _state[_n] += (127 - _state[_n]) * global_info["animation_speed"]

def reduce_background(_path: str = "") -> None:
    try:
        if not _path: _path = filedialog.askopenfilename(title="MIDI-MCSTRUCTURE NEXT", filetypes=[("Image Files", ".png"), ("Image Files", ".jpg"), ("Image Files", ".jpeg")])
        if _path:
            pygame.image.save(pygame.transform.smoothscale(pygame.image.load(_path), (800, 450)), "Asset/image/custom_menu_background.png")
            shutil.rmtree("Cache/image")
            global_info["message"].append("已成功设置背景，重启软件生效！")
    except:
        logger.error(traceback.format_exc())
        global_info["message"].append("无法加载图片文件！")

def set_selector_num(_num: None | int = None) -> None:
    if _num is None:
        global_info["message"].append("请输入最多压缩到单条指令内的时间项数！")
        add_page(overlay_page, [keyboard_screen, {"value": global_info["setting"]["max_selector_num"], "text": "", "callback": set_selector_num, "button_state": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}])
    else:
        if _num >= 2:
            global_info["setting"]["max_selector_num"] = _num
        else:
            global_info["setting"]["max_selector_num"] = 2
            global_info["message"].append("单条指令内的时间项数至少为2个！")

def show_download(_title: str, _url: str, _target_path, _callback=lambda: remove_page(overlay_page)):
    _state = {"state": 0, "object": None}
    threading.Thread(target=download, args=(_url, _state, _target_path), daemon=True).start()
    add_page(overlay_page, [download_screen, {"state": _state, "title": _title, "time": 0, "done": False, "callback": _callback}])

def reboot_to_update():
    global_info["exit"] = 2

def start_install_editor():
    remove_page(overlay_page)
    threading.Thread(target=install_editor, daemon=True).start()

def install_editor():
    try:
        enter_to_editor()
    except:
        logger.error(traceback.format_exc())

def enter_to_editor(_path: str = ""):
    add_page(overlay_page, [processing_screen, {}])
    _remove = True
    try:
        if _path: shutil.copy(_path, "Asset/text/profile.json")

        try:
            with open("Editor/metadata.json", "rb") as _io:
                _meta_data = json.loads(_io.read())

            if global_info["editor_update"] and _meta_data["version"] < global_info["editor_update"]["version"]:
                raise Exception("New Edition Version is Available")

            subprocess.Popen("Editor/ProfileEditor.exe").wait()
        except:
            _remove = False
            remove_page(overlay_page)

            logger.error(traceback.format_exc())

            if global_info["editor_update"]["version"] > 0:
                show_download(
                    "ProfileEditor V" + str(global_info["editor_update"]["version"]),
                    global_info["editor_update"]["download_url"],
                    "Editor",
                    start_install_editor
                )
            else:
                global_info["message"].append("无法加载编辑器版本信息，请稍后重试！")

            raise

        if load_profile():
            global_info["message"].append("已重新加载配置文件！")
        else:
            global_info["message"].append("无法加载配置文件，已加载备配置文件！")
    except:
        logger.error(traceback.format_exc())
    finally:
        if _remove: remove_page(overlay_page)

def open_filedialog():
    try:
        if _path := filedialog.askopenfilename(title="MIDI-MCSTRUCTURE NEXT", filetypes=[("MIDI Files", ".mid")]):
            global_info["convertor"]["file"] = _path
            if os.path.exists(os.path.splitext(_path)[0] + ".lrc"):
                global_info["message"].append("检测到同名的.lrc文件，启用歌词显示即可加载歌词！")
            else:
                global_info["message"].append("未检测到同名的.lrc文件，若启用歌词显示将尝试从MIDI中获取")
    except:
        logger.error(traceback.format_exc())

def set_time_per_tick(_time: None | int = None) -> None:
    if _time is None:
        global_info["message"].append("请输入每游戏刻的时间！")
        add_page(overlay_page, [keyboard_screen, {"value": global_info["convertor"]["time_per_tick"], "text": "ms/tick", "callback": set_time_per_tick, "button_state": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}])
    else:
        global_info["convertor"]["time_per_tick"] = _time

def start_task(_id: None | int = None) -> None:
    if not global_info["convertor"]["file"]:
        return
    if global_info["convertor"]["edition"] == -1:
        return
    if global_info["convertor"]["output_format"] == -1:
        return
    if global_info["convertor"]["time_per_tick"] == -1:
        return

    if global_info["convertor"]["command_type"] == 2 and _id is None:
        global_info["message"].append("请输入编号！")
        add_page(overlay_page, [keyboard_screen, {"value": global_info["setting"]["id"], "text": "", "callback": start_task, "button_state": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}])
    else:
        if _id is not None: global_info["setting"]["id"] = _id
        _argument = global_info["convertor"].copy()
        _argument["compression"] = global_info["setting"]["max_selector_num"] if global_info["convertor"]["compression"] else 1
        threading.Thread(target=convertor, args=(_argument, _id), daemon=True).start()

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
        with requests.get("https://gitee.com/mrdxhmagic/midi-mcstructure_next/raw/master/update.json") as _response:
            _response.raise_for_status()
            _update_log = _response.json()

        _update_list = []
        for _i in _update_log:
            match _i["API"]:
                case 3:
                    _update_list.append(_i)
                case 4:
                    if _i["version"] > global_info["editor_update"]["version"]: global_info["editor_update"] = _i
                case 5:
                    global_info["mcpack_update"][0] = _i["hash"]
                    global_info["mcpack_update"][1] = _i["download_url"]
                case _:
                    logger.info("Unknown API Version: " + str(_i["API"]))

        if global_info["mcpack_update"][0]: update_mcpack()

        _update_list.sort(key=lambda _i: _i["version"], reverse=True)

        for _i in _update_list:
            if _i["edition"] not in global_info["update_list"][0]:
                global_info["update_list"][0].append(_i["edition"])
                global_info["update_list"][1][_i["edition"]] = []
            global_info["update_list"][1][_i["edition"]].append(_i)

        global_info["new_version"] = _update_list[0]["version"] > global_info["setting"]["version"]
    except:
        logger.error(traceback.format_exc())

def download(_url, _state, _target_path, _extract=True):
    try:
        _state["state"] = 0

        with NetStream(_url) as _net:
            _state["object"] = _net
            with tarfile.open(fileobj=_net, mode="r|zst") as _io:
                _io.extractall(_target_path)

        _state["state"] = 1
    except:
        logger.error(traceback.format_exc())
        _state["state"] = -1

def update_mcpack():
    try:
        if os.path.exists("Cache/mcpack/" + global_info["mcpack_update"][0] + ".tar.zst"):
            logger.info("Behavior Package is the Lasest Version!")
        else:
            logger.info("Try to update Behavior Package")
            if os.path.exists("Cache/mcpack"):
                shutil.rmtree("Cache/mcpack")
            os.makedirs("Cache/mcpack")

            _real_hash = hashlib.md5()
            with open("Cache/mcpack/" + global_info["mcpack_update"][0] + ".tar.zst", "ab") as _io:
                with requests.get(global_info["mcpack_update"][1], stream=True) as _response:
                    _response.raise_for_status()

                    for _data_chunk in _response.iter_content(chunk_size=1024):
                        _real_hash.update(_data_chunk)
                        _io.write(_data_chunk)

            if global_info["mcpack_update"][0] != str(_real_hash.hexdigest()):
                raise IOError("Broken Package, Please Try Again.")

            global_info["message"].append("行为包模板更新成功！")
    except:
        logger.warn(traceback.format_exc())
        global_info["message"].append("MMS检测到行为包模板更新，但因某些原因无法更新")

# 各种函数（用于GUI）
def loading_screen(_info, _input) -> pygame.Surface:
    _surf = ui_manager.get_blur_background(True)
    if _info["progress"] is not None:
        pygame.draw.rect(_surf, (255, 255, 255), ui_manager.get_abs_position((0.25, 0.733), True) + ui_manager.get_abs_position((0.5, 0.053)), 2)
        pygame.draw.rect(_surf, (255, 255, 255), ui_manager.get_abs_position((0.255, 0.742), True) + ui_manager.get_abs_position((0.49 * (_info["progress"][0] / _info["progress"][1]), 0.036)), 0)
        if _info["progress"][0] == _info["progress"][1]:
            _info["alpha"] += (255 - _info["alpha"]) * global_info["animation_speed"]
            _surf.set_alpha(round_45(_info["alpha"]))
    _surf.blits(((global_asset["loading_mask"], ui_manager.get_abs_position((0, 0), True)), (global_asset["logo"], ui_manager.get_abs_position((0.15, 0.429), True))))
    return _surf

def menu_screen(_info, _input):
    if "drop_file" in _input:
        match os.path.splitext(_input["drop_file"])[1]:
            case ".mid":
                add_page(overlay_page, [convertor_screen, {"button_state": [0, 0, 0, 0, 0]}])
                global_info["convertor"]["file"] = _input["drop_file"]
            case ".mspf":
                threading.Thread(target=enter_to_editor, args=[_input["drop_file"]], daemon=True).start()
            case _i if _i in (".jpeg", ".jpg", ".png"):
                threading.Thread(target=reduce_background, args=[_input["drop_file"]], daemon=True).start()
            case _:
                global_info["message"].append("不支持的文件格式 " + os.path.basename(_input["drop_file"]))

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("转换文件", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("软件设置" + ("（新版本）" if global_info["new_version"] else ""), 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("关于MIDI-MCSTRUCTURE NEXT", 0.035, _info["button_state"][2]), 2)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                add_page(overlay_page, [convertor_screen, {"button_state": [0, 0, 0, 0, 0]}])
            case 1:
                add_page(overlay_page, [software_setting_screen, {"button_state": [0, 0, 0, 0, 0, 0, 0]}])
            case 2:
                if global_info["setting"]["version"]:
                    _edition = "V" + str(global_info["setting"]["version"])
                else:
                    _edition = "Unknown"
                if global_info["setting"]["edition"]:
                    _edition += "-" + str(global_info["setting"]["edition"])
                add_page(overlay_page, [about_screen, {"edition": _edition, "button_state": [0, 0, 0]}])

    change_button_alpha(_info["button_state"], _id)

    return _root

def convertor_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    if "drop_file" in _input:
        if os.path.splitext(_input["drop_file"])[1] == ".mid":
            global_info["convertor"]["file"] = _input["drop_file"]
        else:
            global_info["message"].append("不支持的文件格式 " + os.path.basename(_input["drop_file"]))

    if global_info["convertor"]["edition"] == 0:
        _ver_text = "基岩版"
        if global_info["convertor"]["output_format"] == 2:
            pass
        elif global_info["convertor"]["version"] == 0:
            _ver_text += "（1.19.50以下）"
        elif global_info["convertor"]["version"] == 1:
            _ver_text += "（1.19.50以上）"
    elif global_info["convertor"]["edition"] == 1:
        _ver_text = "Java版"
        if global_info["convertor"]["version"] == 0:
            _ver_text += "（1.13以下）"
        elif global_info["convertor"]["version"] == 1:
            _ver_text += "（1.13以上）"
    else:
        _ver_text = "选择游戏版本"

    if global_info["convertor"]["output_format"] != -1:
        if global_info["convertor"]["output_format"] == 0:
            _base_text = "mcstructure"
        elif global_info["convertor"]["output_format"] == 1:
            _base_text = "mcfunction"
        elif global_info["convertor"]["output_format"] == 2:
            _base_text = "SAPI行为包"
        else:
            _base_text = ""

        if global_info["convertor"]["output_format"] == 2:
            pass
        elif global_info["convertor"]["command_type"] == 0:
            _base_text += "/命令链延迟"
        elif global_info["convertor"]["command_type"] == 1:
            _base_text += "/计分板时钟"
        elif global_info["convertor"]["command_type"] == 2:
            _base_text += "/时钟与编号"

        if global_info["convertor"]["volume"]: _base_text += "/" + str(global_info["convertor"]["volume"]) + "%"

        if global_asset["structure"] and global_info["convertor"]["output_format"] == 0: _base_text += "/" + os.path.splitext(global_asset["structure"][global_info["convertor"]["structure"]])[0]
    else:
        _base_text = "基本设置"

    if global_info["convertor"]["time_per_tick"] != -1:
        _other_text = str(global_info["convertor"]["time_per_tick"]) + "ms"
        if global_info["convertor"]["panning"]:
            _other_text += "/声相偏移"
        if global_info["convertor"]["skip"]:
            _other_text += "/静音跳过"
        if global_info["convertor"]["percussion"]:
            _other_text += "/打击乐器"
        if global_info["convertor"]["adjustment"]:
            _other_text += "/乐器调整"
        if global_info["convertor"]["lyrics"]["enable"]:
            _other_text += "/歌词"
        if global_info["convertor"]["compression"]:
            _other_text += "/压缩"
    else:
        _other_text = "其他设置"

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, (os.path.splitext(os.path.basename(global_info["convertor"]["file"]))[0] if global_info["convertor"]["file"] else "选择MIDI文件", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, (_ver_text, 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, (_base_text, 0.035, _info["button_state"][2]), 2),
            (0.025, 0.444, 0.95, 0.089, (_other_text, 0.035, _info["button_state"][3]), 3),
            (0.025, 0.578, 0.95, 0.089, ("开始转换", 0.035, _info["button_state"][4]), 4)
        ),
        pygame.mouse.get_pos()
    )

    change_button_alpha(_info["button_state"], _id)

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                threading.Thread(target=open_filedialog, daemon=True).start()
            case 1:
                if global_info["convertor"]["edition"] == -1:
                    global_info["convertor"]["edition"] = 0
                add_page(overlay_page, [game_edition_screen, {"button_state": [0, 0]}])
            case 2:
                if global_info["convertor"]["output_format"] == -1:
                    global_info["convertor"]["output_format"] = 0
                add_page(overlay_page, [setting_screen, {"button_state": [0, 0, 0, 0]}])
            case 3:
                if global_info["convertor"]["time_per_tick"] == -1:
                    global_info["convertor"]["time_per_tick"] = 50
                add_page(overlay_page, [other_setting_screen, {"button_state": [0, 0, 0, 0, 0, 0, 0]}])
            case 4:
                if not global_info["convertor"]["file"]:
                    global_info["message"].append("请选择文件")
                elif global_info["convertor"]["edition"] == -1:
                    global_info["message"].append("请选择游戏版本")
                elif global_info["convertor"]["output_format"] == -1:
                    global_info["message"].append("请完成常用设置")
                elif global_info["convertor"]["time_per_tick"] == -1:
                    global_info["message"].append("请完成其他设置")
                else:
                    start_task()

    return _root

def software_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        global_info["new_version"] = False
        remove_page(overlay_page)

    match global_info["setting"]["log_level"]:
        case 0:
            _text = "DISABLE"
        case 1:
            _text = "FATAL"
        case 2:
            _text = "ERROR"
        case 3:
            _text = "WARN"
        case 4:
            _text = "INFO"
        case 5:
            _text = "DEBUG"
        case _:
            _text = "未知"

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("查看更新" + ("（新版本）" if global_info["new_version"] else ""), 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("单指令内时间数 " + str(global_info["setting"]["max_selector_num"]), 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("界面刷新率 " + (str(global_info["setting"]["fps"]) + "Hz" if global_info["setting"]["fps"] else "无限制"), 0.035, _info["button_state"][2]), 2),
            (0.025, 0.444, 0.95, 0.089, ("动画速度 " + (str(global_info["setting"]["animation_speed"]) if global_info["setting"]["animation_speed"] != 0 else "禁用"), 0.035, _info["button_state"][3]), 3),
            (0.025, 0.578, 0.95, 0.089, ("日志等级 " + _text, 0.035, _info["button_state"][4]), 4),
            (0.025, 0.711, 0.95, 0.089, ("自定义背景", 0.035, _info["button_state"][5]), 5),
            (0.025, 0.844, 0.95, 0.089, ("MMS指令编辑器", 0.035, _info["button_state"][6]), 6)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                add_page(overlay_page, [version_list_screen, {"tag_index": 0, "index": 0, "edition_info": global_info["update_list"], "button_state": [0, 0, 0, 0, 0]}])
            case 1:
                set_selector_num()
            case 2:
                global_info["setting"]["fps"] += 30
                if global_info["setting"]["fps"] > 120:
                    global_info["setting"]["fps"] = 0
            case 3:
                global_info["setting"]["animation_speed"] += 1
                if global_info["setting"]["animation_speed"] >= 16:
                    global_info["setting"]["animation_speed"] = 0
            case 4:
                global_info["setting"]["log_level"] += 1
                if global_info["setting"]["log_level"] >= 6:
                    global_info["setting"]["log_level"] = 0
                logger.set_log_level(global_info["setting"]["log_level"])
            case 5:
                threading.Thread(target=reduce_background, daemon=True).start()
            case 6:
                threading.Thread(target=enter_to_editor, daemon=True).start()

    change_button_alpha(_info["button_state"], _id)

    return _root

def version_list_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    if global_info["update_list"][1]:
        _ver_list = _info["edition_info"][1][_info["edition_info"][0][_info["tag_index"]]]

        _root, _id = ui_manager.apply_ui(
            (
                (0.025, 0.044, 0.575, 0.089, (_info["edition_info"][0][_info["tag_index"]], 0.035, _info["button_state"][4]), 4),
                (0.625, 0.044, 0.05, 0.089, ("◀", 0.035, _info["button_state"][0]), 0),
                (0.7, 0.044, 0.2, 0.089, (str(_info["index"] + 1) + "/" + str(len(_ver_list)), 0.035, 255), -1),
                (0.925, 0.044, 0.05, 0.089, ("▶", 0.035, _info["button_state"][1]), 1),
                (0.025, 0.178, 0.95, 0.089, ("V" + str(_ver_list[_info["index"]]["version"]) + ("-" + str(_ver_list[_info["index"]]["edition"]) if _ver_list[_info["index"]]["edition"] else ""), 0.035, 255), -1),
                (0.025, 0.311, 0.95, 0.089, (_ver_list[_info["index"]]["tips"], 0.035, 255), -1),
                (0.025, 0.444, 0.95, 0.089, ("查看版本详情", 0.035, _info["button_state"][2]), 2),
                (0.025, 0.578, 0.95, 0.089, ("立即下载并安装", 0.035, _info["button_state"][3]), 3)
            ),
            pygame.mouse.get_pos()
        )

        if "mouse_left" in _input and not _input["mouse_left"]:
            match _id:
                case 0:
                    _info["index"] -= 1
                    if _info["index"] < 0:
                        _info["index"] = len(_ver_list) - 1
                case 1:
                    _info["index"] += 1
                    if _info["index"] >= len(_ver_list):
                        _info["index"] = 0
                case 2:
                    if _ver_list[_info["index"]]["description_url"]: webbrowser.open(_ver_list[_info["index"]]["description_url"])
                case 3:
                    _ver_info = _ver_list[_info["index"]]
                    show_download(
                        ("V" + str(global_info["setting"]["version"]) + "  ➡  " if global_info["setting"]["version"] else "") + "V" + str(_ver_info["version"]),
                        _ver_info["download_url"],
                        "Cache/extracted",
                        reboot_to_update

                    )
                case 4:
                    _info["index"] = 0
                    _info["tag_index"] += 1
                    if _info["tag_index"] >= len(_info["edition_info"][0]):
                        _info["tag_index"] = 0

        change_button_alpha(_info["button_state"], _id)
    else:
        _root = ui_manager.get_blur_background()
        _text_surface = global_asset["font"].render("无法获取版本信息", True, (255, 255, 255))
        _text_position = ui_manager.get_abs_position((0.5, 0.5), True)
        _root.blit(_text_surface, (_text_position[0] - _text_surface.get_size()[0] / 2, _text_position[1] - global_asset["font"].get_height() / 2))

    return _root

def about_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.267, ("", 0, 0), -1),
            (0.025, 0.267, 0.95, 0, (_info["edition"], 0.035, 255), -1),
            (0.025, 0.356, 0.95, 0.1, ("交流群(密码14890357)", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.489, 0.95, 0.1, ("MMS-NEXT 开源仓库", 0.035, _info["button_state"][1]), 1),
            (0.025, 0.622, 0.95, 0.1, ("MMS 开源仓库", 0.035, _info["button_state"][2]), 2)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        if _id == 0:
            webbrowser.open("qm.qq.com/q/9oBhTyDN8k")
        elif _id == 1:
            webbrowser.open("gitee.com/mrdxhmagic/midi-mcstructure_next")
        elif _id == 2:
            webbrowser.open("gitee.com/mrdxhmagic/midi-mcstructure")

    change_button_alpha(_info["button_state"], _id)

    _root.blit(global_asset["logo"], ui_manager.get_abs_position((0.155, 0.062), True))

    return _root

def download_screen(_info, _input):
    if _info["state"]["state"] == -1 and _info["time"] != -1:
        _info["time"] += timer.get_time()
    if _info["time"] >= 3000:
        remove_page(overlay_page)
        _info["time"] = -1

    if _info["state"]["object"] is None:
        _text = "等待中"
    elif _info["state"]["state"] == 0:
        _text = str(round_45((_info["state"]["object"].tell() / _info["state"]["object"].size) * 100, 2)) + "%" if _info["state"]["object"].size else "等待中"
    elif _info["state"]["state"] == 1:
        _text = "下载完成"
        if not _info["done"]:
            _info["callback"]()
            _info["done"] = True
    elif _info["state"]["state"] == -1:
        _text = "下载失败，请重试"
    else:
        _text = ""

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, (_info["title"], 0.035, 255), -1),
            (0.025, 0.177, 0.95, 0.089, (_text, 0.035, 255), -1)
        ),
        pygame.mouse.get_pos()
    )

    return _root

def adj_mapping_screen(_info, _input):
    _config_length = len(_info["data"][_info["channels"][_info["channel_index"]]])
    _page_num = round_01(_config_length / 6)

    _config_list = []
    _index_offset = _info["index"] * 6
    for _n, _i in enumerate((0.178, 0.311, 0.444, 0.578, 0.711, 0.844)):
        if _n + _index_offset >= _config_length: break
        _data = _info["data"][_info["channels"][_info["channel_index"]]][_n + _index_offset]
        _mapping = global_asset["mapping"]["percussion"] if _info["channels"][_info["channel_index"]] == 9 else global_asset["mapping"]

        _text = ""
        if _data[1] == -1:
            _text += _mapping["default"].upper() + "(D)"
        else:
            _text += _mapping.get(str(_data[1]), _mapping["undefined"]).upper() + "(" + str(_data[1]) + ")"

        if _overriding := _info["mapping"].get(_info["channels"][_info["channel_index"]]):
            if _data[1] in _overriding: _text += " ➡ " + str(_mapping[str(_overriding[_data[1]])]).upper()

        _config_list.extend(
            (
                (0.025, _i, 0.25, 0.089, (get_time_text(_data[0][0]) + " - " + get_time_text(_data[0][1]), 0.035, 255), -1),
                (0.3, _i, 0.675, 0.089, (_text, 0.035, _info["button_state"][_n + 4]), _n + 4)
            )
        )

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.075, 0.089, ("OK", 0.035, _info["button_state"][0]), 0),
            (0.125, 0.044, 0.475, 0.089, ("通道 " + str(_info["channels"][_info["channel_index"]] + 1), 0.035, _info["button_state"][1]), 1),
            (0.625, 0.044, 0.05, 0.089, ("◀", 0.035, _info["button_state"][2]), 2),
            (0.7, 0.044, 0.2, 0.089, (str(_info["index"] + 1) + "/" + str(_page_num) if _config_length else "无数据", 0.035, 255), -1),
            (0.925, 0.044, 0.05, 0.089, ("▶", 0.035, _info["button_state"][3]), 3)
        ) + tuple(_config_list),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                remove_page(overlay_page)
                _info["done"][0] = True
            case 1:
                _info["channel_index"] += 1
                if _info["channel_index"] >= len(_info["channels"]):
                    _info["channel_index"] = 0
                _info["index"] = 0
            case 2:
                _info["index"] -= 1
                if _info["index"] < 0:
                    _info["index"] = _page_num - 1
            case 3:
                _info["index"] += 1
                if _info["index"] >= _page_num:
                    _info["index"] = 0
            case _n if 4 <= _n <= 9:
                if _info["channels"][_info["channel_index"]] not in _info["mapping"]: _info["mapping"][_info["channels"][_info["channel_index"]]] = {}
                add_page(overlay_page, [packing_screen, {"done": _info["done"], "button_state": [0, 0, 0, 0, 0, 0, 0, 0], "index": 0, "percussion": _info["channels"][_info["channel_index"]] == 9, "mapping": _info["mapping"][_info["channels"][_info["channel_index"]]], "origin": _info["data"][_info["channels"][_info["channel_index"]]][_info["index"] * 6 + _id - 4][1]}])

    change_button_alpha(_info["button_state"], _id)

    return _root

def packing_screen(_info, _input):
    if ("mouse_right" in _input and not _input["mouse_right"]) or _info["done"][0]:
        remove_page(overlay_page)

    _config = tuple((global_asset["instruments"]["percussion"] if _info["percussion"] else global_asset["instruments"]["other"]).keys())
    _config_length = len(_config)
    _page_num = round_01(_config_length / 6)

    _config_list = []
    _index_offset = _info["index"] * 6
    for _n, _i in enumerate((0.178, 0.311, 0.444, 0.578, 0.711, 0.844)):
        if _n + _index_offset >= _config_length: break
        _config_list.append((0.025, _i, 0.95, 0.089, ("" if _n + _index_offset >= _config_length else _config[_n + _index_offset].upper(), 0.035, _info["button_state"][_n + 2]), _n + 2))

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.575, 0.089, ("打击乐器" if _info["percussion"] else "非打击乐器", 0.035, 255), -1),
            (0.625, 0.044, 0.05, 0.089, ("◀", 0.035, _info["button_state"][0]), 0),
            (0.7, 0.044, 0.2, 0.089, (str(_info["index"] + 1) + "/" + str(_page_num) if _config_length else "无数据", 0.035, 255), -1),
            (0.925, 0.044, 0.05, 0.089, ("▶", 0.035, _info["button_state"][1]), 1)
        ) + tuple(_config_list),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                _info["index"] -= 1
                if _info["index"] < 0:
                    _info["index"] = _page_num - 1
            case 1:
                _info["index"] += 1
                if _info["index"] >= _page_num:
                    _info["index"] = 0
            case _n if 2 <= _n <= 7:
                _index = _info["index"] * 6 + _id - 2
                _info["mapping"][_info["origin"]] = (global_asset["instruments"]["percussion"] if _info["percussion"] else global_asset["instruments"]["other"])[_config[_index]]
                remove_page(overlay_page)

    change_button_alpha(_info["button_state"], _id)

    return _root

def setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("输出格式 " + ["mcstructure", "mcfunction", "SAPI行为包"][global_info["convertor"]["output_format"]], 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("播放模式 " + (["命令链延迟", "计分板时钟", "时钟与编号"][global_info["convertor"]["command_type"]] if global_info["convertor"]["output_format"] != 2 else ("SAPI" if global_info["convertor"]["output_format"] == 2 else "不可用")), 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("平均音量 " + (str(global_info["convertor"]["volume"]) + "%" if global_info["convertor"]["volume"] else "保持原始音量"), 0.035, _info["button_state"][2]), 2),
            (0.025, 0.444, 0.95, 0.089, ("结构模板 " + (os.path.splitext(global_asset["structure"][global_info["convertor"]["structure"]])[0] if global_info["convertor"]["output_format"] == 0 and global_asset["structure"] else "不可用"), 0.035, _info["button_state"][3]), 3)
        ),
        pygame.mouse.get_pos()
    )

    change_button_alpha(_info["button_state"], _id)

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                global_info["convertor"]["output_format"] += 1
                if global_info["convertor"]["edition"] == 1:
                    global_info["convertor"]["output_format"] = 1
                elif global_info["convertor"]["output_format"] > (2 if global_info["convertor"]["version"] == 1 else 1):
                    global_info["convertor"]["output_format"] = 0

                if global_info["convertor"]["output_format"] == 1:
                    if global_info["convertor"]["command_type"] == 0:
                        global_info["convertor"]["command_type"] = 1
                elif global_info["convertor"]["output_format"] == 2:
                    global_info["convertor"]["command_type"] = 0
            case 1:
                if global_info["convertor"]["output_format"] != 2:
                    global_info["convertor"]["command_type"] += 1
                    if global_info["convertor"]["command_type"] >= 3:
                        if global_info["convertor"]["output_format"] == 0:
                            global_info["convertor"]["command_type"] = 0
                        else:
                            global_info["convertor"]["command_type"] = 1
            case 2:
                global_info["convertor"]["volume"] += 10
                if global_info["convertor"]["volume"] >= 110:
                    global_info["convertor"]["volume"] = 0
            case 3:
                if global_info["convertor"]["output_format"] == 0: global_info["convertor"]["structure"] += 1
                if global_info["convertor"]["structure"] >= len(global_asset["structure"]): global_info["convertor"]["structure"] = 0
        if global_info["convertor"]["command_type"] == 0: global_info["convertor"]["compression"] = False

    return _root

def other_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("播放速度 " + str(global_info["convertor"]["time_per_tick"]) + "ms/tick", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("声相偏移 " + ("启用" if global_info["convertor"]["panning"] else "关闭"), 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("静音跳过 " + ("启用" if global_info["convertor"]["skip"] else "关闭"), 0.035, _info["button_state"][2]), 2),
            (0.025, 0.444, 0.95, 0.089, ("打击乐器 " + ("保留" if global_info["convertor"]["percussion"] else "去除"), 0.035, _info["button_state"][3]), 3),
            (0.025, 0.578, 0.95, 0.089, ("乐器调整 " + ("启用" if global_info["convertor"]["adjustment"] else "关闭"), 0.035, _info["button_state"][4]), 4),
            (0.025, 0.711, 0.95, 0.089, ("歌词字幕设置", 0.035, _info["button_state"][5]), 5),
            (0.025, 0.844, 0.95, 0.089, ("指令压缩 " + ("不可用" if global_info["convertor"]["command_type"] == 0 or (global_info["convertor"]["edition"] == 1 and global_info["convertor"]["version"] == 0) else ("启用" if global_info["convertor"]["compression"] else "关闭")), 0.035, _info["button_state"][6]), 6)
        ),
        pygame.mouse.get_pos()
    )

    change_button_alpha(_info["button_state"], _id)

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0: set_time_per_tick()
            case 1: global_info["convertor"]["panning"] = not global_info["convertor"]["panning"]
            case 2: global_info["convertor"]["skip"] = not global_info["convertor"]["skip"]
            case 3: global_info["convertor"]["percussion"] = not global_info["convertor"]["percussion"]
            case 4: global_info["convertor"]["adjustment"] = not global_info["convertor"]["adjustment"]
            case 5: add_page(overlay_page, [lyrics_setting_screen, {"button_state": [0, 0, 0]}])
            case 6:
                if global_info["convertor"]["command_type"] != 0 and not (global_info["convertor"]["edition"] == 1 and global_info["convertor"]["version"] == 0):
                    global_info["convertor"]["compression"] = not global_info["convertor"]["compression"]

    return _root

def lyrics_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("歌词显示 " + ("启用" if global_info["convertor"]["lyrics"]["enable"] else "关闭"), 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("平滑进度 " + ("启用" if global_info["convertor"]["lyrics"]["smooth"] else "关闭"), 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("自动分割 " + ("启用" if global_info["convertor"]["lyrics"]["joining"] else "关闭"), 0.035, _info["button_state"][2]), 2)
        ),
        pygame.mouse.get_pos()
    )

    change_button_alpha(_info["button_state"], _id)

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                global_info["convertor"]["lyrics"]["enable"] = not global_info["convertor"]["lyrics"]["enable"]
            case 1:
                global_info["convertor"]["lyrics"]["smooth"] = not global_info["convertor"]["lyrics"]["smooth"]
            case 2:
                global_info["convertor"]["lyrics"]["joining"] = not global_info["convertor"]["lyrics"]["joining"]

    return _root

def game_edition_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("游戏版本 " + ["基岩版", "Java版"][global_info["convertor"]["edition"]], 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("指令语法 " + ["1.19.50/1.13以下", "1.19.50/1.13以上"][global_info["convertor"]["version"]], 0.035, _info["button_state"][1]), 1)
        ),
        pygame.mouse.get_pos()
    )

    change_button_alpha(_info["button_state"], _id)

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                if global_info["convertor"]["edition"] == 0:
                    global_info["convertor"]["edition"] = 1
                    global_info["convertor"]["output_format"] = 1
                    if global_info["convertor"]["command_type"] == 0:
                        global_info["convertor"]["command_type"] = 1
                else:
                    global_info["convertor"]["edition"] = 0
            case 1:
                if global_info["convertor"]["version"] == 0:
                    global_info["convertor"]["version"] = 1
                else:
                    global_info["convertor"]["version"] = 0
                    if global_info["convertor"]["output_format"] == 2:
                        global_info["convertor"]["output_format"] = 0

        if global_info["convertor"]["version"] == 0 and global_info["convertor"]["edition"] == 1:
            global_info["convertor"]["compression"] = False

    return _root

def keyboard_screen(_info: dict, _input: dict[str, bool]) -> pygame.Surface:
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)
        _info["callback"](_info["value"])

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.256, 0.8, 0.089, (str(_info["value"]) + _info["text"], 0.035, 255), -1),
            (0.85, 0.256, 0.05, 0.089, ("←", 0.035, _info["button_state"][10]), 10),
            (0.925, 0.256, 0.05, 0.089, ("C", 0.035, _info["button_state"][11]), 11),
            (0.025, 0.389, 0.219, 0.089, ("1", 0.035, _info["button_state"][1]), 1),
            (0.269, 0.389, 0.219, 0.089, ("2", 0.035, _info["button_state"][2]), 2),
            (0.513, 0.389, 0.219, 0.089, ("3", 0.035, _info["button_state"][3]), 3),
            (0.756, 0.389, 0.219, 0.089, ("+1", 0.035, _info["button_state"][12]), 12),
            (0.025, 0.522, 0.219, 0.089, ("4", 0.035, (_info["button_state"][4])), 4),
            (0.269, 0.522, 0.219, 0.089, ("5", 0.035, _info["button_state"][5]), 5),
            (0.513, 0.522, 0.219, 0.089, ("6", 0.035, _info["button_state"][6]), 6),
            (0.756, 0.522, 0.219, 0.089, ("0", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.656, 0.219, 0.089, ("7", 0.035, _info["button_state"][7]), 7),
            (0.269, 0.656, 0.219, 0.089, ("8", 0.035, _info["button_state"][8]), 8),
            (0.513, 0.656, 0.219, 0.089, ("9", 0.035, _info["button_state"][9]), 9),
            (0.756, 0.656, 0.219, 0.089, ("-1", 0.035, _info["button_state"][13]), 13)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case _n if 0 <= _n <= 9:
                _info["value"] *= 10
                _info["value"] += _id
            case 10:
                _info["value"] //= 10
            case 11:
                _info["value"] = 0
            case 12:
                _info["value"] += 1
            case 13:
                _info["value"] -= 1

    change_button_alpha(_info["button_state"], _id)

    return _root

def processing_screen(_info, _input):
    return ui_manager.get_blur_background()

global_info = {"exit": 0, "watch_dog": 0, "message": [], "message_info": [0, 0, False], "new_version": False, "update_list": [[], {}], "mcpack_update": ["", ""], "editor_update": {"version": 0}, "downloader": [{"state": "waiting", "downloaded": 0, "total": 0}], "setting": {"id": 1, "fps": 60, "log_level": 5, "version": 0, "edition": "", "animation_speed": 10, "max_selector_num": 0, "disable_update_check": False}, "profile": {}, "convertor": {"file": "", "edition": -1, "version": 1, "command_type": 0, "output_format": -1, "volume": 30, "structure": 0, "skip": True, "time_per_tick": -1, "adjustment": True, "percussion": True, "panning": False, "lyrics": {"enable": False, "smooth": True, "joining": False}, "compression": False}}
global_asset: dict[str, pygame.Surface | pygame.font.Font | list | dict] = {}
overlay_page = []

pygame.display.init()
pygame.display.set_caption("MIDI-MCSTRUCTURE NEXT  GUI")
pygame.display.set_icon(pygame.image.load("Asset/image/icon.png"))
window = pygame.display.set_mode((800, 450), pygame.RESIZABLE)

logger = log.Logger(5)
ui_manager = UIManager()

try:
    timer = pygame.time.Clock()

    threading.Thread(target=watchdog).start()
    threading.Thread(target=asset_load, daemon=True).start()

    while not global_info["exit"]:
        window.fill((0, 0, 0, 255))

        env_list = {}
        for evt in pygame.event.get():
            if evt.type == pygame.QUIT:
                global_info["exit"] = 1
            elif evt.type == pygame.MOUSEBUTTONDOWN:
                if evt.button == 1:
                    env_list["mouse_left"] = True
                if evt.button == 3:
                    env_list["mouse_right"] = True
            elif evt.type == pygame.MOUSEBUTTONUP:
                if evt.button == 1:
                    env_list["mouse_left"] = False
                if evt.button == 3:
                    env_list["mouse_right"] = False
            elif evt.type == pygame.DROPFILE:
                env_list["drop_file"] = evt.file
            elif evt.type == pygame.VIDEORESIZE:
                threading.Thread(target=change_size, args=[(evt.w, evt.h), True], daemon=True).start()
                window = pygame.display.set_mode((evt.w, evt.h), pygame.RESIZABLE)

        global_info["animation_speed"] = timer.get_fps()
        if 0 < global_info["setting"]["animation_speed"] < global_info["animation_speed"]:
            global_info["animation_speed"] = global_info["setting"]["animation_speed"] / global_info["animation_speed"]
        else:
            global_info["animation_speed"] = 1

        if overlay_page:
            render_page(window, overlay_page, env_list)

        global_info["watch_dog"] = 0

        pygame.display.flip()
        timer.tick(global_info["setting"]["fps"])
except KeyboardInterrupt:
    global_info["exit"] = 1
except:
    global_info["exit"] = 3
    logger.fatal(traceback.format_exc())
finally:
    if global_info["exit"] != 3: pygame.quit()

    if not os.path.exists("Asset/text"):
        os.makedirs("Asset/text")

    with open("Asset/text/setting.json", "w") as io:
        io.write(json.dumps(global_info["setting"], indent=2))

    if global_info["exit"] == 2:
        subprocess.Popen("Updater/updater.exe")

    if global_info["exit"] == 3:
        window.blit(global_asset["error"], (0, 0))
        pygame.display.flip()
    else:
        logger.done()
        os._exit(0)