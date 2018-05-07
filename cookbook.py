#!/usr/local/bin/python3.6
# -*- coding: utf-8 -*-

import traceback
import yaml
import click
import sys
import re
import os
import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape

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
			self.quantities = quantities.split(',')

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
		self.source = None

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


def process_file(file, output_dir=None):
	#print(f'--> {file}')
	
	basename = os.path.basename(file)
	name,_,ext = basename.rpartition('.')

	try:
		with open(file,'r') as f:
			recipe = Recipe(yaml.load(f))
			
			if output_dir:
				#print(f'output file --> {output_file}')
				output_file = os.path.join(output_dir, f'{name}.rst')

				if not os.path.exists(output_dir):
					os.makedirs(output_dir)

				with open(output_file, 'w') as out_file:
					recipe_to_rst(recipe, out_file)

	except RecipeException as e:
		print(f'err: {file}: {e!s}')
	except Exception as e:
		print(f'[!]: {file}: {e!s}')
		traceback.print_exc()


def process_dir(root, output_dir):
	
	#print(f'root --> {root}')
	root = root.strip(os.pathsep)
	basename = os.path.basename(root)
	
	for dirpath, dirnames, filenames in os.walk(root):

		# if we dont have an output, we only validate each input file
		if output_dir: 
			output_dir = os.path.join(
				output_dir.strip(os.pathsep), # this is where we want the output
				basename, # the name of the source dir given on the command line
				dirpath.replace(root,'').lstrip(os.pathsep) # relative path by removing the root
			)

		for file in filenames:
			if file.endswith('.yaml'):
				process_file(
					os.path.join(dirpath,file),
					output_dir
				)


jinja_env = Environment(
    loader = FileSystemLoader('./templates')
)
rst_template = jinja_env.get_template('rst.jinja2')

def recipe_to_rst(recipe, out_file):
	out_file.write(rst_template.render(recipe=recipe))

@click.command()
@click.option('--output', '-o',
	type=click.Path(exists=False),
	help='Set the output directory for the translated files. It activate the translation; if no output set, only validation is done.')
@click.argument('files', nargs=-1, type=click.Path(exists=True))
def main(files, output):
	for f in files:
		if os.path.isdir(f):
			process_dir(f, output)
		elif os.path.isfile(f):
			process_file(f, output)


if __name__ == '__main__':
	main()


