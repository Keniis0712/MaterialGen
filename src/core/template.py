import pathlib

from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory=pathlib.Path(__file__).parent.parent / "templates")
