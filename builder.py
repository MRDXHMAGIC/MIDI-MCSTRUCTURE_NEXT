import os
import json
import shutil
import tarfile
import subprocess
from compression.zstd import CompressionParameter


with open("Asset/text/setting.json", "rb") as io:
    setting = json.loads(io.read())

VERSION = setting["version"]
EDITION = setting["edition"]

TITLE = f"V{VERSION}-{EDITION}"


if os.path.exists("dist"): shutil.rmtree("dist")
os.mkdir("dist")


shutil.copytree("Asset", "dist/Asset")
with open("dist/Asset/text/setting.json", "rb") as io:
    setting = json.loads(io.read())

setting["log_level"] = 4
setting["disable_update_check"] = False

with open("dist/Asset/text/setting.json", "w", encoding="utf-8") as io:
    io.write(json.dumps(setting, indent=2))


if os.path.exists("dist/Asset/text/default_profile.json"): os.remove("dist/Asset/text/default_profile.json")
if os.path.exists("dist/Asset/image/custom_menu_background.png"): os.remove("dist/Asset/image/custom_menu_background.png")


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
    "version": VERSION,
    "edition": EDITION,
    "download_url": f"https://gitee.com/mrdxhmagic/midi-mcstructure_next/releases/download/{TITLE}/MIDI-MCSTRUCTURE_NEXT_{TITLE}.tar.zst",
    "description_url": f"https://gitee.com/mrdxhmagic/midi-mcstructure_next/releases/tag/{TITLE}"
}

print()

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
