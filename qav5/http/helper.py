# -*- coding: utf-8 -*-

import re
from inspect import signature, _empty
from functools import wraps
try:
    import simplejson as json
except ImportError:
    import json


def _set_or_update_node(parent: dict, key: str, d: dict):
    if isinstance(parent.get(key, None), dict):
        parent[key].update(d)
    else:
        parent[key] = d


def smart_payload(func):
    """自动组装payload"""
    @wraps(func)
    def _wrapper(*args, **kwargs):
        func(*args, **kwargs)  # to raise TypeError

        parameters = signature(func).parameters
        arguments = list(parameters.keys())
        payload = {parameter.name: parameter.default for _, parameter in parameters.items() if parameter.default
                   is not _empty and parameter.name != "self"}
        if arguments[0] == "self":
            arguments.pop(0)
            args = args[1:]

        if args:
            for index, val in enumerate(args):
                arg_name = arguments[index]
                payload[arg_name] = val
        payload.update(kwargs)
        return payload
    return _wrapper


def api(rule, method="post", is_json_req=True, arg_handler=None, remove_null=False, hooks=None, **kwargs):
    """
    同时支持restful风格接口调用

    :param rule: 接口地址,如果是restful接口,则: /query/<id>/
    :param method: 请求方式 get/post/option ...
    :param is_json_req: 是否是json请求,如果传True，传给requests.request为 json=payload
    :param arg_handler: 定义后,可以更改参数名称,如将驼峰参数名修改为其lower_case
    :param remove_null: 是否移除payload中value为None|空字符串的key
    :param hooks: [function(client: BaseClient, method: str, request: requests.request入参)]
    :param kwargs: 具体参考BaseClient._call_api的请求参数
    :return:
    """

    def wrapper(func):
        @wraps(func)
        def _wrapper(self, *fargs, **fkwargs):
            payload = smart_payload(func)(self, *fargs, **fkwargs)

            # parse rule
            c = re.compile(r'<\S*?>')
            endpoint = rule
            paths = c.findall(endpoint)
            for path in paths:
                tp = path[1:-1]
                if tp not in payload:
                    raise ValueError("invalid restful api rule")
                else:
                    endpoint = endpoint.replace(path, str(payload.pop(tp)))  # url path must be string

            if remove_null:
                payload = {k: v for k, v in payload.items() if v not in(None, "")}

            if arg_handler:
                payload = {arg_handler(k): v for k, v in payload.items()}

            req_kwargs = kwargs.pop("req_kwargs", {})
            if method.upper() == "GET":
                _set_or_update_node(req_kwargs, 'params', payload)
            elif is_json_req:
                _set_or_update_node(req_kwargs, 'json', payload)
            else:
                _set_or_update_node(req_kwargs, 'datastore', payload)
            if hooks is not None:
                if callable(hooks):
                    # 用于提取Client接口的公共行为，比如将`self.token`写入请求头
                    # def request_with_token(client, method, request):
                    #     request['headers'] = {"Authentication": getattr(client, "token")}
                    hooks(self, method, req_kwargs)
                else:
                    for hook in hooks:
                        hook(self, method, req_kwargs)

            return self._call_api(endpoint, method, req_kwargs, **kwargs)
        return _wrapper
    return wrapper


def locust_injector(name=None, catch_response=None):
    """该装饰器用于在压测时，对封装后的接口方法临时注入name,catch_response两个额外的参数，避免直接修改代码改变这两个参数的值
    eg. :
    class SampleClient(BaseClient):
        def pay(self, amount):
            pass


    client = SampleClient()
    locust_injector(name="GET: /pay", catch_response=True)(client.pay)(100)

    :param name:
    :param catch_response:
    :return:
    """

    def wrapper(func):
        @wraps(func)
        def inject(*args, **kwargs):
            self = func.__self__
            extended = dict()
            if name is not None:
                extended['name'] = name
            if catch_response is not None:
                extended['catch_response'] = catch_response
            if extended:
                self._injector['locust_extended'] = extended

            return func(*args, **kwargs)
        return inject
    return wrapper


def register_node_only_once(node_name, node_cls):
    """只注册一次节点，多次调用返回已存在的node instance"""
    def wrapper(func):
        @wraps(func)
        def _wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)

            if node_name not in getattr(self, "_tree"):
                return getattr(self, "register_node")(node_name, node_cls)
            node_inst = getattr(self, "_tree")[node_name]
            if not isinstance(node_inst, node_cls):
                raise TypeError("expect: {}\tactual: {}".format(node_inst.__class__.__name__, node_cls.__name__))
            return node_inst
        return _wrapper
    return wrapper
