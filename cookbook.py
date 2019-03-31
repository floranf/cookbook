#!/usr/local/bin/python3.6
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

class RecipeException(Exception):
    def __init__(self, message):
        self.message = message
        
    def __str__(self):
        return self.message


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
        self.publish = True
        self.img = ""

        if 'publish' in data:
            self.publish = data['publish']

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

        if 'groups' in data and data['groups']:
            for group in data['groups']:
                if group in config.groups.keys():
                    config.groups[group]['recipes'].append(self)
                else:
                    raise RecipeException(f'the group "${group}" does not exist')
        
        config.recipes.append(self)


def process_file(file, output_dir=None):
    #print(f'--> {file}')
    basename = file.name
    name = file.stem
    try:
        with file.open() as f:
            recipe = Recipe(yaml.load(f))
            if not recipe.publish:
                return
            source_imagefile = file.with_suffix('.png')
            print(f"check for image = {source_imagefile}")
            if source_imagefile.exists():
                recipe.img = source_imagefile.name
            if output_dir:
                output_file = Path(output_dir, name).with_suffix('.rst')
                print(f'output file --> {output_file}')
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                with output_file.open('w') as out_file:
                    recipe_to_rst(recipe, out_file)
                if recipe.img:
                    output_imagefile = output_file.with_suffix('.png')
                    print(f"output image = {output_imagefile}")
                    shutil.copyfile(source_imagefile, output_imagefile)

    except RecipeException as e:
        print(f'ERROR: {file}: {e!s}')
        sys.exit(1)
    except Exception as e:
        print(f'[!]: {file}: {e!s}')
        traceback.print_exc()


def process_dir(root, output_dir):
    basename = root.name
    for dirpath, dirnames, filenames in os.walk(root):
        # if we dont have an output, we only validate each input file
        if output_dir:
            output_dir = os.path.join(
                output_dir.strip(os.pathsep), # this is where we want the output
                basename, # the name of the source dir given on the command line
                dirpath.replace(str(root),'').lstrip(os.pathsep) # relative path by removing the root
            )
        for file in filenames:
            if file.endswith('.yaml'):
                process_file(
                    Path(dirpath,file),
                    output_dir
                )


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
@click.option('--output', '-o',
    type=click.Path(exists=False),
    help='Set the output directory for the translated files. It activate the translation; if no output set, only validation is done.')
@click.argument('files', nargs=-1, type=click.Path(exists=True))
def main(files, output):
    # process all recipes files
    for p in [Path(f) for f in files]:
        if p.is_dir():
            process_dir(p, output)
        elif p.is_file():
            process_file(p, output)

    # generate all groups
    
    p = Path(output, 'groups')
    p.mkdir(parents=True, exist_ok=True)
    for group in config.groups.values():
        if not len(group['recipes']):
            continue
        p = Path(output, 'groups', group['title'] + '.rst')
        with p.open(mode='w') as f:
            group_to_rst(group, f)

        

if __name__ == '__main__':
    main()


