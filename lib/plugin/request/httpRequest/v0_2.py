# -*- coding: utf-8 -*-

"""
HTTP/HTTPS请求插件
    功能简述：
        可发起GET/POST类型的HTTP/HTTPS接口，支持自定义header，支持自定义url，并收集操作耗时、目标服务器IP、重定向耗时、请求头返
        回头大小、请求体返回体大小等数据。对于GET请求，可灵活定制其url参数；对于POST请求，支持form-data/x-www-form-urlencoded/raw三
        类请求体，且form-data方式可支持文件发送

    实现逻辑：
        初始化时，检查各个断言项目的数据填写是否合法，并写入初始化log
        执行时，读取tree_parent父级插件相关数据，判断值是否符合要求，并写入执行log

    需求入参：
        {
            "method": "GET"/"POST"，
                目前支持get和post请求两种
            "url": ""，
                地址字符串
            "headers": [...]，
                支持填写多条，每一条内容的格式为[key，value]
            "encode": ""，
                body编码，默认utf-8
            "body_type": 0/1/2，
                body内容类型，0代表form-data/1代表x-www-form-urlencoded/2代表raw
            "form_data": [...]，
                支持填写多条，每一条内容的格式为{"key":"表单参数键值对的key"，"value":"表单参数键值对的value"，"type":"text/file"，"file":"后端转换处理后的文件名称"}
            "form_urlencoded": [...]
                支持填写多条，每一条内容的格式为["表单参数键值对的key"，"表单参数键值对的value"]
            "raw_body": ""
                文本形式的内容
        }
"""

import urllib3
import re
import copy
import time
import json

from ..request import RequestPlugin


class HttpRequest(RequestPlugin):
    requestPool = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化公共连接池
        if not HttpRequest.requestPool:
            HttpRequest.requestPool = urllib3.PoolManager(self.base_user_num)
        # 添加插件自有属性
        # 请求
        self.request_method = ''
        self.request_method_lower = ''
        self.request_url = ''
        # self.request_encode = ''
        self.request_headers = {}
        self.request_headers_lower = {}
        self.request_body_type = 0
        self.request_body_content = None
        self.request_timeout = 0
        self.request_port = ''
        # 返回
        self.response = None
        self.response_headers = []
        self.response_body_content = None
        self.response_code = 0
        self.request_details = {}
        # 根据传入的数据,进行数据检查
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    @staticmethod
    def check_single_header(headers):
        for pivh in headers:
            if type(pivh) is not list or len(pivh) != 2:
                return False
            elif type(pivh[0]) is not str or type(pivh[1]) is not str:
                return False
        return True

    @staticmethod
    def check_body_formdata(form_data):
        for pivf in form_data:
            if type(pivf) is not dict:
                return False
            else:
                if 'key' not in pivf or type(pivf['key']) is not str:
                    return False
                elif 'value' not in pivf or type(pivf['value']) is not str:
                    return False
                elif 'type' not in pivf or type(pivf['type']) is not str or pivf['type'] not in ('text', 'file'):
                    return False
                elif 'file' not in pivf or type(pivf['file']) is not str:
                    return False
                elif 'mime' not in pivf or type(pivf['mime']) is not str:
                    return False
        return True

    @staticmethod
    def check_body_urlencoded(form_data):
        for pivfu in form_data:
            if type(pivfu) is not list or len(pivfu) != 2:
                return False
            else:
                if type(pivfu[0]) is not str:
                    return False
                elif type(pivfu[1]) is not str:
                    return False
        return True

    def check_before_run(self):
        """
        初始化说明点
        1 method:数据类型str,且仅支持get/post方式
        2 url:数据类型str
        3 headers:数据类型list.list中各项数据的数据类型亦为list,长度2
            0位置数据类型str;
            1位置数据类型str
        4 body_type:数据类型int,且仅支持0,1,2
        5 form_data/form_urlencoded/raw_body:不同的body_type获取对应的数据
            5.1 form_data:数据类型list.list中各项数据的类型为dict,且有key/value/type/file/mime五项数据
                五项数据的数据类型均为str,且type仅支持text/file
            5.2 form_urlencoded:数据类型list.list中各项数据的数据类型亦为list,长度2
                0位置数据类型str;
                1位置数据类型str
            5.3 raw_body:数据类型str
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
            # method
            if 'method' not in plugin_init_value or type(plugin_init_value['method']) is not str:
                log += '请求类型检查失败,原因:请求类型整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['method'].lower() not in ['get', 'post']:
                log += '请求类型检查失败,原因:所填写请求类型暂不不支持;'
                check_flag = False
            # url
            if 'url' not in plugin_init_value or type(plugin_init_value['url']) is not str:
                log += 'URL检查失败,原因:URL整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['url'] == '':
                log += 'URL检查失败,原因:URL不能为空;'
                check_flag = False
            # headers
            if 'headers' not in plugin_init_value or type(plugin_init_value['headers']) is not list:
                log += '请求头检查失败,原因:请求头整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif not self.check_single_header(plugin_init_value['headers']):
                log += '请求头检查失败,原因:请求头内容格式或数据类型非法;'
                check_flag = False
            # body_type
            if 'body_type' not in plugin_init_value or type(plugin_init_value['body_type']) is not int:
                log += '请求体类型检查失败,原因:请求体类型整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['body_type'] not in (0, 1, 2):
                log += '请求体类型检查失败,原因:请求体类型暂不不支持;'
                check_flag = False
            # body_content
            if plugin_init_value['body_type'] == 0:
                # form_data
                if 'form_data' not in plugin_init_value or type(plugin_init_value['form_data']) is not list:
                    log += 'form_data内容检查失败,原因:form_data整体数据缺失或数据异常,请联系管理员;'
                    check_flag = False
                elif not self.check_body_formdata(plugin_init_value['form_data']):
                    log += 'form_data内容检查失败,原因:form_data内容格式或数据类型非法;'
                    check_flag = False
            elif plugin_init_value['body_type'] == 1:
                # form_urlencoded
                if 'form_urlencoded' not in plugin_init_value or type(plugin_init_value['form_urlencoded']) is not list:
                    log += 'form_urlencoded内容检查失败,原因:form_urlencoded整体数据缺失或数据异常,请联系管理员;'
                    check_flag = False
                elif not self.check_body_urlencoded(plugin_init_value['form_urlencoded']):
                    log += 'form_urlencoded内容检查失败,原因:form_urlencoded内容格式或数据类型非法;'
                    check_flag = False
            elif plugin_init_value['body_type'] == 2:
                # raw_body
                if 'raw_body' not in plugin_init_value or type(plugin_init_value['raw_body']) is not str:
                    log += 'raw_body内容检查失败,原因:raw_body整体数据缺失或数据异常,请联系管理员;'
                    check_flag = False
            # connectTimeout
            if 'connectTimeout' not in plugin_init_value or type(plugin_init_value['connectTimeout']) is not int:
                log += '超时时间检查失败,原因:超时时间整体数据缺失或数据异常,请联系管理员;'
                check_flag = False
            elif plugin_init_value['connectTimeout'] < 0:
                log += '超时时间检查失败,原因:超时时间请填写自然数;'
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
            # method
            self.request_method = self.plugin_value['method']
            self.request_method_lower = self.request_method.lower()
            # url
            self.request_url = self.plugin_value['url']
            # headers
            # 将list转换为dict
            self.request_headers = {k: v for k, v in self.plugin_value['headers']}
            self.request_headers_lower = {k.lower(): v for k, v in self.request_headers.items()}
            # body_type
            self.request_body_type = self.plugin_value['body_type']
            # 根据body的类型,在header中没有content-type的时候,自动添加上对应type的header
            if 'content-type' not in self.request_headers_lower:
                if self.request_body_type == 0:
                    pass
                elif self.request_body_type == 1:
                    self.request_headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
                    self.request_headers_lower['content-type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
                elif self.request_body_type == 2:
                    self.request_headers['Content-Type'] = 'text/plain; charset=UTF-8'
                    self.request_headers_lower['content-type'] = 'text/plain; charset=UTF-8'
            # body_content
            if self.plugin_value['body_type'] == 0:
                self.request_body_content = {}
                # 数据转换
                for pivfd in self.plugin_value['form_data']:
                    if pivfd['type'] == 'text':
                        self.request_body_content[pivfd['key']] = pivfd['value']
                    else:
                        try:
                            with open('%s/files/%s' % (self.base_data['file_path'], pivfd['file']), mode='rb') as f:
                                self.request_body_content[pivfd['key']] = (pivfd['value'], f.read(), pivfd['mime'])
                        except Exception as e:
                            return False, '运行前插件所需文件打开失败,原因:%s;' % repr(e)
            elif self.plugin_value['body_type'] == 1:
                self.request_body_content = {}
                # 数据转换
                for pivfu in self.plugin_value['form_urlencoded']:
                    self.request_body_content[pivfu[0]] = pivfu[1]
            elif self.plugin_value['body_type'] == 2:
                self.request_body_content = self.plugin_value['raw_body']
            # connectTimeout
            self.request_timeout = self.plugin_value['connectTimeout']
            return True, None

    def run_test(self):
        # 禁止直接使用原始日志
        self.plugin_run_log = copy.copy(self.plugin_base_run_log)
        # 公共日志部分
        self.plugin_run_log["id"] = self.plugin_id
        self.plugin_run_log["oid"] = self.plugin_oid
        self.plugin_run_log["wid"] = self.worker_info_id
        self.plugin_run_log["uid"] = self.vuser_index
        self.plugin_run_log["st"] = round(time.time()*1000)
        # 运行前数据填充
        run_init_result, run_init_log = self.init_before_run()
        if run_init_result:
            self.plugin_run_log["hr_u"] = self.request_url
            # 根据请求类型执行不同代码段
            try:
                if self.request_method_lower == 'get':
                    self.response = HttpRequest.requestPool.request(
                        method=self.request_method,
                        timeout=self.request_timeout,
                        url=self.request_url,
                        headers=self.request_headers,
                        retries=0
                    )
                elif self.request_method_lower == 'post':
                    if self.request_body_type == 0:
                        the_boundary = ''
                        if "content-type" in self.request_headers_lower:
                            the_boundary = re.findall('boundary=(.*)', self.request_headers_lower["content-type"])
                        self.response = HttpRequest.requestPool.request(
                            method=self.request_method,
                            url=self.request_url,
                            timeout=self.request_timeout,
                            headers=self.request_headers,
                            multipart_boundary=the_boundary[1] if len(the_boundary) > 0 else None,
                            fields=self.request_body_content,
                            retries=0
                        )
                    elif self.request_body_type == 1:
                        self.response = HttpRequest.requestPool.request(
                            method=self.request_method,
                            url=self.request_url,
                            fields=self.request_body_content,
                            timeout=self.request_timeout,
                            headers=self.request_headers,
                            encode_multipart=False,
                            retries=0
                        )
                    else:
                        self.response = HttpRequest.requestPool.request(
                            method=self.request_method,
                            url=self.request_url,
                            timeout=self.request_timeout,
                            headers=self.request_headers,
                            body=self.request_body_content,
                            retries=0
                        )
            except Exception as e:
                self.plugin_run_log['et'] = round(time.time()*1000)
                self.plugin_run_log['t'] = round((self.plugin_run_log['et'] - self.plugin_run_log['st']))
                self.plugin_run_log['s'] = False
                self.plugin_run_log['f'] = '请求发生错误:%s;' % repr(e)
                self.response_code = -1
                self.plugin_run_log["c"] = -1
            else:
                self.plugin_run_log['et'] = round(time.time()*1000)
                self.plugin_run_log['t'] = round((self.plugin_run_log['et'] - self.plugin_run_log['st']))
                # 这块多多测试,感觉会有问题
                if self.response:
                    self.plugin_run_log["hr_rh"] = json.dumps(self.response.info_map['rq_h'])
                    self.plugin_run_log["hr_rhl"] = self.response.info_map['rq_hl']
                    self.plugin_run_log["hr_rb"] = self.response.info_map['rq_b'][:10485760]  # 请求体信息(httpRequest插件用),限制10MB大小
                    self.plugin_run_log["hr_rbl"] = self.response.info_map['rq_bl']
                    self.plugin_run_log["rl"] = self.plugin_run_log["hr_rhl"] + self.plugin_run_log["hr_rbl"]
                    self.response_code = self.response.status
                    self.plugin_run_log["c"] = self.response.status
                    # 客户端和服务端出错时将结果置为失败
                    if self.response.status > 399:
                        self.plugin_run_log['s'] = False
                        self.plugin_run_log['f'] = '请求失败，请求返回码：%d;' % self.response.status
                    else:
                        self.plugin_run_log['s'] = True
                        self.plugin_run_log['f'] = '请求成功;'
                    self.plugin_run_log["hr_rsh"] = json.dumps(dict(self.response.getheaders()))
                    self.plugin_run_log["hr_rshl"] = len(str(self.response._fp.headers))
                    try:
                        hr_rsb = self.response.data.decode('utf-8')  # 返回体信息(httpRequest插件用)
                    except Exception as e:
                        self.plugin_run_log["hr_rsb"] = '返回内容UTF8解码失败，内容类型暂不支持显示：%s' % repr(e)
                    else:
                        self.plugin_run_log["hr_rsb"] = hr_rsb[:10485760]  # 限制10MB大小
                    self.plugin_run_log["hr_rsbl"] = self.response._fp_bytes_read
                    self.plugin_run_log["rsl"] = self.plugin_run_log["hr_rshl"] + self.plugin_run_log["hr_rsbl"]
                    self.response_body_content = self.response.data.decode('utf-8')
                    # 获取头是否有更好的方式
                    self.response_headers = dict(self.response.getheaders())
                else:
                    # response是否需要判空,且可能为文件
                    # 本处逻辑后续补全
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
            self.plugin_run_log['et'] = round(time.time()*1000)
            self.plugin_run_log['t'] = round((self.plugin_run_log['et'] - self.plugin_run_log['st']))
            self.plugin_run_log['s'] = False
            self.plugin_run_log['f'] = '请求发生错误:%s;' % run_init_log

        # 调用方法将运行日志暂存至日志控制器
        self.run_log_controller.set(self.plugin_run_log)
