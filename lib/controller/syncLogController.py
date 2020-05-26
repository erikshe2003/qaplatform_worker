# -*- coding: utf-8 -*-

"""
测试插件运行时的日志控制器
1个测试任务内部包含1个日志控制器，不同的测试任务之间，日志控制器不共享
！！！别忘了，测试任务结束时判断一下队列中还有没有没法送的日志，有的话最后发送一次，不要缺
"""

import threading

from lib.controller.logController import LogController

from handler.log import sys_logger, app_logger
from handler.config import app_config


class SyncLogController(LogController):
    def __init__(self, table, task_id, key_word):
        super().__init__(table)
        sys_logger.debug('实例初始化开始')
        self._continue = True
        # 将测试任务基础数据转换为多个变量
        # 基础数据校验在server接收数据的时候就要做好，本处无需再做
        self.task_id = task_id
        self.key_word = key_word
        sys_logger.debug('实例初始化结束')

    def trans(self, log):
        """
        根据配置文件中的行数限制，传递日志至日志存储服务中
        :param log: log的内容，可以是单条也可以是多条
        :return: 本方法无返回
        """
        if type(log) is str:
            self.trans_one('task%d%s' % (self.task_id, self.key_word), {'log': log})
        elif type(log) is dict:
            self.trans_one('task%d%s' % (self.task_id, self.key_word), log)
        elif type(log) is list:
            self.trans_many('task%d%s' % (self.task_id, self.key_word), log)
