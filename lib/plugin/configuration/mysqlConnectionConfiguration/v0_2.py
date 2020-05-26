# -*- coding: utf-8 -*-

"""
Mysql连接配置插件
    功能简述:
        配置mysql连接，支持配置最大连接数、超时时间、域名、端口号、用户名密码等选项

    实现逻辑:
        初始化时,检查各项参数是否符合输入要求,通过后创建mysql连接,并将连接提交至总参数化存储实例中

    需求入参:{"max_pool_size":0,"pool_timeout":10000,"host":"","port":3306,"user":"","pwd":"","database":"","charset":"UTF-8","var":"","auto_commit":true}
        {
            "max_pool_size"：0,
                连接池配置连接数量,为自然数,默认为0
            "pool_timeout":10000,
                单个连接超时时间,为正整数,默认为10000
            "host":"",
                mysql服务地址名称
            "port":3306,
                mysql服务端口号,为正整数,默认为3306
            "user":"",
                连接用户名
            "pwd":"",
                连接密码
            "database":"",
                连接数据库,可为空
            "charset":"UTF-8",
                数据库字符集,默认为utf-8
            "var":"",
                连接池的参数化变量名称,需符合变量命名规范
            "auto_commit":true
                语句执行自动提交状态位,默认为true
        }
"""

import json

from sqlalchemy import create_engine

from ..configuration import ConfigurationPlugin

from handler.scheduler import kill_test_task_job


class MysqlConnectionConfiguration(ConfigurationPlugin):
    connectionPool = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 添加插件自有属性
        self.db_connection_poolsize = 0
        self.db_connection_timeout = 0
        self.db_connection_host = ""
        self.db_connection_port = 0
        self.db_connection_user = ""
        self.db_connection_pwd = ""
        self.db_connection_database = ""
        self.db_connection_charset = ""
        self.db_connection_var = ""
        self.db_connection_auto = ""
        # 根据传入的数据，进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    def check_before_run(self):
        """
        初始化说明点
        1 max_pool_size:数据类型int,支持自然数
        2 pool_timeout:数据类型int,支持正整数
        3 host:数据类型str
        4 port:数据类型int,支持正整数
        5 user:数据类型str
        6 pwd:数据类型str
        7 database:数据类型str
        8 charset:数据类型str
        9 var:数据类型str
        10 auto_commit:数据类型bool
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
            # user
            if 'user' not in plugin_init_value or type(plugin_init_value['user']) is not str:
                log += '用户名检查失败,原因:用户名数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['user'] == "":
                log += '用户名检查失败,原因:用户名缺失,用户名未填写;'
                check_flag = False
            # pwd
            if 'pwd' not in plugin_init_value or type(plugin_init_value['pwd']) is not str:
                log += '密码检查失败,原因:密码数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['pwd'] == "":
                log += '密码检查失败,原因:密码缺失,密码未填写;'
                check_flag = False
            # database
            if 'database' not in plugin_init_value or type(plugin_init_value['database']) is not str:
                log += '数据库名检查失败,原因:数据库名数据缺失或数据异常,请联系管理员;'
                check_flag = False
            # charset
            if 'charset' not in plugin_init_value or type(plugin_init_value['charset']) is not str:
                log += '字符集检查失败,原因:字符集数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['charset'] == "":
                log += '字符集检查失败,原因:字符集缺失,字符集未填写;'
                check_flag = False
            # var
            if 'var' not in plugin_init_value or type(plugin_init_value['var']) is not str:
                log += '变量名检查失败,原因:变量名数据缺失或数据异常,请联系管理员;'
                check_flag = False
            # auto_commit
            if 'auto_commit' not in plugin_init_value or type(plugin_init_value['auto_commit']) is not bool:
                log += '自动提交检查失败,原因:自动提交数据缺失或数据异常,请联系管理员;'
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
            # user
            self.db_connection_user = self.plugin_value['user']
            # pwd
            self.db_connection_pwd = self.plugin_value['pwd']
            # database
            self.db_connection_database = self.plugin_value['database']
            # charset
            self.db_connection_charset = self.plugin_value['charset']
            # var
            self.db_connection_var = self.plugin_value['var']
            # auto_commit
            self.db_connection_auto = self.plugin_value['auto_commit']
            # 进行数据填充
            try:
                args = {
                    'user': self.db_connection_user,
                    'password': self.db_connection_pwd,
                    'host': self.db_connection_host,
                    'port': self.db_connection_port,
                    'charset': self.db_connection_charset.replace('-', ''),  # 数据库编码无-
                    'autocommit': self.db_connection_auto
                }
                if self.db_connection_database != '':
                    args['database'] = self.db_connection_database
                MysqlConnectionConfiguration.connectionPool = create_engine(
                    "mysql+pymysql://",
                    connect_args=args,
                    pool_size=self.base_user_num if self.db_connection_poolsize == 0 else self.db_connection_poolsize,
                    pool_timeout=self.db_connection_timeout/1000
                )
            except Exception as e:
                return False, '数据库连接失败,原因:%s;' % repr(e)
            else:
                self.run_parameter_controller.update({self.db_connection_var: MysqlConnectionConfiguration.connectionPool})
                return True, None

    def run_test(self):
        # 对于本参数化插件来说，第一次被调用run_test即调用init_before_run去初始化迭代器
        if not MysqlConnectionConfiguration.connectionPool:
            run_init_result, run_init_log = self.init_before_run()
            # 如果失败强行终止测试任务运行
            if not run_init_result:
                self.trans_init_log(run_init_log)
                kill_test_task_job(self.base_data)
