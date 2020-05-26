# -*- coding: utf-8 -*-

import logging
from logging.config import fileConfig


try:
    # 加载配置文件
    fileConfig("config/log.ini")
    # 创建日志记录器,并加入文本日志处理器
    app_logger = logging.getLogger("app")
    sys_logger = logging.getLogger("sys")
    msg = "日志配置文件读取成功，成功生成日志记录器"
    sys_logger.debug(msg)
except Exception as e:
    msg = "日志配置文件读取失败，失败原因：" + repr(e)
    raise RuntimeError(msg)
