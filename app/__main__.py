from app.schema import Schema
from app.generator_cpp import GeneratorCpp

PATH = 'b3-market-data-messages-1.3.1.xml'

def main() -> None:
    # TODO: args
    schema = Schema.loadFromFile(PATH)
    GeneratorCpp('result').run(schema)

if __name__ == '__main__':
    main()
