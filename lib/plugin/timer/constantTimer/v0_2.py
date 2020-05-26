# -*- coding: utf-8 -*-

"""
固定延时器插件
    功能简述：
        在插件之间实现延时,时间固定

    实现逻辑：
        使用gevent提供的sleep方法实现延时

    需求入参：
        {
            "time": 0
                延时ms数
        }
"""

import json
import gevent

from ..timer import TimerPlugin

from handler.scheduler import kill_test_task_job


class ConstantTimer(TimerPlugin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 添加插件自有属性
        self.time_wait = 0
        # 根据传入的数据,进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    def check_before_run(self):
        """
        初始化说明点
        1 time:数据类型int
        :return: (False, log)/(True, None)
        """
        log = ''
        check_flag = True

        try:
            plugin_init_value = json.loads(self.plugin_init_value_str)
        except Exception as e:
            log += '数据整体检查失败,原因:%s;' % repr(e)
            check_flag = False
        else:
            # time
            if 'time' not in plugin_init_value or type(plugin_init_value['time']) is not int:
                log += '延时时间检查失败,原因:延时时间整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['time'] < 0:
                log += '延时时间检查失败,原因:延时时间请填写正整数;'
                check_flag = False
        finally:
            if not check_flag:
                return False, log
            else:
                return True, None

    def init_before_run(self):
        # 参数化处理
        plugin_value_str = self.parameters_replace(self.plugin_init_value_str)

        # 预处理
        try:
            self.plugin_value = json.loads(plugin_value_str)
        except Exception as e:
            return False, '运行前插件原始数据预处理失败:%s;' % repr(e)
        else:
            # time
            self.time_wait = self.plugin_value['time']

        return True, None

    def run_test(self):
        # 运行前数据填充
        run_init_result, run_init_log = self.init_before_run()
        if run_init_result:
            gevent.sleep(self.time_wait/1000)
        else:
            # 如果失败强行终止测试任务运行
            self.trans_init_log(run_init_log)
            kill_test_task_job(self.base_data)
