#!/usr/local/bin/python3.7
# -*- coding: utf-8 -*-

import yaml
import re
import os
import uuid
import importlib
from pathlib import Path
from loguru import logger
import inspect
from distutils.dir_util import copy_tree
from distutils.dir_util import remove_tree

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
        r = re.compile(r'''^(?P<id>[A-Z]+\.) *(\((?P<quantity>[^)]+)\))? *(?P<name>[^;]+)? *(; *(?P<details>.*))?''')
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
        r = re.compile(r'''^(?P<id>[0-9]+\.)? *(\((?P<quantities>[^)]+)\))? *(?P<action>[^;]+)? *(; *(?P<details>.*))?''')
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
            self.quantities = quantities  # .split(',')

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


class Book:
    def __init__(self, data):
        self.title = data['title']
        self.descriptions = data['descriptions'] 
        self.authors = data['authors']
        self.revision = data['revision']
        self.renderer = data['renderer']

def _process_file(file, recipes):
    """
    Process a recipe file and add it to the recipes list.

    file : pathlib.Path
        The path to the recipe file to process.
    recipes : list
        The list of recipes to add to.
    """
    logger.info(f'processing file: {file}')
    try:
        with file.open() as f:
            data = yaml.safe_load(f)
            if not data:
                logger.warning(f'empty file found: {file}')
                return
            recipe = Recipe(data)
            # Look for the image to go with this recipe.
            # The image file name must be the as the recipe.  
            for format in ['.png', '.jpeg']:
                source_imagefile = file.with_suffix(format)
                if source_imagefile.exists():
                    recipe.img = source_imagefile.name
                    break
            recipes.append(recipe)
    except CookbookException as ex:
        raise SourceException(str(file)) from ex
    except Exception as ex:
        raise SourceException(str(file), "unexpected exception while processing file") from ex


def _process_dir(input, recipes):
    """
    Process an recipe directory.

    Parameters
    ----------
    input : pathlib.Path
        The path to de directory of recipes to process.
    recipes : list
        The list of recipes to add to.
    """
    for dirpath, dirnames, filenames in os.walk(input):
        for file in filenames:
            if Path(file).name == "book.yaml":
                continue
            if file.endswith('.yaml'):
                _process_file(Path(dirpath, file), recipes)


def load_book(inputs):
    #breakpoint()
    for p in [Path(i) for i in inputs]:
        if p.is_dir():
            f = Path(p,'book.yaml')
            if f.exists():
                return Book(yaml.safe_load(f.open()))
        elif p.is_file():
            if p.name == "book.yaml":
                return Book(yaml.safe_load(p.open()))
    return None


def load_recipes(inputs):
    recipes = list()
    for p in [Path(i) for i in inputs]:
        if p.is_dir():
            _process_dir(p, recipes)
        elif p.is_file():
            if p.name == "book.yaml":
                continue
            _process_file(p, recipes)
    return recipes


def render(book, recipes, output):
    logger.info(f'loading renderer: {book.renderer}')
    module = importlib.import_module(f'cookbook.renderers.{book.renderer}.renderer')
    #logger.info(dir(module.Renderer))
    basePath = Path(inspect.getfile(module)).parent
    ressourcesPath = Path(basePath, "ressources")
    skeletonPath = Path(basePath, "skeleton")
    out = Path(output)
    if out.exists():
        remove_tree(str(out))
    copy_tree(str(skeletonPath), str(out))




