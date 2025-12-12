import time
import queue
import threading

class Logger:
    def __init__(self, _log_level: int = 5) -> None:
        self.__info = [False]
        self.__log_level = _log_level
        self.__log_queue = queue.Queue()
        self.__log_thread = threading.Thread(target=logger, args=[self.__info, self.__log_queue])
    def __log_info(self, _header: str, _text: str) -> None:
        if not isinstance(_text, str):
            raise TypeError("Information Must be str!")
        if not self.__log_thread.is_alive():
            self.__log_thread.start()
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
        if self.__log_thread.is_alive():
            self.__info[0] = True
            self.__log_thread.join()

def logger(_info: list[bool], _queue: queue.Queue[tuple[str]]) -> None:
    while True:
        while _queue.empty():
            if _info[0]: return
            time.sleep(0.1)

        _time = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
        with open("log.txt", "a", encoding="utf-8") as _io:
            while True:
                # 如果一段时间内没有日志就保存文件
                for _ in range(3):
                    # 退出计时循环
                    if not _queue.empty(): break
                    time.sleep(0.1)
                else:
                    # 如果计时结束就退出写入日志循环
                    break

                # 写入日志内容
                _text: tuple[str] = _queue.get()
                _header = _text[0] + " " + _time
                _io.writelines(((_header if _n == 0 else " " * len(_header)) + " | " + _i + "\n") for _n, _i in enumerate(_text[1].splitlines()))
