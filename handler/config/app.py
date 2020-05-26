# -*- coding: utf-8 -*-

import configparser

from handler.log import sys_logger


app_config = configparser.ConfigParser()
msg = "准备读取环境配置文件生成配置对象"
sys_logger.info(msg)
try:
    app_config.read(filenames="config/app.ini", encoding="utf-8")
    msg = "环境配置文件读取成功，成功生成配置对象"
    sys_logger.debug(msg)
except Exception as e:
    msg = "环境配置文件读取失败，失败原因：" + repr(e)
    sys_logger.error(msg)
    raise e
else:
    """
    检查app.ini内各项内容是否符合填写要求
    log: interval/every
    """
    try:
        app_config.getint('log', 'interval')
        app_config.getint('log', 'every')
    except Exception as e:
        sys_logger.error(repr(e))
        raise e
