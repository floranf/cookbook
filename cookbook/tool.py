import sys
import traceback
import click
from loguru import logger
from cookbook.parser import render, load_recipes, load_book, SourceException

@click.command()
@click.option('--renderer', '-r',
              help='Select the renderer to be used.')
@click.option('--verbose', '-v',
              is_flag=True,
              help='Enable verbose output.')
@click.option('--output', '-o',
              type=click.Path(exists=False),
              help='Set the output directory for the translated files. \
              It activate the translation; if no output set, only validation is done.')
@click.argument('inputs', nargs=-1, type=click.Path(exists=True))
def main(inputs, output, verbose, renderer):
    # quick exit if there is no inputs
    if not inputs:
        return 0
    try:
        book = load_book(inputs)
        recipes = load_recipes(inputs)
        if renderer:
            book.renderer = renderer
        if output:
            render(book, recipes)
    except SourceException as e:
        logger.error(f'[!]: {e!s}')
        if verbose:
            traceback.print_exc()
        return 1
    except Exception as e:
        logger.error(f"Error: {e!s}")
        if verbose:
            traceback.print_exc()
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())