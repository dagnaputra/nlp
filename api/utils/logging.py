# from __future__ import annotations

# import os
# import sys
# from typing import Callable

# import loguru

# loguru.logger.remove()
# loguru.logger.configure(extra={"request_id": "", "user": ""})

# if os.environ.get("LOGGER_FORMAT", "text") == "text":
#     logger_format = (
#         "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
#         "<level>{level: <8}</level> | "
#         "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
#         "{extra[request_id]} {extra[user]} - <level>{message}</level>"
#     )
#     loguru.logger.add(sys.stdout, format=logger_format)
# else:
#     logger_format = "{time} {level} {message} request_id={extra[request_id]}"
#     loguru.logger.add(sys.stdout, serialize=True, format=logger_format)


# def get_logger() -> Callable[[str], loguru.Logger]:
#     def bind_request_id(request_id: str = "") -> loguru.Logger:
#         return loguru.logger.bind(request_id=request_id)

#     return bind_request_id


# class Logger:
#     def __init__(self, request_id: str = ""):
#         self.request_id = request_id
#         self.logger = get_logger()(request_id)  # type: ignore

#     def info(self, msg: str) -> None:
#         self.logger.opt(depth=1).info(msg)

#     def debug(self, msg: str) -> None:
#         self.logger.opt(depth=1).debug(msg)

#     def error(self, msg: str) -> None:
#         self.logger.opt(depth=1).error(msg)

#     def warn(self, msg: str) -> None:
#         self.logger.opt(depth=1).warning(msg)
