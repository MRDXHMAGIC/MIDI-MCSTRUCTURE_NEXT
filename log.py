import time
import queue
import threading

class Logger:
    def __init__(self, _log_level: int = 5) -> None:
        self.__log_level = _log_level
        self.__log_queue = queue.SimpleQueue()
        self.__thread = threading.Thread(target=logger, args=[self.__log_queue])
        self.__thread.start()
    def __log_info(self, _header: str, _text: str) -> None:
        if not isinstance(_text, str):
            raise TypeError("Information Must be str!")
        self.__log_queue.put((_header, _text))
    def set_log_level(self, _level: int):
        self.__log_level = _level
    def fatal(self, _text: str) -> None:
        if self.__log_level >= 1:
            self.__log_info("[F]", _text)
    def error(self, _text: str) -> None:
        if self.__log_level >= 2:
            self.__log_info("[E]", _text)
    def warn(self, _text: str) -> None:
        if self.__log_level >= 3:
            self.__log_info("[W]", _text)
    def info(self, _text: str) -> None:
        if self.__log_level >= 4:
            self.__log_info("[I]", _text)
    def debug(self, _text: str) -> None:
        if self.__log_level >= 5:
            self.__log_info("[D]", _text)
    def done(self) -> None:
        self.__log_info("[DONE]", "")
        self.__thread.join()

def logger(_queue: queue.SimpleQueue[tuple[str]]) -> None:
    while True:
        _text = _queue.get()
        if _text[0] == "[DONE]":
            break
        _header = _text[0] + " " + time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
        with open("log.txt", "a", encoding="utf-8") as _io:
                _io.writelines(((_header if _n == 0 else " " * len(_header)) + " | " + _i + "\n") for _n, _i in enumerate(_text[1].splitlines()))
