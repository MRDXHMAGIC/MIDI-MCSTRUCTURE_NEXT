import pygame
from tools import round_45

def to_tuple(_list: list) -> tuple:
    return tuple((to_tuple(_i) if isinstance(_i, list) or isinstance(_i, tuple) else _i) for _i in _list)

class UIManager:
    __font_cache: dict[int, pygame.font.Font] = {}
    __surf_cache: dict[str, pygame.Surface] = {}

    def __init__(self, _size: tuple[int] = (800, 450)) -> None:
        self.display_size: tuple[int] = _size

        self.__window_offset = (0, 0)
        self.__window_size = _size
        self.__font_path = ""
        self.__resource: dict[str, pygame.Surface] = {}

    def __get_surf(self, _arguments: tuple[tuple[int]]) -> pygame.Surface:
        if not self.__surf_cache: return pygame.Surface(self.display_size).convert_alpha()
        # Arguments format: ((label_length, label_height, position_x, position_y), (label_length, label_height, position_x, position_y))
        if _arguments not in self.__surf_cache:
            _base_surf: pygame.Surface = self.__surf_cache["blur"].copy()
            _mask_surf: pygame.Surface = self.__surf_cache["background"].copy()
            for _label in _arguments:
                _label_surf: pygame.Surface = pygame.Surface(_label[2:4]).convert_alpha()
                _label_surf.fill((255, 255, 255, 0))
                _label_surf.blits((
                (self.__resource["corner_0"], (0, 0)),
                (self.__resource["corner_1"], (0, _label[3] - self.__resource["corner_3"].get_size()[1])),
                (self.__resource["corner_2"], (_label[2] - self.__resource["corner_2"].get_size()[0], _label[3] - self.__resource["corner_2"].get_size()[1])),
                (self.__resource["corner_3"], (_label[2] - self.__resource["corner_1"].get_size()[0], 0))
                ))
                _mask_surf.blit(_label_surf, (_label[0] + self.__window_offset[0], _label[1] + self.__window_offset[1]), special_flags=pygame.BLEND_RGBA_MULT)
            _base_surf.blit(_mask_surf, (0, 0))
            self.__surf_cache[_arguments] = _base_surf
        return self.__surf_cache[_arguments].copy()

    def add_resource(self, *, _font_path, _background_surf: pygame.Surface, _corner_surf: pygame.Surface, _blur_surf: pygame.Surface) -> None:
        self.__font_path  =_font_path
        for _n in range(4):
            self.__resource["corner_" + str(_n)] = pygame.transform.rotate(_corner_surf, _n * 90).convert_alpha()

        self.__resource["background"] = _background_surf.copy()
        self.__resource["blur"] = _blur_surf.copy()

        self.change_size(self.display_size)

    def change_size(self, _size: tuple[int]) -> None:
        self.display_size = _size
        self.__surf_cache.clear()

        _surf_size = self.__resource["blur"].get_size()
        if _surf_size[0] / _surf_size[1] > _size[0] / _size[1]:
            _target_size = (round_45((_size[1] / _surf_size[1]) * _surf_size[0]), _size[1])
        else:
            _target_size = (_size[0], round_45((_size[0] / _surf_size[0]) * _surf_size[1]))
        _background = pygame.transform.smoothscale(self.__resource["blur"], _target_size)
        _background = _background.subsurface(pygame.Rect((round_45((_target_size[0] - _size[0]) / 2), round_45((_target_size[1] - _size[1]) / 2), _size[0], _size[1])))

        _surf_size = self.__resource["background"].get_size()
        if _surf_size[0] / _surf_size[1] > _size[0] / _size[1]:
            _target_size = (_size[0], round_45((_size[0] / _surf_size[0]) * _surf_size[1]))
        else:
            _target_size = (round_45((_size[1] / _surf_size[1]) * _surf_size[0]), _size[1])
        self.__window_size = _target_size
        self.__window_offset = (round_45((_size[0] - _target_size[0]) / 2), round_45((_size[1] - _target_size[1]) / 2))
        _background.blit(pygame.transform.smoothscale(self.__resource["background"], _target_size), self.__window_offset)
        _blur_surf = pygame.Surface(_size).convert_alpha()
        _blur_surf.blit(pygame.transform.smoothscale(self.__resource["blur"], _target_size), self.__window_offset)

        self.__surf_cache["background"] = _background
        self.__surf_cache["blur"] = _blur_surf

    def get_abs_position(self, _position: tuple[int], _offset: bool = False) -> tuple[int]:
        return tuple(int(round_45(_i * self.__window_size[_n % 2]) + (self.__window_offset[_n % 2] if _offset else 0)) for _n, _i in enumerate(_position))

    def get_background(self) -> pygame.Surface:
        return self.__surf_cache.get("background", pygame.Surface(self.display_size).convert_alpha()).copy()

    def get_blur_background(self, _black_background: bool = False) -> pygame.Surface:
        _root = pygame.Surface(self.display_size).convert_alpha() if _black_background or "background" not in self.__surf_cache else self.__surf_cache["background"].copy()
        if "blur" in self.__surf_cache: _root.blit(self.__surf_cache["blur"].subsurface(pygame.Rect(self.get_abs_position((0, 0), True) + self.get_abs_position((1, 1)))), self.get_abs_position((0, 0), True))
        return _root

    def apply_ui(self, _arguments: tuple[tuple[int, tuple]], _mouse_position=None) -> tuple[int, pygame.Surface]:
        # Arguments format: ((label_length, label_height, position_x, position_y, (text, size, alpha), id), (label_length, label_height, position_x, position_y, (text, size, alpha), id))
        _id = -1
        _label_array = []
        _text_surf_array = []
        for _label in to_tuple(_arguments):
            _label = self.get_abs_position(_label[0:4]) + _label[4:]
            if _label[3] != 0:
                _label_array.append(_label[0:4])

            if _mouse_position is not None:
                if 0 <= _mouse_position[0] - _label[0] - self.__window_offset[0] <= _label[2] and 0 <= _mouse_position[1] - _label[1] - self.__window_offset[1] <= _label[3]:
                    _id = _label[5]

            if _label[4][0] and _label[4][2]:
                _text_size = int(round_45(_label[4][1] * self.__window_size[0]))
                if _text_size not in self.__font_cache:
                    self.__font_cache[_text_size] = pygame.font.Font(self.__font_path, _text_size)
                _text_surf = self.__font_cache[_text_size].render(_label[4][0], True, (255, 255, 255))
                _text_surf.set_alpha(_label[4][2])
                _text_surf_size = _text_surf.get_size()
                _text_surf_array.append((_text_surf, (int(round_45((_label[0] + _label[2] / 2) - _text_surf_size[0] / 2)) + self.__window_offset[0], int(round_45((_label[1] + _label[3] / 2) - _text_surf_size[1] / 2)) + self.__window_offset[1])))
        _root = self.__get_surf(tuple(_label_array))
        _root.blits(_text_surf_array)
        return _root, _id
