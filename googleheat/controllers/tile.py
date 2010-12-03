import logging

from pylons import request, response, session, config, tmpl_context as c, url
from pylons.controllers.util import abort, redirect

from googleheat.lib.base import BaseController, render
from googleheat.model import Points
from googleheat.model.meta import Session
from googleheat.lib.gmerc import ll2px
from googleheat.lib.gheatbase import Tile

log = logging.getLogger(__name__)

class TileController(BaseController):

    def render(self, color_scheme=None, zoom=None, x=None, y=None):
        response.cache_expires(seconds=0)
        try:
            assert color_scheme in config['pylons.app_globals'].color_schemes, ("bad color_scheme: " + color_scheme)
            assert zoom.isdigit() and x.isdigit() and y.isdigit(), "not digits"
            zoom = int(zoom)
            x = int(x)
            y = int(y)
            assert 0 <= zoom <= 30, "bad zoom: %d" % zoom
        except AssertionError, err:
            log.warn(err.args[0])
            abort('Bad request.')

        # Build and save the file.
        # ========================
        # The tile that is built here will be served by the static handler.

        color_scheme = config['pylons.app_globals'].color_schemes[color_scheme]
        fspath = config.get("tile_path") + "/%s-%d-%d,%d.png" % (color_scheme.name, zoom, x, y)
        tile = Tile(color_scheme, config['pylons.app_globals'].dots, zoom, x, y, fspath)
        if tile.is_empty():
            log.info('serving empty tile for ' + fspath)
            fspath = color_scheme.get_empty_fspath(zoom)
        elif tile.is_stale():
            log.info('rebuilding ' + fspath)
            tile.rebuild()
            tile.save()
        else:
            log.info('serving cached tile ' + fspath)

        response.content_type = 'image/png'
        fd = open(fspath, 'r')
        image_data = fd.read()
        fd.close()
        return image_data

