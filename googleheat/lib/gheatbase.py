"""Mostly gheat code"""

import datetime
import logging
import os
import stat
import time

from googleheat.model import Points
from googleheat.model.meta import Session
from pylons import config

import gmerc
import pygame

log = logging.getLogger(__name__)

WHITE = (255, 255, 255)

OPACITY = 127
MAX_ZOOM = 31

class ColorScheme(object):
    """Base class for color scheme representations.
    """

    def __init__(self, name, fspath):
        """Takes the name and filesystem path of the defining PNG.
        """
        self.name = name
        self.hook_set(fspath)
        self.empties_dir = config.get("empties_path")
        self.build_empties()

    def build_empties(self):
        """Build empty tiles for this color scheme.
        """
        empties_dir = self.empties_dir

        if config.get("build_empties"):
            if not os.path.isdir(empties_dir):
                os.makedirs(empties_dir, 0755)
            if not os.access(empties_dir, os.R_OK|os.W_OK|os.X_OK):
                raise ConfigurationError( "Permissions too restrictive on "
                                        + "empties directory "
                                        + "(%s)." % empties_dir
                                         )
            for fname in os.listdir(empties_dir):
                if fname.endswith('.png') and fname.startswith(self.name):
                    os.remove(os.path.join(empties_dir, fname))
            for zoom in range(0, MAX_ZOOM + 1):
                fspath = os.path.join(empties_dir, self.name + '-' + str(zoom)+'.png')
                self.hook_build_empty(OPACITY, fspath)


    def get_empty_fspath(self, zoom):
        fspath = os.path.join(self.empties_dir, self.name + '-' + str(zoom)+'.png')
        if not os.path.isfile(fspath):
            self.build_empties() # so we can rebuild empties on the fly
        return fspath


    def hook_set(self, fspath):
        colors = pygame.image.load(fspath)
        self.colors = colors = colors.convert_alpha()
        self.color_map = pygame.surfarray.pixels3d(colors)[0]
        
        self.alpha_map = pygame.surfarray.pixels_alpha(colors)[0]
        
        # these alpha ranges played better with some of the color schemes we had used
        #self.alpha_map = range(0,257,4) + [255]*191
        #self.alpha_map.reverse()
        
    def hook_build_empty(self, opacity, fspath):
        tile = pygame.Surface((int(config.get("size")),int(config.get("size"))), pygame.SRCALPHA, 32)
        tile.fill(self.color_map[255])
        tile.convert_alpha()

        (conf, pixel) = opacity, self.alpha_map[255]
        opacity = int(( (conf/255.0)    # from configuration
                      * (pixel/255.0)   # from per-pixel alpha
                       ) * 255)

        pygame.surfarray.pixels_alpha(tile)[:,:] = opacity 
        pygame.image.save(tile, fspath)


class Dot(object):
    """Base class for dot representations.

    Unlike color scheme, the same basic external API works for both backends. 
    How we compute that API is different, though.

    """

    def __init__(self, zoom):
        """Takes a zoom level.
        """
        name = 'dot%d.png' % zoom
        fspath = config.get("dots_path") + "/" + name
        self.img, self.half_size = self.hook_get(fspath)
        
    def hook_get(self, fspath):
        img = pygame.image.load(fspath)
        half_size = img.get_size()[0] / 2
        return img, half_size


class Tile(object):
    img = None

    def __init__(self, color_scheme, dots, zoom, x, y, fspath):
        """x and y are tile coords per Google Maps.
        """

        # Calculate some things.
        # ======================

        dot = dots[zoom]


        # Translate tile to pixel coords.
        # -------------------------------

        x1 = x * int(config.get("size"))
        x2 = x1 + 255
        y1 = y * int(config.get("size"))
        y2 = y1 + 255
    
    
        # Expand bounds by one-half dot width.
        # ------------------------------------
    
        x1 = x1 - dot.half_size
        x2 = x2 + dot.half_size
        y1 = y1 - dot.half_size
        y2 = y2 + dot.half_size
        expanded_size = (x2-x1, y2-y1)
    
    
        # Translate new pixel bounds to lat/lng.
        # --------------------------------------
    
        n, w = gmerc.px2ll(x1, y1, zoom)
        s, e = gmerc.px2ll(x2, y2, zoom)


        # Save
        # ====

        self.dot = dot.img
        self.pad = dot.half_size

        self.x = x
        self.y = y

        self.x1 = x1
        self.y1 = y1

        self.x2 = x2
        self.y2 = y2

        self.expanded_size = expanded_size
        self.llbound = (n,s,e,w)
        self.zoom = zoom
        self.fspath = fspath
        self.opacity = OPACITY
        self.color_scheme = color_scheme
  

    def is_empty(self):
        """With attributes set on self, return a boolean.

        Calc lat/lng bounds of this tile (include half-dot-width of padding)
        SELECT count(uid) FROM points

        """
        q = Session.query(Points)
        q = q.filter(Points.latitude <= self.llbound[0])
        q = q.filter(Points.latitude >= self.llbound[1])
        q = q.filter(Points.longitude <= self.llbound[2])
        q = q.filter(Points.longitude >= self.llbound[3])
        numpoints = q.count() # this is guaranteed to exist, right?
        return numpoints == 0


    def is_stale(self):
        """With attributes set on self, return a boolean.

        Calc lat/lng bounds of this tile (include half-dot-width of padding)
        SELECT count(uid) FROM points WHERE modtime < modtime_tile

        """
        if not os.path.isfile(self.fspath):
            return True
   
        timestamp = os.stat(self.fspath)[stat.ST_MTIME]
        modtime = datetime.datetime.fromtimestamp(timestamp)
        
        q = Session.query(Points)
        q = q.filter(Points.latitude <= self.llbound[0])
        q = q.filter(Points.latitude >= self.llbound[1])
        q = q.filter(Points.longitude <= self.llbound[2])
        q = q.filter(Points.longitude >= self.llbound[3])
        q = q.filter(Points.modtime > modtime)
        numpoints = q.count() # this is guaranteed to exist, right?
        return numpoints != 0


    def rebuild(self):
        """Rebuild the image at self.img. Real work delegated to subclasses.
        """

        # Calculate points.
        # =================
        # Build a closure that gives us the x,y pixel coords of the points
        # to be included on this tile, relative to the top-left of the tile.

        q = Session.query(Points)
        q = q.filter(Points.latitude <= self.llbound[0])
        q = q.filter(Points.latitude >= self.llbound[1])
        q = q.filter(Points.longitude <= self.llbound[2])
        q = q.filter(Points.longitude >= self.llbound[3])

        def points():
            """Yield x,y pixel coords within this tile, top-left of dot.
            """
            for point in q.all():
                x, y = gmerc.ll2px(point.latitude, point.longitude, self.zoom)
                x = x - self.x1 # account for tile offset relative to 
                y = y - self.y1 #  overall map
                yield x-self.pad,y-self.pad


        # Main logic
        # ==========
        # Hand off to the subclass to actually build the image, then come back 
        # here to maybe create a directory before handing back to the backend
        # to actually write to disk.

        self.img = self.hook_rebuild(points())

        dirpath = os.path.dirname(self.fspath)
        if dirpath and not os.path.isdir(dirpath):
            os.makedirs(dirpath, 0755)


    def hook_rebuild(self, points):
        """Rebuild and save the file using the current library.

        The algorithm runs something like this:

            o start a tile canvas/image that is a dots-worth oversized
            o loop through points and multiply dots on the tile
            o trim back down to straight tile size
            o invert/colorize the image
            o make it transparent

        Return the img object; it will be sent back to hook_save after a
        directory is made if needed.

        Trim after looping because we multiply is the only step that needs the
        extra information.

        The coloring and inverting can happen in the same pixel manipulation 
        because you can invert colors.png. That is a 1px by 256px PNG that maps
        grayscale values to color values. You can customize that file to change
        the coloration.

        """
        """Given a list of points, save a tile.

        This uses the Pygame backend.

        Good surfarray tutorial (old but still applies):

            http://www.pygame.org/docs/tut/surfarray/SurfarrayIntro.html

        Split out to give us better profiling granularity.

        """
        tile = self._start()
        tile = self._add_points(tile, points)
        tile = self._trim(tile)
        tile = self._colorize(tile)
        
        return tile


    def _start(self):
        tile = pygame.Surface(self.expanded_size, 0, 32)
        tile.fill(WHITE)
        return tile
        #@ why do we get green after this step?


    def _add_points(self, tile, points):
        for dest in points:
            tile.blit(self.dot, dest, None, pygame.BLEND_MULT)
        return tile


    def _trim(self, tile):
        tile = tile.subsurface(self.pad, self.pad, int(config.get("size")), int(config.get("size"))).copy()
        #@ pygame.transform.chop says this or blit; this is plenty fast 
        return tile


    def _colorize(self, tile):

        # Invert/colorize
        # ===============
        # The way this works is that we loop through all pixels in the image,
        # and set their color and their transparency based on an index image.
        # The index image can be as wide as we want; we only look at the first
        # column of pixels. This first column is considered a mapping of 256
        # gray-scale intensity values to color/alpha.

        # Optimized: I had the alpha computation in a separate function because 
        # I'm also using it above in ColorScheme (cause I couldn't get set_alpha
        # working). The inner loop runs 65536 times, and just moving the 
        # computation out of a function and inline into the loop sped things up 
        # about 50%. It sped it up another 50% to cache the values, since each
        # of the 65536 variables only ever takes one of 256 values. Not super
        # fast still, but more reasonable (1.5 seconds instead of 12).
        #
        # I would expect that precomputing the dictionary at start-up time 
        # should give us another boost, but it slowed us down again. Maybe 
        # since with precomputation we have to calculate more than we use, the 
        # size of the dictionary made a difference? Worth exploring ...

        _computed_opacities = dict()

        tile = tile.convert_alpha(self.color_scheme.colors)
        tile.lock()
        pix = pygame.surfarray.pixels3d(tile)
        alp = pygame.surfarray.pixels_alpha(tile)
        for x in range(int(config.get("size"))):
            for y in range(int(config.get("size"))):
                key = pix[x,y,0]

                conf, pixel = self.opacity, self.color_scheme.alpha_map[key]

                if (conf, pixel) not in _computed_opacities:
                    opacity = int(( (conf/255.0)    # from configuration
                                  * (pixel/255.0)   # from per-pixel alpha
                                   ) * 255)
                    _computed_opacities[(conf, pixel)] = opacity
                pix[x,y] = self.color_scheme.color_map[key]
                alp[x,y] = _computed_opacities[(conf, pixel)]
        tile.unlock()

        return tile


    def save(self):
        pygame.image.save(self.img, self.fspath)


