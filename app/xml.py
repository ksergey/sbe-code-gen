from __future__ import annotations
import xml.etree.ElementTree as ET
from typing import ClassVar, Optional, Any

class SentinelClass:
    _instance: ClassVar[Optional[SentinelClass]] = None

    @staticmethod
    def getInstance() -> SentinelClass:
        if SentinelClass._instance is None:
            SentinelClass._instance = SentinelClass()
        return SentinelClass._instance

SENTINEL = SentinelClass.getInstance()

def loadXMLFromFile(path: str) -> ET.Element:
    file = open(path, 'r', encoding='utf-8')
    it = ET.iterparse(file)

    # strip namespace
    for _, el in it:
        _, _, el.tag = el.tag.rpartition('}')

    root = it.root

    def inject(node: ET.Element, root: ET.Element):
        for child in node:
            child.attrib['__root__'] = root
            inject(child, root)

    inject(root, root)

    return root


def documentRoot(node: ET.Element) -> ET.Element:
    return node.attrib.get('__root__')

def attr(node: ET.Element, name: str, default: Any = SENTINEL, cast = SENTINEL) -> Any:
    if name in node.attrib:
        if isinstance(cast, SentinelClass):
            return node.attrib[name]
        else:
            return cast(node.attrib[name])
    else:
        if isinstance(default, SentinelClass):
            raise Exception(f'attribute "{name}" not found in xml-node ({node})')
        return default
