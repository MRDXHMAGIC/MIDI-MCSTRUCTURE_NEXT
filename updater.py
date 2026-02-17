import os
import sys
import json
import time
import traceback
from shutil import rmtree, copyfile

log = []
def add_log(_hand: str, _content: str, _indent: int = 1) -> None:
    log.extend(f"[{_hand}]{"  " * _indent}{line.strip()}" for line in _content.splitlines())


def get_path(*_paths):
    return os.path.join(sys.argv[1], *_paths)


def install(_indent: int = 3, _stack = ""):
    add_log("D", f"{os.path.basename(_stack)}:" if _stack else "RootFolder:", _indent - 1)
    for _token in os.listdir(get_path("Update", _stack)):
        if not os.path.isdir(get_path(_stack)):
            add_log("D", "Make Directory: " + _stack, _indent)
            os.makedirs(get_path(_stack))


        if os.path.join(_stack, _token) in ("Update", "Updater"):
            add_log("D", "Skip " + os.path.join("Update", _stack, _token), _indent)

        elif os.path.isfile(get_path("Update", _stack, _token)):
            if os.path.splitext(_token)[1] == ".exe" and not _stack:
                if os.path.exists(get_path(_stack, "MIDI-MCSTRUCTURE_NEXT" + os.path.splitext(_token)[1])):
                    add_log("D", "Replace Main Executable File: " + _token, _indent)
                    os.replace(get_path("Update", _stack, _token), get_path(_stack, "MIDI-MCSTRUCTURE_NEXT" + os.path.splitext(_token)[1]))
                else:
                    add_log("D", "Copy Main Executable File: " + _token, _indent)
                    copyfile(get_path("Update", _stack, _token), get_path(_stack, "MIDI-MCSTRUCTURE_NEXT" + os.path.splitext(_token)[1]))
            elif os.path.exists(get_path(_stack, _token)):
                add_log("D", "Replace File: " + _token, _indent)
                os.replace(get_path("Update", _stack, _token), get_path(_stack, _token))
            else:
                add_log("D", "Copy File: " + _token, _indent)
                copyfile(get_path("Update", _stack, _token), get_path(_stack, _token))

        elif os.path.isdir(get_path("Update", _stack, _token)):
            install(_indent + 1, os.path.join(_stack, _token))

try:
    time.sleep(1)
    os.chdir(get_path())

    add_log("I", "Wipe Cache")
    if os.path.exists("Cache"): rmtree("Cache")

    add_log("I", "Load Old Settings")
    with open(get_path("Asset/text/setting.json"), "r", encoding="utf-8") as io:
        old_setting = json.load(io)

    add_log("I", "MMS-NEXT V" + str(old_setting["version"]))
    add_log("D", "Position: " + get_path())

    new_setting = None
    try:
        add_log("I", "Load New Settings")
        with open(get_path("Update/Asset/text/setting.json"), "r", encoding="utf-8") as io:
            new_setting = json.load(io)

        add_log("I", "Copy Settings:")
        for k in list(old_setting.keys()):
            if k in new_setting and k not in ("version", "edition"):
                add_log("I", f"{k}: {old_setting[k]} -> {new_setting[k]}", 2)
                new_setting[k] = old_setting[k]

        add_log("I", "Save Settings")
        with open(get_path("Update/Asset/text/setting.json"), "w", encoding="utf-8") as io:
            json.dump(new_setting, io)
    except:
        add_log("E", traceback.format_exc())

    add_log("I", "Install Update:")
    install()

    add_log("I", "Clean Up Update Files")
    if os.path.exists("Update"): rmtree("Update")

    add_log("I", "Update Successfully:")
    add_log("I", "V" + str(old_setting["version"]) + ((" -> V" + str(new_setting["version"])) if new_setting is not None else ""), 2)
except:
    add_log("F", traceback.format_exc())
finally:
    if log:
        with open(get_path("update_log.txt"), "w", encoding="utf-8") as io:
            io.write("[I] MMS Updater (Built at {BUILT_TIME}):\n")
            io.writelines(line + "\n" for line in log)

    os.startfile(get_path("MIDI-MCSTRUCTURE_NEXT.exe"))

    os._exit(0)