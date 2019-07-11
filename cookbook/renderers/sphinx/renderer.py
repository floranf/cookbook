import cookbook.renderers.sphinx.config 
from jinja2 import Environment, FileSystemLoader
from cookbook.renderers.renderer import BaseRenderer
from loguru import logger
from pathlib import Path

class Renderer(BaseRenderer):

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    def _recipe_to_rst(self, recipe, out_file):
        out_file.write(recipe_template.render(recipe=recipe))

    def _group_to_rst(self, group, out_file):
        out_file.write(group_template.render(group=group))

    def render(self, book, recipes, output, ressources):
        logger.info(f'Rendering book: {book.title}')
        self.templates = Path(ressources, 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(str(self.templates)))
        self.recipe_template = self.jinja_env.get_template('recipe.jinja2')
        self.group_template = self.jinja_env.get_template('group.jinja2')

        for recipe in recipes:
            logger.info(f'Rendering recipe: {recipe.title}')
            #self._recipe_to_rst(recipe, Path(output)

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

    # name = file.stem
    # if output:
    #     output_file = Path(output, name).with_suffix('.rst')
    #     if not os.path.exists(output):
    #         os.makedirs(output)
    #     with output_file.open('w') as out_file:
    #         recipe_to_rst(recipe, out_file)
    #     if recipe.img:
    #         output_imagefile = output_file.with_suffix('.png')
    #         shutil.copyfile(source_imagefile, output_imagefile)


    #     if 'groups' in data and data['groups']:
    #         for group in data['groups']:
    #             if group in config.groups.keys():
    #                 config.groups[group]['recipes'].append(self)

    #     config.recipes.append(self)

