# -*- coding: utf-8 -*-

"""
Mysql请求插件
    功能简述：
        支持自定义操作的连接池，支持执行mysql语句，支持将结果保存并参数化
        sql执行结果暂时不作限制，测试任务可使用内存由进程去管控，超过限制直接杀进程

    实现逻辑：
        根据连接池名称，至总参数化存储实例获取连接池，然后获取连接，执行并获取数据

    需求入参：
        {
            "pool":"...",
                连接池名称，可为空。未填写则该报错报错，填写了但没有这个参数则该报错报错
            "sql":"...",
                SQL语句
            # "result":"abcde",
            #     执行结果保存参数变量名
            "vars":"abc,bcd,cde",
                执行结果按列拆分后的每列变量名
        }
"""

import time
import json
import copy
import re
import pandas
import numpy

from ..request import RequestPlugin

from lib.storage.customValueBottle import VuserDataBottle

from pymysql.err import ProgrammingError


class MysqlRequest(RequestPlugin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 添加插件自有属性
        self.request_pool_name = ''
        self.request_sql = ''
        self.request_vars = ''
        self.request_vars_list = []
        self.response_code = 0
        # 根据传入的数据,进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    @staticmethod
    def check_var_names(names):
        # 变量名称需符合填写规范
        for ns in names.split(','):
            if not re.match(r"(\b[_a-zA-Z][_a-zA-Z0-9.]*)", ns):
                return False
        return True

    def check_before_run(self):
        """
        初始化说明点
        1 pool:数据类型str
        2 sql:数据类型str
        3 vars:数据类型str.各个参数变量名命名规则需符合规范要求
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
            # sql
            if 'sql' not in plugin_init_value or type(plugin_init_value['sql']) is not str:
                log += 'SQL语句检查失败,原因:SQL语句整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            # vars
            if 'vars' not in plugin_init_value or type(plugin_init_value['vars']) is not str:
                log += '参数名称检查失败,原因:参数名称整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['vars'] != "" and not self.check_var_names(plugin_init_value['vars']):
                log += '参数名称检查失败,原因:参数名称填写非法,请按照格式要求填写;'
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
            self.request_sql = self.plugin_value['sql']
            # vars
            self.request_vars = self.plugin_value['vars']
            self.request_vars_list = self.plugin_value['vars'].split(',')
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
            self.plugin_run_log["mr_rb"] = self.request_sql
            # 从参数化存储实例中获取数据库引擎
            db_engine = self.run_parameter_controller.get(self.request_pool_name)
            if db_engine:
                try:
                    db_connect = db_engine.connect()
                    db_proxy = db_connect.execute(self.request_sql)
                except ProgrammingError as e1:
                    """
                    已知错误
                    1 空sql会报空错误
                    2 无效的sql会报错误
                    3 库不存在或没有权限访问会报错
                    4 表不存在会报错
                    """
                    # 先把时间记录
                    self.plugin_run_log['et'] = round(time.time() * 1000)
                    self.plugin_run_log['t'] = round((self.plugin_run_log['et'] - self.plugin_run_log['st']))
                    self.plugin_run_log['s'] = False
                    # 从错误中提取错误码及错误信息
                    self.response_code = e1.orig.args[0]
                    self.plugin_run_log["c"] = self.response_code
                    self.plugin_run_log['f'] = '请求发生错误:%s;' % e1.orig.args[1]
                    # 数据包大小计算
                    # self.plugin_run_log["rl"] = 0
                    # self.plugin_run_log["rsl"] = 0
                except Exception as e2:
                    # 先把时间记录
                    self.plugin_run_log['et'] = round(time.time() * 1000)
                    self.plugin_run_log['t'] = round((self.plugin_run_log['et'] - self.plugin_run_log['st']))
                    self.plugin_run_log['s'] = False
                    # 从错误中提取错误码及错误信息
                    self.response_code = -1
                    self.plugin_run_log["c"] = self.response_code
                    self.plugin_run_log['f'] = '请求发生错误:%s;' % repr(e2)
                else:
                    # 先把时间记录
                    self.plugin_run_log['et'] = round(time.time() * 1000)
                    self.plugin_run_log['t'] = round((self.plugin_run_log['et'] - self.plugin_run_log['st']))
                    self.plugin_run_log['s'] = True
                    # 数据包大小计算
                    # self.plugin_run_log["rl"] = 0
                    # self.plugin_run_log["rsl"] = 0
                    # 根据returns_rows区分select还是insert/update/delete
                    if self.request_vars != "":
                        if db_proxy.returns_rows:
                            # select语句无论有无结果都会返回list，但是得做好空数据或者列数不够的判错机制
                            all_data = {var: [] for var in self.request_vars_list}
                            # 添加缓冲
                            cache_nrow = 1000
                            # 首次读取
                            cache_data_list = db_proxy.fetchmany(cache_nrow)
                            while len(cache_data_list) > 0:
                                dataframe = pandas.DataFrame(cache_data_list, dtype=numpy.str)
                                for i, val in enumerate(self.request_vars_list):
                                    if i < dataframe.shape[1]:
                                        all_data[val] += dataframe[i].to_list()
                                    else:
                                        all_data[val] += [None for i in range(dataframe.shape[0])]
                                cache_data_list = db_proxy.fetchmany(cache_nrow)
                            for rvl in self.request_vars_list:
                                # 将数据以{参数名: {协程/线程号1: 参数值1, 协程/线程号2: 参数值2}}的形式存储进总参数存储实例
                                if type(self.run_parameter_controller.get(rvl)) is VuserDataBottle:
                                    self.run_parameter_controller.get(rvl).update({self.vuser_index: all_data[rvl]})
                                else:
                                    v = VuserDataBottle()
                                    v.update({self.vuser_index: all_data[rvl]})
                                    self.run_parameter_controller.update({rvl: v})
                        else:
                            # insert/delete/update语句无返回内容，不能调用fetchall，不过可以获取到影响行数rowcount
                            # 不作任何处理
                            pass
                finally:
                    # 通用代码段
                    # 5.对自身结果作断言
                    for pa in self.plugins_assertion:
                        pa.run_test()
                    # 6.执行后置插件操作
                    for ppp in self.plugins_postprocessor:
                        ppp.run_test()
            else:
                # 引擎参数变量不存在则报错
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
