import os
import time
import json
import pygame
import shutil
import tarfile
import subprocess
from tools import get_color
from compression.zstd import CompressionParameter

if os.path.exists("dist"): shutil.rmtree("dist")
os.mkdir("dist")

with open("Asset/text/setting.json", "rb") as io:
    setting = json.loads(io.read())

VERSION = setting["version"]
EDITION = setting["edition"]

TITLE = f"V{VERSION}-{EDITION}"


pygame.font.init()

root = pygame.Surface((760, 450))
font = pygame.font.Font("Resource/minecraft.ttf", 32)
background = pygame.transform.gaussian_blur(pygame.image.load("Asset/image/default_menu_background.png"), 24)

font.set_linesize(40)

icon = pygame.Surface((450, 450))
qq_bg = pygame.Surface((800, 450))

for x in range(qq_bg.size[0]):
    for y in range(qq_bg.size[1]):
        qq_bg.set_at((x, y), tuple(map(lambda i: i * (x / (qq_bg.size[0] - 1)) * (1 - (y / (qq_bg.size[1] - 1))), background.get_at((x, y)))))


for x in range(icon.size[0]):
    for y in range(icon.size[1]):
        icon.set_at((x, y), tuple(map(lambda i: i * (x / (icon.size[0] - 1)) * (1 - (y / (icon.size[1] - 1))), background.get_at((x, y)))))


icon.blit(pygame.transform.scale(pygame.image.load("icon.png"), (360, 360)), (45, 45))
qq_bg.blit(pygame.image.load("Asset/image/logo.png"), ((qq_bg.size[0] - 560) // 2, (qq_bg.size[1] - 64) // 2))

pygame.image.save(qq_bg, "dist/background.png")
pygame.image.save(icon, "dist/qq_icon.png")


for x in range(root.size[0]):
    for y in range(root.size[1]):
        root.set_at((x, y), tuple(map(lambda i: i * (x / (root.size[0] - 1)) * (1 - (y / (root.size[1] - 1))), background.get_at((x + 20, y)))))

text_surf = font.render(f"V{setting["version"] // 1000000}\n{setting["version"] % 1000000}", True, get_color(pygame.image.load("Asset/image/default_menu_background.png")))

offset = [float("INF"), 0]

for x in range(text_surf.size[0]):
    for y in range(text_surf.size[1]):
        if text_surf.get_at((x, y))[3] != 0:
            if offset[0] > x:
                offset[0] = x

            if offset[1] < y:
                offset[1] = y

offset = (offset[0], offset[1])

root.blit(pygame.image.load("Asset/image/logo.png"), ((root.size[0] - 560) // 2, (root.size[1] - 64) // 2))
root.blit(text_surf, (40 - offset[0], root.size[1] - 40 - offset[1]))

pygame.image.save(root, "dist/boot.png")




options = {
    CompressionParameter.compression_level: CompressionParameter.compression_level.bounds()[1],
    CompressionParameter.checksum_flag: True
}




shutil.copytree("Asset", "dist/Asset")
with open("dist/Asset/text/setting.json", "rb") as io:
    setting = json.loads(io.read())

setting["log_level"] = 4
setting["ask_mapping"] = False
setting["remove_chord"] = True
setting["channels_num"] = 64
setting["compression_level"] = 0
setting["disable_update_check"] = False

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

subprocess.Popen(f".venv/Scripts/pyinstaller.exe -D -w --optimize 2 --splash dist/boot.png -i icon.ico main.py -y -n \"MIDI-MCSTRUCTURE_NEXT\"").wait()

shutil.copytree("dist/Asset", "dist/MIDI-MCSTRUCTURE_NEXT/Asset")


assert input("Continue?")


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
