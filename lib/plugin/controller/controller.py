# -*- coding: utf-8 -*-

from ..basePlugin import BasePlugin


class ControllerPlugin(BasePlugin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 根据传入的数据，初始化插件本身
        self.plugin_check_result, self.plugin_check_log = self.check_before_run()

    def run_test(self):
        for pc in self.plugins_configuration:
            pc.run_test()
        # 本插件仅提供简单的插件集合功能，本身无功能逻辑，故跳过自身的测试步骤，执行子插件的测试
        for pcc in self.plugins_common:
            pcc.run_test()
