import os
import time
import json
import py7zr
import shutil
import traceback
import subprocess

log = []
root = os.path.dirname(os.path.dirname(os.path.split(os.path.realpath(__file__))[0])).replace("\\", "/") + "/"

try:
    log.append("[N] Load Old Settings")
    with open(root + "Asset/text/setting.json", "r") as io:
        old_setting = json.load(io)
    log.append("[I] MMS-NEXT V" + str(old_setting["version"]))
    log.append("[N] Position: " + root)

    if os.path.exists(root + "Cache/extracted"):
        log.append("[W] Remove Directory: Cache/extracted")
        shutil.rmtree(root + "Cache/extracted")
    log.append("[N] Make Directory: Cache/extracted")
    os.makedirs(root + "Cache/extracted")

    log.append("[N] Extract Package")
    with py7zr.SevenZipFile(root + "Cache/download/package.7z", "r") as io:
        io.extractall(root + "Cache/extracted")

    log.append("[N] Load New Settings")
    with open(root + "Cache/extracted/Asset/text/setting.json", "r") as io:
        new_setting = json.load(io)
    log.append("[N] Copy Settings:")
    for k in list(old_setting.keys()):
        if k in new_setting and k not in ("version", "edition"):
            log.append("[N]   " + str(k) + ": " + str(old_setting[k]) + " -> " + str(new_setting[k]))
            new_setting[k] = old_setting[k]
    log.append("[N] Save Settings")
    with open(root + "Cache/extracted/Asset/text/setting.json", "w") as io:
        json.dump(new_setting, io)

    if os.path.exists(root + "Cache/extracted/Asset/mcstructure") and os.path.exists(root + "Asset/mcstructure"):
        log.append("[N] Move Structures:")
        for i in os.listdir(root + "Asset/mcstructure"):
            if os.path.splitext(i)[1] == ".mcstructure":
                log.append("[N]     Find: " + i)
                if not os.path.exists(root + "Cache/extracted/Asset/mcstructure/" + i):
                    log.append("[N]     Move: " + i)
                    shutil.move(root + "Asset/mcstructure/" + i, root + "Cache/extracted/Asset/mcstructure/" + i)


    log.append("[N] Install Update:")
    for i in os.listdir(root):
        if i not in ("Updater", "Cache"):
            log.append("[N]   Try to Remove: " + i)
            n = 0
            while n <= 16:
                try:
                    if os.path.isdir(root + i):
                        shutil.rmtree(root + i)
                    elif os.path.isfile(root + i):
                        os.remove(root + i)
                    break
                except:
                    n += 1

    for i in os.listdir(root + "Cache/extracted"):
        log.append("[N]   Try to Move: " + i)
        if os.path.splitext(i)[1] == ".exe":
            shutil.move(root + "Cache/extracted/" + i, root + "MIDI-MCSTRUCTURE_NEXT.exe")
        elif os.path.isdir(root + "Cache/extracted/" + i) and i != "Updater":
            shutil.move(root + "Cache/extracted/" + i, root + i)

    log.append("[I] Update Successfully:")
    log.append("[I]   V" + str(old_setting["version"]) + " -> V" + str(new_setting["version"]))
except:
    log.extend(("[E] " + line for line in traceback.format_exc().splitlines()))
finally:
    if log:
        with open("log.txt", "a") as io:
            io.write("[V250718B] " + time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()) + ":\n")
            io.writelines("  " + line + "\n" for line in log)

    subprocess.Popen(root + "MIDI-MCSTRUCTURE_NEXT.exe")
    os._exit(0)