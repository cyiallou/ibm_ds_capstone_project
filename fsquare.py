"""Class for foursquare API calls and the processing of the response (json file).

Needs Foursquare client_id and client_secret. Register at their developer website.

Dependencies:
-------------
* requests module for making server requests.
* warnings module for raising helpful warnings.
* typing module for useful type casting.
"""
import requests
from typing import List, Tuple
from warnings import warn


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
            a = f'&query={search_params["query"]}'
        elif tp=='qur':
            a = f'&categoryId={search_params["categories"]}'
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


    def get_fsquare_data(self, api_params:dict, queries:List[str], tp:str, categories={}, coords=[[]], verbose=False) -> Tuple:
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

        categories: dict, (Optional. Default={})
            The categories to search for.
        
        coords: List[List] or numpy.ndarray[numpy.ndarray, numpy.ndarray],
                (Optional. Default=[[]])
            Centre coordinates as (latitude, longitude) of the area(s)
            to search.
            
        verbose: bool, (Optional. Default=False)
            Set to True to print out useful messages to track progress.
            
        Returns:
        --------
        fsq_data: dict,
            The merged responses from the API calls. It stores all the venues.

        venue_ids: List[str],
            The unique id strings of each venue.
            
        restaurants: dict,
            The merged responses from the API calls. It only stores the venues
            specified by the category ID in categories input.
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

        all_fsq_data = {'venues': []}  # to be populated by the API responses
        venue_ids = list()  # to be populated by the unique venue ids
        restaurants = {}
        for _,val in categories.items():
            restaurants[val] = []

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
                    if response['meta']['code']==429:
                        warn("API regural calls limit exceeded")
                        return None
                    venues = response['response']['venues']
                except:
                    venues = []
                for venue in venues:
                    # avoid adding duplicates to fsq_data
                    if venue['id'] not in venue_ids:
                        all_fsq_data['venues'].append(venue)
                        venue_ids.append(venue['id'])
                        
                        # add to the restaurants dictionary
                        venue_category_id = venue['categories'][0]['id']  # get the venue category id
                        if str(venue_category_id) in venue_categories:
                            restaurants[venue_categories[str(venue_category_id)]] += [venue]
            if verbose & ((i+1) % 10)==0:
                print(f'Finished searching area {i+1} of {number_of_areas_to_search}\n')
        if verbose:
            print(f'Finished processing {number_of_areas_to_search} areas.')
            
        return all_fsq_data, venue_ids, restaurants
