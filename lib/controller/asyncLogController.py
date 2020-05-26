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


class AsyncLogController(LogController):
    def __init__(self, table, task_id, key_word):
        super().__init__(table)
        sys_logger.debug('实例初始化开始')
        self._continue = True
        # 将测试任务基础数据转换为多个变量
        # 基础数据校验在server接收数据的时候就要做好，本处无需再做
        self.task_id = task_id
        self.key_word = key_word
        """
        日志控制器内部维护
        1.异步的、定时(根据配置文件)检查日志暂存条目数、定量(根据配置文件)地将日志条目发送给日志存储服务
        2.一个队列，用来暂存日志条目。队列线程安全
        """
        self.log_temporary_storage = []
        self.log_check_time_interval = app_config.getint("log", "interval")
        self.log_send_item_num = app_config.getint("log", "every")
        self.log_trans_timer = None
        sys_logger.debug('实例初始化结束')
        # 异步开启日志同步线程
        self.trans()

    def set(self, log):
        """
        支持传入单条log，将其添加入storage
        :param log: 单条log的内容
        :return: 本方法无返回
        """
        try:
            if type(log) is dict:
                self.log_temporary_storage.append(log)
            elif type(log) is list:
                self.log_temporary_storage += log
        except Exception as e:
            app_logger.error('暂存日志失败,原因:%s' % repr(e))
        else:
            app_logger.debug('暂存日志成功')

    def trans(self):
        """
        根据配置文件中的行数限制，传递日志至日志存储服务中
        :return: 本方法无返回
        """
        # 判断行数是否满足要求，不满足直接pass
        # 计算要传输的数据行数
        actual_data_rownum = len(self.log_temporary_storage)
        trans_data_rownum = self.log_send_item_num if actual_data_rownum >= self.log_send_item_num else actual_data_rownum
        self.trans_many(
            'task%d%s' % (self.task_id, self.key_word),
            self.log_temporary_storage[:trans_data_rownum]
        )
        try:
            del (self.log_temporary_storage[:trans_data_rownum])
        except Exception as e:
            app_logger.error('清除日志失败,原因:%s' % (repr(e)))
        else:
            app_logger.debug('暂存日志成功')
        if self._continue:
            self.log_trans_timer = threading.Timer(
                self.log_check_time_interval,
                self.trans
            )
            self.log_trans_timer.start()

    def cancel(self):
        # 要判断定时线程的有无与状态
        try:
            self._continue = False
            self.log_trans_timer and self.log_trans_timer.cancel()
        except Exception as e:
            app_logger.error('取消日志失败,原因:%s' % (repr(e)))
        else:
            app_logger.debug('取消日志成功')
        finally:
            # 最后一次传输日志内容
            self.trans_many(
                'task%d%s' % (self.task_id, self.key_word),
                self.log_temporary_storage
            )
