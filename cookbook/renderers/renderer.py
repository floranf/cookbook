class BaseRenderer:
    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    def init(ressourcesPath, outPath):
        """
        Initialise, if needed, the renderer.
        ressourcesPath is the path to the resource folder for this renderer.
        outPath is the path to the output directory.
        """
        pass
    
    def render(book, recipes, output):
        """
        Renders a list of recipes.
        recipes: the list of recipes to render.
        """
        pass
