import os
from IPython.display import display, Markdown

def markdown(str):
    display(Markdown(str))


is_debug = os.getenv('DEBUG', 'false')=='true'
def debug(*args):
    if is_debug:
        print(*args)



