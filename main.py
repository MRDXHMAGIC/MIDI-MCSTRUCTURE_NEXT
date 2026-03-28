import os
import sys
import log
import json
import time
import pickle
import shutil
import pygame
import tarfile
import hashlib
import requests
import evaltools
import threading
import traceback
import subprocess
import webbrowser
from math import ceil
from tools import round_int, round_45, uuid, is_number, get_time_text, get_color, limit
from writer import write_cmd
from tkinter import filedialog
from database import LyricsList, Note, Lyrics, Eval
from ui_manager import UIManager
from midi_reader import MIDIReader

class NetBuffer:
    __slots__ = (
        "pos",
        "size",
        "__data",
        "__done",
        "__exception"
    )

    def __init__(self):
        self.pos = 0
        self.size = 0
        self.__data = b""
        self.__done = False
        self.__exception = None

    def write(self, _data):
        if self.__exception is not None: raise self.__exception
        self.__data += _data

    def set_done(self):
        self.__done = True

    def set_exception(self, _exception):
        self.__exception = _exception

    def get_progress(self):
        return 0 if self.size == 0 else self.pos / self.size

    def read(self, _size: int = -1):
        while (_size == -1 or len(self.__data) < _size) and not self.__done: pass

        if self.__exception is not None:
            raise self.__exception
        elif _size == -1:
            _data, self.__data = self.__data, b""
            self.pos += len(_data)
        else:
            _data, self.__data = self.__data[:_size], self.__data[_size:]
            self.pos += _size

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

        if global_info["setting"]["version"] > 0:
            logger.info("MMS Version Code: " + str(global_info["setting"]["version"]))

        if not global_info["setting"]["disable_update_check"]:
            threading.Thread(target=get_version_list, daemon=True).start()
        else:
            logger.info("Update Check is Disable.")

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

        global_info["color"] = get_color(global_asset["menu"])

        _blur = False
        if os.path.exists("Cache/image/blur.png"):
            global_asset["blur"] = pygame.image.load("Cache/image/blur.png").convert_alpha()
        else:
            global_asset["blur"] = pygame.Surface(global_asset["menu"].get_size()).convert_alpha()
            _blur = True

        change_size((800, 450), False)

        if _blur:
            global_asset["blur"] = pygame.transform.gaussian_blur(global_asset["menu"], 3).convert_alpha()

            if not os.path.exists("Cache/image"): os.makedirs("Cache/image")
            pygame.image.save(global_asset["blur"], "Cache/image/blur.png")

            ui_manager.add_resource(_font_path="Asset/font/font.ttf", _corner_surf=pygame.image.load("Asset/image/corner_mask.png"), _blur_surf=global_asset["blur"], _background_surf=global_asset["menu"])

        logger.debug("Set Pygame Max Channels...")
        pygame.mixer.set_num_channels(global_info["setting"]["channels_num"])

        logger.debug("Loading Features Files...")
        with open("Asset/text/features.json", "rb") as _io:
            global_asset["features"] = json.loads(_io.read())

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

        if os.path.isdir("Updater"):
            logger.info("Removing Updater...")
            shutil.rmtree("Updater")

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

        for _i in sys.argv[1:]:
            if os.path.splitext(_i)[1] == ".mid" and os.path.exists(_i):
                global_info["convertor"]["file"] = _i
                break
        else:
            time.sleep(0.5)

        remove_page(overlay_page)

        if global_info["convertor"]["file"]:
            add_page(overlay_page, [menu_screen, {"button_state": [0, 0, 0, 0, 0]}], 1, False)
            add_page(overlay_page, [convertor_screen, {"button_state": [0, 0, 0, 0, 0]}], 1)
        else:
            while overlay_page: pass
            add_page(overlay_page, [menu_screen, {"button_state": [0, 0, 0, 0, 0]}], 0, False)

        global_info["message_info"][2] = True
    except:
        global_info["exit"] = 3
        logger.error(traceback.format_exc())

def change_size(_size: tuple[int], _exit: bool) -> tuple[list[int] | None, pygame.Surface]:
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
        add_page(overlay_page, [loading_screen, {"progress": None, "alpha": 0}], 1)
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
def repack_note(_note: Note, _id = None) -> Note:
    _data = _note.dump()
    return Note(_data["program"], _data["volume"], _data["pitch"], _data["panning"], _id)

def read_midi(_setting: dict, _profile: dict) -> dict:
    with open(_setting["file"], "rb") as _io:
        _path_hash = str(hashlib.file_digest(_io, "md5").hexdigest())

    _midi_reader = MIDIReader(_setting["file"])

    if not os.path.exists("Cache/mapping"): os.makedirs("Cache/mapping")

    try:
        with open("Cache/mapping/" + _path_hash + ".pkl", "rb") as _io:
            _mapping = pickle.load(_io)
        if _setting["ask_mapping"]: global_info["message"].append("请调整乐器音色映射方案（已加载缓存方案）")
    except:
        logger.debug(traceback.format_exc())
        _mapping = {}
        if _setting["ask_mapping"]: global_info["message"].append("请调整乐器音色映射方案")

    if _setting["ask_mapping"]:
        _instruments = _midi_reader.scan_instruments()

        _info = {"button_state": [0, 0, 0, 0, 0, 0, 0, 0, 0], "index": 0, "channel_index": 0,
                 "channels": sorted(_instruments.keys()), "data": _instruments, "mapping": _mapping, "done": [False]}
        add_page(overlay_page, [adj_mapping_screen, _info])

        while not _info["done"][0]:
            time.sleep(0.1)

        try:
            with open("Cache/mapping/" + _path_hash + ".pkl", "wb") as _io:
                pickle.dump(_mapping, _io, protocol=5)
        except:
            logger.debug(traceback.format_exc())

    _midi_reader.override_mapping(_mapping)

    if _setting["enable_accurate_tick"]:
        _setting["time_per_tick"] = min(
            ((_n, _midi_reader.get_time_accuracy(_n / 10)) for _n in
             range((_setting["time_per_tick"] - _setting["max_time_error"]) * 10,
                   1 + (_setting["time_per_tick"] + _setting["max_time_error"]) * 10)),
            key=lambda _i: _i[1]
        )[0] / 10
        logger.debug(f"The best speed is {_setting["time_per_tick"]} ms/tick")

    # 存放音符和歌词字幕合并后的最终结果
    _result: dict[int, set[Note | Lyrics]] = {}

    # 调整平均音量，音符数据取整，最终合并到结果中
    _lyrics_buffer: dict[int, str] = {}
    _average_volume = [0, 0]
    for _k, _i in get_notes(_midi_reader, _setting, _profile):
        if isinstance(_i, Note):
            # 如果启用控制平均音量功能，就记录音量信息
            if _setting["volume"]:
                _average_volume[0] += 1
                _average_volume[1] += _i.dump()["volume"]

            # 将音符数据合并到结果中
            if _k not in _result:
                _result[_k] = set()

            if _setting["remove_chord"]:
                _result[_k].add(_i)
            else:
                _note_id = 0
                while repack_note(_i, _note_id) in _result[_k]:
                    _note_id += 1
                else:
                    _result[_k].add(repack_note(_i, _note_id))

        elif isinstance(_i, str):
            if _k not in _lyrics_buffer:
                _lyrics_buffer[_k] = ""
            _lyrics_buffer[_k] += _i

        else:
            raise TypeError("Unknown Data Type: " + str(type(_i)))

    if _average_volume[0] and _average_volume[1]:
        Note.master_volume = (_setting["volume"] / 100) / (_average_volume[1] / _average_volume[0])
    else:
        Note.master_volume = 1

    # 歌词数据处理
    if _setting["lyrics"]["enable"]:
        if os.path.exists(os.path.splitext(_setting["file"])[0] + ".lrc"):
            logger.info("Find LRC File: " + os.path.splitext(_setting["file"])[0] + ".lrc")

            for _charset in ("utf-8", "ANSI"):
                try:
                    with open(os.path.splitext(_setting["file"])[0] + ".lrc", "r", encoding=_charset) as _io:
                        _lyrics_buffer.clear()
                        for _k, _i in load_lrc(_io.readlines(), _setting["time_per_tick"]):
                            _lyrics_buffer[_k] = _i
                    break
                except:
                    pass
            else:
                raise IOError("Cannot read .lrc file!")
        # 渲染歌词字幕
        if _lyrics_buffer:
            _last_l = None
            for _k, _l in LyricsList(_lyrics_buffer, _setting["lyrics"]["smooth"], _setting["lyrics"]["joining"]):
                # 判断与上个歌词显示内容是否不同
                if _last_l == _l and _setting["compression"] == -1:
                    continue
                # 将歌词数据合并到结果中
                if _k not in _result:
                    _result[_k] = set()

                _result[_k].add(_l)
                _last_l = _l

    return _result

def get_profile(_setting: dict) -> dict:
    _profile = None

    if _setting["output_format"] == 3:
        _profile = global_asset["profile"]["midi_preview"]
    elif global_info["convertor"]["edition"] == 0:
        if global_info["convertor"]["version"] == 0:
            _profile = global_asset["profile"]["old_bedrock"]
        elif global_info["convertor"]["version"] == 1:
            _profile = global_asset["profile"]["new_bedrock"]
    elif global_info["convertor"]["edition"] == 1:
        if global_info["convertor"]["version"] == 0:
            _profile = global_asset["profile"]["old_java"]
        elif global_info["convertor"]["version"] == 1:
            _profile = global_asset["profile"]["new_java"]

    return _profile

def convertor(_setting: dict, _task_id = None):
    try:
        if _task_id is None: _task_id = 0

        _setting["remove_chord"] = global_info["setting"]["remove_chord"]
        _setting["interpolation"] = global_info["setting"]["interpolation"]

        # 根据设置的游戏版本选择合适的配置文件
        _profile = get_profile(_setting)

        # 读取MIDI音乐
        _result = read_midi(_setting, _profile)

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
            _crc, _buffer = write_cmd(
                {
                    "structure": "Asset/mcstructure/" + global_asset["structure"][_setting["structure"]],
                    "cmd_list": ((_cmd[0], _cmd[1].replace("{ADDRESS}", str(_task_id))) for _cmd in cmd_convertor(_setting, _profile, _time_offset, _result)),
                    "map": (
                        ("__ADDRESS__", str(_task_id)),
                        ("__TOTAL__", str(max(_result.keys()))),
                        ("__NAME__", _music_name)
                    )
                }
            )

            if _save_path := filedialog.asksaveasfilename(title="MIDI-MCSTRUCTURE NEXT",
                                                          initialfile=_music_name + "-" + _crc,
                                                          filetypes=[("Structure Files", ".mcstructure")],
                                                          defaultextension=".mcstructure"):

                with open(_save_path, "wb") as _io:
                    _io.write(_buffer)

        elif _setting["output_format"] == 1:
            if _setting["command_type"] == 0: raise ValueError("Unsupported Command Type!")

            with open("Cache/convertor/function.mcfunction", "w", encoding="utf-8") as _io:
                for _, _cmd in cmd_convertor(_setting, _profile, _time_offset, _result):
                    _io.write(f"{_cmd.replace("{ADDRESS}", str(_task_id))}\n")

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
                if _setting["new_java_pack"]:
                    os.makedirs("Cache/output/data/mms/function")

                    shutil.copyfile(
                        "Cache/convertor/function.mcfunction",
                        f"Cache/output/data/mms/function/player_{time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())}.mcfunction"
                    )

                else:
                    os.makedirs("Cache/output/data/mms/functions")

                    shutil.copyfile(
                        "Cache/convertor/function.mcfunction",
                        f"Cache/output/data/mms/functions/midi_player_{time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())}.mcfunction"
                    )

                _behavior_file = {
                    "pack": {
                        "description": {"text": "Generated by MIDI-MCSTRUCTURE", "color": "light_purple"},
                        "pack_format": 9999,
                        "supported_formats": [0, 9999],
                        "min_format": 0,
                        "max_format": 9999
                    }
                }

                with open("Cache/output/pack.mcmeta", "w", encoding="utf-8") as _io:
                    _io.write(json.dumps(_behavior_file))

                shutil.copyfile(
                    "Asset/image/icon.png",
                    "Cache/output/pack.png"
                )

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
                for _n, _note in enumerate(_i.dump(False) for _i in _result[_k]):
                    if _n == 0:
                        _delay = _k - _last
                    else:
                        _delay = 0

                    match _note:
                        case {"type": "note", "program": _sound, "pitch": _pitch, "volume": _volume, "panning": (_x, _y)}:
                            _buffer.append(json.dumps([_delay, "n", _sound, _pitch, _volume, _x, _y]))
                        case {"type": "lyrics", "last": _last, "real_f": _rf, "real_s": _rs, "next": _next}:
                            _buffer.append(json.dumps([_delay, "l", _last, _rf, _rs, _next]))
                        case _:
                            raise TypeError("Unknown Data Type: " + _note["type"])
                _last = _k

            shutil.unpack_archive("Cache/mcpack/" + os.listdir("Cache/mcpack")[0], "Cache/convertor")

            with open("Cache/convertor/scripts/main.js", "r", encoding="utf-8") as _io:
                _code = _io.read()

            with open("Cache/convertor/scripts/main.js", "w", encoding="utf-8") as _io:
                _io.write(_code.replace("{SOUND_NAME}", _music_name, 1).replace("{SOUND_DATA}", f"[\n  {",\n  ".join(_buffer)}\n]", 1))

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
        elif _setting["output_format"] == 3:
            _available_pitch = set()
            for _n in os.listdir("Cache/sounds"):
                if os.path.isdir("Cache/sounds/" + _n):
                    _available_pitch.update(float(os.path.splitext(_i)[0]) for _i in os.listdir("Cache/sounds/" + _n))

            _sound_list = {}
            for _k in sorted(_result.keys()):
                for _note in map(lambda _i: _i.dump(False), filter(lambda _i: isinstance(_i, Note), _result[_k])):
                    _pitch = min(((abs(_n - _note["pitch"]), _n) for _n in _available_pitch), key=lambda _i: _i[0])[1]

                    if _note["program"] not in _sound_list:
                        _sound_list[_note["program"]] = {}

                    if _note["pitch"] not in _sound_list[_note["program"]]:
                        if os.path.exists(f"Cache/sounds/{_note["program"]}/{_pitch}.ogg"):
                            _sound_list[_note["program"]][_note["pitch"]] = pygame.mixer.Sound(f"Cache/sounds/{_note["program"]}/{_pitch}.ogg")
                        else:
                            logger.debug(f"Sound {_note["program"]}: {_pitch}.ogg is not Exist!")

            _setting["player_info"]["armed"] = True
            _setting["player_info"]["length"] = max(_result.keys())

            _clock = pygame.Clock()
            while _setting["player_info"]["armed"]:
                if not 0 <= _setting["player_info"]["position"] <= _setting["player_info"]["length"]:
                    _setting["player_info"]["play"] = False
                    _setting["player_info"]["position"] = 0

                if _setting["player_info"]["play"]:
                    if _notes := _result.get(_setting["player_info"]["position"], None):
                        for _note in map(lambda _i: _i.dump(False), _notes):
                            match _note:
                                case {"type": "note", "program": _program, "pitch": _pitch, "volume": _volume, "panning": _}:
                                    if _sound := _sound_list[_program].get(_pitch, None):
                                        _sound.set_volume(_volume)
                                        _sound.play()
                                    else:
                                        logger.debug("Cannot Found Sound: " + str(_program))
                                case {"type": "lyrics", "last": _last, "real_f": _rf, "real_s": _rs, "next": _next}:
                                    _setting["player_info"]["lyrics"] = (_rf, _rs)
                                case _:
                                    raise TypeError("Unknown Data Type: " + _note["type"])
                    _setting["player_info"]["position"] += 1
                _clock.tick(20)
    except:
        global_info["message"].append("转换失败，请将log.txt发送给开发者以修复问题！")
        logger.error(traceback.format_exc())
    finally:
        evaltools.clear_cache()

def get_notes(_midi_file: MIDIReader, _setting: dict, _profile: dict) -> tuple[int, Note | str]:
    if not _setting["extension"]:
        for _i in _profile["sound_extension"]:
            if abs(_i[2] - 1) < 0.00001:
                _sound_limit = _i
                break
        else:
            raise ValueError("Cannot Found a Suitable Limit!")

    for _time, _data in _midi_file:
        if _data.type == "lyrics":
            # 返回文本数据
            yield round_int(_time / _setting["time_per_tick"]), _data.value

        elif _data.type == "note":
            # 去除打击乐器
            if _data.percussion and not _setting["percussion"]: continue

            # 获取游戏中的乐器名称
            _linear_note = False
            if _data.percussion:
                _program = _profile["sound_list"].get(global_asset["mapping"]["percussion"].get(str(_data.program), global_asset["mapping"]["percussion"]["undefined"]), _profile["sound_list"][global_asset["mapping"]["percussion"]["undefined"]])

                if "linear_note" in global_asset["features"]["percussion"].get(str(_data.source_program), global_asset["features"]["percussion"]["undefined"]): _linear_note = True
            else:
                if _data.program == -1:
                    _program = _profile["sound_list"][global_asset["mapping"]["default"]]
                else:
                    _program = _profile["sound_list"].get(global_asset["mapping"].get(str(_data.program), global_asset["mapping"]["undefined"]), _profile["sound_list"][global_asset["mapping"]["undefined"]])

                if "linear_note" in global_asset["features"].get(str(_data.source_program), global_asset["features"]["undefined"]): _linear_note = True

            if _program is None: continue

            _delay_time = 0
            while _data.time + _delay_time < _time:
                # 一个音符可以对应多个我的世界乐器，因此这里遍历一下从配置文件中获取的数据
                for _note in _program:
                    # 累加配置文件中我的世界乐器之间的时间间隔
                    _delay_time += _note[3]

                    _pitch_index = _data.pitch
                    _note_velocity = _data.velocity

                    # 进行插值处理
                    if _linear_note and _setting["hold"]:
                        match _setting["interpolation"]:
                            case 1: _note_velocity *= limit(0, 1 - _delay_time / (_time - _data.time), 1)
                            case 2: _note_velocity *= limit(0, (_delay_time / (_time - _data.time) - 1) ** 2, 1)

                    # 如果启用调整音符功能，则会根据配置文件对音量和音调进行调整
                    if _setting["adjustment"]:
                        _pitch_index += _note[2]
                        _note_velocity *= _note[1]

                    _pitch = get_pitch(_pitch_index)

                    if _setting["extension"]:
                        for _i in _profile["sound_extension"]:
                            if _i[0][0] <= _pitch <= _i[0][1]:
                                _sound = _i[1].replace("{SOUND}", _note[0])
                                _pitch *= _i[2]
                                break
                        else:
                            logger.warn("Can Not Found a Suitable Extension, Pitch=" + str(_pitch))
                            continue
                    elif _sound_limit[0][0] <= _pitch <= _sound_limit[0][1]:
                        _sound = _sound_limit[1].replace("{SOUND}", _note[0])
                    else:
                        break
                    # 返回音符数据
                    yield round_int((_data.time + _delay_time) / _setting["time_per_tick"]), Note(_sound, (_note_velocity, round_45(_note_velocity, 1), 1)[_setting["level"] if _setting["compression"] != -1 else 0], _pitch, _data.panning)

                    if not _setting["adjustment"]: break

                if not (_setting["hold"] and _linear_note): break

                _delay_time += _setting["time_per_tick"]
        else:
            raise TypeError("Unknown Data Type: " + str(_data.type))

def get_pitch(_index: int) -> float:
    return 2 ** ((_index - 66) / 12)

def cmd_convertor(_setting: dict, _profile: dict, _start_time: int, _result: dict[int, set[Note | Lyrics]]) -> tuple[int, str]:
    if _setting["command_type"] == 0:
        _raw_cmd: str = _profile["command"]["delay"][0]
    elif _setting["command_type"] == 1:
        _raw_cmd: str = _profile["command"]["clock"][0]
    elif _setting["command_type"] == 2:
        _raw_cmd: str = _profile["command"]["address"][0]
    else:
        raise ValueError("Unknown Command Type: " + str(_setting["command_type"]))

    _raw_cmd = _raw_cmd[1:] if _raw_cmd.startswith("/") and _setting["output_format"] == 1 else _raw_cmd

    _single_selector = Eval(_profile["selector"]["single"])
    _multiple_selector = Eval(_profile["selector"].get("multiple", _profile["selector"]["single"]))

    if _setting["panning"]:
        _raw_cmd = _raw_cmd.replace("{POSITION}", "{PANNING}")
    else:
        _raw_cmd = _raw_cmd.replace("{POSITION}", "~ ~ ~")

    if _setting["command_type"] == 0:
        _last_time = _start_time
        for _k in sorted(_result.keys()):
            for _n, _i in enumerate(_result[_k]):
                if isinstance(_i, Note):
                    _cmd = _i.format(_raw_cmd)
                elif isinstance(_i, Lyrics):
                    _cmd = _i.format(_profile["command"]["lyrics"][0])
                else:
                    raise TypeError("Unknown Data Type: " + str(type(_i)))

                yield _k - _last_time, _cmd.replace("{TIME}", str(_k - _start_time))

                _last_time = _k
    else:
        _data_buffer: dict[Note | Lyrics, set[int]] = {}
        for _k in sorted(_result.keys()):
            for _i in _result[_k]:
                if _i not in _data_buffer:
                    _data_buffer[_i] = set()

                _data_buffer[_i].add(_k - _start_time)

        for _k in _data_buffer:
            _time_nodes = tuple(_data_buffer[_k])

            while _time_nodes:
                _full_length = 1 if _setting["compression"] == -1 else len(_time_nodes)
                _length_areas = (1, _full_length)

                while True:
                    for _n, _length in enumerate((_length_areas[0], (_length_areas[0] + _length_areas[1]) // 2, _length_areas[1])):
                        if _length == 1:
                            _selector = _single_selector.eval({}, {"time": _time_nodes[0], "tools": evaltools, "enable_address": _setting["command_type"] == 2}).replace("{VALUE}", str(_time_nodes[0]))
                        else:
                            _selector = _multiple_selector.eval({}, {"nodes": _time_nodes[:_length], "tools": evaltools, "enable_address": _setting["command_type"] == 2})

                        if isinstance(_k, Note):
                            _cmd = _k.format(_raw_cmd.replace("{SELECTOR}", _selector))
                        elif isinstance(_k, Lyrics):
                            _cmd = _k.format(_profile["command"]["lyrics"][_setting["command_type"]].replace("{SELECTOR}", _selector))
                        else:
                            raise TypeError("Unknown Data Type: " + str(type(_k)))

                        if len(_cmd) > _setting["compression"]:
                            if _n == 0:
                                _length_areas = (_length_areas[0], _length_areas[0])
                            elif _n == 1:
                                _length_areas = (_length_areas[0], _length - 1)
                            elif _n == 2:
                                _length_areas = ((_length_areas[0] + _length - 1) // 2, _length - 1)
                            break
                        elif _n == 2:
                            _length_areas = (_length, _length)
                            break

                    if _length_areas[0] == _length_areas[1]: break

                _time_nodes = _time_nodes[_length:]

                yield 0, _cmd

    if _setting["command_type"] == 0:
        _raw_cmd = _profile["command"]["delay"][1:]
    elif _setting["command_type"] == 1:
        _raw_cmd = _profile["command"]["clock"][1:]
    elif _setting["command_type"] == 2:
        _raw_cmd = _profile["command"]["address"][1:]
    else:
        _raw_cmd = []

    for _i in _raw_cmd:
        _cmd = _i.replace("{TIME}", str(max(_result.keys()) - _start_time))
        yield 0, _cmd[1:] if _cmd.startswith("/") and _setting["output_format"] == 1 else _cmd

def load_lrc(_lines: list[str], _time_per_tick: int = 50) -> dict[int, str]:
    _offset = 0
    for _line in filter(lambda _i: bool(_i), map(lambda _i: _i.strip(), _lines)):
        _tags = []
        _start = None
        _argument = ""
        for _i in range(len(_line)):
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
                _time = round_int(((float(_tag_type) * 60 + float(_value)) * 1000 - _offset) / _time_per_tick)
                yield _time, _argument

            elif _tag_type == "offset":
                _offset = int(_value)

# 页面渲染函数
def render_page(_root: pygame.Surface, _overlay: list, _event: dict):
    _pages = []
    _pages_num = len(_overlay)
    for _n in range(_pages_num - 1, -1, -1):
        try:
            _window = _overlay[_n][0](_overlay[_n][1], _event if _n + 1 == _pages_num and _overlay[_n][2] == 1 else {})
            _window.set_alpha(round_int(_overlay[_n][2] * 255))
            _pages.append(_window)

            if _overlay[_n][3]:
                _overlay[_n][2] += (1.1 - _overlay[_n][2]) * global_info["animation_speed"]
                if _overlay[_n][2] >= 1: _overlay[_n][2] = 1
            else:
                _overlay[_n][2] += (-0.1 - _overlay[_n][2]) * global_info["animation_speed"]
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as _exception:
            if sum(1 for _i in _overlay if _i[3]) > 1:
                global_info["message"].append("MMS-UI错误，请将log.txt发送给开发者以修复问题！")
                logger.error(traceback.format_exc())
                del _overlay[_n:]
                return
            else:
                raise _exception

        if _overlay[_n][2] == 1: break
        elif _overlay[_n][2] <= 0: del _overlay[_n]

    _root.blits((_page, (0, 0)) for _page in reversed(_pages))

    if global_info["message"] and global_info["message_info"][2]:
        _h = global_info["message_info"][0] * 0.089

        if ui_manager.get_abs_position((0, _h))[1] <= 3 and global_info["message_info"][1] > 3000:
            global_info["message_info"] = [0, 0, True]
            del global_info["message"][0]

        try:
            _message_surf = pygame.transform.box_blur(_root.subsurface((ui_manager.get_abs_position((0, 1 - _h), True) + ui_manager.get_abs_position((1, _h)))), 2)
            _text_surface = global_asset["font"].render(global_info["message"][0], True, global_info["color"])
            _text_surface.set_alpha(255 * global_info["message_info"][0])

            _text_position = ui_manager.get_abs_position((0.5, 1.044 - _h), True)
            _message_surf.blits(((global_asset["message_mask"], (0, 0)), (_text_surface, ((_message_surf.size[0] - _text_surface.get_size()[0]) / 2, (ui_manager.get_abs_position((0, 0.089))[1] - global_asset["font"].get_height()) / 2))))

            _root.blit(_message_surf, ui_manager.get_abs_position((0, 1 - _h), True))
        except:
            pass

        if global_info["message_info"][1] <= 3000:
            global_info["message_info"][0] += (1 - global_info["message_info"][0]) * global_info["animation_speed"]
        else:
            global_info["message_info"][0] -= global_info["message_info"][0] * global_info["animation_speed"]

        global_info["message_info"][1] += timer.get_time()

# 功能函数
def watchdog():
    try:
        while True:
            if global_info["watch_dog"] >= 100:
                logger.fatal("Run Timed Out of 3000ms Exceeded!\nProcess is Killed by Watchdog!")
                logger.done()
                break
            global_info["watch_dog"] += 1
            time.sleep(0.1)
    finally:
        os._exit(1)

def change_button_alpha(_state: list[float], _index: int) -> None:
    if pygame.mouse.get_pressed(3)[0]: _index = -1
    for _n in range(len(_state)):
        if _n == _index:
            _state[_n] += (255 - _state[_n]) * global_info["animation_speed"]
        else:
            _state[_n] += (127 - _state[_n]) * global_info["animation_speed"]

def produce_background(_path: str = "") -> None:
    try:
        if _path:
            global_asset["menu"] = pygame.transform.smoothscale(pygame.image.load(_path), (800, 450)).convert_alpha()

            global_info["color"] = get_color(global_asset["menu"])

            global_asset["blur"] = pygame.transform.gaussian_blur(global_asset["menu"], 3)

            pygame.image.save(global_asset["menu"], "Asset/image/custom_menu_background.png")

            if not os.path.exists("Cache/image"): os.makedirs("Cache/image")
            pygame.image.save(global_asset["blur"], "Cache/image/blur.png")

            ui_manager.add_resource(_font_path="Asset/font/font.ttf", _corner_surf=pygame.image.load("Asset/image/corner_mask.png"), _blur_surf=global_asset["blur"], _background_surf=global_asset["menu"])
            global_info["message"].append("已成功设置背景！")
        else:
            threading.Thread(target=open_filedialog, args=(produce_background, (("Image Files", ".png"), ("Image Files", ".jpg"), ("Image Files", ".jpeg")))).start()
    except:
        global_info["message"].append("无法加载图片文件！")
        raise

def set_volume(_num: None | int = None):
    if _num is None:
        global_info["message"].append("请输入平均音量！")
        add_page(overlay_page, [keyboard_screen, {"value": global_info["convertor"]["volume"], "text": "%", "callback": set_volume, "button_state": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}])
    else:
        if 0 < _num <= 100:
            global_info["convertor"]["volume"] = _num
        else:
            global_info["message"].append("平均音量需要在0%到100%之间！")

def set_selector_num(_num: None | int = None) -> None:
    if _num is None:
        global_info["message"].append("请输入最大指令长度！")
        add_page(overlay_page, [keyboard_screen, {"value": global_info["setting"]["max_cmd_length"], "text": "字", "callback": set_selector_num, "button_state": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}])
    else:
        global_info["setting"]["max_cmd_length"] = _num

def show_download(_title: str, _url: str, _target_path, _callback=lambda: remove_page(overlay_page)):
    _state = {"state": 0, "buffer": NetBuffer()}
    threading.Thread(target=download, args=(_url, _state, _target_path, _callback), daemon=True).start()
    add_page(overlay_page, [download_screen, {"state": _state, "title": _title}])

def reboot(_code: int = 2):
    if _code == 2: shutil.unpack_archive("Asset/updater/package.tar.zst", "Updater")
    global_info["exit"] = _code

def install_editor():
    try:
        remove_page(overlay_page)
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
        except Exception as _exc:
            _remove = False
            remove_page(overlay_page)

            logger.error(traceback.format_exc())

            if global_info["editor_update"]["version"] > 0:
                _text = ["你需要MMS配置文件编辑器 V", str(global_info["editor_update"]["version"]), "，是否安装？\n软件包大小为", "--", "MB"]
                threading.Thread(target=get_resource_size, args=(global_info["editor_update"]["download_url"], _text), daemon=True).start()
                add_page(overlay_page, [asking_screen, {"button_state": [0, 0], "button_text": ["下载并安装", "取消"], "argument": ("ProfileEditor V" + str(global_info["editor_update"]["version"]), global_info["editor_update"]["download_url"], "Editor", install_editor), "callback": show_download, "content": _text}], 0, True)
            else:
                global_info["message"].append("无法加载编辑器版本信息，请稍后重试！")

            raise _exc

        if load_profile():
            global_info["message"].append("已重新加载配置文件！")
        else:
            global_info["message"].append("无法加载配置文件，已加载备配置文件！")
    except:
        logger.error(traceback.format_exc())
    finally:
        if _remove: remove_page(overlay_page)

def open_filedialog(_callback, _type: tuple[tuple[str]], *_args):
    try:
        if _path := filedialog.askopenfilename(title="MIDI-MCSTRUCTURE NEXT", filetypes=_type):
            _callback(_path, *_args)
    except:
        logger.error(traceback.format_exc())

def midi_file_callback(_path: str):
    global_info["convertor"]["file"] = _path
    if os.path.exists(os.path.splitext(_path)[0] + ".lrc"):
        global_info["message"].append("检测到同名的.lrc文件，启用歌词显示即可加载歌词！")
    else:
        global_info["message"].append("未检测到同名的.lrc文件，若启用歌词显示将尝试从MIDI中获取")

def player_callback(_path: str, _ask: bool, _info):
    if _ask:
        _info["position"] = 0
        _info["length"] = 0
        _info["lyrics"] = ("", "")

    _info["armed"] = False
    _info["file"] = _path

    try:
        convertor(
            {
                "file": _path,
                "edition": 0,
                "version": 1,
                "command_type": 0,
                "output_format": 3,
                "volume": global_info["convertor"]["volume"],
                "structure": 0,
                "skip": False,
                "time_per_tick": global_info["convertor"]["time_per_tick"],
                "max_time_error": global_info["convertor"]["max_time_error"],
                "enable_accurate_tick": global_info["convertor"]["enable_accurate_tick"],
                "adjustment": global_info["convertor"]["adjustment"],
                "percussion": global_info["convertor"]["percussion"],
                "panning": False,
                "lyrics": {
                    "enable": global_info["convertor"]["lyrics"]["enable"],
                    "smooth": global_info["convertor"]["lyrics"]["smooth"],
                    "joining": global_info["convertor"]["lyrics"]["joining"]
                },
                "compression": -1,
                "extension": False,
                "hold": global_info["convertor"]["hold"],
                "ask_mapping": _ask and global_info["setting"]["ask_mapping"],
                "player_info": _info
             },
            None
        )
    except:
        _info["armed"] = True

def enter_to_player(_remove: bool = True):
    if _remove: remove_page(overlay_page)
    if (os.path.exists("Cache/sounds") and any(_path.endswith(".ver") for _path in os.listdir("Cache/sounds"))) and (global_info["sounds_update"]["version"] == -1 or os.path.exists("Cache/sounds/" + str(global_info["sounds_update"]["version"]) + ".ver")):
        if global_info["convertor"]["time_per_tick"] == -1:
            global_info["convertor"]["time_per_tick"] = 50
        add_page(overlay_page, [player_screen, {"button_state": [0, 0, 0, 0, 0], "file": "", "play": False, "armed": True, "length": 0, "position": 0, "lyrics": ("", "")}])
    elif global_info["sounds_update"]["version"] == -1:
        global_info["message"].append("MMS音乐预览需要下载音效包，但目前无网络连接")
        logger.info("No Internet Connection.")
    else:
        _text = ["你需要Minecraft音效包 V", str(global_info["sounds_update"]["version"]), "，是否下载？\n音效包大小为", "--", "MB"]
        threading.Thread(target=get_resource_size, args=(global_info["editor_update"]["download_url"], _text), daemon=True).start()
        add_page(overlay_page, [asking_screen, {"button_state": [0, 0], "button_text": ["下载", "取消"], "argument": ("SoundCollection V" + str(global_info["sounds_update"]["version"]), global_info["sounds_update"]["download_url"], "Cache/sounds", enter_to_player), "callback": show_download, "content": _text}], 0, True)

def set_time_per_tick(_time: None | int = None) -> None:
    if _time is None:
        global_info["message"].append("请输入每游戏刻的时间！")
        add_page(overlay_page, [keyboard_screen, {"value": global_info["convertor"]["time_per_tick"], "text": "ms/tick", "callback": set_time_per_tick, "button_state": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}])
    else:
        if _time >= 1:
            global_info["convertor"]["time_per_tick"] = _time
            if _time < global_info["convertor"]["max_time_error"]:
                global_info["convertor"]["max_time_error"] = _time
        else:
            _time = 1
            global_info["message"].append("每游戏刻的时间至少要大于0！")

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
        _argument["level"] = global_info["setting"]["compression_level"]
        _argument["ask_mapping"] = global_info["setting"]["ask_mapping"]
        _argument["compression"] = global_info["setting"]["max_cmd_length"] if global_info["convertor"]["compression"] else -1
        threading.Thread(target=run_task, args=(_argument, _id), daemon=True).start()

def run_task(_args, _id):
    add_page(overlay_page, [processing_screen, {}])
    try:
        convertor(_args, _id)
    finally:
        remove_page(overlay_page)

def exit_mapping_screen(_info) -> None:
    _info[0] = 1

def get_resource_size(_url: str, _info: dict) -> None:
    try:
        with requests.head(_url, allow_redirects=True) as _response:
            _response.raise_for_status()
            _info[3] = str(round_45(int(_response.headers["content-length"]) / 1048576, 2))
    except:
        logger.error(traceback.format_exc())

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
                    if _i.get("mms_version", 0) == 2 and _i["version"] > global_info["editor_update"]["version"]:
                        global_info["editor_update"] = _i
                case 5:
                    global_info["mcpack_update"][0] = _i["hash"]
                    global_info["mcpack_update"][1] = _i["download_url"]
                case 6:
                    global_info["sounds_update"] = _i
                case 7:
                    global_info["links"][_i["type"]] = _i["url"]
                case _:
                    logger.debug("Unknown API Version: " + str(_i["API"]))

        if global_info["mcpack_update"][0]: update_mcpack()

        _update_list.sort(key=lambda _i: _i["version"], reverse=True)

        for _i in _update_list:
            if _i["edition"] not in global_info["update_list"][0]:
                global_info["update_list"][0].append(_i["edition"])
                global_info["update_list"][1][_i["edition"]] = []
            global_info["update_list"][1][_i["edition"]].append(_i)

        if _update_list[0]["version"] > global_info["setting"]["version"]:
            global_info["new_version"] = "V" + str(_update_list[0]["version"]) + "-" + str(_update_list[0]["edition"])
    except:
        logger.error(traceback.format_exc())

def download(_url, _state, _target_path, _callback):
    try:
        _state["state"] = 0

        threading.Thread(target=downloader, args=(_url, _state["buffer"]), daemon=True).start()

        with tarfile.open(fileobj=_state["buffer"], mode="r|zst") as _io:
            _io.extractall(_target_path)

        _callback()
        _state["state"] = 1
    except Exception as _exception:
        logger.error(traceback.format_exc())

        _state["buffer"].set_exception(_exception)
        _state["state"] = -1

        time.sleep(3)

        remove_page(overlay_page)

def downloader(_url, _buffer: NetBuffer):
    try:
        _response = requests.get(_url, stream=True)

        _response.raise_for_status()

        _buffer.size = int(_response.headers.get("content-length", 0))

        with _response as _net:
            for _block in _net.iter_content(5120):
                _buffer.write(_block)

    except Exception as _exception:
        logger.error(traceback.format_exc())
        _buffer.set_exception(_exception)
    finally:
        _buffer.set_done()

def unpack(_path: str, _ask: bool = False):
    try:
        if _ask:
            global_info["message"].append("正在解压软件包...")
            shutil.unpack_archive("Asset/updater/package.tar.zst", "Updater")
            shutil.unpack_archive(_path, "Update")
            global_info["exit"] = 2
        else:
            add_page(overlay_page, [asking_screen, {"button_state": [0, 0], "button_text": ["安装", "取消"], "argument": (_path, True), "callback": unpack, "content": "是否将以下文件作为软件安装包安装？\n" + os.path.basename(_path)}], 0, True)
    except:
        logger.error(traceback.format_exc())
        global_info["message"].append("无法解压软件包！")

def update_mcpack():
    try:
        if os.path.exists("Cache/mcpack/" + global_info["mcpack_update"][0] + ".tar.zst"):
            logger.info("Behavior Package is the Lasest Version!")
        else:
            logger.info("Try to update Behavior Package")
            if os.path.exists("Cache/mcpack"): shutil.rmtree("Cache/mcpack")
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
    if "mouse_right" in _input and not _input["mouse_right"]:
        add_page(overlay_page, [asking_screen, {"button_state": [0, 0], "button_text": ["退出", "取消"], "argument": [1], "callback": reboot, "content": "退出软件？"}], 0, True)

    if "drop_file" in _input:
        match os.path.splitext(_input["drop_file"])[1]:
            case ".mid":
                add_page(overlay_page, [convertor_screen, {"button_state": [0, 0, 0, 0, 0]}])
                global_info["convertor"]["file"] = _input["drop_file"]
            case ".mspf":
                threading.Thread(target=enter_to_editor, args=[_input["drop_file"]], daemon=True).start()
            case _i if _i.lower() in (".jpeg", ".jpg", ".png"):
                threading.Thread(target=produce_background, args=[_input["drop_file"]], daemon=True).start()
            case _i if _i.lower() in (".zst", ".xz", ".gz", ".zip"):
                threading.Thread(target=unpack, args=[_input["drop_file"]], daemon=True).start()
            case _:
                global_info["message"].append("不支持的文件 " + os.path.basename(_input["drop_file"]))

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("转换文件", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("试听音乐", 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("软件设置", 0.035, _info["button_state"][2]), 2),
            (0.025, 0.444, 0.95, 0.089, ("发现新版本 " + global_info["new_version"] if global_info["new_version"] else "查看更新", 0.035, _info["button_state"][3]), 3),
            (0.025, 0.578, 0.95, 0.089, ("关于MIDI-MCSTRUCTURE NEXT", 0.035, _info["button_state"][4]), 4)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                add_page(overlay_page, [convertor_screen, {"button_state": [0, 0, 0, 0, 0]}])
            case 1:
                enter_to_player(False)
            case 2:
                add_page(overlay_page, [software_setting_screen, {"button_state": [0, 0, 0, 0, 0]}])
            case 3:
                add_page(overlay_page, [version_list_screen, {"size": ["你是否要下载并安装", "该版本", "？\n该软件包大小为", "--", "MB"], "tag_index": 0, "index": 0, "edition_info": global_info["update_list"], "button_state": [0, 0, 0, 0, 0]}])
            case 4:
                if global_info["setting"]["version"]:
                    _edition = "V" + str(global_info["setting"]["version"])
                else:
                    _edition = "Unknown"
                if global_info["setting"]["edition"]:
                    _edition += "-" + str(global_info["setting"]["edition"])
                add_page(overlay_page, [about_screen, {"edition": _edition, "button_state": [0, 0, 0, 0]}])

    change_button_alpha(_info["button_state"], _id)

    return _root

def player_screen(_info, _input):
    if ("mouse_right" in _input and not _input["mouse_right"]) and _info["armed"]:
        remove_page(overlay_page)
        _info["armed"] = False

    if "drop_file" in _input and os.path.splitext(_input["drop_file"])[1] == ".mid":
        threading.Thread(target=player_callback, args=(_input["drop_file"], True, _info), daemon=True).start()

    if not _info["armed"]: _info["progress"] = 0

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, (os.path.splitext(os.path.basename(_info["file"]))[0] if _info["file"] else "选择MIDI文件", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("播放设置", 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.05, 0.089, ("◀", 0.035, _info["button_state"][2]), 2),
            (0.1, 0.311, 0.15, 0.089, (get_time_text(round_int(_info["position"] * 0.05)), 0.035, 255), -1),
            (0.275, 0.311, 0.45, 0.089, (("暂停" if _info["play"] else "播放") if _info["armed"] else "处理中", 0.035, _info["button_state"][3]), 3),
            (0.75, 0.311, 0.15, 0.089, (get_time_text(round_int(_info["length"] * 0.05)), 0.035, 255), -1),
            (0.925, 0.311, 0.05, 0.089, ("▶", 0.035, _info["button_state"][4]), 4),
            (0.025, 0.444, 0.95, 0.089, ("", 0.035, 255), -1)
        ),
        pygame.mouse.get_pos()
    )

    _text_surf1 = global_asset["font"].render(_info["lyrics"][0], True, global_info["color"])
    _text_surf2 = global_asset["font"].render(_info["lyrics"][1], True, (255, 255, 255))
    if global_info["color"] == (255, 255, 255): _text_surf2.set_alpha(127)

    _text_width = _text_surf1.size[0] + _text_surf2.size[0]

    _text_position = ui_manager.get_abs_position((0.5, 0.489), True)

    _root.blits(
        (
            (_text_surf1, (_text_position[0] - _text_width / 2, _text_position[1] - global_asset["font"].get_height() / 2)),
            (_text_surf2, (_text_position[0] - _text_width / 2 + _text_surf1.size[0], _text_position[1] - global_asset["font"].get_height() / 2))
        )
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                if _info["armed"]: threading.Thread(target=open_filedialog, args=(player_callback, [("MIDI Files", ".mid")], True, _info), daemon=True).start()
            case 1:
                add_page(overlay_page, [player_setting_screen, {"button_state": [0, 0, 0, 0, 0, 0], "info": _info}])
            case 2:
                if _info["position"] >= 100:
                    _info["position"] -= 100
                else:
                    _info["position"] = 0
            case 3:
                _info["play"] = not _info["play"]
            case 4:
                if _info["length"] - _info["position"] >= 100:
                    _info["position"] += 100
                else:
                    _info["position"] = _info["length"]

    change_button_alpha(_info["button_state"], _id)

    return _root

def player_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        if _info["info"]["file"]: threading.Thread(target=player_callback, args=(_info["info"]["file"], False, _info["info"]), daemon=True).start()
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("播放速度设置", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("歌词字幕设置", 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("打击乐器 " + ("保留" if global_info["convertor"]["percussion"] else "去除"), 0.035, _info["button_state"][2]), 2),
            (0.025, 0.444, 0.95, 0.089, ("乐器调整 " + ("启用" if global_info["convertor"]["adjustment"] else "关闭"), 0.035, _info["button_state"][3]), 3),
            (0.025, 0.578, 0.95, 0.089, ("长音特性 " + ("启用" if global_info["convertor"]["hold"] else "关闭"), 0.035, _info["button_state"][4]), 4),
            (0.025, 0.711, 0.95, 0.089, ("平均音量 " + (str(global_info["convertor"]["volume"]) + "%" if global_info["convertor"]["volume"] else "保持原始音量"), 0.035, _info["button_state"][5]), 5)
        ),
        pygame.mouse.get_pos()
    )

    change_button_alpha(_info["button_state"], _id)

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0: add_page(overlay_page, [speed_setting_screen, {"button_state": [0, 0, 0]}])
            case 1: add_page(overlay_page, [lyrics_setting_screen, {"button_state": [0, 0, 0]}])
            case 2: global_info["convertor"]["percussion"] = not global_info["convertor"]["percussion"]
            case 3: global_info["convertor"]["adjustment"] = not global_info["convertor"]["adjustment"]
            case 4: global_info["convertor"]["hold"] = not global_info["convertor"]["hold"]
            case 5: set_volume()

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
            if global_info["convertor"]["new_java_pack"]:
                _ver_text += "（1.21以上）"
            else:
                _ver_text += "（1.13到1.21）"
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
        if global_info["convertor"]["hold"]:
            _other_text += "/长音"
        if global_info["convertor"]["adjustment"]:
            _other_text += "/乐器调整"
        if global_info["convertor"]["lyrics"]["enable"]:
            _other_text += "/歌词"
        if global_info["convertor"]["compression"]:
            _other_text += "/压缩"
        if global_info["convertor"]["extension"]:
            _other_text += "/音域扩展"
    else:
        _other_text = "高级设置"

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
                threading.Thread(target=open_filedialog, args=(midi_file_callback, [("MIDI Files", ".mid")]), daemon=True).start()
            case 1:
                if global_info["convertor"]["edition"] == -1:
                    global_info["convertor"]["edition"] = 0
                add_page(overlay_page, [game_edition_screen, {"button_state": [0, 0, 0]}])
            case 2:
                if global_info["convertor"]["output_format"] == -1:
                    global_info["convertor"]["output_format"] = 0
                add_page(overlay_page, [setting_screen, {"button_state": [0, 0, 0, 0]}])
            case 3:
                if global_info["convertor"]["time_per_tick"] == -1:
                    global_info["convertor"]["time_per_tick"] = 50
                add_page(overlay_page, [advanced_setting_screen, {"button_state": [0, 0, 0, 0, 0, 0, 0]}])
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

def convertor_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("移除重复音符 " + ("是" if global_info["setting"]["remove_chord"] else "不"), 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("询问映射关系 " + ("是" if global_info["setting"]["ask_mapping"] else "不"), 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("长音插值方式 " + (("持续", "线性", "二次")[global_info["setting"]["interpolation"]]), 0.035, _info["button_state"][2]), 2)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0: global_info["setting"]["remove_chord"] = not global_info["setting"]["remove_chord"]
            case 1: global_info["setting"]["ask_mapping"] = not global_info["setting"]["ask_mapping"]
            case 2:
                global_info["setting"]["interpolation"] += 1
                if global_info["setting"]["interpolation"] > 2:
                    global_info["setting"]["interpolation"] = 0

    change_button_alpha(_info["button_state"], _id)

    return _root

def software_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    if "drop_file" in _input:
        match os.path.splitext(_input["drop_file"])[1]:
            case ".mspf":
                threading.Thread(target=enter_to_editor, args=[_input["drop_file"]], daemon=True).start()
            case _i if _i.lower() in (".jpeg", ".jpg", ".png"):
                threading.Thread(target=produce_background, args=[_input["drop_file"]], daemon=True).start()
            case _:
                global_info["message"].append("不支持的文件 " + os.path.basename(_input["drop_file"]))

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
            (0.025, 0.044, 0.95, 0.089, ("编辑指令模板", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("指令压缩设置", 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("软件个性设置", 0.035, _info["button_state"][2]), 2),
            (0.025, 0.444, 0.95, 0.089, ("音乐转换设置", 0.035, _info["button_state"][3]), 3),
            (0.025, 0.578, 0.95, 0.089, ("软件日志等级 " + _text, 0.035, _info["button_state"][4]), 4)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0: threading.Thread(target=enter_to_editor, daemon=True).start()
            case 1: add_page(overlay_page, [compression_setting_screen, {"button_state": [0, 0]}])
            case 2: add_page(overlay_page, [custom_setting_screen, {"button_state": [0, 0, 0]}])
            case 3: add_page(overlay_page, [convertor_setting_screen, {"button_state": [0, 0, 0]}])
            case 4:
                global_info["setting"]["log_level"] += 1
                if global_info["setting"]["log_level"] >= 6:
                    global_info["setting"]["log_level"] = 0
                logger.set_log_level(global_info["setting"]["log_level"])

    change_button_alpha(_info["button_state"], _id)

    return _root

def custom_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    if "drop_file" in _input:
        match os.path.splitext(_input["drop_file"])[1]:
            case _i if _i.lower() in (".jpeg", ".jpg", ".png"):
                threading.Thread(target=produce_background, args=[_input["drop_file"]], daemon=True).start()
            case _:
                global_info["message"].append("不支持的文件 " + os.path.basename(_input["drop_file"]))

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("界面刷新率 " + (str(global_info["setting"]["fps"]) + "Hz" if global_info["setting"]["fps"] else "无限制"), 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("界面动画速度 " + (str(global_info["setting"]["animation_speed"]) if global_info["setting"]["animation_speed"] != 0 else "禁用"), 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("更改界面背景", 0.035, _info["button_state"][2]), 2)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                global_info["setting"]["fps"] += 30
                if global_info["setting"]["fps"] > 120:
                    global_info["setting"]["fps"] = 0
            case 1:
                global_info["setting"]["animation_speed"] += 1
                if global_info["setting"]["animation_speed"] >= 16:
                    global_info["setting"]["animation_speed"] = 0
            case 2:
                threading.Thread(target=produce_background, daemon=True).start()

    change_button_alpha(_info["button_state"], _id)

    return _root

def compression_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("参数压缩等级 " + ["标准", "高", "极限"][global_info["setting"]["compression_level"]], 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("最大指令长度 " + str(global_info["setting"]["max_cmd_length"]) + "字", 0.035, _info["button_state"][1]), 1)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                global_info["setting"]["compression_level"] += 1
                if global_info["setting"]["compression_level"] == 3:
                    global_info["setting"]["compression_level"] = 0
            case 1:
                set_selector_num()

    change_button_alpha(_info["button_state"], _id)

    return _root

def version_list_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        global_info["new_version"] = ""
        remove_page(overlay_page)

    if "drop_file" in _input:
        match os.path.splitext(_input["drop_file"])[1]:
            case _i if _i.lower() in (".zst", ".xz", ".gz", ".zip"):
                threading.Thread(target=unpack, args=[_input["drop_file"]], daemon=True).start()
            case _:
                global_info["message"].append("不支持的文件 " + os.path.basename(_input["drop_file"]))

    if global_info["update_list"][1]:
        _ver_list = _info["edition_info"][1][_info["edition_info"][0][_info["tag_index"]]]

        _root, _id = ui_manager.apply_ui(
            (
                (0.025, 0.044, 0.575, 0.089, (_info["edition_info"][0][_info["tag_index"]], 0.035, _info["button_state"][4]), 4),
                (0.625, 0.044, 0.05, 0.089, ("◀", 0.035, _info["button_state"][0]), 0),
                (0.7, 0.044, 0.2, 0.089, (str(_info["index"] + 1) + "/" + str(len(_ver_list)), 0.035, 255), -1),
                (0.925, 0.044, 0.05, 0.089, ("▶", 0.035, _info["button_state"][1]), 1),
                (0.025, 0.178, 0.95, 0.089, ("V" + str(_ver_list[_info["index"]]["version"]) + ("-" + str(_ver_list[_info["index"]]["edition"]) if _ver_list[_info["index"]]["edition"] else ""), 0.035, 255), -1),
                (0.025, 0.311, 0.95, 0.089, ("查看版本详情", 0.035, _info["button_state"][2]), 2),
                (0.025, 0.444, 0.95, 0.089, ("下载并安装", 0.035, _info["button_state"][3]), 3)
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
                    if _ver_list[_info["index"]]["description_url"]: add_page(overlay_page, [asking_screen, {"button_state": [0, 0], "button_text": ["在浏览器中查看", "好的"], "argument": [_ver_list[_info["index"]]["description_url"]], "callback": lambda _url: webbrowser.open(_url), "content": _ver_list[_info["index"]]["tips"]}], 0, True)
                case 3:
                    _ver_info = _ver_list[_info["index"]]
                    _info["size"][3] = "--"
                    _info["size"][1] = " V" + str(_ver_info["version"]) + "-" + str(_ver_info["edition"])
                    threading.Thread(target=get_resource_size, args=(_ver_info["download_url"], _info["size"]), daemon=True).start()
                    add_page(overlay_page, [asking_screen, {"button_state": [0, 0], "button_text": ["下载并安装", "取消"], "argument": (("V" + str(global_info["setting"]["version"]) + "  ➡  " if global_info["setting"]["version"] else "") + "V" + str(_ver_info["version"]), _ver_info["download_url"], "Update", reboot), "callback": show_download, "content": _info["size"]}], 0, True)
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
            (0.025, 0.356, 0.463, 0.1, ("QQ 交流群", 0.035, _info["button_state"][0]), 0),
            (0.513, 0.356, 0.463, 0.1, ("Gitee 开源仓库", 0.035, _info["button_state"][1]), 1),
            (0.025, 0.489, 0.463, 0.1, ("音域扩展包下载", 0.035, _info["button_state"][2]), 2),
            (0.513, 0.489, 0.463, 0.1, ("MMS播放器下载", 0.035, _info["button_state"][3]), 3)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0: add_page(overlay_page, [asking_screen, {"button_state": [0, 0], "button_text": ["在浏览器中查看", "好的"], "argument": (), "callback": lambda: webbrowser.open(global_info["links"]["qq"]), "content": "群号：574931138\n密码：14890357"}], 0, True)
            case 1: webbrowser.open(global_info["links"]["mms"])
            case 2: webbrowser.open(global_info["links"]["sound_extension"])
            case 3: webbrowser.open(global_info["links"]["player"])

    change_button_alpha(_info["button_state"], _id)

    _root.blit(global_asset["logo"], ui_manager.get_abs_position((0.155, 0.062), True))

    return _root

def download_screen(_info, _input):
    if _info["state"]["state"] == -1:
        _text = "下载失败，请重试"
    elif _info["state"]["state"] == 0:
        _text = str(round_45(_info["state"]["buffer"].get_progress() * 100, 2)) + "%" if _info["state"]["buffer"].get_progress() else "等待中"
    elif _info["state"]["state"] == 1:
        _text = "下载完成"
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
    if "mouse_right" in _input and not _input["mouse_right"]:
        add_page(overlay_page, [asking_screen, {"button_state": [0, 0], "button_text": ["是", "否"], "argument": [_info["done"]], "callback": exit_mapping_screen, "content": "退出映射编辑界面？"}], 0, True)

    if _info["done"][0] == 1:
        remove_page(overlay_page)
        _info["done"][0] = 2

    _config_length = len(_info["data"][_info["channels"][_info["channel_index"]]])
    _page_num = ceil(_config_length / 6)

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
                (0.3, _i, 0.675, 0.089, (_text, 0.035, _info["button_state"][_n + 3]), _n + 3)
            )
        )

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.575, 0.089, ("通道 " + str(_info["channels"][_info["channel_index"]] + 1), 0.035, _info["button_state"][0]), 0),
            (0.625, 0.044, 0.05, 0.089, ("◀", 0.035, _info["button_state"][1]), 1),
            (0.7, 0.044, 0.2, 0.089, (str(_info["index"] + 1) + "/" + str(_page_num) if _config_length else "无数据", 0.035, 255), -1),
            (0.925, 0.044, 0.05, 0.089, ("▶", 0.035, _info["button_state"][2]), 2)
        ) + tuple(_config_list),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                _info["channel_index"] += 1
                if _info["channel_index"] >= len(_info["channels"]):
                    _info["channel_index"] = 0
                _info["index"] = 0
            case 1:
                _info["index"] -= 1
                if _info["index"] < 0:
                    _info["index"] = _page_num - 1
            case 2:
                _info["index"] += 1
                if _info["index"] >= _page_num:
                    _info["index"] = 0
            case _n if 3 <= _n <= 8:
                if _info["channels"][_info["channel_index"]] not in _info["mapping"]: _info["mapping"][_info["channels"][_info["channel_index"]]] = {}
                add_page(overlay_page, [packing_screen, {"done": _info["done"], "button_state": [0, 0, 0, 0, 0, 0, 0, 0], "index": 0, "percussion": _info["channels"][_info["channel_index"]] == 9, "mapping": _info["mapping"][_info["channels"][_info["channel_index"]]], "origin": _info["data"][_info["channels"][_info["channel_index"]]][_info["index"] * 6 + _id - 3][1]}])

    change_button_alpha(_info["button_state"], _id)

    return _root

def packing_screen(_info, _input):
    if ("mouse_right" in _input and not _input["mouse_right"]) or _info["done"][0]:
        remove_page(overlay_page)

    _config = tuple((global_asset["instruments"]["percussion"] if _info["percussion"] else global_asset["instruments"]["other"]).keys())
    _config_length = len(_config)
    _page_num = ceil(_config_length / 6)

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
            (0.025, 0.044, 0.95, 0.089, ("输出格式 " + ("mcstructure", "mcfunction", "SAPI行为包")[global_info["convertor"]["output_format"]], 0.035, _info["button_state"][0]), 0),
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
                    global_info["message"].append("目标游戏存档需要安装MMS播放器行为包（关于页面下载）！")
            case 1:
                if global_info["convertor"]["output_format"] != 2:
                    global_info["convertor"]["command_type"] += 1
                    if global_info["convertor"]["command_type"] >= 3:
                        if global_info["convertor"]["output_format"] == 0:
                            global_info["convertor"]["command_type"] = 0
                        else:
                            global_info["convertor"]["command_type"] = 1
            case 2:
                set_volume()
            case 3:
                if global_info["convertor"]["output_format"] == 0: global_info["convertor"]["structure"] += 1
                if global_info["convertor"]["structure"] >= len(global_asset["structure"]): global_info["convertor"]["structure"] = 0
        if global_info["convertor"]["command_type"] == 0: global_info["convertor"]["compression"] = False

    return _root

def advanced_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("播放速度设置", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("歌词字幕设置", 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("不常用的设置", 0.035, _info["button_state"][2]), 2),
            (0.025, 0.444, 0.95, 0.089, ("长音特性 " + ("启用" if global_info["convertor"]["hold"] else "关闭"), 0.035, _info["button_state"][3]), 3),
            (0.025, 0.578, 0.95, 0.089, ("乐器调整 " + ("启用" if global_info["convertor"]["adjustment"] else "关闭"), 0.035, _info["button_state"][4]), 4),
            (0.025, 0.711, 0.95, 0.089, ("音域扩展 " + ("启用" if global_info["convertor"]["extension"] else "关闭"), 0.035, _info["button_state"][5]), 5),
            (0.025, 0.844, 0.95, 0.089, ("指令压缩 " + ("不可用" if global_info["convertor"]["command_type"] == 0 or (global_info["convertor"]["edition"] == 1 and global_info["convertor"]["version"] == 0) else ("启用" if global_info["convertor"]["compression"] else "关闭")), 0.035, _info["button_state"][6]), 6)
        ),
        pygame.mouse.get_pos()
    )

    change_button_alpha(_info["button_state"], _id)

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0: add_page(overlay_page, [speed_setting_screen, {"button_state": [0, 0, 0]}])
            case 1: add_page(overlay_page, [lyrics_setting_screen, {"button_state": [0, 0, 0]}])
            case 2: add_page(overlay_page, [other_setting_screen, {"button_state": [0, 0, 0]}])
            case 3: global_info["convertor"]["hold"] = not global_info["convertor"]["hold"]
            case 4: global_info["convertor"]["adjustment"] = not global_info["convertor"]["adjustment"]
            case 5:
                global_info["convertor"]["extension"] = not global_info["convertor"]["extension"]
                if global_info["convertor"]["extension"]:
                    if global_info["convertor"]["edition"] == 0:
                        global_info["message"].append("基岩版无需开启，此功能是为Java版设计！")
                    else:
                        global_info["message"].append("目标游戏存档需要安装MMS音域扩展资源包（关于页面下载）！")
            case 6:
                if global_info["convertor"]["command_type"] != 0 and not (global_info["convertor"]["edition"] == 1 and global_info["convertor"]["version"] == 0):
                    global_info["convertor"]["compression"] = not global_info["convertor"]["compression"]

    return _root

def other_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("静音跳过 " + ("启用" if global_info["convertor"]["skip"] else "关闭"), 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("声相偏移 " + ("启用" if global_info["convertor"]["panning"] else "关闭"), 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("打击乐器 " + ("保留" if global_info["convertor"]["percussion"] else "去除"), 0.035, _info["button_state"][2]), 2)
        ),
        pygame.mouse.get_pos()
    )

    change_button_alpha(_info["button_state"], _id)

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0: global_info["convertor"]["skip"] = not global_info["convertor"]["skip"]
            case 1: global_info["convertor"]["panning"] = not global_info["convertor"]["panning"]
            case 2: global_info["convertor"]["percussion"] = not global_info["convertor"]["percussion"]

    return _root

def speed_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, (f"播放速度 {global_info["convertor"]["time_per_tick"]}ms/tick", 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, (f"时间对齐 {("启用" if global_info["convertor"]["enable_accurate_tick"] else "关闭")}", 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, (f"最大容差 ±{global_info["convertor"]["max_time_error"]}ms", 0.035, _info["button_state"][2]), 2)
        )[:3 if global_info["convertor"]["enable_accurate_tick"] else 2],
        pygame.mouse.get_pos()
    )

    change_button_alpha(_info["button_state"], _id)

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0: set_time_per_tick()
            case 1: global_info["convertor"]["enable_accurate_tick"] = not global_info["convertor"]["enable_accurate_tick"]
            case 2:
                global_info["convertor"]["max_time_error"] += 1
                if global_info["convertor"]["max_time_error"] > min(global_info["convertor"]["time_per_tick"], 8):
                    global_info["convertor"]["max_time_error"] = 1

    return _root

def lyrics_setting_screen(_info, _input):
    if "mouse_right" in _input and not _input["mouse_right"]:
        remove_page(overlay_page)

    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.089, ("歌词显示 " + ("启用" if global_info["convertor"]["lyrics"]["enable"] else "关闭"), 0.035, _info["button_state"][0]), 0),
            (0.025, 0.177, 0.95, 0.089, ("平滑进度 " + ("启用" if global_info["convertor"]["lyrics"]["smooth"] else "关闭"), 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("自动合并 " + ("启用" if global_info["convertor"]["lyrics"]["joining"] else "关闭"), 0.035, _info["button_state"][2]), 2)
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
            (0.025, 0.177, 0.95, 0.089, ("指令语法 " + ["1.19.50/1.13以下", "1.19.50/1.13以上"][global_info["convertor"]["version"]], 0.035, _info["button_state"][1]), 1),
            (0.025, 0.311, 0.95, 0.089, ("数据包格式 " + ("1.21以上" if global_info["convertor"]["new_java_pack"] else "1.21以下"), 0.035, _info["button_state"][2]), 2)
        )[:3 if global_info["convertor"]["edition"] == 1 and global_info["convertor"]["version"] == 1 else 2],
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
            case 2:
                global_info["convertor"]["new_java_pack"] = not global_info["convertor"]["new_java_pack"]

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

def asking_screen(_info, _input):
    _root, _id = ui_manager.apply_ui(
        (
            (0.025, 0.044, 0.95, 0.778, ("".join(_info["content"]), 0.035, 255), -1),
            (0.025, 0.867, 0.463, 0.089, (_info["button_text"][0], 0.035, _info["button_state"][0]), 0),
            (0.513, 0.867, 0.463, 0.089, (_info["button_text"][1], 0.035, _info["button_state"][1]), 1)
        ),
        pygame.mouse.get_pos()
    )

    if "mouse_left" in _input and not _input["mouse_left"]:
        match _id:
            case 0:
                remove_page(overlay_page)
                _info["callback"](*_info["argument"])
            case 1:
                remove_page(overlay_page)

    change_button_alpha(_info["button_state"], _id)

    return _root


if base_path := getattr(sys, "_MEIPASS", None):
    if os.path.basename(base_path) == "_internal":
        os.chdir(os.path.dirname(base_path))
    else:
        os.chdir(base_path)

global_info = {"exit": 0, "watch_dog": 0, "color": (255, 255, 255), "message": [], "message_info": [0, 0, False], "links": {"player": "gitee.com/mrdxhmagic/mms-midi-player/releases", "sound_extension": "www.123865.com/s/se2RTd-goEg", "mms": "gitee.com/mrdxhmagic/midi-mcstructure_next", "qq": "qm.qq.com/q/9oBhTyDN8k"}, "new_version": False, "update_list": [[], {}], "sounds_update": {"version": -1, "download_url": ""}, "mcpack_update": ["", ""], "editor_update": {"version": 0}, "downloader": [{"state": "waiting", "downloaded": 0, "total": 0}], "setting": {"id": 1, "fps": 60, "version": 0, "edition": "Unknown", "log_level": 5, "interpolation": 0, "ask_mapping": False, "remove_chord": True, "channels_num": 32, "max_cmd_length": 256, "animation_speed": 10, "compression_level": 0, "disable_update_check": False}, "profile": {}, "convertor": {"file": "", "edition": -1, "version": 1, "new_java_pack": False, "command_type": 0, "output_format": -1, "volume": 30, "structure": 0, "skip": True, "time_per_tick": -1, "max_time_error": 5, "enable_accurate_tick": False, "adjustment": True, "percussion": True, "panning": False, "lyrics": {"enable": False, "smooth": True, "joining": False}, "hold": False, "extension": False, "compression": False, "ask_mapping": True}}
global_asset: dict[str, pygame.Surface | pygame.font.Font | list | dict] = {}
overlay_page = []

pygame.init()
pygame.display.set_caption("MIDI-MCSTRUCTURE NEXT  GUI")
pygame.display.set_icon(pygame.image.load("Asset/image/icon.png"))
window = pygame.display.set_mode((800, 450), pygame.RESIZABLE)

logger = log.Logger(5)
ui_manager = UIManager()

try:
    import pyi_splash
    pyi_splash.close()
except:
    logger.debug(traceback.format_exc())

try:
    timer = pygame.time.Clock()

    threading.Thread(target=watchdog, daemon=True).start()
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
    logger.fatal(traceback.format_exc())
    global_info["exit"] = 3
finally:
    if not os.path.exists("Asset/text"):
        os.makedirs("Asset/text")

    with open("Asset/text/setting.json", "w") as io:
        io.write(json.dumps(global_info["setting"], indent=2))

    if global_info["exit"] == 2:
        subprocess.run(("Updater/updater.exe", os.path.abspath("")))
    elif global_info["exit"] == 3:
        window.blit(global_asset["error"], (0, 0))
        pygame.display.flip()
        time.sleep(3)

    pygame.quit()
    logger.done()
    os._exit(0)