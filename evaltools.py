def generate_legacy_nodes(_nodes: tuple[int]) -> tuple[int, tuple[int]]:
    _legacy_nodes = [[None, min(_nodes) - 2]]
    for _n in filter(lambda _i: _i not in _nodes, range(min(_nodes) - 1, max(_nodes) + 1)):
        if _legacy_nodes[-1][1] + 1 == _n:
            _legacy_nodes[-1][1] += 1
        else:
            _legacy_nodes.append([_n, _n])

    return tuple((_i[0] if _i[0] == _i[1] else tuple(_i) for _i in _legacy_nodes)) + ((max(_nodes) + 1, None),)

def join_nodes(_nodes: tuple[int]) -> tuple[int, tuple[int]]:
    _result = [[min(_nodes)] * 2]

    for _n in sorted(_nodes)[1:]:
        if _result[-1][1] + 1 == _n:
            _result[-1][1] += 1
        else:
            _result.append([_n] * 2)

    return tuple((_i[0] if _i[0] == _i[1] else tuple(_i) for _i in _result))

def map_nodes(_nodes: tuple[int, tuple[int]], _format: str) -> tuple[str]:
    return tuple(map(lambda _i: _format.replace("{VALUE}", f"{"" if _i[0] is None else _i[0]}..{"" if _i[1] is None else _i[1]}") if isinstance(_i, (tuple, list)) else _format.replace("{VALUE}", str(_i)), _nodes))
