# -*- coding: utf-8 -*-

from configparser import ConfigParser
from handler.log import sys_logger


database_config = ConfigParser()
msg = "准备读取数据库配置文件生成配置对象"
sys_logger.info(msg)
try:
    database_config.read(filenames="config/database.ini", encoding="utf-8")
    msg = "数据库配置文件读取成功，成功生成配置对象"
    sys_logger.debug(msg)
except Exception as e:
    msg = "数据库配置文件读取失败，失败原因：" + repr(e)
    sys_logger.error(msg)
    raise RuntimeError(msg)
