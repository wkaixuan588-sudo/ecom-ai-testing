# -*- coding: utf-8 -*-
"""Allure 集成：按目录自动打 layer 标签（unit/api），统一 epic 归属。"""
import allure


def pytest_collection_modifyitems(items):
    for item in items:
        path = str(item.fspath)
        if "/tests/unit/" in path:
            item.add_marker(allure.label("layer", "unit"))
        elif "/tests/api/" in path:
            item.add_marker(allure.label("layer", "api"))
        item.add_marker(allure.epic("电商订单计价系统"))
