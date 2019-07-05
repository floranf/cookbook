#!/usr/local/bin/python3.7
# -*- coding: utf-8 -*-

import traceback
import yaml
import click
import sys
import re
import os
import uuid
import jinja2
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
import config


class CookbookException(Exception):
    def __init__(self, message=""):
        self.message = message

    def __str__(self):
        return f"{self.message}: {self.__cause__}"


class SourceException(CookbookException):
    def __init__(self, filename, message=""):
        CookbookException.__init__(self, message)
        self.filename = filename
        
    def __str__(self):
        return f"{self.filename}: {CookbookException.__str__(self)}"


class RecipeException(CookbookException):
    pass


class IngredientException(RecipeException):
    pass


class StepException(RecipeException):
    pass


class Ingredient:
    ''' Format: id. (quantity) name; details'''
    
    def __init__(self, data):
        r = re.compile('''^(?P<id>[A-Z]+\.) *(\((?P<quantity>[^)]+)\))? *(?P<name>[^;]+)? *(; *(?P<details>.*))?''')
        m = r.match(data)
        if not m:
            raise IngredientException(f'invalid ingredient definition: {data!s}')

        self.id = m.group('id')
        if not self.id:
            raise IngredientException(f'missing ingredient id: {data!s}')
        self.id = self.id.strip('.')

        self.quantity = m.group('quantity')
        if not self.quantity:
            raise IngredientException(f'missing ingredient quantity: {data!s}')

        self.name = m.group('name')
        if not self.name:
            raise IngredientException(f'missing ingredient name: {data!s}')

        # details are optional 
        self.details = m.group('details')
        

    def __str__(self):
        details = ""
        if self.details:
            details = f"; {self.details}"
        return f'{self.id}. ({self.quantity}) {self.name}{details}'


class Step:
    ''' Format: id. (quantity list)+ action'''
    
    def __init__(self, data):
        r = re.compile('''^(?P<id>[0-9]+\.)? *(\((?P<quantities>[^)]+)\))? *(?P<action>[^;]+)? *(; *(?P<details>.*))?''')
        m = r.match(data)
        if not m:
            raise StepException(f'***invalid step definition: {data!s}')

        self.id = m.group('id')
        if not self.id:
            raise StepException(f'missing step id: {data!s}')
        self.id = self.id.strip('.')

        # Quantities are optional
        self.quantities = []
        quantities = m.group('quantities')
        if quantities:
            self.quantities = quantities #.split(',')

        self.action = m.group('action')
        if not self.action:
            raise StepException(f'missing step action: {data!s}')

        # details are optional
        self.details = m.group('details')

    def __str__(self):
        quantities = ""
        if self.quantities:
            quantities = f"({', '.join(self.quantities)}) "
        details = ""
        if self.details:
            details = f"; {self.details}"
        return f'{self.id}. {quantities}{self.action}{details}'


class Recipe:
    '''
    A recipe must have: title, ingredients, steps
    should have: dates, images, intro
    ''' 
    def __init__(self, data):
        self.id = uuid.uuid4().hex
        self.sources = []
        self.title = ''
        self.ingredients = []
        self.steps = []
        self.img = ""
        self.tags = []

        if 'id' in data:
            self.id = data['id']

        if 'title' in data and data['title']:
            self.title = data['title']
        else:
            raise RecipeException('a recipe must have a title')

        self.ingredients = [Ingredient(i) for i in data['ingredients']]
        if not self.ingredients:
            raise RecipeException('a recipe must have one or more ingredients')

        self.steps = [Step(s) for s in data['steps']]
        if not self.steps:
            raise RecipeException('a recipe must have one or more steps')

        if 'sources' in data:
            self.sources = data['sources']

        if 'tags' in data:
            self.tags = data['tags']

        if 'groups' in data and data['groups']:
            for group in data['groups']:
                if group in config.groups.keys():
                    config.groups[group]['recipes'].append(self)
        
        config.recipes.append(self)


def process_file(file, output):
    """
    Process a recipe file.

    file : pathlib.Path
        The path to the recipe file to process.
    output : pathlib.Path
        The path to the directory for the rendered file.
        If we dont have an output, we will only validate each input file.
    """
    try:
        name = file.stem
        with file.open() as f:
            recipe = Recipe(yaml.safe_load(f))
            source_imagefile = file.with_suffix('.png')
            if source_imagefile.exists():
                recipe.img = source_imagefile.name
            if output:
                output_file = Path(output, name).with_suffix('.rst')
                if not os.path.exists(output):
                    os.makedirs(output)
                with output_file.open('w') as out_file:
                    recipe_to_rst(recipe, out_file)
                if recipe.img:
                    output_imagefile = output_file.with_suffix('.png')
                    shutil.copyfile(source_imagefile, output_imagefile)
    except CookbookException as ex:
        raise SourceException(str(file)) from ex
    except Exception as ex:
        raise SourceException(str(file), "unexpected exception while processing file") from ex


def process_dir(input, output):
    """
    Process an recipe directory.
    
    Parameters
    ----------
    input : pathlib.Path
        The path to de directory of recipes to process.
    output : pathlib.Path
        The path to the directory for the rendered files.
    """
    for dirpath, dirnames, filenames in os.walk(input):
        # build path to reflect the input directory structure
        if output:
            out = Path(output, input.name, Path(dirpath).relative_to(input))
        for file in filenames:
            if file.endswith('.yaml'):
                pass
                process_file(Path(dirpath, file), out)


jinja_env = Environment(
    loader = FileSystemLoader('./templates')
)

recipe_template = jinja_env.get_template('recipe.jinja2')
group_template = jinja_env.get_template('group.jinja2')


def recipe_to_rst(recipe, out_file):
    out_file.write(recipe_template.render(recipe=recipe))


def group_to_rst(group, out_file):
    out_file.write(group_template.render(group=group))


@click.command()
@click.option('--verbose', '-v',
    is_flag=True,
    help='Enable verbose output.')
@click.option('--output', '-o',
    type=click.Path(exists=False),
    help='Set the output directory for the translated files. It activate the translation; if no output set, only validation is done.')
@click.argument('inputs', nargs=-1, type=click.Path(exists=True))
def main(inputs, output, verbose):
    try:
        # process all recipes files
        for p in [Path(i) for i in inputs]:
            if p.is_dir():
                process_dir(p, output)
            elif p.is_file():
                process_file(p, output)
    
    except SourceException as e:
        print(f'[!]: {e!s}')
        if verbose:
            traceback.print_exc()
        return 1
    except Exception as e:
        print(f"Error: {e!s}")
        if verbose:
            traceback.print_exc()
        return 1

    # quick exit if there is no inputs
    if not inputs:
        return 0

    # generate all groups
    if output:
        p = Path(output, 'groups')
        p.mkdir(parents=True, exist_ok=True)
        for group in config.groups.values():
            if not len(group['recipes']):
                continue
            p = Path(output, 'groups', group['title'] + '.rst')
            with p.open(mode='w') as f:
                group_to_rst(group, f)
    return 0

        
if __name__ == '__main__':
    sys.exit(main())


