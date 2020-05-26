# -*- coding: utf-8 -*-

"""
测试插件运行时的日志控制器基类
"""

from pymongo import MongoClient

from handler.log import app_logger
from handler.config import database_config


class LogController:
    def __init__(self, table):
        self.log_table = table
        self.log_pool = None
        self.log_pool_table = None
        self.log_pool_make_result, self.log_pool_make_msg = self.make_log_pool()

    def trans_one(self, c_name, log):
        try:
            collection = self.log_pool_table[c_name]
            collection.insert_one(log)
        except Exception as e:
            app_logger.error('mongodb写入日志失败,原因:%s' % repr(e))
            return False
        else:
            app_logger.debug('mongodb写入日志成功')
            return True

    def trans_many(self, c_name, logs):
        try:
            collection = self.log_pool_table[c_name]
            collection.insert_many(logs)
        except Exception as e:
            app_logger.error('mongodb写入日志失败,原因:%s' % repr(e))
            return False
        else:
            app_logger.debug('mongodb写入日志成功')
            return True

    def make_log_pool(self):
        try:
            self.log_pool = MongoClient(
                host=database_config.get("logMongodb", "host"),
                port=int(database_config.get("logMongodb", "port")),
                maxPoolSize=100
            )
            self.log_pool_table = self.log_pool[self.log_table]
            self.log_pool_table.authenticate(
                database_config.get("logMongodb", "username"),
                database_config.get("logMongodb", "password")
            )
        except Exception as e:
            msg = "mongodb连接池初始化失败，失败原因：" + repr(e)
            app_logger.error(msg)
            return False, repr(e)
        else:
            msg = "mongodb连接池初始化成功"
            app_logger.debug(msg)
            return True, None
