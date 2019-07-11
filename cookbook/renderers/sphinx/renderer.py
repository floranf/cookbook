import cookbook.renderers.sphinx.config 
from jinja2 import Environment, FileSystemLoader
from cookbook.renderers.renderer import BaseRenderer
from loguru import logger
from pathlib import Path

class Renderer(BaseRenderer):

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    def _recipe_to_rst(self, recipe, out_file):
        out_file.write(self.recipe_template.render(recipe=recipe))

    def _group_to_rst(self, group, out_file):
        out_file.write(self.group_template.render(group=group))

    def render(self, book, recipes, output, ressources):
        logger.info(f'Rendering book: {book.title}')
        self.templates = Path(ressources, 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(str(self.templates)))
        self.recipe_template = self.jinja_env.get_template('recipe.jinja2')
        self.group_template = self.jinja_env.get_template('group.jinja2')

        recipes_path = Path(output, 'book','recipes')
        recipes_path.mkdir( parents=True)
        for recipe in recipes:
            logger.info(f'Rendering recipe: {recipe.title}')
            output_file = Path(recipes_path ,recipe.file.name).with_suffix('.rst')
            with output_file.open('w') as out_file:
                self._recipe_to_rst(recipe, out_file)
            if recipe.img:
                output_imagefile = output_file.with_suffix(recipe.img.suffix)
                shutil.copyfile(recipe.img, output_imagefile)



    # def render():
    # # generate all groups
    # if output:
    #     p = Path(output, 'groups')
    #     p.mkdir(parents=True, exist_ok=True)
    #     for group in config.groups.values():
    #         if not len(group['recipes']):
    #             continue
    #         p = Path(output, 'groups', group['title'] + '.rst')
    #         with p.open(mode='w') as f:
    #             group_to_rst(group, f)

    #     if 'groups' in data and data['groups']:
    #         for group in data['groups']:
    #             if group in config.groups.keys():
    #                 config.groups[group]['recipes'].append(self)

    #     config.recipes.append(self)

