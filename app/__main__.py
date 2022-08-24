from argparse import ArgumentParser
from app.schema import Schema
from app.generator_cpp import GeneratorCpp

PATH = 'b3-market-data-messages-1.3.1.xml'

def main() -> None:
    parser = ArgumentParser(prog='sbe-code-gen', description='SBE codec generator')
    parser.add_argument('--schema', help='path to xml schema', required=True)
    parser.add_argument('--destination', help='path to directory where codec will be written', required=True)
    args = parser.parse_args()

    schema = Schema.loadFromFile(args.schema)
    GeneratorCpp(args.destination).run(schema)

if __name__ == '__main__':
    main()
