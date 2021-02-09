from _version import __version__
from _project import __project__

def docker_image(image_name):
    return image_name + ":" + __version__

def dag_name(name):
    return __project__ + "-" + name + "-" + __version__

