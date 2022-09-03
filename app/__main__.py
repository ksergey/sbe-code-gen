from argparse import ArgumentParser
from app.parser import Parser
from app.generator_cpp import GeneratorCpp

def main() -> None:
    parser = ArgumentParser(prog='sbe-code-gen', description='SBE codec generator')
    parser.add_argument('--schema', help='path to xml schema', required=True)
    parser.add_argument('--destination', help='path to directory where codec will be written', required=True)

    args = parser.parse_args()

    schema = Parser.fromFile(args.schema).getSchema()
    generator = GeneratorCpp(args.destination)
    generator.generate(schema)

if __name__ == '__main__':
    main()
