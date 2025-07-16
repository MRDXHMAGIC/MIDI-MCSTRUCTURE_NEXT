import pynbt

def list_position(_size, _position):
    _n = _position[2]
    _n += _position[1] * _size[2]
    _n += _position[0] * (_size[1] * _size[2])
    return _n

def check(_size, _position):
    if _position[0] >= _size[0] or _position[0] < 0:
        return False
    elif _position[1] >= size[1] or _position[1] < 0:
        return False
    elif _position[2] >= size[2] or _position[2] < 0:
        return False
    else:
        return True

delay = 0
music_name = ""
structure_id = 0
length_of_time = 0

with open("Cache/convertor/raw_command.txt", "r", encoding="utf-8") as io:
    for command in io.read().splitlines():
        if command[:2] == "# ":
            command = command[2:].split("=", 1)
            if len(command) == 2:
                if command[0] == "tick_delay":
                    delay = int(command[1])
                elif command[0] == "music_name":
                    music_name = command[1]
                elif command[0] == "structure_id":
                    structure_id = int(command[1])
                elif command[0] == "length_of_time":
                    length_of_time = int(command[1])
                elif command[0] == "structure_path":
                    structure = pynbt.NBTFile(open(command[1], "rb"), little_endian=True)
                    position = [0, 0, 0]
                    size = (structure["size"][0].value, structure["size"][1].value, structure["size"][2].value)

                    for n in structure["structure"]["palette"]["default"]["block_position_data"]:
                        i = structure["structure"]["palette"]["default"]["block_position_data"][n]["block_entity_data"]
                        if i["CustomName"].value == "start":
                            position = [i["x"].value - structure["structure_world_origin"][0].value,
                                        i["y"].value - structure["structure_world_origin"][1].value,
                                        i["z"].value - structure["structure_world_origin"][2].value]
                        elif i["CustomName"].value == "append":
                            i["Command"] = pynbt.TAG_String(i["Command"].value.replace("__ADDRESS__", str(structure_id)).replace("__TOTAL__", str(length_of_time)).replace("__NAME__", music_name))
                        i["CustomName"] = pynbt.TAG_String("")

                    n = 0
                    air_palette = -1
                    for n, i in enumerate(structure["structure"]["palette"]["default"]["block_palette"]):
                        if i["name"].value == "minecraft:air":
                            air_palette = n
                            break
                    if air_palette == -1:
                        air_palette = n + 1
                        structure["structure"]["palette"]["default"]["block_palette"].append(
                            pynbt.TAG_Compound({
                                "name": pynbt.TAG_String("minecraft:air"),
                                "states": pynbt.TAG_Compound(),
                                "val": pynbt.TAG_Short(0),
                                "version": pynbt.TAG_Int(18090528)
                            })
                        )
        else:
            n = str(list_position(size, position))
            if structure["structure"]["palette"]["default"]["block_position_data"].get(n) and check(size, position):
                structure["structure"]["palette"]["default"]["block_position_data"][n]["block_entity_data"]["Command"] = pynbt.TAG_String(command)
                structure["structure"]["palette"]["default"]["block_position_data"][n]["block_entity_data"]["TickDelay"] = pynbt.TAG_Int(delay)
                direct = structure["structure"]["palette"]["default"]["block_palette"][structure["structure"]["block_indices"][0][list_position(size, position)].value]["states"]["facing_direction"].value
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
    n = str(list_position(size, position))
    direct = structure["structure"]["palette"]["default"]["block_palette"][structure["structure"]["block_indices"][0][list_position(size, position)].value]["states"]["facing_direction"].value
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
    if structure["structure"]["palette"]["default"]["block_position_data"][n]["block_entity_data"]["Command"].value == "":
        del structure["structure"]["palette"]["default"]["block_position_data"][n]
        structure["structure"]["block_indices"][0][int(n)] = pynbt.TAG_Int(air_palette)
        structure["structure"]["block_indices"][1][int(n)] = pynbt.TAG_Int(-1)
    if not check(size, position):
        break

with open("Cache/convertor/structure.mcstructure", "wb") as io:
    structure.save(io, little_endian=True)
