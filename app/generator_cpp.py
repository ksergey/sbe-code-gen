import os
import pathlib
from jinja2 import Environment, FileSystemLoader, select_autoescape
import app.schema
from app.common import *
from typing import Any

class AsFieldTypeWrapper:
    def __init__(self, type: Any) -> None:
        self.__dict__ = type.__dict__.copy()
        self.type = type
        self.offset = type.offsetAttr
        self.valueRef = type.constValue

class GeneratorCpp:
    def __init__(self, destDir: str) -> None:
        self._destDir = destDir
        self._env = Environment(
            loader=FileSystemLoader(f'{pathlib.Path(__file__).parent.resolve()}/cpp'),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        # replace tokens to cpp keywords
        self._env.filters['cpp'] = GeneratorCpp._cpp
        # emulate type behavior as field
        self._env.filters['asField'] = lambda var: AsFieldTypeWrapper(var)
        # test for types
        self._env.filters['isType'] = lambda var: isinstance(var, app.schema.EncodedDataType)
        self._env.filters['isComposite'] = lambda var: isinstance(var, app.schema.Composite)
        self._env.filters['isEnum'] = lambda var: isinstance(var, app.schema.Enum)
        self._env.filters['isSet'] = lambda var: isinstance(var, app.schema.Set)
        self._env.filters['isFloatingPoint'] = lambda var: var.primitiveType in [ 'float', 'double' ]
        self._env.filters['isChar'] = lambda var: var.primitiveType == 'char'
        self._env.filters['isField'] = lambda var: isinstance(var, app.schema.Field)
        self._env.filters['isGroup'] = lambda var: isinstance(var, app.schema.Group)
        self._env.filters['isData'] = lambda var: isinstance(var, app.schema.Data)
        # test for presence
        self._env.filters['isRequired'] = lambda var: var.presence == Presence.REQUIRED
        self._env.filters['isOptional'] = lambda var: var.presence == Presence.OPTIONAL
        self._env.filters['isConstant'] = lambda var: var.presence == Presence.CONSTANT
        # some manipulations
        self._env.filters['method0'] = lambda var: var[0].lower() + var[1:]
        self._env.filters['method1'] = lambda var: var[0].upper() + var[1:]
        self._env.filters['class'] = lambda var: var[0].upper() + var[1:]

    def run(self, schema: app.schema.Schema) -> None:
        if not os.path.exists(self._destDir):
            os.makedirs(self._destDir)

        package = None
        if schema.package is not None:
            package = schema.package.split('.')

        def generate(templateName: str, name: str, **kwargs):
            template = self._env.get_template(templateName)
            filename = self._env.filters['class'](name)
            with open(f'{self._destDir}/{filename}.h', mode = 'w', encoding = 'utf8') as o:
                o.write(template.render(**kwargs, schema = {
                    'id': schema.id,
                    'version': schema.version,
                    'package': package
                }))

        for type in schema.types.values():
            if isinstance(type, app.schema.Composite):
                generate('composite_impl.tmpl', type.name, composite=type, includes=self._includesFor(type))
            elif isinstance(type, app.schema.Enum):
                generate('enum_impl.tmpl', type.name, enum=type, includes=[])
            elif isinstance(type, app.schema.Set):
                generate('set_impl.tmpl', type.name, set=type, includes=[])

        for message in schema.messages.values():
            generate('message_impl.tmpl', message.name, message=message, includes=self._includesFor(message))

    def _includesFor(self, value: Any) -> list:
        result = []
        if isinstance(value, (app.schema.Message, app.schema.Group)):
            for field in value.fields:
                if isinstance(field, app.schema.Field):
                    if isinstance(field.type, (app.schema.Composite, app.schema.Enum, app.schema.Set)):
                        name = self._env.filters['class'](field.type.name)
                        result.append(f'{name}.h')
                elif isinstance(field, app.schema.Group):
                    name = self._env.filters['class'](field.dimensionType.name)
                    result.append(f'{name}.h')
                    result = result + self._includesFor(field)
                elif isinstance(field, app.schema.Data):
                    name = self._env.filters['class'](field.type.name)
                    result.append(f'{name}.h')

        return result

    @staticmethod
    def _cpp(value) -> str:
        return {
            'int8': 'std::int8_t',
            'int16': 'std::int16_t',
            'int32': 'std::int32_t',
            'int64': 'std::int64_t',
            'uint8': 'std::uint8_t',
            'uint16': 'std::uint16_t',
            'uint32': 'std::uint32_t',
            'uint64': 'std::uint64_t',
            'CHAR_NULL': '0',
            'CHAR_MIN': '0x20',
            'CHAR_MAX': '0x7e',
            'INT8_NULL': 'std::numeric_limits<std::int8_t>::min()',
            'INT8_MIN': 'std::numeric_limits<std::int8_t>::min() + 1',
            'INT8_MAX': 'std::numeric_limits<std::int8_t>::max()',
            'INT16_NULL': 'std::numeric_limits<std::int16_t>::min()',
            'INT16_MIN': 'std::numeric_limits<std::int16_t>::min() + 1',
            'INT16_MAX': 'std::numeric_limits<std::int16_t>::max()',
            'INT32_NULL': 'std::numeric_limits<std::int32_t>::min()',
            'INT32_MIN': 'std::numeric_limits<std::int32_t>::min() + 1',
            'INT32_MAX': 'std::numeric_limits<std::int32_t>::max()',
            'INT64_NULL': 'std::numeric_limits<std::int64_t>::min()',
            'INT64_MIN': 'std::numeric_limits<std::int64_t>::min() + 1',
            'INT64_MAX': 'std::numeric_limits<std::int64_t>::max()',
            'UINT8_NULL': 'std::numeric_limits<std::uint8_t>::max()',
            'UINT8_MIN': 'std::numeric_limits<std::uint8_t>::min()',
            'UINT8_MAX': 'std::numeric_limits<std::uint8_t>::max() - 1',
            'UINT16_NULL': 'std::numeric_limits<std::uint16_t>::max()',
            'UINT16_MIN': 'std::numeric_limits<std::uint16_t>::min()',
            'UINT16_MAX': 'std::numeric_limits<std::uint16_t>::max() - 1',
            'UINT32_NULL': 'std::numeric_limits<std::uint32_t>::max()',
            'UINT32_MIN': 'std::numeric_limits<std::uint32_t>::min()',
            'UINT32_MAX': 'std::numeric_limits<std::uint32_t>::max() - 1',
            'UINT64_NULL': 'std::numeric_limits<std::uint64_t>::max()',
            'UINT64_MIN': 'std::numeric_limits<std::uint64_t>::min()',
            'UINT64_MAX': 'std::numeric_limits<std::uint64_t>::max() - 1',
            'FLOAT_NULL': 'std::numeric_limits<float>::quiet_NaN()',
            'FLOAT_MIN': 'std::numeric_limits<float>::min()',
            'FLOAT_MAX': 'std::numeric_limits<float>::max()',
            'DOUBLE_NULL': 'std::numeric_limits<double>::quiet_NaN()',
            'DOUBLE_MIN': 'std::numeric_limits<double>::min()',
            'DOUBLE_MAX': 'std::numeric_limits<double>::max()'
        }.get(value, value)
