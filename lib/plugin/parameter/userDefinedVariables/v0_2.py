# -*- coding:utf-8 -*-

"""
自定义变量参数化插件
    功能简述:
        支持键值对的参数化方式,其中键即为变量名称,值即为内容.本插件仅有初始化内容

    实现逻辑:
        初始化时,检查各项参数是否符合输入要求,通过后将数据变换为字典并提交至总参数化存储实例

    需求入参:
        {
            "vars":[...],
                支持填写多条,每一条内容的格式为[key,value],且key与value内容均为字符串
        }
"""

import json
import re

from ..parameter import ParameterPlugin


class UserDefinedVariables(ParameterPlugin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 添加插件自有属性
        self.parameters_pair = {}
        # 根据传入的数据，进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    @staticmethod
    def check_single_pair(pairs):
        for p in pairs:
            if type(p) is not list or len(p) != 2:
                return False
            elif type(p[0]) is not str or type(p[1]) is not str:
                return False
            # 参数化变量名称需符合要求
            elif p[0] != "" and not re.match(r"(\b[_a-zA-Z][_a-zA-Z0-9.]*)", p[0]):
                return False
        return True

    def check_before_run(self):
        """
        初始化说明点
        1 vars:数据类型list.list中各项数据的数据类型亦为list,其长度为2,0位置数据类型str,数据命名支持数字字母下划线,
            且首位仅支持填写下划线或字母;1位置数据类型str
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
            # vars
            if 'vars' not in plugin_init_value or type(plugin_init_value['vars']) is not list:
                log += '变量检查失败,原因:变量整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif not self.check_single_pair(plugin_init_value['vars']):
                log += '变量检查失败,原因:变量内容格式或数据类型非法,请检查;'
                check_flag = False
            else:
                # 本插件无运行步骤,此处直接填充总参数化存储实例
                # 忽略变量名未填写的情况
                self.parameters_pair = {}
                for k, v in plugin_init_value['vars']:
                    if k != '':
                        self.parameters_pair[k] = v
                self.run_parameter_controller.update(self.parameters_pair)

        if not check_flag:
            return False, log
        else:
            return True, None
