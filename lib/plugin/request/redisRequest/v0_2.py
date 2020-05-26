# -*- coding: utf-8 -*-

"""
Redis请求插件
    功能简述：
        支持自定义操作的连接池，支持执行mysql语句，支持将结果保存并参数化
        语句执行结果暂时不作限制，测试任务可使用内存由进程去管控，超过限制直接杀进程

    实现逻辑：
        根据连接池名称，至总参数化存储实例获取连接池，然后获取连接，执行并获取数据

    需求入参：
        {
            "pool":"...",
                连接池名称，可为空。未填写则该报错报错，填写了但没有这个参数则该报错报错
            "command":"...",
                语句
            "var":"...",
                执行结果变量名
        }
"""

import time
import json
import copy
import re

from redis import StrictRedis

from lib.storage.customValueBottle import VuserDataBottle

from ..request import RequestPlugin


class RedisRequest(RequestPlugin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 添加插件自有属性
        self.request_pool_name = ''
        self.request_command = ''
        self.request_var = ''
        self.response_code = 0
        # 根据传入的数据,进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    def check_before_run(self):
        """
        初始化说明点
        1 pool:数据类型str
        2 command:数据类型str
        3 var:数据类型str.命名规则需符合规范要求
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
            # pool
            if 'pool' not in plugin_init_value or type(plugin_init_value['pool']) is not str:
                log += '连接池检查失败,原因:连接池整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            # command
            if 'command' not in plugin_init_value or type(plugin_init_value['command']) is not str:
                log += 'command语句检查失败,原因:command语句整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            # var
            if 'var' not in plugin_init_value or type(plugin_init_value['var']) is not str:
                log += '执行结果参数名检查失败,原因:执行结果参数名整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['var'] != "" and not re.match(r"(\b[_a-zA-Z][_a-zA-Z0-9.]*)", plugin_init_value['var']):
                log += '执行结果参数名检查失败,原因:执行结果参数名填写非法,请按照格式要求填写;'
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
            # pool
            self.request_pool_name = self.plugin_value['pool']
            # sql
            self.request_command = self.plugin_value['command']
            # vars
            self.request_var = self.plugin_value['var']
            return True, None

    def run_test(self):
        # 禁止直接使用原始日志
        self.plugin_run_log = copy.copy(self.plugin_base_run_log)
        # 公共日志部分
        self.plugin_run_log["id"] = self.plugin_id
        self.plugin_run_log["oid"] = self.plugin_oid
        self.plugin_run_log["wid"] = self.worker_info_id
        self.plugin_run_log["uid"] = self.vuser_index
        self.plugin_run_log["st"] = round(time.time() * 1000)
        # 运行前数据填充
        run_init_result, run_init_log = self.init_before_run()
        if run_init_result:
            self.plugin_run_log["rr_rb"] = self.request_command
            # 从参数化存储实例中获取数据库引擎
            redis_pool = self.run_parameter_controller.get(self.request_pool_name)
            if redis_pool:
                try:
                    db_connect = StrictRedis(connection_pool=redis_pool)
                    db_result = db_connect.execute_command(self.request_command)
                except Exception as e:
                    # 先把时间记录
                    self.plugin_run_log['et'] = round(time.time() * 1000)
                    self.plugin_run_log['t'] = round((self.plugin_run_log['et'] - self.plugin_run_log['st']))
                    self.plugin_run_log['s'] = False
                    # 从错误中提取错误码及错误信息
                    self.response_code = -1
                    self.plugin_run_log["c"] = self.response_code
                    self.plugin_run_log['f'] = '请求发生错误:%s;' % e
                else:
                    # 先把时间记录
                    self.plugin_run_log['et'] = round(time.time() * 1000)
                    self.plugin_run_log['t'] = round((self.plugin_run_log['et'] - self.plugin_run_log['st']))
                    self.plugin_run_log['s'] = True
                    """
                    redis常见返回值
                    b'OK' : bytes(utf8适用)
                    ... : int
                    b'...' : bytes(utf8不适用)
                    [b'...'] : list(utf8适用)
                    b'...' : bytes(utf8适用)
                    None
                    [b'...', None] : list(bytes(utf8适用)/None)
                    [b'...1', b'...2'](长度固定为2)
                    [b'subscribe', b'redisChat', 1] list(utf8适用)
                    [b'...'] : list(utf8适用)(目前仅知深度为2)
                    exception
                    """
                    if self.request_var != "":
                        # 将数据以{参数名: {协程/线程号1: 参数值1, 协程/线程号2: 参数值2}}的形式存储进总参数存储实例
                        if type(self.run_parameter_controller.get(self.request_var)) is VuserDataBottle:
                            self.run_parameter_controller.get(self.request_var).update({self.vuser_index: db_result})
                        else:
                            v = VuserDataBottle()
                            v.update({self.vuser_index: db_result})
                            self.run_parameter_controller.update({self.request_var: v})
                finally:
                    # 通用代码段
                    # 5.对自身结果作断言
                    for pa in self.plugins_assertion:
                        pa.run_test()
                    # 6.执行后置插件操作
                    for ppp in self.plugins_postprocessor:
                        ppp.run_test()
            else:
                # 连接池参数变量不存在则报错
                # 先把时间记录
                self.plugin_run_log['et'] = round(time.time() * 1000)
                self.plugin_run_log['t'] = round((self.plugin_run_log['et'] - self.plugin_run_log['st']))
                self.plugin_run_log['s'] = False
                self.response_code = -1
                self.plugin_run_log["c"] = self.response_code
                self.plugin_run_log['f'] = '请求发生错误:连接池未定义;'
        else:
            # 先把时间记录
            self.plugin_run_log['et'] = round(time.time() * 1000)
            self.plugin_run_log['t'] = round((self.plugin_run_log['et'] - self.plugin_run_log['st']))
            self.plugin_run_log['s'] = False
            self.response_code = -1
            self.plugin_run_log["c"] = self.response_code
            self.plugin_run_log['f'] = '请求发生错误:%s;' % run_init_log

        # 调用方法将运行日志暂存至日志控制器
        self.run_log_controller.set(self.plugin_run_log)
