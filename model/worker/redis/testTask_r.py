# -*- coding: utf-8 -*-

import json

from handler.pool.redisPool import redis_pool
from handler.log import app_logger


class TestTaskR:
    def __init__(self):
        self.key = "testTask"

    def query(self, task_id):
        try:
            data = redis_pool.hget(self.key, task_id).decode()
        except Exception as e:
            msg = "redis|" + self.key + " query failed:" + repr(e)
            app_logger.error(msg)
            return None
        else:
            msg = "redis|" + self.key + " query succeed"
            app_logger.debug(msg)
            return data

    def set(self, task_id, value):
        """
            记录定时任务基础数据
            :param task_id: 测试任务id
            :param value: 任务定时执行信息
        """
        try:
            redis_pool.hset(self.key, task_id, value)
        except Exception as e:
            msg = "redis|" + self.key + " insert failed:" + repr(e)
            app_logger.error(msg)
            return False
        else:
            msg = "redis|" + self.key + " insert succeed"
            app_logger.debug(msg)
            return True
