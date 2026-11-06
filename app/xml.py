# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from __future__ import annotations
import os
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

''' Tag name of <xi:include> node '''
XINCLUDE_TAG = '{http://www.w3.org/2001/XInclude}include'

''' Attribute name used to track which file a node originally came from
    (for nodes pulled in via <xi:include>) '''
SOURCE_FILE_ATTR = 'data-source-file'

'''
Recursively resolve <xi:include> nodes inside `node`.

Unlike xml.etree.ElementInclude, provenance is tracked: every node spliced
in from an included file is annotated with SOURCE_FILE_ATTR set to the
basename of the file it came from. The annotation uses "setdefault"
semantics, so a node inside a doubly-nested include keeps the basename of
the innermost file it was defined in.

Included XML documents are spliced whole (the included file's root element
takes the place of the <xi:include> node), which mirrors the behaviour of
xml.etree.ElementInclude for include nodes without xpointer.
Only parse="xml" includes are supported.
'''
def _resolve_xincludes(node: ET.Element, base_path: str, stack: tuple) -> None:
    for child in list(node):
        if child.tag != XINCLUDE_TAG:
            _resolve_xincludes(child, base_path, stack)
            continue

        href = child.attrib.get('href')
        if href is None:
            raise Exception('"href" attribute is required for <xi:include>')
        if child.attrib.get('parse', 'xml') != 'xml':
            raise Exception(f'only parse="xml" is supported for <xi:include> (href: "{href}")')

        path = os.path.normpath(href if os.path.isabs(href) else os.path.join(os.path.dirname(base_path), href))
        real_path = os.path.realpath(path)
        if real_path in stack:
            raise Exception(f'infinite loop detected while resolving <xi:include> href: "{href}"')

        sub_root = ET.parse(path).getroot()
        _resolve_xincludes(sub_root, path, stack + (real_path,))

        # annotate the included content with its source file,
        # but keep provenance of already-annotated (nested include) nodes
        source_file = os.path.basename(path)
        for el in sub_root.iter():
            el.attrib.setdefault(SOURCE_FILE_ATTR, source_file)

        # splice the whole included root element in place of the include node
        position = list(node).index(child)
        node.remove(child)
        node.insert(position, sub_root)

def load_xml_from_file(path: str) -> ET.Element:
    root = ET.parse(path).getroot()
    if root.tag == XINCLUDE_TAG:
        raise Exception('<xi:include> is not allowed as the root node')

    _resolve_xincludes(root, path, (os.path.realpath(path),))
    # label the schema's own nodes (already-annotated include nodes keep theirs)
    for el in root.iter():
        el.attrib.setdefault(SOURCE_FILE_ATTR, os.path.basename(path))

    # strip namespace
    for el in root.iter():
        _, _, el.tag = el.tag.rpartition('}')

    return root

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
