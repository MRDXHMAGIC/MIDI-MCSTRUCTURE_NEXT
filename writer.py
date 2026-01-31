import io
import amulet_nbt
from zlib import crc32
from tools import get_list_position, check_position

class Position:
    def __init__(self, _position: tuple[int] = (0, 0, 0)) -> None:
        self.__x = _position[0]
        self.__y = _position[1]
        self.__z = _position[2]

        self.max_size = [0, 0, 0]

    @property
    def x(self) -> int:
        return self.__x

    @x.setter
    def x(self, _value: int):
        self.__x = _value
        self.max_size[0] = max(self.max_size[0], _value)

    @property
    def y(self) -> int:
        return self.__y

    @y.setter
    def y(self, _value: int):
        self.__y = _value
        self.max_size[1] = max(self.max_size[1], _value)

    @property
    def z(self) -> int:
        return self.__z

    @z.setter
    def z(self, _value: int):
        self.__z = _value
        self.max_size[2] = max(self.max_size[2], _value)

    def list_pos(self, _size: tuple[int]) -> int:
        return get_list_position(_size, self)

def change_pos(_position: Position, _direction: int) -> Position:
    if _direction == 0:
        _position.y -= 1
    elif _direction == 1:
        _position.y += 1
    elif _direction == 2:
        _position.z -= 1
    elif _direction == 3:
        _position.z += 1
    elif _direction == 4:
        _position.x -= 1
    elif _direction == 5:
        _position.x += 1

def write_cmd(_task) -> io.FileIO:
    _structure = amulet_nbt.load(_task["structure"], little_endian=True, compressed=False).compound

    _size = (_structure["size"][0].py_int, _structure["size"][1].py_int, _structure["size"][2].py_int)

    _position = Position()
    for _n in _structure["structure"]["palette"]["default"]["block_position_data"].keys():
        _i = _structure["structure"]["palette"]["default"]["block_position_data"][_n]["block_entity_data"]
        if _i["CustomName"].py_str == "start":
            _position = Position((
                _i["x"].py_int - _structure["structure_world_origin"][0].py_int,
                _i["y"].py_int - _structure["structure_world_origin"][1].py_int,
                _i["z"].py_int - _structure["structure_world_origin"][2].py_int
            ))

        elif _i["CustomName"].py_str == "append":
            _cmd = _i["Command"].py_str
            for _k, _v in _task["map"]:
                _cmd = _cmd.replace(_k, _v)
            _i["Command"] = amulet_nbt.StringTag(_cmd)

        _i["CustomName"] = amulet_nbt.StringTag("")

    _n = 0
    for _n, _i in enumerate(_structure["structure"]["palette"]["default"]["block_palette"]):
        if _i["name"].py_str == "minecraft:air":
            _air_palette = _n
            break
    else:
        _air_palette = _n + 1
        _structure["structure"]["palette"]["default"]["block_palette"].append(
            amulet_nbt.CompoundTag({
                "name": amulet_nbt.StringTag("minecraft:air"),
                "states": amulet_nbt.CompoundTag(),
                "val": amulet_nbt.ShortTag(0),
                "version": amulet_nbt.IntTag(18090528)
            })
        )

    for _delay, _command in _task["cmd_list"]:
        if not check_position(_size, _position): break

        if _block_data := _structure["structure"]["palette"]["default"]["block_position_data"].get(str(_position.list_pos(_size))):
            _block_data["block_entity_data"]["Command"] = amulet_nbt.StringTag(_command)
            _block_data["block_entity_data"]["TickDelay"] = amulet_nbt.IntTag(_delay)
            change_pos(_position, _structure["structure"]["palette"]["default"]["block_palette"][_structure["structure"]["block_indices"][0][_position.list_pos(_size)].py_int]["states"]["facing_direction"].py_int)
        else:
            break

    while check_position(_size, _position):
        _n = _position.list_pos(_size)

        change_pos(_position, _structure["structure"]["palette"]["default"]["block_palette"][_structure["structure"]["block_indices"][0][_position.list_pos(_size)].py_int]["states"]["facing_direction"].py_int)

        if _structure["structure"]["palette"]["default"]["block_position_data"][str(_n)]["block_entity_data"]["Command"].py_str == "":
            del _structure["structure"]["palette"]["default"]["block_position_data"][str(_n)]
            _structure["structure"]["block_indices"][0][_n] = amulet_nbt.IntTag(_air_palette)
            _structure["structure"]["block_indices"][1][_n] = amulet_nbt.IntTag(-1)

    _buffer = _structure.to_nbt(little_endian=True, compressed=False)


    return hex(crc32(_buffer) & 0xFFFFFFFF)[2:].upper(), _buffer