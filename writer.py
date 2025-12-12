import log
import argparse
import traceback
import amulet_nbt

def get_list_position(_size, _position):
    _n = _position[2]
    _n += _position[1] * _size[2]
    _n += _position[0] * (_size[1] * _size[2])
    return _n

def check_position(_size, _position):
    if _position[0] >= _size[0] or _position[0] < 0:
        return False
    elif _position[1] >= size[1] or _position[1] < 0:
        return False
    elif _position[2] >= size[2] or _position[2] < 0:
        return False
    else:
        return True

logger = log.Logger()

try:
    args_parser = argparse.ArgumentParser(
        prog="writer",
        description="Write Minecraft Command into .mcstructure.",
        epilog="Belong to MIDI-MCSTRUCTURE NEXT Project."
    )

    args_parser.add_argument("output", type=str)
    args_parser.add_argument("-id", "--structure_id", default=0, type=int)
    args_parser.add_argument("-s", "--structure", required=True, type=str)
    args_parser.add_argument("-l", "--log_level", default=5, type=int)
    args_parser.add_argument("-c", "--command", required=True, type=str)

    args = args_parser.parse_args()

    logger.set_log_level(args.log_level)

    with open(args.command, "r", encoding="utf-8") as io:
        commands = io.read()

    delay = 0
    music_name = ""
    command_list = []
    length_of_time = 0
    for command in commands.splitlines():
        if command.startswith("# "):
            command = command[2:].split("=", 1)
            if len(command) == 2:
                if command[0] == "tick_delay":
                    delay = int(command[1])
                elif command[0] == "music_name":
                    music_name = command[1]
                elif command[0] == "length_of_time":
                    length_of_time = int(command[1])
        else:
            command_list.append((command, delay))

    structure = amulet_nbt.load(args.structure, little_endian=True, compressed=False).compound

    size = (structure["size"][0].py_int, structure["size"][1].py_int, structure["size"][2].py_int)

    logger.info("Structure Size: " + str(size[0]) + "*" + str(size[1]) + "*" + str(size[2]))

    position = [0, 0, 0]
    for n in structure["structure"]["palette"]["default"]["block_position_data"]:
        i = structure["structure"]["palette"]["default"]["block_position_data"][n]["block_entity_data"]
        if i["CustomName"].py_str == "start":
            position = [i["x"].py_int - structure["structure_world_origin"][0].py_int,
                        i["y"].py_int - structure["structure_world_origin"][1].py_int,
                        i["z"].py_int - structure["structure_world_origin"][2].py_int]

            logger.debug("Set Position: " + str(position[0]) + " " + str(position[1]) + " " + str(position[2]))
        elif i["CustomName"].py_str == "append":
            i["Command"] = amulet_nbt.StringTag(i["Command"].py_str.replace("__ADDRESS__", str(args.structure_id)).replace("__TOTAL__", str(length_of_time)).replace("__NAME__", music_name))
        i["CustomName"] = amulet_nbt.StringTag("")

    n = 0
    for n, i in enumerate(structure["structure"]["palette"]["default"]["block_palette"]):
        if i["name"].py_str == "minecraft:air":
            air_palette = n
            break
    else:
        air_palette = n + 1
        structure["structure"]["palette"]["default"]["block_palette"].append(
            amulet_nbt.CompoundTag({
                "name": amulet_nbt.StringTag("minecraft:air"),
                "states": amulet_nbt.CompoundTag(),
                "val": amulet_nbt.ShortTag(0),
                "version": amulet_nbt.IntTag(18090528)
            })
        )

    for command, delay in command_list:
        n = str(get_list_position(size, position))
        if n in structure["structure"]["palette"]["default"]["block_position_data"] and check_position(size, position):
            structure["structure"]["palette"]["default"]["block_position_data"][n]["block_entity_data"]["Command"] = amulet_nbt.StringTag(command)
            structure["structure"]["palette"]["default"]["block_position_data"][n]["block_entity_data"]["TickDelay"] = amulet_nbt.IntTag(delay)
            direct = structure["structure"]["palette"]["default"]["block_palette"][structure["structure"]["block_indices"][0][get_list_position(size, position)].py_int]["states"]["facing_direction"].py_int
            if direct == 0:
                position[1] -= 1
            elif direct == 1:
                position[1] += 1
            elif direct == 2:
                position[2] -= 1
            elif direct == 3:
                position[2] += 1
            elif direct == 4:
                position[0] -= 1
            elif direct == 5:
                position[0] += 1
        else:
            break

    while True:
        n = str(get_list_position(size, position))
        direct = structure["structure"]["palette"]["default"]["block_palette"][structure["structure"]["block_indices"][0][get_list_position(size, position)].py_int]["states"]["facing_direction"].py_int
        if direct == 0:
            position[1] -= 1
        elif direct == 1:
            position[1] += 1
        elif direct == 2:
            position[2] -= 1
        elif direct == 3:
            position[2] += 1
        elif direct == 4:
            position[0] -= 1
        elif direct == 5:
            position[0] += 1
        if structure["structure"]["palette"]["default"]["block_position_data"][n]["block_entity_data"]["Command"].py_str == "":
            del structure["structure"]["palette"]["default"]["block_position_data"][n]
            structure["structure"]["block_indices"][0][int(n)] = amulet_nbt.IntTag(air_palette)
            structure["structure"]["block_indices"][1][int(n)] = amulet_nbt.IntTag(-1)
        if not check_position(size, position):
            break

    amulet_nbt.TAG_Compound(structure).save_to(args.output, little_endian=True, compressed=False)
except:
    logger.fatal(traceback.format_exc())
finally:
    logger.done()