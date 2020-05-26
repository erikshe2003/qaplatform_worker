# -*- coding: utf-8 -*-

import datetime
import time
import re

from sqlalchemy.engine.base import Engine
from redis.connection import ConnectionPool

from lib.storage.iterator import TextIterator, ListIterator
from lib.storage.customValueBottle import VuserDataBottle


class BasePlugin:
    def __init__(self, base_data, plugin_data, vuser_index, parent_node, init_log_ctrl, run_log_ctrl, worker_info,
                 parameter_ctrl):
        self.tree_parent = parent_node
        # 提取插件基础数据
        self.base_data = base_data
        self.base_user_num = base_data["v_user"]
        self.worker_info = worker_info
        self.worker_info_id = worker_info["id"]
        self.vuser_index = vuser_index
        # 基础数据如标题说明等等暂不支持参数化
        self.plugin_data = plugin_data
        self.plugin_id = plugin_data["id"]
        self.plugin_oid = plugin_data["originalId"]
        self.plugin_title = plugin_data["title"]
        self.plugin_desc = plugin_data["desc"]
        self.plugin_status = plugin_data["status"]
        self.plugin_init_value_str = plugin_data["value"]
        self.plugin_check_result = True
        self.plugin_check_log = ""
        self.plugin_value = {}
        # log
        self.init_log_controller = init_log_ctrl
        self.run_log_controller = run_log_ctrl
        # parameters
        self.run_parameter_controller = parameter_ctrl
        """
        插件执行时顺序为:
        1.初始化配置/参数化类子插件。配置类、参数化类插件理论上仅执行一次，是否需要刷新内容，待后续系统测试阶段再说
        2.执行一些前置子插件操作
        3.执行自身
        4.执行一般类别的子插件
        5.对自身结果作断言
        6.执行后置插件操作
        这里只是把不同类型的子插件分门别类起来，具体的执行由flowController控制
        """
        # 添加type=configuration/parameter的插件实例
        self.plugins_configuration = []
        # 添加type=preprocessor的插件实例
        self.plugins_preprocessor = []
        # 添加type=controller/request/timer的插件实例
        self.plugins_common = []
        # 添加type=assertion的插件实例
        self.plugins_assertion = []
        # 添加type=postprocessor的插件实例
        self.plugins_postprocessor = []
        # 各类状态位
        self.plugin_run_log = {}
        self.plugin_base_run_log = {
            "id": 0,  # 插件id
            "oid": 0,  # 插件原始id
            "wid": 0,  # worker_id
            "uid": 0,  # 虚拟用户_id
            "st": 0.0,  # 开始时间
            "et": 0.0,  # 结束时间
            "s": True,  # 执行结果
            "c": 0,  # 返回状态码
            "f": "",  # 执行信息
            "t": 0.0,  # 请求总时长
            "rl": 0,  # 发送数据包大小
            "rsl": 0,  # 返回数据包大小
            "hr_u": "",  # 请求url(httpRequest插件用)
            "hr_rh": "",  # 请求头信息(httpRequest插件用)
            "hr_rhl": 0,  # 请求头长度(httpRequest插件用)
            "hr_rb": "",  # 请求体信息(httpRequest插件用)
            "hr_rbl": 0,  # 请求体长度(httpRequest插件用)
            "hr_rsh": "",  # 返回头信息(httpRequest插件用)
            "hr_rshl": 0,  # 返回头长度(httpRequest插件用)
            "hr_rsb": "",  # 返回体信息(httpRequest插件用)
            "hr_rsbl": 0,  # 返回体长度(httpRequest插件用)
            "mr_rb": "",  # 请求语句(mysqlRequest插件用)
            "mr_rbl": "",  # 请求大小(mysqlRequest插件用)
            "mr_rsb": "",  # 返回数据(mysqlRequest插件用)
            "mr_rsbl": "",  # 返回数据大小(mysqlRequest插件用)
            "rr_rb": "",  # 请求语句(redisRequest插件用)
        }

    def trans_init_log(self, msg, level=None):
        log = "%s %s Worker:%d " % (
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
            'INFO' if level is None else 'ERROR',
            self.worker_info_id
        ) + msg
        self.init_log_controller.trans(log)

    def check_before_run(self):
        return True, None

    def init_before_run(self):
        return True, None

    def run_test(self):
        pass

    def parameters_replace(self, init_value_str):
        # print('%s: ST:%s' % (self.plugin_id, time.time()))
        # 参数化替换
        """
        测试正则1 r"\$\{(\b[_a-zA-Z][_a-zA-Z0-9.]*)\[(\d+|\*)\]\}"
        测试文本1 '${g}${g[11]}${g[*]}${g[aaa]}'
        测试结果1 [('g', '11'), ('g', '*')] 符合从列表中取值规则

        测试正则2 r"\$\{(\b[_a-zA-Z][_a-zA-Z0-9.]*)\}"
        测试文本2 '${g}${g[11]}${g[*]}${g[aaa]}'
        测试结果2 ['g'] 符合一般取值规则

        测试正则3(联合1与2) r"\$\{(\b[_a-zA-Z][_a-zA-Z0-9.]*)\}|\$\{(\b[_a-zA-Z][_a-zA-Z0-9.]*)\[(\d+|\*)\]\}"
        测试文本3 '${g}${g[11]}${g[*]}'
        测试结果3 [('g', '', ''), ('', 'g', '11'), ('', 'g', '*')] 遍历后判断位置0是否有值来区分符合哪样规则
        """
        re_find_result = re.findall(
            r"\$\{(\b[_a-zA-Z][_a-zA-Z0-9.]*)\}|\$\{(\b[_a-zA-Z][_a-zA-Z0-9.]*)\[(\d+|\*)\]\}",  # 当前仅支持深度为1的自然数下标取值
            init_value_str
        )
        for rfr in re_find_result:
            # 查询出来的结果必须为3位
            if len(rfr) == 3:
                # 查询出来的结果要么位置0有值1和2无值要么位置0无值1和2有值
                if rfr[0] != '' and rfr[1] == '' and rfr[2] == '':
                    parameter = self.run_parameter_controller.get(rfr[0])
                    # 如果能找到则替换,否则保持原样
                    if parameter is not None:
                        # 变量名对应值为迭代器 通过传入参数名称及虚拟用户号获取数据并替换
                        if type(parameter) is TextIterator or type(parameter) is ListIterator:
                            init_value_str = re.sub(
                                r"\$\{%s\}" % rfr[0],
                                parameter.get(rfr[0], self.vuser_index),
                                init_value_str
                            )
                        # 变量名对应值为Mysql数据库驱动/Redis连接池 不替换
                        elif type(parameter) is Engine or type(parameter) is ConnectionPool:
                            pass
                        # 变量名对应值为VuserDataBottle 通过传入协程/线程号获取数据并尝试转换为字符串最后替换
                        elif type(parameter) is VuserDataBottle:
                            # 当前仅支持输出str/int/bytes
                            if type(parameter.get(self.vuser_index)) in (str, int):
                                init_value_str = re.sub(
                                    r"\$\{%s\}" % rfr[0],
                                    str(parameter.get(self.vuser_index)),
                                    init_value_str
                                )
                            elif type(parameter.get(self.vuser_index)) in (bytes,):
                                try:
                                    init_value_str = re.sub(
                                        r"\$\{%s\}" % rfr[0],
                                        parameter.get(self.vuser_index).decode(),
                                        init_value_str
                                    )
                                except:
                                    pass
                        # 变量名对应值为dict/list 转换为字符串后替换
                        elif type(parameter) is dict or type(parameter) is list:
                            init_value_str = re.sub(
                                r"\$\{%s\}" % rfr[0],
                                str(parameter),
                                init_value_str
                            )
                        # 变量名对应值为字符串 直接替换
                        elif type(parameter) is str:
                            init_value_str = re.sub(
                                r"\$\{%s\}" % rfr[0],
                                parameter,
                                init_value_str
                            )
                        # 变量名对应值为bytes 尝试使用utf8编码解码为字符串并替换
                        elif type(parameter) is bytes:
                            try:
                                init_value_str = re.sub(
                                    r"\$\{%s\}" % rfr[0],
                                    parameter.decode('utf8'),
                                    init_value_str
                                )
                            except:
                                try:
                                    init_value_str = re.sub(
                                        r"\$\{%s\}" % rfr[0],
                                        str(parameter),
                                        init_value_str
                                    )
                                except:
                                    pass
                        # 变量名对应值为其他 尝试转换为字符串后替换
                        else:
                            try:
                                init_value_str = re.sub(
                                    r"\$\{%s\}" % rfr[0],
                                    str(parameter),
                                    init_value_str
                                )
                            except:
                                pass
                    # 如果不能找到则不作参数化替换
                    else:
                        pass
                elif rfr[0] == '' and rfr[1] != '':
                    parameter = self.run_parameter_controller.get(rfr[1])
                    # 编号可写 * 代表返回行数/个数
                    if rfr[2] == '*':
                        # 如果能找到则替换,否则保持原样
                        if parameter is not None:
                            # 场景1 变量名对应值为迭代器 获取迭代器内部数据长度并替换
                            if type(parameter) is TextIterator or type(parameter) is ListIterator:
                                init_value_str = re.sub(
                                    r"\$\{%s\[\*\]\}" % rfr[1],
                                    str(len(parameter.data)),
                                    init_value_str
                                )
                            # 场景2 变量名对应值为Mysql数据库驱动/Redis连接池 不替换
                            elif type(parameter) is Engine or type(parameter) is ConnectionPool:
                                pass
                            # 场景3 变量名对应值为VuserLists 通过传入协程/线程号获取长度
                            elif type(parameter) is VuserDataBottle:
                                #  当前仅支持输出str/list/dict/bytes，超出长度不替换
                                if type(parameter.get(self.vuser_index)) in (str, list, dict, bytes):
                                    try:
                                        init_value_str = re.sub(
                                            r"\$\{%s\[\*\]\}" % rfr[1],
                                            str(len(parameter.get(self.vuser_index))),
                                            init_value_str
                                        )
                                    except:
                                        pass
                            # 场景4 变量名对应值为dict/list 获取长度并替换
                            elif type(parameter) is dict or type(parameter) is list:
                                init_value_str = re.sub(
                                    r"\$\{%s\[\*\]\}" % rfr[1],
                                    str(len(parameter)),
                                    init_value_str
                                )
                            # 场景5 变量名对应值为字符串 替换为长度值并替换
                            elif type(parameter) is str:
                                init_value_str = re.sub(
                                    r"\$\{%s\[\*\]\}" % rfr[1],
                                    str(len(parameter)),
                                    init_value_str
                                )
                            # 场景6 变量名对应值为bytes 替换为长度值并替换
                            elif type(parameter) is bytes:
                                init_value_str = re.sub(
                                    r"\$\{%s\[\*\]\}" % rfr[1],
                                    str(len(parameter)),
                                    init_value_str
                                )
                            # 场景7 变量名对应值为其他 尝试替换为长度值并替换
                            else:
                                try:
                                    init_value_str = re.sub(
                                        r"\$\{%s\[\*\]\}" % rfr[1],
                                        str(len(parameter)),
                                        init_value_str
                                    )
                                except:
                                    pass
                        # 如果不能找到则不作参数化替换
                        else:
                            pass
                    # 变量名[编号]，编号为自然数，返回值，超出不作替换
                    elif rfr[2].isdigit:
                        # 如果能找到则替换,否则保持原样
                        if parameter is not None:
                            # 场景1 变量名对应值为迭代器 通过传入参数名称、虚拟用户号及int行号获取数据并替换
                            if type(parameter) is TextIterator or type(parameter) is ListIterator:
                                init_value_str = re.sub(
                                    r"\$\{%s\[%s\]\}" % (rfr[1], rfr[2]),
                                    parameter.get_by_index(rfr[1], int(rfr[2])),
                                    init_value_str
                                )
                            # 场景2 变量名对应值为Mysql数据库驱动/Redis连接池 不替换
                            elif type(parameter) is Engine or type(parameter) is ConnectionPool:
                                pass
                            # 场景3 变量名对应值为VuserLists 通过传入协程/线程号及int行号获取数据并替换
                            elif type(parameter) is VuserDataBottle:
                                #  当前仅支持输出str/list/bytes，超出长度不替换
                                if type(parameter.get(self.vuser_index)) in (str, list):
                                    try:
                                        init_value_str = re.sub(
                                            r"\$\{%s\[%s\]\}" % (rfr[1], rfr[2]),
                                            str(parameter.get(self.vuser_index)[int(rfr[2])]),
                                            init_value_str
                                        )
                                    except:
                                        pass
                                elif type(parameter.get(self.vuser_index)) in (bytes,):
                                    try:
                                        init_value_str = re.sub(
                                            r"\$\{%s\[%s\]\}" % (rfr[1], rfr[2]),
                                            parameter.get(self.vuser_index)[int(rfr[2])].decode(),
                                            init_value_str
                                        )
                                    except:
                                        pass
                            # 场景4 变量名对应值为dict 不替换
                            elif type(parameter) is dict:
                                pass
                            # 场景5 变量名对应值为list 通过传入int行号获取数据并替换
                            elif type(parameter) is list:
                                try:
                                    init_value_str = re.sub(
                                        r"\$\{%s\[%s\]\}" % (rfr[1], rfr[2]),
                                        str(parameter[int(rfr[2])]),
                                        init_value_str
                                    )
                                except:
                                    pass
                            # 场景5 变量名对应值为字符串 替换为对应序号的单个字符，若超过长度则不替换
                            elif type(parameter) is str:
                                if rfr[2] > len(parameter):
                                    pass
                                else:
                                    init_value_str = re.sub(
                                        r"\$\{%s\[%s\]\}" % (rfr[1], rfr[2]),
                                        parameter[rfr[2]],
                                        init_value_str
                                    )
                            # 场景6 变量名对应值为bytes 替换为对应序号的单个字符，若超过长度则不替换
                            elif type(parameter) is bytes:
                                if rfr[2] > len(parameter):
                                    pass
                                else:
                                    init_value_str = re.sub(
                                        r"\$\{%s\[%s\]\}" % (rfr[1], rfr[2]),
                                        parameter[rfr[2]].decode('utf8'),
                                        init_value_str
                                    )
                            # 场景7 变量名对应值为其他 不替换
                            else:
                                pass
                        # 如果不能找到则不作参数化替换
                        else:
                            pass
                # 不作参数化替换
                else:
                    pass
            # 不作参数化替换
            else:
                pass
        # print('%s: ET:%s' % (self.plugin_id, time.time()))
        return init_value_str
