# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

import importlib
import traceback
import sys
from argparse import ArgumentParser
from app.parser import Parser

def main() -> None:
    parser = ArgumentParser(prog='sbe-code-gen', description='SBE codec generator')
    parser.add_argument('--schema', help='path to xml schema', required=True, action='append')
    parser.add_argument('--destination', help='path to directory where codec will be written', required=True)
    parser.add_argument('--generator', help='choose generator (available: cpp-min, cpp-split, python)', default='cpp-min')
    parser.add_argument('--package', help='override schema package property')
    parser.add_argument('--bundle', help='generate all --schema occurrences into one destination '
                        '(support.h + fragment headers + one <package>/schema.h per schema); '
                        'only cpp-split currently supports it',
                        action='store_true')

    args = parser.parse_args()

    try:
        module = importlib.import_module(f'app.generation.{args.generator}')
        Generator = getattr(module, 'Generator')
        if args.bundle:
            if args.package:
                raise Exception('--package is not supported together with --bundle')
            generate_bundle = getattr(module, 'generate_bundle', None)
            if generate_bundle is None:
                raise Exception(f'generator "{args.generator}" does not support --bundle')
            schemas = [Parser.from_file(path).get_schema() for path in args.schema]
            generate_bundle(schemas, args.destination)
        else:
            if len(args.schema) > 1:
                raise Exception('multiple --schema occurrences require --bundle')
            schema = Parser.from_file(args.schema[0]).get_schema()
            generator = Generator(args.destination)
            generator.generate(schema, package=args.package)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        sys.exit(f'error: {e}')

if __name__ == '__main__':
    main()
