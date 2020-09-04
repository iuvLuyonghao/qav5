# -*- coding: utf-8 -*-

import os
import timeit
import requests
import logging
from qav5.utils import Counter, merge_dicts

try:
    import simplejson as json
except (ImportError, SyntaxError):
    import json

C = Counter()


def _join_urls(root, *args):
    """拼接url

    :param root: 根路径
    :param args:
    :return:
    """
    urls = []
    if root.endswith(r"\/"):
        root = root[:-2]
    elif root.endswith("/"):
        root = root[:-1]
    urls.append(root)

    for path in args:
        if path is None or path.strip() == "":
            continue

        if path.startswith(r"\/"):
            path = path[2:]
        elif path.startswith("/"):
            path = path[1:]
        urls.append(path)
    return "/".join(urls)


class BaseClient:
    ELASTIC_ENV_HEADER = "x-env-flag"

    def __init__(self, base_url, session=None, **kwargs):
        self.base_url = base_url
        if session and not isinstance(session, requests.Session):
            raise TypeError('need the instance of requests.Session class')
        self.session = session
        self.response_handlers = []  # 移除默认的status_coder_checker ,不对3xx抛异常处理
        self.json_handlers = []
        self.interceptor = None
        self.logger = logging.getLogger(__name__)
        self.req_kwargs = dict(timeout=90)  # 默认超时时间

        # 提取特性环境标识
        elastic_env_flag = kwargs.pop("elastic_env_flag", None) or os.environ.get("HULK_ELASTIC_ENV_FLAG")
        if elastic_env_flag and elastic_env_flag != "base":  # base表示基础环境，在该环境不用传递特性环境标识
            self.req_kwargs['headers'] = {self.ELASTIC_ENV_HEADER: elastic_env_flag}

        self.req_kwargs.update(kwargs)
        self.on_performance_test = False  # 压力测试标识位,当True时即处于压力测试中,此时self.session应该为locust的HttpSession
        if os.environ.get("HULK_PROXY") and "proxies" not in kwargs:
            self.req_kwargs['proxies'] = {"http": os.environ.get("HULK_PROXY")}

        self._injector = dict()  # 用于存储临时执行注入的参数

    def _call_api(self, endpoint, method="post", req_kwargs=None, *, locust_extended=None, is_json_resp=True,
                  interceptor=None, disable_log=False):
        """http调用函数

        :param endpoint: 接口地址,用self.base_url拼接成完整的请求地址
        :param method: http请求方式
        :param req_kwargs: 透传给requests.request的请求参数（不包含url, method），* 后为间隔符，前面是位置参数，后面为命名关键字参数，命名关键字传参要指定名字，否则会报错
        :param locust_extended: locust.io扩展参数
        :param is_json_resp: 是否json响应
        :param interceptor: 该参数赋值后,会改变输出值
        :param disable_log: 部分接口不打印日志,如文件上传接口
        :return:
        """
        url = _join_urls(self.base_url, endpoint)
        req_id = C.counter
        kwargs = self.req_kwargs.copy()
        merge_dicts(kwargs, req_kwargs)

        if self.on_performance_test:
            extended_from_injector = self._injector.get("locust_extended", None)
            if extended_from_injector:  # 当压测时，优先从self._injector提取name,catch_response这两个额外参数，避免直接修改封装
                name = extended_from_injector.get("name", None)
                catch_response = extended_from_injector.get("catch_response", False)
                self._injector['locust_extended'] = None
            elif locust_extended is None:
                name = None
                catch_response = False
            else:
                name = locust_extended.get('name', None)
                catch_response = locust_extended.get('catch_response', False)
            return self.session.request(method, url, name=name, catch_response=catch_response, **kwargs)
            # 处于性能测试时,不再做下一步的解析, 直接返回locust中的对象;如果需要对返回内容做断言,请参考
            # http://docs.locust.io/en/latest/api.html

        if not disable_log:
            self.logger.info("start request", extra=dict(method=method, parameters=kwargs, url=url, request_id=req_id))

        if not self.session:
            self.session = requests.session()
        start = timeit.default_timer()
        response = self.session.request(method, url, **kwargs)

        if not disable_log:
            self.logger.info("got response", extra=dict(
                response=response.text, request_id=req_id, is_json_format=is_json_resp, url=response.url,
                status_code=response.status_code,
                latency=int((timeit.default_timer() - start) * 1000)))

        for handler in self.response_handlers:
            handler(response)

        response.raise_for_status()  # requests 自带对status code检查的方法,对>=400的status code 抛出异常

        if is_json_resp:
            try:
                resp_to_json = response.json()
            except ValueError:
                if not disable_log:
                    self.logger.error('convert response to json fail', extra=dict(request_id=req_id))
                raise
            else:
                for handler in self.json_handlers:
                    handler(resp_to_json)

        intercept_func = interceptor or self.interceptor
        return response if intercept_func is None else intercept_func(response, locals().get('resp_to_json', None))
