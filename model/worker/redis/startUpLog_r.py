# -*- coding: utf-8 -*-

import json

from handler.pool.redisPool import redis_pool
from handler.log import app_logger


class StartUpLogR:
    def __init__(self):
        self.key = "startUpLog"

    def set(self, server_ip, startup_date, startup_flag, error_info=None):
        """
            记录启动日志
            :param server_ip: 注册服务器的ip地址
            :param startup_date: 启动日期
            :param startup_flag: 启动与注册结果状态
            :param error_info: 启动与注册错误信息，若成功则不记录
            :return: data: True/False
        """
        try:
            value = json.dumps(
                {
                    "server_ip": server_ip,
                    "date": startup_date,
                    "flag": startup_flag,
                    "error_info": error_info,
                },
                ensure_ascii=False
            )
            redis_pool.lpush(self.key, value)
        except Exception as e:
            msg = "startUpLog程序启动日志入库失败:" + repr(e)
            app_logger.error(msg)
            return False
        else:
            msg = "startUpLog程序启动日志入库成功"
            app_logger.debug(msg)
            return True
