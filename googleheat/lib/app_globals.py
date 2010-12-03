"""The application's Globals object"""

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from googleheat.lib.gheatbase import ColorScheme, Dot

import os
import pygame
import pylons

class Globals(object):
    """Globals acts as a container for objects available throughout the
    life of the application

    """

    def __init__(self, config):
        """One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable

        """
        self.cache = CacheManager(**parse_cache_config_options(config))
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        pygame.display.init()
        pygame.display.set_mode((1,1), 0, 32)
        self.dots = dict([(zoom, Dot(zoom)) for zoom in range(int(config.get("max_zoom")))]) # factored for easier use from scripts
        
        self.color_schemes = dict()
        for fname in os.listdir(config.get("color_schemes")):
            if not fname.endswith('.png'):
                continue
            name = os.path.splitext(fname)[0]
            fspath = os.path.join(config.get("color_schemes"), fname)
            self.color_schemes[name] = ColorScheme(name, fspath)