"""Class for making foursquare API calls and processing the response (json file).

Needs Foursquare client_id and client_secret. Register at their developer website.

Dependencies:
-------------
* requests - for making server requests.
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
        if tp == 'cat':
            a = f'&categoryId={search_params["categories"]}'
        elif tp == 'qur':
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
            if (len(coords) == 1) & (len(coords[0]) == 0):
                coords = [[api_params['search_params']['latitude'], api_params['search_params']['longitude']]]
            number_of_areas_to_search = len(coords)
        else:
            if sum(coords[0].shape) != 2:
                raise ValueError(f'coords must be of shape (?, 2). Got {coords.shape}.')
            number_of_areas_to_search = coords.shape[0]

        all_fsq_data = {'venues': [], 'venue_ids': []}  # to be populated by the API responses
        for i, longlat in enumerate(coords):  # search within each specified area
            api_params['search_params']['longitude'] = longlat[0]
            api_params['search_params']['latitude'] = longlat[1]
            for item in queries:  # search for each query
                if tp == 'cat':
                    api_params['search_params']['categories'] = item
                elif tp == 'qur':
                    api_params['search_params']['query'] = item
                try:
                    response = self.make_fsquare_api_call(api_params['search_params'], api_params['fixed_search_params'], tp=tp)
                    # display some useful warnings
                    exit_func = self._check_response_code(response['meta']['code'])
                    if exit_func:
                        return all_fsq_data, venue_ids
                    
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

    def get_all_fsquare_categories(self, fixed_api_params:dict, categ_name:str, w:str):
        """Calls the Foursquare API to get all the venue categories.

        Arguments:
        ----------
        fixed_api_params: dict,
            Holds the API credentials and version.

        categ_name: str,
            The main category name to search for.

        w: str,
            String to search in the name of the venues of the main category
            defined by the argument cat_name.

        Returns:
        --------
        all_categories: dict,
            API raw response: All the venue categories.

        w_categories: list,
            The category IDs of the venues that have the string w in their name.

        Notes:
        ------
        * Look at https://developer.foursquare.com/docs/resources/categories
          for the category names and identity numbers.
        """
        url = ('https://api.foursquare.com/v2/venues/categories'
               f'?client_id={fixed_api_params["client_id"]}'
               f'&client_secret={fixed_api_params["client_secret"]}'
               f'&v={fixed_api_params["version"]}')
        all_categories = requests.get(url).json()

        exit_func = self._check_response_code(all_categories['meta']['code'])
        if exit_func:
            return None

        valid_main_category_names = [item['name'] for item in all_categories['response']['categories']]
        if categ_name not in valid_main_category_names:
            raise ValueError(f"String '{categ_name}' is not a main category name. "
                    f"Viable names are:\n{valid_main_category_names}")

        # get the category names that have the string defined by the argument w
        w_categories = []
        for primary in all_categories['response']['categories']:
            if primary['name'] == categ_name:
                w_categories = self._find_str_recur(w_categories, primary, w)

        return all_categories, w_categories

    def _find_str_recur(self, out:list, d:dict, w:str) -> list:
        """Finds w in d recursively and appends the result to out.

        Arguments:
        ----------
        out: list,
            Stores the values from the nested dictionary d that have the
            string w in the d['categories][i]['name'] value. i is a list
            index.

        d: dict,
            Nested dictionary. The whole or part of an API response as in
            json file format.

        w: str,
            String to search in the name of the venues.

        Returns:
        --------
        out: list,
            The input list appended with new entries if conditions are met.
        """
        if len(d['categories']) != 0:
            for item in d['categories']:
                if w.lower() in item['name'].lower():
                    out.append(item['id'])
                    self._find_str_recur(out, item, w)
        else:
            pass
        return out

    @staticmethod
    def _check_response_code(code:int) -> bool:
        """Returns a warning given the API status code."""
        exit_func = False
        if code == 429:
            warn("API regural calls limit exceeded. Function returned.")
            exit_func = True
        elif code == 500:  # server error
            warn(f"Server error. Response output: {reponse}")
        else:
            warn(f"API response status code: {code}")
        return exit_func

