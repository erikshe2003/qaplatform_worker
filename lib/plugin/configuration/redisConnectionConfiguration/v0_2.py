# -*- coding: utf-8 -*-

"""
Redis连接配置插件
    功能简述:
        配置redis连接，支持配置最大连接数、超时时间、域名、端口号、用户名密码等选项

    实现逻辑:
        初始化时,检查各项参数是否符合输入要求,通过后创建redis连接,并将连接提交至总参数化存储实例中

    需求入参:{"max_pool_size":0,"pool_timeout":10000,"host":"","port":6379,"pwd":"","db":0,"var":""}
        {
            "max_pool_size"：0,
                连接池配置连接数量,为自然数,默认为0
            "pool_timeout":10000,
                单个连接超时时间,为正整数,默认为10000
            "host":"",
                mysql服务地址名称
            "port":6379,
                mysql服务端口号,为正整数,默认为6379
            "pwd":"",
                连接密码
            "db":0,
                连接数据库
            "var":"",
                连接池的参数化变量名称,需符合变量命名规范
        }
"""

import json

from redis import ConnectionPool

from handler.scheduler import kill_test_task_job

from ..configuration import ConfigurationPlugin

"""
    socket_connect_timeout：
        21s内host异常导致连接失败，异常内容为：Timeout connecting to server，超过21shost异常导致连接失败，异常内容为：
        redis.exceptions.ConnectionError: Error 10060 connecting to 192.169.123.23:6379. 由于连接方在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败。
"""


class RedisConnectionConfiguration(ConfigurationPlugin):
    connectionPool = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 添加插件自有属性
        self.db_connection_poolsize = 0
        self.db_connection_timeout = 0
        self.db_connection_host = ""
        self.db_connection_port = 0
        self.db_connection_pwd = ""
        self.db_connection_db = 0
        self.db_connection_var = ""
        # 根据传入的数据，进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    def check_before_run(self):
        """
        初始化说明点
        1 max_pool_size:数据类型int,支持自然数
        2 pool_timeout:数据类型int,支持正整数
        3 host:数据类型str
        4 port:数据类型int,支持正整数
        5 pwd:数据类型str
        6 db:数据类型int
        7 var:数据类型str
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
            # max_pool_size
            if 'max_pool_size' not in plugin_init_value:
                log += '最大连接数检查失败,原因:最大连接数数据缺失,请联系管理员;'
                check_flag = False
            elif plugin_init_value['max_pool_size'] is None:
                log += '最大连接数检查失败,原因:最大连接数为必填项;'
                check_flag = False
            elif type(plugin_init_value['max_pool_size']) is not int:
                log += '最大连接数检查失败,原因:最大连接数数数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['max_pool_size'] < 0:
                log += '最大连接数检查失败,原因:最大连接数请填写自然数;'
                check_flag = False
            # pool_timeout
            if 'pool_timeout' not in plugin_init_value:
                log += '连接超时检查失败,原因:连接超时数据缺失,请联系管理员;'
                check_flag = False
            elif plugin_init_value['pool_timeout'] is None:
                log += '连接超时检查失败,原因:连接超时为必填项;'
                check_flag = False
            elif type(plugin_init_value['pool_timeout']) is not int:
                log += '连接超时检查失败,原因:连接超时数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['pool_timeout'] < 1:
                log += '连接超时检查失败,原因:连接超时请填写正整数;'
                check_flag = False
            # host
            if 'host' not in plugin_init_value or type(plugin_init_value['host']) is not str:
                log += '域名检查失败,原因:域名数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['host'] == "":
                log += '域名检查失败,原因:域名缺失,域名未填写;'
                check_flag = False
            # port
            if 'port' not in plugin_init_value:
                log += '端口号检查失败,原因:端口号数据缺失,请联系管理员;'
                check_flag = False
            elif plugin_init_value['port'] is None:
                log += '端口号检查失败,原因:端口号为必填项;'
                check_flag = False
            elif type(plugin_init_value['port']) is not int:
                log += '端口号检查失败,原因:端口号数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['port'] < 1:
                log += '端口号检查失败,原因:端口号请填写正整数;'
                check_flag = False
            # pwd
            if 'pwd' not in plugin_init_value or type(plugin_init_value['pwd']) is not str:
                log += '密码检查失败,原因:密码数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['pwd'] == "":
                log += '密码检查失败,原因:密码缺失,密码未填写;'
                check_flag = False
            # db
            if 'db' not in plugin_init_value or type(plugin_init_value['db']) is not int:
                log += '数据库编号检查失败,原因:数据库编号数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['db'] < 0:
                log += '数据库编号检查失败,原因:数据库编号请填写自然数;'
                check_flag = False
            # var
            if 'var' not in plugin_init_value or type(plugin_init_value['var']) is not str:
                log += '变量名检查失败,原因:变量名数据缺失或数据异常,请联系管理员;'
                check_flag = False
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
            # max_pool_size
            self.db_connection_poolsize = self.plugin_value['max_pool_size']
            # pool_timeout
            self.db_connection_timeout = self.plugin_value['pool_timeout']
            # host
            self.db_connection_host = self.plugin_value['host']
            # port
            self.db_connection_port = self.plugin_value['port']
            # pwd
            self.db_connection_pwd = self.plugin_value['pwd']
            # db
            self.db_connection_db = self.plugin_value['db']
            # var
            self.db_connection_var = self.plugin_value['var']
            # 进行数据填充
            try:
                RedisConnectionConfiguration.connectionPool = ConnectionPool(
                    host=self.db_connection_host,
                    port=self.db_connection_port,
                    password=self.db_connection_pwd,
                    max_connections=None if self.db_connection_poolsize == 0 else self.db_connection_poolsize,
                    socket_connect_timeout=self.db_connection_timeout/1000,
                    db=self.db_connection_db
                )
            except Exception as e:
                return False, '数据库连接失败,原因:%s;' % repr(e)
            else:
                self.run_parameter_controller.update({self.db_connection_var: RedisConnectionConfiguration.connectionPool})
                return True, None

    def run_test(self):
        # 对于本参数化插件来说，第一次被调用run_test即调用init_before_run去初始化迭代器
        if not RedisConnectionConfiguration.connectionPool:
            run_init_result, run_init_log = self.init_before_run()
            # 如果失败强行终止测试任务运行
            if not run_init_result:
                self.trans_init_log(run_init_log)
                kill_test_task_job(self.base_data)
