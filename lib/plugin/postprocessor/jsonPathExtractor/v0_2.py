# -*- coding: utf-8 -*-

"""
jsonPath提取器插件
    功能简述：
        挂载在http请求插件之下，支持从父级插件的返回值中提取相应的值以供后续使用
        如果失败，不报错但不生成参数

    实现逻辑：
        获取父级http请求插件的返回值，提取符合jsonpath规则的值

    需求入参：
        {
            "var": "...",
                参数名称，可为空。未填写则不作参数化
            "expr": "...",
                jsonPath语句
            "match_no": xxx,
                匹配数字。为空默认取第一个结果；为0随机取；大于0则取相应序号的值(代码中需要-1)
            "default": "...",
                取不到值时的默认值
            "all": true/false,
                是否统计所有，则将所有匹配结果值存为list
        }
"""

import json
import jsonpath
import re
import random

from ..postprocessor import PostprocessorPlugin

from lib.storage.customValueBottle import VuserDataBottle

from handler.scheduler import kill_test_task_job


class JsonPathExtractor(PostprocessorPlugin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 添加插件自有属性
        self.post_var = ""
        self.post_expr = ""
        self.post_match_no = 0
        self.post_default = ""
        self.post_all = True
        # 根据传入的数据,进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    def check_before_run(self):
        """
        初始化说明点
        1 var:数据类型str.命名规则需符合规范要求
        2 expr:数据类型str
        3 match_no:数据类型int.需 > -2
        4 default:数据类型str
        5 all:数据类型bool
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
            # var
            if 'var' not in plugin_init_value or type(plugin_init_value['var']) is not str:
                log += '变量名检查失败,原因:变量名整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['var'] != "" and not re.match(r"(\b[_a-zA-Z][_a-zA-Z0-9.]*)", plugin_init_value['var']):
                log += '变量名检查失败,原因:变量名填写非法,请按照格式要求填写;'
                check_flag = False
            # expr
            if 'expr' not in plugin_init_value or type(plugin_init_value['expr']) is not str:
                log += 'JsonPath表达式检查失败,原因:JsonPath表达式整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            # match_no
            if 'match_no' not in plugin_init_value or type(plugin_init_value['match_no']) is not int:
                log += '匹配序号检查失败,原因:匹配序号整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['match_no'] < 0:
                log += '匹配序号检查失败,原因:匹配序号需填写自然数;'
                check_flag = False
            # default
            if 'default' not in plugin_init_value or type(plugin_init_value['default']) is not str:
                log += '默认值检查失败,原因:默认值整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            # all
            if 'all' not in plugin_init_value or type(plugin_init_value['all']) is not bool:
                log += '是否统计所有检查失败,原因:是否统计所有整体数据缺失或数据异常,请联系管理员;'
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
            # var
            self.post_var = self.plugin_value['var']
            # expr
            self.post_expr = self.plugin_value['expr']
            # match_no
            self.post_match_no = self.plugin_value['match_no']
            # default
            self.post_default = self.plugin_value['default']
            # all
            self.post_all = self.plugin_value['all']
            return True, None

    def run_test(self):
        run_init_result, run_init_log = self.init_before_run()
        # 如果失败强行终止测试任务运行
        if run_init_result:
            try:
                response_json_dict = json.loads(self.tree_parent.response_body_content)
            except:
                # 解析失败直接忽略
                pass
            else:
                # 尝试jsonpath解析
                jsonpath_result = jsonpath.jsonpath(response_json_dict, self.post_expr)
                if jsonpath_result:
                    # 根据match_no/default
                    l = len(jsonpath_result)
                    if self.post_match_no == 0:
                        result = jsonpath_result[random.randint(0, l)]
                    elif self.post_match_no - 1 < l:
                        result = jsonpath_result[self.post_match_no - 1]
                    else:
                        result = self.post_default
                    # 将数据以{参数名: {协程/线程号1: 参数值1, 协程/线程号2: 参数值2}}的形式存储进总参数存储实例
                    if type(self.run_parameter_controller.get(self.post_var)) is VuserDataBottle:
                        self.run_parameter_controller.get(self.post_var).update({self.vuser_index: result})
                    else:
                        vdb1 = VuserDataBottle()
                        vdb1.update({self.vuser_index: result})
                        self.run_parameter_controller.update({self.post_var: vdb1})
                    if self.post_all:
                        # 将数据以{参数名: {协程/线程号1: 参数值1, 协程/线程号2: 参数值2}}的形式存储进总参数存储实例
                        if type(self.run_parameter_controller.get('%s_All' % self.post_var)) is VuserDataBottle:
                            self.run_parameter_controller.get('%s_All' % self.post_var).update({self.vuser_index: jsonpath_result})
                        else:
                            vdb2 = VuserDataBottle()
                            vdb2.update({self.vuser_index: jsonpath_result})
                            self.run_parameter_controller.update({('%s_All' % self.post_var): vdb2})
        else:
            self.trans_init_log(run_init_log)
            kill_test_task_job(self.base_data)
