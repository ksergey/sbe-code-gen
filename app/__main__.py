import importlib
from argparse import ArgumentParser, SUPPRESS
from app.parser import Parser

def main() -> None:
    parser = ArgumentParser(prog='sbe-code-gen', description='SBE codec generator')
    parser.add_argument('--schema', help='path to xml schema', required=True)
    parser.add_argument('--destination', help='path to directory where codec will be written', required=True)
    parser.add_argument('--generator', help=SUPPRESS, default='cpp')

    args = parser.parse_args()

    try:
        module = importlib.import_module(f'app.generation.{args.generator}')
        Generator = getattr(module, 'Generator')

        schema = Parser.fromFile(args.schema).getSchema()
        generator = Generator(args.destination)
        generator.generate(schema)

    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()
