# -*- coding: utf-8 -*-

from collections import Iterable
from .model import datastore_attr_name


class DataStore:

    def __init__(self):
        self._current_namespace = self._default_namespace = self._objects = self._labels = self._groups = None
        self.reset()

    def reset(self):
        self._current_namespace = self._default_namespace = "main"
        self._objects = {self._default_namespace: {}}
        self._labels = {self._default_namespace: {}}
        self._groups = {self._default_namespace: {}}

    @property
    def namespace(self):
        return self._current_namespace

    @namespace.setter
    def namespace(self, val):
        self._current_namespace = val
        if val not in self._objects:
            self._objects[val] = {}
        if val not in self._labels:
            self._labels[val] = {}
        if val not in self._groups:
            self._groups[val] = {}

    @property
    def objects(self):
        main_objects = self._objects[self._default_namespace].copy()
        if self.namespace != self._default_namespace:
            main_objects.update(self._objects[self.namespace])
        return main_objects

    @property
    def labels(self):
        main_labels = self._labels[self._default_namespace].copy()
        if self.namespace != self._default_namespace:
            main_labels.update(self._labels[self.namespace])
        return main_labels

    @property
    def groups(self):
        if self.namespace == self._default_namespace:
            return self._groups[self._default_namespace]

        main_groups = {k: v[:] for k, v in self._groups[self._default_namespace].items()}

        ns_groups = self._groups[self.namespace]
        for group_name, obj_ids in ns_groups.items():
            if group_name not in main_groups:  # 该group不存在于主命名空间时
                main_groups[group_name] = obj_ids
            else:
                main_groups[group_name].extend(obj_ids)
        return main_groups

    def receive(self, data, label=None, group=None, namespace=None):
        namespace = namespace or self._default_namespace
        if not self._objects.get(namespace, None):
            self._objects[namespace] = dict()
        self._objects[namespace][data.id] = data
        setattr(data, datastore_attr_name, self)

        if label is not None:
            if not isinstance(label, str) and isinstance(label, Iterable):
                for t in label:
                    self._store_tag(data.id, t, namespace)
            else:
                self._store_tag(data.id, label, namespace)

        if group is not None:
            if not isinstance(group, str) and isinstance(group, Iterable):
                for g in group:
                    self._store_group(data.id, g, namespace)
            else:
                self._store_group(data.id, group, namespace)

    def _store_tag(self, obj_id, label, namespace=None):
        namespace = namespace or self._default_namespace
        if namespace not in self._labels:
            self._labels[namespace] = dict()
        self._labels[namespace][label] = obj_id

    def _store_group(self, obj_id, group, namespace=None):
        namespace = namespace or self._default_namespace
        if namespace not in self._groups:
            self._groups[namespace] = dict()
        if group not in self._groups[namespace]:
            self._groups[namespace][group] = [obj_id]
        else:
            self._groups[namespace][group].append(obj_id)

    def __getitem__(self, item):
        if item in self.labels:
            return self.find_obj_by_label(item)
        elif item in self.groups:
            return self.find_obj_by_group(item)
        else:
            raise KeyError("cannot find item: {}".format(item))

    def __getattr__(self, item):
        return self.__getitem__(item)

    def find_obj_by_id(self, obj_id):
        return self.objects.get(obj_id, None)

    def find_obj_by_label(self, label):
        obj_id = self.labels.get(label, None)
        if obj_id is None:
            return None
        return self.find_obj_by_id(obj_id)

    def find_obj_by_group(self, group):
        obj_ids = self.groups.get(group, None)
        if obj_ids is None:
            return None
        m = map(self.find_obj_by_id, obj_ids)
        return list(m)

    def find_obj(self, **kwargs):
        keys = list(self.objects.keys())
        for k, v in kwargs.items():
            for oid, obj in self.objects.items():
                if oid in keys:
                    if getattr(obj, k, None) == v:
                        pass
                    else:
                        keys.remove(oid)
                else:
                    continue

        if keys:
            return [self.objects[k] for k in keys]
        else:
            return None
