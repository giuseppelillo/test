from _version import __version__

def dag_name(name):
    return name + "-" + __version__

def docker_image(image_name):
    return image_name + ":" + __version__
