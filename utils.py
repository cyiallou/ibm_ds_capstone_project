import pyproj
from typing import Tuple
import numpy as np
import numpy.matlib


def lonlat_to_xy(Lon:float, Lat:float, inverse=False, zone=33) -> Tuple:
    """Transforms latitude and longitude to UTM coordinates.
    
    Arguments:
    ----------
    Lat: float, Latitude value if inverse=False, otherwise x value.
    
    Lon: float, Longitude value if inverse=False, otherwise y value.
    
    inverse: bool, False if converting from lat, long to x, y otherwise set to True.
    
    zone: int, The UTM zone (33 is the UTM zone of Berlin).


    Returns:
    --------
    The transformed coordinates (latitude, longitude) or (eastings, northings)
    with units are degrees and meters respectively.
    """
    P = pyproj.Proj(proj='utm', zone=zone, ellps='WGS84', preserve_units=True)
    return P(Lon, Lat, inverse=inverse)


def compute_xy_distance(Lat1, Lon1, Lat2, Lon2):
    G = pyproj.Geod(ellps='WGS84')
    return G.inv(Lon1, Lat1, Lon2, Lat2)[2]


def calc_xy_distance(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx*dx + dy*dy)


def create_grid(centre:Tuple[float, float], radius:int, minor_radius:int, area_shape:str, ov=True):
    """Creates a grid with centres given in cartesian coordinates.

    TODO: Create grid for other shapes besides circles.

    Arguments:
    ----------
    centre: Tuple[float, float], The centre of the grid.

    radius: int, The grid radius in meters.

    minor_radius: int, The radius of the grid shapes.

    shape: str, The grid shapes to use.

    ov: bool, True to allow an overlap between grid shapes (recommended for
              shape='circle') or False to not allow overlap. In either case,
              the centres are equidistant from each other.

    Returns:
    --------
    centres_x: numpy.ndarray, Grid centres in cartesian coordinates (x axis).

    centres_y: numpy.ndarray, Grid centres in cartesian coordinates (y axis).

    area_radius: float, The radius of each grid circle.
    """
    # calculate the minimum value needed to make the grid shapes overlap
    if ov:
        ov_amount = minor_radius * (2 ** 0.5) - minor_radius
    else:
        ov_amount = 0

    # number of elements needed: n = distance / step.
    # step = 2*minor_radius, distance = 2*radius. Hence, n = radius / minor_radius
    n = np.ceil(radius / (minor_radius - ov_amount))
    
    # make sure centre will be in grid_centres
    num_grid_areas = n - 1 if (n - radius/minor_radius)>=0.5 else n

    # compute the new circle radius
    area_radius = minor_radius - ov_amount

    # create the grid
    grid_centres_x, grid_centres_y = [], []
    for i, val in enumerate(centre):
        start = val - radius + minor_radius
        stop = val + radius - minor_radius
        grid_centres = np.linspace(start, stop, int(num_grid_areas))
        # broadcast to a square array
        if i==0:
            centres_x = np.matlib.repmat(grid_centres, np.max(grid_centres.shape), 1)
        elif i==1:
            centres_y = np.matlib.repmat(grid_centres, np.max(grid_centres.shape), 1)
        else:
            raise ValueError(f"Number of elements in centre should be 2. Got {len(centre)} instead")

    return centres_x, centres_y, area_radius
