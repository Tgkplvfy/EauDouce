# -*- coding: utf-8 -*-
"""
    EauDouce.libs.plugins
    ~~~~~~~~~~~~~~

    Plugins Manager: load and run plugins.

    :copyright: (c) 2017 by Mr.tao.
    :license: MIT, see LICENSE for more details.
"""

import os
from utils.tool import plugin_logger

class PluginManager(object):
    """
    定义插件基类, 遵循格式如下:
    插件为目录, 目录名称为插件名称, 插件入口文件是__init__.py, 文件内包含name、description、version、author、license、url、README、state等插件信息.
    静态资源请通过提供的接口上传至又拍云.
    plugins/
    ├── plugin1
    │   ├── __init__.py
    │   ├── LICENSE
    │   ├── README
    │   └── templates
    │       └── plugin1
    └── plugin2
        ├── __init__.py
        ├── LICENSE
        ├── README
        └── templates
            └── plugin2
    """

    def __init__(self):
        self.plugins     = []
        self.plugin_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins")
        self.__scanPlugins()

    def __getPluginInfo(self, package, plugin):
        """ 组织插件信息 """
        try:
            url = plugin.__url__
        except AttributeError:
            url = None

        try:
            license = plugin.__license__
        except AttributeError:
            license = None

        try:
            license_file = plugin.__license_file__
        except AttributeError:
            license_file = None

        try:
            readme_file = plugin.__readme_file__
        except AttributeError:
            readme_file = None

        try:
            plugin_state = plugin.__state__
        except AttributeError:
            plugin_state = "enabled"

        return {
            "plugin_name": plugin.__name__,
            "plugin_description": plugin.__description__,
            "plugin_version": plugin.__version__,
            "plugin_author": plugin.__author__,
            "plugin_url": url,
            "plugin_license": license,
            "plugin_license_file": license_file,
            "plugin_readme_file": readme_file,
            "plugin_state": plugin_state,
            "plugin_tpl_path": os.path.join("plugins", package, "templates"),
            "plugin_tpl_tep": {},
            "plugin_cep": {}
        }

    def __scanPlugins(self):
        """ 扫描插件目录 """
        plugin_logger.info("Initialization Plugins Start, loadPlugins path: {0}".format(self.plugin_path))
        if os.path.exists(self.plugin_path):
            for package in os.listdir(self.plugin_path):
                _plugin_path = os.path.join(self.plugin_path, package)
                if os.path.isdir(_plugin_path):
                    if os.path.isfile(os.path.join(_plugin_path, "__init__.py")):
                        plugin_logger.info("find plugin package: {0}".format(package))
                        self.__runPlugins(package)
        else:
            plugin_logger.warning("Plugins directory not in here!")

    def __runPlugins(self, package):
        """ 动态加载插件模块,遵循插件格式的才能被启用并运行,否则删除加载 """

        #: 动态加载模块(plugins.package): 可以查询自定义的信息, 并通过getPluginClass获取插件的类定义
        plugin = __import__("{0}.{1}".format("plugins", package), fromlist=["plugins",])
        #: 检测插件信息
        if plugin.__name__ and plugin.__version__ and plugin.__description__ and plugin.__author__:
            #: 获取插件信息
            pluginInfo = self.__getPluginInfo(package, plugin)
            #: 获取插件主类并实例化
            p = plugin.getPluginClass()
            i = p()
            plugin_logger.info("runPlugin: package is {0}.{1}, class instance is {2}".format("plugins", package, i))
            #: 更新插件信息
            pluginInfo.update(plugin_instance=i)
            #: 运行插件主类的run方法
            if hasattr(i, "run"):
                i.run()
            #: 注册模板扩展点
            if hasattr(i, "register_tep"):
                tep = i.register_tep()
                plugin_logger.info("The plugin {0} wants to register the following template extension points: {1}".format(package, tep))
                if isinstance(tep, dict):
                    pluginInfo.update(plugin_tpl_tep=tep)
                    plugin_logger.info("Register TEP Success")
                else:
                    plugin_logger.error("Register TEP Failed, not a dict")
            #: 注册上下文扩展点
            if hasattr(i, "register_cep"):
                cep = i.register_cep()
                plugin_logger.info("The plugin {0} wants to register the following context extension points: {1}".format(package, cep))
                if isinstance(cep, dict):
                    pluginInfo.update(plugin_cep=cep)
                    plugin_logger.info("Register CEP Success")
                else:
                     plugin_logger.error("Register CEP Failed, not a dict")
            #: 加入全局插件中
            if hasattr(i, "run") or hasattr(i, "register_tep") or hasattr(i, "register_cep"):
                self.plugins.append(pluginInfo)
            else:
                plugin_logger.error("The current class {0} does not have the `run` or `register_tep` or `register_cep` method".format(i))
        else:
            del plugin
            plugin_logger.warning("This plugin `{0}` is not enabled without following the standard plugin format".format(package))

    @property
    def get_all_plugins(self):
        """ 获取所有插件 """
        return self.plugins

    @property
    def get_enabled_plugins(self):
        """ 获取所有启用的插件 """
        return [ p for p in self.get_all_plugins if p["plugin_state"] == "enabled" ]

    @property
    def get_all_tep(self):
        """模板扩展点, Template extension point, 分别对应基础模板的头部、导航、页脚、脚本, 博客详情页的头部、文章底部:
        TEP: base_front_header_include
        TEP: base_front_header_string
        TEP: base_front_navigation_include
        TEP: base_front_navigation_string
        TEP: base_front_footer_include
        TEP: base_front_footer_string
        TEP: base_front_script_include
        TEP: base_front_script_string
        TEP: blog_show_header_include
        TEP: blog_show_header_string
        TEP: blog_show_content_include
        """
        return dict(
            base_front_header_include     = lambda: [ plugin["plugin_tpl_tep"].get("base_front_header_include") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("base_front_header_include") ],
            base_front_header_string      = lambda: [ plugin["plugin_tpl_tep"].get("base_front_header_string") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("base_front_header_string") ],
            base_front_navigation_include = lambda: [ plugin["plugin_tpl_tep"].get("base_front_navigation_include") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("base_front_navigation_include") ],
            base_front_navigation_string  = lambda: [ plugin["plugin_tpl_tep"].get("base_front_navigation_string") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("base_front_navigation_string") ],
            base_front_footer_include     = lambda: [ plugin["plugin_tpl_tep"].get("base_front_footer_include") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("base_front_footer_include") ],
            base_front_footer_string      = lambda: [ plugin["plugin_tpl_tep"].get("base_front_footer_string") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("base_front_footer_string") ],
            base_front_script_include     = lambda: [ plugin["plugin_tpl_tep"].get("base_front_script_include") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("base_front_script_include") ],
            base_front_script_string      = lambda: [ plugin["plugin_tpl_tep"].get("base_front_script_string") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("base_front_script_string") ],
            blog_show_header_include      = lambda: [ plugin["plugin_tpl_tep"].get("blog_show_header_include") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("blog_show_header_include") ],
            blog_show_header_string       = lambda: [ plugin["plugin_tpl_tep"].get("blog_show_header_string") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("blog_show_header_string") ],
            blog_show_content_include     = lambda: [ plugin["plugin_tpl_tep"].get("blog_show_content_include") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("blog_show_content_include") ],
            blog_show_script_include     = lambda: [ plugin["plugin_tpl_tep"].get("blog_show_script_include") for plugin in self.get_enabled_plugins if plugin["plugin_tpl_tep"].get("blog_show_script_include") ],
        )

    @property
    def get_all_cep(self):
        """上下文扩展点, Context extension point, 分别对应请求前、请求后(返回前):
        CEP: before_request_hook
        CEP: after_request_hook
        """
        return dict(
            before_request_hook     = lambda: [ plugin["plugin_cep"].get("before_request_hook") for plugin in self.get_enabled_plugins if plugin["plugin_cep"].get("before_request_hook") ],
            after_request_hook      = lambda: [ plugin["plugin_cep"].get("after_request_hook") for plugin in self.get_enabled_plugins if plugin["plugin_cep"].get("after_request_hook") ],
        )

    @property
    def get_all_bep(self):
        """蓝图扩展点"""
        pass