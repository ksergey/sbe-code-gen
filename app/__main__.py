# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

import importlib
import sys
from argparse import ArgumentParser, SUPPRESS
from app.parser import Parser

def main() -> None:
    parser = ArgumentParser(prog='sbe-code-gen', description='SBE codec generator')
    parser.add_argument('--schema', help='path to xml schema', required=True)
    parser.add_argument('--destination', help='path to directory where codec will be written', required=True)
    parser.add_argument('--generator', help='choose generator (available: cpp, cppng)', default='cpp')

    args = parser.parse_args()

    try:
        module = importlib.import_module(f'app.generation.{args.generator}')
        Generator = getattr(module, 'Generator')

        schema = Parser.fromFile(args.schema).getSchema()
        generator = Generator(args.destination)
        generator.generate(schema)

    except Exception as e:
        sys.exit(f'error: {e}')

if __name__ == '__main__':
    main()
