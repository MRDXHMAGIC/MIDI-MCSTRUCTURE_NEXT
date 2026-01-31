import os
import time
import json
import shutil
import tarfile
import subprocess
from compression.zstd import CompressionParameter

ONE_FILE = False

with open("Asset/text/setting.json", "rb") as io:
    setting = json.loads(io.read())

VERSION = setting["version"]
EDITION = setting["edition"]

TITLE = f"V{VERSION}-{EDITION}"

options = {
    CompressionParameter.compression_level: CompressionParameter.compression_level.bounds()[1],
    CompressionParameter.checksum_flag: True
}


if os.path.exists("dist"): shutil.rmtree("dist")
os.mkdir("dist")


shutil.copytree("Asset", "dist/Asset")
with open("dist/Asset/text/setting.json", "rb") as io:
    setting = json.loads(io.read())

setting["log_level"] = 4
setting["disable_update_check"] = ONE_FILE

with open("dist/Asset/text/setting.json", "w", encoding="utf-8") as io:
    io.write(json.dumps(setting, indent=2))


if os.path.exists("dist/Asset/text/default_profile.json"): os.remove("dist/Asset/text/default_profile.json")
if os.path.exists("dist/Asset/image/custom_menu_background.png"): os.remove("dist/Asset/image/custom_menu_background.png")


with open("updater.py", "r", encoding="utf-8") as io:
    code = io.read()

with open("dist/updater.py", "w", encoding="utf-8") as io:
    io.write(code.replace("{BUILT_TIME}", time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()), 1))

subprocess.Popen(".venv/Scripts/pyinstaller.exe -D -w --optimize 2 -i icon.ico dist/updater.py -y -n \"Updater\"").wait()

if not os.path.exists("dist/Asset/updater"): os.makedirs("dist/Asset/updater")
with tarfile.open("dist/Asset/updater/package.tar.zst", "w:zst", options=options) as io:
    io.add("dist/Updater", arcname="")

subprocess.Popen(f".venv/Scripts/pyinstaller.exe {"-F" if ONE_FILE else "-D"} -w --optimize 2 --add-data \"dist/Asset/*;./Asset\" --splash boot.png -i icon.ico main.py -y -n \"MIDI-MCSTRUCTURE_NEXT\"").wait()

assert ONE_FILE or not input("Continue?")


with tarfile.open(f"dist/MIDI-MCSTRUCTURE_NEXT_{TITLE}.tar.zst", "w:zst", options=options) as io:
    io.add("dist/MIDI-MCSTRUCTURE_NEXT", arcname="")


edition_info = {
    "API": 3,
    "tips": input("Tips: ").replace("\\n", "\n"),
    "version": VERSION,
    "edition": EDITION,
    "download_url": f"https://gitee.com/mrdxhmagic/midi-mcstructure_next/releases/download/{TITLE}/MIDI-MCSTRUCTURE_NEXT_{TITLE}.tar.zst",
    "description_url": f"https://gitee.com/mrdxhmagic/midi-mcstructure_next/releases/tag/{TITLE}"
}

print(TITLE)

with open("update.json", "rb") as io:
    update_log = json.loads(io.read())

for n in range(len(update_log)):
    if update_log[n]["API"] != edition_info["API"]:
        pass
    elif update_log[n]["version"] != edition_info["version"]:
        pass
    elif update_log[n]["edition"] == edition_info["edition"]:
        update_log[n] = edition_info
        break
else:
    update_log.append(edition_info)

with open("update.json", "w", encoding="utf-8") as io:
    io.write(json.dumps(update_log, indent=2))
