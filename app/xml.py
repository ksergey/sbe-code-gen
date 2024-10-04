# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from __future__ import annotations
import xml.etree.ElementTree as ET
from typing import ClassVar, Optional, Any

class SentinelClass:
    instance_: ClassVar[Optional[SentinelClass]] = None

    @staticmethod
    def getInstance() -> SentinelClass:
        if SentinelClass.instance_ is None:
            SentinelClass.instance_ = SentinelClass()
        return SentinelClass.instance_

SENTINEL = SentinelClass.getInstance()

def load_xml_from_file(path: str) -> ET.Element:
    file = open(path, 'r', encoding='utf-8')
    it = ET.iterparse(file)

    # strip namespace
    for _, el in it:
        _, _, el.tag = el.tag.rpartition('}')

    return it.root

def attr(node: ET.Element, name: str, default: Any = SENTINEL, cast = SENTINEL) -> Any:
    if name in node.attrib:
        if isinstance(cast, SentinelClass):
            return node.attrib[name]
        else:
            try:
                return cast(node.attrib[name])
            except (ValueError, TypeError):
                raise Exception(f'can\'t cast "{node.attrib[name]}" to "{cast}"')
    else:
        if isinstance(default, SentinelClass):
            raise Exception(f'attribute "{name}" not found in xml-node ({node})')
        return default
