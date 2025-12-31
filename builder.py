import os
import json
import time
import shutil
import hashlib
import tarfile
import subprocess
from compression.zstd import CompressionParameter


VERSION = int(input("Version: "))
EDITION = input("Edition: ")
print()

TITLE = time.strftime(f"V{VERSION}%y%m%d-{EDITION}", time.localtime())

if os.path.exists("dist"): shutil.rmtree("dist")
os.mkdir("dist")

shutil.copytree("Asset", "dist/Asset")

if os.path.exists("dist/Asset/text/default_profile.json"): os.remove("Asset/text/default_profile.json")
if os.path.exists("dist/Asset/image/custom_menu_background.png"): os.remove("Asset/image/custom_menu_background.png")

with open("dist/Asset/text/setting.json", "rb") as io:
    setting = json.loads(io.read())
setting["version"] = int(TITLE[1:9])
setting["edition"] = EDITION
setting["disable_update_check"] = False
with open("dist/Asset/text/setting.json", "w", encoding="utf-8") as io:
    io.write(json.dumps(setting, indent=2))

subprocess.Popen(".venv/Scripts/pyinstaller.exe -D -w -i ././icon.ico ././main.py -y -n \"MIDI-MCSTRUCTURE_NEXT\"").wait()
shutil.move("dist/Asset", "dist/MIDI-MCSTRUCTURE_NEXT/Asset")
subprocess.Popen(".venv/Scripts/pyinstaller.exe -D -w -i ././icon.ico ././writer.py -y -n \"Writer\"").wait()
shutil.move("dist/Writer", "dist/MIDI-MCSTRUCTURE_NEXT/Writer")
subprocess.Popen(".venv/Scripts/pyinstaller.exe -D -w -i ././icon.ico ././updater.py -y -n \"Updater\"").wait()
shutil.move("dist/Updater", "dist/MIDI-MCSTRUCTURE_NEXT/Updater")

options = {
    CompressionParameter.compression_level: CompressionParameter.compression_level.bounds()[1],
    CompressionParameter.checksum_flag: True
}

with tarfile.open(f"dist/MIDI-MCSTRUCTURE_NEXT_{TITLE}.tar.zst", "w:zst", options=options) as io:
    io.add("dist/MIDI-MCSTRUCTURE_NEXT", "")

edition_info = {
    "API": 3,
    "tips": input("Tips: "),
    "version": setting["version"],
    "edition": setting["edition"],
    "download_url": f"https://gitee.com/mrdxhmagic/midi-mcstructure_next/releases/download/{TITLE}/MIDI-MCSTRUCTURE_NEXT_{TITLE}.tar.zst",
    "description_url": f"https://gitee.com/mrdxhmagic/midi-mcstructure_next/releases/tag/{TITLE}"
}

print()

with open("update.json", "rb") as io:
    update_log = json.loads(io.read())

for n in range(len(update_log)):
    if update_log[n]["API"] != edition_info["API"]:
        pass
    elif update_log[n]["version"] != setting["version"]:
        pass
    elif update_log[n]["edition"] == setting["edition"]:
        update_log[n] = edition_info
        break
else:
    update_log.append(edition_info)

with open("update.json", "w", encoding="utf-8") as io:
    io.write(json.dumps(update_log, indent=2))
