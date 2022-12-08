# Copyright 2022 XProbe Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect
from typing import TYPE_CHECKING, Callable, Dict, Set

import pandas

from ...core.adapter import (
    MARS_DATAFRAME_GROUPBY_TYPE,
    MARS_DATAFRAME_TYPE,
    MARS_SERIES_GROUPBY_TYPE,
    MARS_SERIES_TYPE,
    MarsCachedAccessor,
    MarsDatetimeAccessor,
    MarsEWM,
    MarsExpanding,
    MarsRolling,
    MarsStringAccessor,
    from_mars,
    mars_dataframe,
    register_converter,
    register_execution_condition,
    wrap_mars_callable,
)

if TYPE_CHECKING:
    from ...core.adapter import MarsEntity


# functions and class constructors defined by mars dataframe


def _collect_module_callables() -> Dict[str, Callable]:
    mars_dataframe_callables = dict()

    # install class constructors.
    mars_dataframe_callables[mars_dataframe.DataFrame.__name__] = wrap_mars_callable(
        mars_dataframe.DataFrame,
        attach_docstring=True,
        is_cls_member=False,
        docstring_src_module=pandas,
        docstring_src=pandas.DataFrame,
    )
    mars_dataframe_callables[mars_dataframe.Series.__name__] = wrap_mars_callable(
        mars_dataframe.Series,
        attach_docstring=True,
        is_cls_member=False,
        docstring_src_module=pandas,
        docstring_src=pandas.Series,
    )
    mars_dataframe_callables[mars_dataframe.Index.__name__] = wrap_mars_callable(
        mars_dataframe.Index,
        attach_docstring=True,
        is_cls_member=False,
        docstring_src_module=pandas,
        docstring_src=pandas.Index,
    )
    # install module functions
    for name, func in inspect.getmembers(mars_dataframe, inspect.isfunction):
        mars_dataframe_callables[name] = wrap_mars_callable(
            func,
            attach_docstring=True,
            is_cls_member=False,
            docstring_src_module=pandas,
            docstring_src=getattr(pandas, name, None),
        )

    return mars_dataframe_callables


MARS_DATAFRAME_CALLABLES: Dict[str, Callable] = _collect_module_callables()


def _collect_dataframe_magic_methods() -> Set[str]:
    magic_methods = set()

    magic_methods_to_skip: Set[str] = {
        "__init__",
        "__dir__",
        "__repr__",
        "__str__",
        "__setattr__",
        "__getattr__",
    }
    all_cls = (
        MARS_DATAFRAME_TYPE
        + MARS_SERIES_TYPE
        + MARS_DATAFRAME_GROUPBY_TYPE
        + MARS_SERIES_GROUPBY_TYPE
    )
    for mars_cls in all_cls:
        for name, _ in inspect.getmembers(mars_cls, inspect.isfunction):
            if (
                name.startswith("__")
                and name.endswith("__")
                and name not in magic_methods_to_skip
            ):
                magic_methods.add(name)
    return magic_methods


MARS_DATAFRAME_MAGIC_METHODS: Set[str] = _collect_dataframe_magic_methods()


def _register_execution_conditions() -> None:
    def _on_dtypes_being_none(mars_entity: "MarsEntity"):
        if hasattr(mars_entity, "dtypes") and mars_entity.dtypes is None:
            return True
        return False

    register_execution_condition(
        mars_dataframe.DataFrame.__name__, _on_dtypes_being_none
    )


_register_execution_conditions()


@register_converter(
    from_cls_list=[
        MarsStringAccessor,
        MarsDatetimeAccessor,
        MarsCachedAccessor,
        MarsEWM,
        MarsExpanding,
        MarsRolling,
    ]
)
class MarsGetAttrProxy:
    def __init__(self, mars_obj):
        self._mars_obj = mars_obj

    def __getattr__(self, item):
        attr = getattr(self._mars_obj, item)
        if callable(attr):
            return wrap_mars_callable(attr, attach_docstring=False, is_cls_member=True)
        else:
            return from_mars(attr)
