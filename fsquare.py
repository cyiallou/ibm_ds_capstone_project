"""Class for foursquare API calls and the processing of the response (json file).

Needs Foursquare client_id and client_secret. Register at their developer website.

Dependencies:
-------------
* requests module for making server requests.
* warnings module for raising helpful warnings.
* typing module for useful type casting.
"""
import requests
from warnings import warn
from typing import List, Tuple


class fsquare():
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.version = '20200121'  # API version to use

    def fsquare_search_settings(self, centre_lat:float, centre_lon:float) -> Tuple:
        """Constructs the search settings for the API call.
        
        Arguments:
        ----------
        self: object,

        centre_lat: float,
            The latitude of the search area for the API call.
        
        centre_lon: float,
            The longitude of the search area for the API call.
        
        Returns:
        --------
        fixed_search_params: dict,
            The API call parameters (avoid changing).
            Holds the API credentials and version.

        search_params: dict,
            The parameters for the search endpoint.
        """
        # construct the fixed search parameters
        fixed_search_params = {'client_id': self.client_id,
                               'client_secret': self.client_secret,
                               'version': self.version,  # YYYYMMDD
                              }
        # change the below as per your request
        search_params = {'query': 'replace_this',
                         'latitude': centre_lat,
                         'longitude': centre_lon,
                         'radius': 500,  # meters, distance from the specified latitude and longitude
                         'limit': 50,  # max venues to get back (max=50)
                         'categories': 'replace_this'
                        }
        return fixed_search_params, search_params

    def make_fsquare_api_call(self, search_params:dict, fixed_params:dict, tp:str) -> dict:
        """Calls the Foursquare API for a search endpoint.

        Arguments:
        ----------
        self: object,

        search_params: dict,
            Holds the specific search parameters i.e. the
            search query, coordinates, radious of search and limit.

        fixed_params: dict,
            Holds the API credentials and version.

        stp: str,
            The search type. Can be 'cat' to search for specific
            categories or 'qur' to search for string queries.

        Returns:
        --------
        API call response as a json file.
        """
        if tp=='cat':
            a = f'&categoryId={search_params["categories"]}'
        elif tp=='qur':
            a = f'&query={search_params["query"]}'
        else:
            raise ValueError(f"tp can be either 'cat' or 'qur'. Got {tp}.")
        
        url = ('https://api.foursquare.com/v2/venues/search'
               f'?client_id={fixed_params["client_id"]}'
               f'&client_secret={fixed_params["client_secret"]}'
               f'&ll={search_params["latitude"]},{search_params["longitude"]}'
               f'&v={fixed_params["version"]}'
               +a+
               f'&radius={search_params["radius"]}'
               f'&limit={search_params["limit"]}')
        return requests.get(url).json()


    def get_fsquare_data(self, api_params:dict, queries:List[str], tp:str, coords=[[]], verbose=0) -> Tuple:
        """Calls the Foursquare API for the search strings in queries
           and outputs the final (merged) responses.
        
        Arguments:
        ----------
        self: object,

        api_params: dict,
            The parameters for the FourSquare API call
            (see make_fsquare_api_call).

        queries: List[str],
            The search strings for the FourSquare API call.

        tp: str,
            The search type. Can be 'cat' to search for specific
            categories or 'qur' to search for string queries.
        
        coords: List[List] or numpy.ndarray[numpy.ndarray, numpy.ndarray],
                (Optional. Default=[[]])
            Centre coordinates as (latitude, longitude) of the area(s)
            to search.
            
        verbose: int, (Optional. Default=0)
            Sets the verbosity level: 0 for printing out nothing, 1 for printing some
            useful messages to track progress and 2 for printing more info (likely to
            print a lot of messages!).
            
        Returns:
        --------
        fsq_data: dict,
            The merged responses from the API calls. It stores all the venues and the
            unique id string of each venue.
        """
        # check coords input
        if type(coords)==list:
            if len(coords)==1 & len(coords[0])==0:
                coords = [[api_params['search_params']['latitude'], api_params['search_params']['longitude']]]
            number_of_areas_to_search = len(coords)
        else:
            if sum(coords[0].shape)!=2:
                raise ValueError(f'coords must be of shape (?, 2). Got {coords.shape}.')
            number_of_areas_to_search = coords.shape[0]

        all_fsq_data = {'venues': [], 'venue_ids': []}  # to be populated by the API responses
        for i, longlat in enumerate(coords):  # search within each specified area
            api_params['search_params']['longitude'] = longlat[0]
            api_params['search_params']['latitude'] = longlat[1]
            for item in queries:  # search for each query
                if tp=='cat':
                    api_params['search_params']['categories'] = item
                elif tp=='qur':
                    api_params['search_params']['query'] = item
                try:
                    response = self.make_fsquare_api_call(api_params['search_params'], api_params['fixed_search_params'], tp=tp)
                    # display some useful warnings
                    if response['meta']['code']==429:
                        warn("API regural calls limit exceeded. Function returned.")
                        return all_fsq_data, venue_ids
                    if response['meta']['code']==500:  # server error
                        warn(f"Server error. Response output: {reponse}")
                    # get the venues
                    venues = response['response']['venues']
                except:
                    venues = []
                for venue in venues:
                    # avoid adding duplicates to fsq_data
                    if venue['id'] not in all_fsq_data['venue_ids']:
                        all_fsq_data['venues'].append(venue)
                        all_fsq_data['venue_ids'].append(venue['id'])
                        if verbose==2:
                            print(f'Added 1 venue (total={len(venue_ids)})\n')
            if verbose & (((i+1) % 10)==0):
                print(f'Finished searching area {i+1} of {number_of_areas_to_search}\n')
        if verbose:
            print(f'Finished processing {number_of_areas_to_search} areas. Found {len(venue_ids)} venues!')
            
        return all_fsq_data
