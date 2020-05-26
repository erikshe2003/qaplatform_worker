# -*- coding: utf-8 -*-

"""
HTTP/HTTPS请求断言插件
    功能简述：
        本插件可对HTTP/HTTPS请求插件作多项内容的断言检查，且各项内容的检查同时生效，检查的结果同时返回。
        断言项目1：检查请求的URL，可填写多条规则。规则支持选择普通字符串匹配模式或者正则匹配模式，其中，字符串匹配模式可根
        据填写的规则内容对URL进行全部匹配断言或者部分匹配断言，且可根据特殊状态位，对URL作内容不匹配断言或者内容
        不包含断言；正则匹配模式可根据填写的正则表达式，对URL进行更为灵活的断言。

        断言项目2：逐项检查请求header中的条目或者请求返回header中的条目，支持普通字符串匹配模式或者正则匹配模式。
        字符串匹配模式可选择全部匹配或者部分匹配。若选择全部匹配，则header条目键值对必须完全等于所填写规则内容；若选择部分匹配，
        则header条目键值对只需包含规则内容即可。正则匹配模式需填写一对匹配header键值对的规则，测试时将会对实际header的
        键值对分别进行断言

        断言项目3：对请求的内容或者请求返回的内容进行断言，支持将返回内容当作一整个字符串进行文本匹配，也可将之当作json字符串并
        填写jsonPath进行断言。文本匹配模式可选择全部匹配或者部分匹配。若选择全部匹配，则内容必须完全等于所填写规则内容；若选
        择部分匹配，则内容只需包含规则内容即可。jsonPath匹配模式下可填写符合要求的jsonPath用以搜索出内容中符合要求的数据，然后
        根据规则内容进行断言，而规则内容支持普通字符串匹配模式或者正则匹配模式。字符串匹配模式可选择全部匹配或者部分匹配以
        对jsonPath提取出的内容进行断言，亦可根据特殊状态位，对提取出的内容作不匹配或者不包含的断言。正则匹配模式可根据填写
        的正则表达式，对jsonPath提取出的内容进行断言

        断言项目4：对请求返回的HTTP状态码进行断言，支持文本匹配模式或者正则表达式模式，可填写多条规则。其中，字符串匹配模式可根
        据填写的规则内容对状态码进行全部匹配断言或者部分匹配断言，且可根据特殊状态位，对状态码作内容不匹配断言或者内容
        不包含断言；正则匹配模式可根据填写的正则表达式，对状态码进行更为灵活的断言。

    实现逻辑：
        初始化时，检查各个断言项目的数据填写是否合法.执行时检查各项断言后改写父级插件(HTTP请求插件)的状态位及log

    需求入参：
        {
            "url_check": [...],
                支持填写多条，每一条内容的格式为["text(文本匹配)/reg(正则匹配)",0(包含)/1(等于),true(是)/false(否),"匹配内容"]

            "header_check": [...],
                支持填写多条，每一条内容的格式为[0(请求)/1(返回),"text(文本匹配)/reg(正则匹配)",0(包含)/1(等于),true(是)/false(否),"匹配键内容","匹配值内容"]

            "body_content_check": [...],
                支持填写多条，每一条内容的格式为[0(请求)/1(返回),"text(文本匹配)/reg(正则匹配)",0(包含)/1(等于),true(是)/false(否),"匹配内容"]

            "body_json_check": [...],
                支持填写多条，每一条内容的格式为[0(请求)/1(返回),"text(文本匹配)/reg(正则匹配)","jsonPath规则","匹配内容"]

            "code_check": [...],
                支持填写多条，每一条内容的格式为["text(文本匹配)/reg(正则匹配)",0(包含)/1(等于),true(是)/false(否),"匹配内容"]
        }
"""

import re
import json
import jsonpath

from lib.plugin.assertion import AssertionPlugin

from handler.scheduler import kill_test_task_job


class HttpRequestAssert(AssertionPlugin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 添加插件自有属性
        self.policys_url_check = []
        self.policys_header_check = []
        self.policys_body_content_check = []
        self.policys_body_json_check = []
        self.policys_code_check = []
        # 根据传入的数据,进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    @staticmethod
    def check_url_check_policys(policys):
        for p in policys:
            if type(p) is not list or len(p) != 4:
                return False
            elif type(p[0]) is not str or p[0] not in ('text', 'reg'):
                return False
            elif type(p[1]) is not int or p[1] not in (0, 1):
                return False
            elif type(p[2]) is not bool:
                return False
            elif type(p[3]) is not str:
                return False
        return True

    @staticmethod
    def check_header_check_policys(policys):
        for p in policys:
            if type(p) is not list or len(p) != 6:
                return False
            elif type(p[0]) is not int or p[0] not in (0, 1):
                return False
            elif type(p[1]) is not str:
                return False
            elif type(p[2]) is not str or p[2] not in ('text', 'reg'):
                return False
            elif type(p[3]) is not int or p[3] not in (0, 1):
                return False
            elif type(p[4]) is not bool:
                return False
            elif type(p[5]) is not str:
                return False
        return True

    @staticmethod
    def check_body_content_check_policys(policys):
        for p in policys:
            if type(p) is not list or len(p) != 5:
                return False
            elif type(p[0]) is not int or p[0] not in (0, 1):
                return False
            elif type(p[1]) is not str or p[1] not in ('text', 'reg'):
                return False
            elif type(p[2]) is not int or p[2] not in (0, 1):
                return False
            elif type(p[3]) is not bool:
                return False
            elif type(p[4]) is not str:
                return False
        return True

    @staticmethod
    def check_body_json_check_policys(policys):
        for p in policys:
            if type(p) is not list or len(p) != 6:
                return False
            elif type(p[0]) is not int or p[0] not in (0, 1):
                return False
            elif type(p[1]) is not str:
                return False
            elif type(p[2]) is not str or p[2] not in ('text', 'reg'):
                return False
            elif type(p[3]) is not str:
                return False
        return True

    @staticmethod
    def check_code_check_policys(policys):
        for p in policys:
            if type(p) is not list or len(p) != 4:
                return False
            elif type(p[0]) is not str or p[0] not in ('text', 'reg'):
                return False
            elif type(p[1]) is not int or p[1] not in (0, 1):
                return False
            elif type(p[2]) is not bool:
                return False
            elif type(p[3]) is not str:
                return False
        return True

    def check_before_run(self):
        """
        初始化说明点
        1 url_check:数据类型list.list中各项数据的数据类型亦为list,长度4
            0位置数据类型str,支持'text'(普通文本)及'reg'(正则);
            1位置数据类型int,支持0(包含)及1(等于);
            2位置数据类型bool,支持true(是)/false(否);
            3位置数据类型str
        2 header_check:数据类型list.list中各项数据的数据类型亦为list,长度6
            0位置数据类型int,支持0(请求)及1(返回);
            1位置数据类型str;
            2位置数据类型str,支持'text'(普通文本)及'reg'(正则);
            3位置数据类型int,支持0(包含)及1(等于);
            4位置数据类型bool,支持true(是)/false(否);
            5位置数据类型str
        3 body_content_check:数据类型list.list中各项数据的数据类型亦为list,长度5
            0位置数据类型int,支持0(请求)及1(返回);
            1位置数据类型str,支持'text'(普通文本)及'reg'(正则);
            2位置数据类型int,支持0(包含)及1(等于);
            3位置数据类型bool,支持true(是)/false(否);
            4位置数据类型str
        4 body_json_check:数据类型list.list中各项数据的数据类型亦为list,长度4
            0位置数据类型int,支持0(请求)及1(返回);
            1位置数据类型str;
            2位置数据类型str,支持'text'(普通文本)及'reg'(正则);
            3位置数据类型str
        5 code_check:数据类型list.list中各项数据的数据类型亦为list,长度4
            0位置数据类型str,支持'text'(普通文本)及'reg'(正则);
            1位置数据类型int,支持0(包含)及1(等于);
            2位置数据类型bool,支持true(是)/false(否);
            3位置数据类型str
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
            # url_check
            if 'url_check' not in plugin_init_value or type(plugin_init_value['url_check']) is not list:
                log = 'URL断言规则检查失败,原因:URL断言规则整体数据缺失或数据异常;'
                check_flag = False
            elif not self.check_url_check_policys(plugin_init_value['url_check']):
                log = 'URL断言规则检查失败,原因:URL断言规则内容填写非法;'
                check_flag = False

            # header_check
            if 'header_check' not in plugin_init_value or type(plugin_init_value['header_check']) is not list:
                log = 'Header断言规则检查失败,原因:Header断言规则整体数据缺失或数据异常;'
                check_flag = False
            elif not self.check_header_check_policys(plugin_init_value['header_check']):
                log = 'Header断言规则检查失败,原因:Header断言规则内容填写非法;'
                check_flag = False

            # body_content_check
            if 'body_content_check' not in plugin_init_value or type(plugin_init_value['body_content_check']) is not list:
                log = 'Body断言(文本)规则检查失败,原因:Body检查(文本)规则整体数据缺失或数据异常;'
                check_flag = False
            elif not self.check_body_content_check_policys(plugin_init_value['body_content_check']):
                log = 'Body断言(文本)规则检查失败,原因:Body断言(文本)规则内容填写非法;'
                check_flag = False

            # body_json_check
            if 'body_json_check' not in plugin_init_value or type(plugin_init_value['body_json_check']) is not list:
                log = 'Body断言(JsonPath)规则检查失败,原因:Body断言(JsonPath)规则整体数据缺失或数据异常;'
                check_flag = False
            elif not self.check_body_json_check_policys(plugin_init_value['body_json_check']):
                log = 'Body断言(JsonPath)规则检查失败,原因:Body断言(JsonPath)规则内容填写非法;'
                check_flag = False

            # code_check
            if 'code_check' not in plugin_init_value or type(plugin_init_value['code_check']) is not list:
                log = 'Code断言规则检查失败,原因:Code断言规则整体数据缺失或数据异常'
                check_flag = False
            elif not self.check_code_check_policys(plugin_init_value['code_check']):
                log = 'Code断言规则检查失败,原因:Code断言规则内容填写非法;'
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
            # url_check
            self.policys_url_check = self.plugin_value['url_check']
            # header_check
            self.policys_header_check = self.plugin_value['header_check']
            # body_content_check
            self.policys_body_content_check = self.plugin_value['body_content_check']
            # body_json_check
            self.policys_body_json_check = self.plugin_value['body_json_check']
            # code_check
            self.policys_code_check = self.plugin_value['code_check']
            return True, None

    def url_assert(self):
        """
        1 url_check:数据类型list.list中各项数据的数据类型亦为list,长度4
            0位置数据类型str,支持'text'(普通文本)及'reg'(正则);
            1位置数据类型int,支持0(包含)及1(等于);
            2位置数据类型bool,支持true(是)/false(否);
            3位置数据类型str
        :return: None
        """
        for puc in self.policys_url_check:
            flag = True
            # 区分"text(文本匹配)/reg(正则匹配)"
            if puc[0] == 'text':
                # 区分true(是)/false(否)
                if puc[2]:
                    # 区分0(包含)/1(等于)
                    if puc[1] == 0:
                        if puc[3] not in self.tree_parent.request_url:
                            flag = False
                    else:
                        if puc[3] != self.tree_parent.request_url:
                            flag = False
                else:
                    # 区分0(包含)/1(等于)
                    if puc[1] == 0:
                        if puc[3] in self.tree_parent.request_url:
                            flag = False
                    else:
                        if puc[3] == self.tree_parent.request_url:
                            flag = False
            elif puc[0] == 'reg':
                if not re.search(puc[3], self.tree_parent.request_url):
                    flag = False
            if not flag:
                self.tree_parent.plugin_run_log['s'] = False
                self.tree_parent.plugin_run_log['f'] += '第%d条URL断言规则断言失败;' % (self.policys_url_check.index(puc) + 1)

    def header_assert(self):
        """
        2 header_check:数据类型list.list中各项数据的数据类型亦为list,长度6
            0位置数据类型int,支持0(请求)及1(返回);
            1位置数据类型str;
            2位置数据类型str,支持'text'(普通文本)及'reg'(正则);
            3位置数据类型int,支持0(包含)及1(等于);
            4位置数据类型bool,支持true(是)/false(否);
            5位置数据类型str
        :return: None
        """
        for phc in self.policys_header_check:
            flag = True
            # 区分0(请求)/1(返回)
            if phc[0] == 0:
                # 没有Header直接报错
                if phc[1] not in self.tree_parent.request_headers:
                    flag = False
                else:
                    # 区分"text(文本匹配)/reg(正则匹配)"
                    if phc[2] == 'text':
                        # 区分true(是)/false(否)
                        if phc[4]:
                            # 区分0(包含)/1(等于)
                            if phc[3] == 0:
                                if phc[5] not in self.tree_parent.request_headers[phc[1]]:
                                    flag = False
                            else:
                                if phc[5] != self.tree_parent.request_headers[phc[1]]:
                                    flag = False
                        else:
                            # 区分0(包含)/1(等于)
                            if phc[3] == 0:
                                if phc[5] in self.tree_parent.request_headers[phc[1]]:
                                    flag = False
                            else:
                                if phc[5] == self.tree_parent.request_headers[phc[1]]:
                                    flag = False
                    elif phc[2] == 'reg':
                        if not re.search(phc[5], self.tree_parent.request_headers[phc[1]]):
                            flag = False
            else:
                # 没有Header直接报错
                if phc[1] not in self.tree_parent.response_headers:
                    flag = False
                else:
                    # 区分"text(文本匹配)/reg(正则匹配)"
                    if phc[2] == 'text':
                        # 区分true(是)/false(否)
                        if phc[4]:
                            # 区分0(包含)/1(等于)
                            if phc[3] == 0:
                                if phc[5] not in self.tree_parent.response_headers[phc[1]]:
                                    flag = False
                            else:
                                if phc[5] != self.tree_parent.response_headers[phc[1]]:
                                    flag = False
                        else:
                            # 区分0(包含)/1(等于)
                            if phc[3] == 0:
                                if phc[5] in self.tree_parent.response_headers[phc[1]]:
                                    flag = False
                            else:
                                if phc[5] == self.tree_parent.response_headers[phc[1]]:
                                    flag = False
                    elif phc[2] == 'reg':
                        if not re.search(phc[5], self.tree_parent.response_headers[phc[1]]):
                            flag = False
            if not flag:
                self.tree_parent.plugin_run_log['s'] = False
                self.tree_parent.plugin_run_log['f'] += '第%d条Header断言规则断言失败;' % (self.policys_header_check.index(phc) + 1)

    def body_content_assert(self):
        """
        3 body_content_check:数据类型list.list中各项数据的数据类型亦为list,长度5
            0位置数据类型int,支持0(请求)及1(返回);
            1位置数据类型str,支持'text'(普通文本)及'reg'(正则);
            2位置数据类型int,支持0(包含)及1(等于);
            3位置数据类型bool,支持true(是)/false(否);
            4位置数据类型str
        :return: None
        """
        for pbcc in self.policys_body_content_check:
            flag = True
            # 区分0(请求)/1(返回)
            if pbcc[0] == 0:
                # 区分"text(文本匹配)/reg(正则匹配)"
                if pbcc[1] == 'text':
                    # 区分true(是)/false(否)
                    if pbcc[3]:
                        # 区分0(包含)/1(等于)
                        if pbcc[2] == 0:
                            if pbcc[4] not in self.tree_parent.request_body_content:
                                flag = False
                        else:
                            if pbcc[4] != self.tree_parent.request_body_content:
                                flag = False
                    else:
                        # 区分0(包含)/1(等于)
                        if pbcc[2] == 0:
                            if pbcc[4] in self.tree_parent.request_body_content:
                                flag = False
                        else:
                            if pbcc[4] == self.tree_parent.request_body_content:
                                flag = False
                elif pbcc[1] == 'reg':
                    if not re.search(pbcc[4], self.tree_parent.request_body_content):
                        flag = False
            else:
                # 区分"text(文本匹配)/reg(正则匹配)"
                if pbcc[1] == 'text':
                    # 区分true(是)/false(否)
                    if pbcc[3]:
                        # 区分0(包含)/1(等于)
                        if pbcc[2] == 0:
                            if pbcc[4] not in self.tree_parent.response_body_content:
                                flag = False
                        else:
                            if pbcc[4] != self.tree_parent.response_body_content:
                                flag = False
                    else:
                        # 区分0(包含)/1(等于)
                        if pbcc[2] == 0:
                            if pbcc[4] in self.tree_parent.response_body_content:
                                flag = False
                        else:
                            if pbcc[4] == self.tree_parent.response_body_content:
                                flag = False
                elif pbcc[1] == 'reg':
                    if not re.search(pbcc[4], self.tree_parent.response_body_content):
                        flag = False
            if not flag:
                self.tree_parent.plugin_run_log['s'] = False
                self.tree_parent.plugin_run_log['f'] += '第%d条Body断言(文本)规则断言失败;' % (self.policys_body_content_check.index(pbcc) + 1)

    def body_json_assert(self):
        """
        4 body_json_check:数据类型list.list中各项数据的数据类型亦为list,长度4
            0位置数据类型int,支持0(请求)及1(返回);
            1位置数据类型str;
            2位置数据类型str,支持'text'(普通文本)及'reg'(正则);
            3位置数据类型str
        :return: None
        """
        request_json = None
        response_json = None

        # 遍历policys_body_json_check
        for pbjc in self.policys_body_json_check:
            # 区分0(请求)/1(返回)
            if pbjc[0] == 0 and request_json is None:
                try:
                    request_json = json.loads(self.tree_parent.request_body_content)
                except:
                    self.tree_parent.plugin_run_log['s'] = False
                    self.tree_parent.plugin_run_log['f'] += '请求内容读取为JSON对象失败;'
                    return
            elif pbjc[0] == 1 and response_json is None:
                try:
                    response_json = json.loads(self.tree_parent.response_body_content)
                except:
                    self.tree_parent.plugin_run_log['s'] = False
                    self.tree_parent.plugin_run_log['f'] += '返回内容读取为JSON对象失败;'
                    return

        for pbjc in self.policys_body_json_check:
            flag = True
            content_collected = jsonpath.jsonpath(request_json if pbjc[0] == 0 else response_json, pbjc[1])
            if content_collected is False:
                flag = False
            else:
                # jsonpath提取出来的数据是list所以需要遍历
                content_collected = [str(jj) for jj in content_collected]
                # 区分"text(文本匹配)/reg(正则匹配)"
                if pbjc[2] == 'text':
                    if pbjc[3] not in content_collected:
                        flag = False
                elif pbjc[2] == 'reg':
                    search_flag = False
                    for cc in content_collected:
                        if not re.search(pbjc[3], cc):
                            pass
                        else:
                            search_flag = True
                            break
                    if search_flag is False:
                        flag = False
            if not flag:
                self.tree_parent.plugin_run_log['s'] = False
                self.tree_parent.plugin_run_log['f'] += '第%d条Body断言(JsonPath)规则断言失败;' % (self.policys_body_json_check.index(pbjc) + 1)

    def code_assert(self):
        """
        5 code_check:数据类型list.list中各项数据的数据类型亦为list,长度4
            0位置数据类型str,支持'text'(普通文本)及'reg'(正则);
            1位置数据类型int,支持0(包含)及1(等于);
            2位置数据类型bool,支持true(是)/false(否);
            3位置数据类型str
        :return: None
        """
        for pcc in self.policys_code_check:
            flag = True
            # 区分"text(文本匹配)/reg(正则匹配)"
            if pcc[0] == 'text':
                # 区分true(是)/false(否)
                if pcc[2]:
                    # 区分0(包含)/1(等于)
                    if pcc[1] == 0:
                        if pcc[3] not in str(self.tree_parent.response_code):
                            flag = False
                    else:
                        if pcc[3] != str(self.tree_parent.response_code):
                            flag = False
                else:
                    # 区分0(包含)/1(等于)
                    if pcc[1] == 0:
                        if pcc[3] in str(self.tree_parent.response_code):
                            flag = False
                    else:
                        if pcc[3] == str(self.tree_parent.response_code):
                            flag = False
            elif pcc[0] == 'reg':
                if not re.match(pcc[3], str(self.tree_parent.response_code)):
                    flag = False
            if not flag:
                self.tree_parent.plugin_run_log['s'] = False
                self.tree_parent.plugin_run_log['f'] += '第%d条Code断言规则断言失败;' % (self.policys_code_check.index(pcc) + 1)

    def run_test(self):
        # 运行前数据填充
        run_init_result, run_init_log = self.init_before_run()
        # 如果失败强行终止测试任务运行
        if not run_init_result:
            self.trans_init_log(run_init_log)
            kill_test_task_job(self.base_data)
        else:
            # 执行各项断言检查
            # 执行URl断言
            self.url_assert()
            # 执行Header断言
            self.header_assert()
            # 执行Body_Content检查
            self.body_content_assert()
            # 执行Body_Json检查
            self.body_json_assert()
            # 执行Code检查
            self.code_assert()
