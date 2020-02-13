"""Web scraper for the trip advisor website.

Dependencies:
-------------
* bs4 - BeautifulSoup, a library to parse HTML documents and navigate the element tree
* requests - to make HTTP requests from code
* re - Regex library, to search for more complex strings
* warnings - to issue useful user warnings
"""
import requests
import re
from bs4 import BeautifulSoup
from typing import List, Tuple
from warnings import warn


class Scraper:
    """
    Examples:
    --------
    >>> from tascraper import Scraper
    >>> URL = 'https://www.tripadvisor.com/Restaurants-g187323-Berlin.html'
    >>> scraper = Scraper()
    >>> links = scraper.parse(url=URL, all_pgs=False)
    scraper.scrape(links)

    To scrape a single page:
    Scraper().scrape_page
    """

    def __init__(self):  # , argv):
        self.base_url = None
        self.domain_name = None
        # self.url = self.parse_arguments(argv)

    # def parse_arguments(self, argv):
    #     assert len(argv) == 2
    #     return argv[0], argv[1]

    def parse(self, url: str, all_pgs=True) -> List[List[str]]:
        """Get list of restaurants.

        Arguments:
        ----------
        url: str,
            The original url (the first page when you search for restaurants on Trip Advisor)

        all_pgs: bool, (optional; default=True)
            Automatically crawl and extract the restaurant listings from subsequent pages.
            Set to False if you only want to get the restaurants found in the input url.

        Returns:
        --------
        links: List[List[str]],
            The restaurant web pages to scrape the data from.
        """
        # check input url
        assert(url.find('http') != -1), "Make sure the input url starts with http:// or https://"

        stp = url.find('/', 8)  # avoid the https://
        self.domain_name = url[url.rfind('.', 0, stp):stp]
        self.base_url = url[:stp]

        print(f'[parse] url: {url}')
        soup = self._get_soup(url)

        if all_pgs:
            # get sub-pages with restaurants
            all_pages = [url] + self._crawler(soup)
            links = list()
            # slow due to _get_soup()
            for page in all_pages:
                links.append(self._get_page_listings(self._get_soup(page)))
        else:
            # get the page listings from a single page
            links = [self._get_page_listings(soup)]

        """
        # Save the links for later use.
        import pickle

        with open('../data/crawled_links.pkl', 'wb') as f:
            pickle.dump(links, f)

        # Load them back:
        with open('../data/crawled_links.pkl', 'rb') as f:
            loaded_links = pickle.load(f)
        """
        return links

    def scrape(self, links: List[List[str]], vb=0) -> List[dict]:
        """Extracts data from each restaurant page in links.

        Arguments:
        ----------
        links: List[List[str]],
            The restaurant web pages to scrape the data from.

        vb: int, (optional; default=0)
            The verbosity level. 0: no verbosity, 1: medium,
            2: high (warning: might print many messages!).

        Returns:
        --------
        data: List[dict],
            The scraped data returned as a list where each element is a dictionary
            that contains the individual restaurant data.
        """
        # check verbosity level input
        if vb not in [0, 1, 2]:
            warn(f"Valid verbosity levels (vb) are [0, 1, 2]. Got {vb}. Changed to 1")
            vb = 1

        data_info = ['venue_id', 'name', 'address', 'postcode', 'city', 'country',
                     'price range', 'cuisines', 'meals', 'special diets', 'features']
        v_id = 0
        data = list()  # populate with the individual restaurant data
        # total_links = for i in
        batch = 0  # to keep track of the number of link batches scraped
        total_batches = len(links)
        for search_page in links:
            batch += 1
            for link in search_page:
                if vb == 2:
                    print(f"Scraping {link}")

                soup = self._get_soup(link)

                # assign a unique id
                venue_id = f'id_{v_id}'
                v_id += 1

                # initialise venue data
                venue_data = {item: '' for item in data_info}
                venue_data['venue_id'] = venue_id

                # ======== Get the info at the top of the page ========
                top_info = soup.find(id='taplc_resp_rr_top_info_rr_resp_0')
                name = top_info.find(class_='ui_header h1')
                addr_street = top_info.find('div', class_='businessListingContainer').find('span',
                                                                                           class_='street-address')
                addr_extended = top_info.find('div', class_='businessListingContainer').find('span',
                                                                                             class_='extended-address')
                locality = top_info.find('div', class_='businessListingContainer').find('span', class_='locality')
                country = top_info.find('div', class_='businessListingContainer').find('span', class_='country-name')

                # check for NoneTypes and get the text for each variable
                checks, texts = self._check_not_none([name, addr_street, addr_extended, locality, country])
                name, [postcode, city], country = texts[0], texts[3].strip(', ').split(), texts[4]

                # concatenate the addresses to get the full address
                if sum(checks[1:3]) == 2:
                    addr_street = texts[1] + f', {texts[2]}'
                else:
                    addr_street = texts[1]

                # populate with the restaurant data
                venue_data['name'] = name
                venue_data['address'] = addr_street
                venue_data['postcode'] = postcode
                venue_data['city'] = city
                venue_data['country'] = country

                # ======== Get the details ========
                # # Gets the about: DOES NOT WORK YET
                # # < div class ="restaurants-detail-overview-cards-DetailsSectionOverviewCard__tagText--1OH6h">European gastronomic culture with oriental-lebanese tradition. A delicatessen / café with wine-trade, presenting fine cuisine and wine from Lebanon combined with finest French pastry. Cultural events to celebrate Lebanese / French friendship. Also providing catering made with fine regional products. Our specialties are more vegan and vegetarian, but also meat and chicken lovers will be extremely happy! Our typical homemade and handmade sweets, with the authentic lebanese Mokka are the perfect finish! By the way, our Hommous is the second to none...</div>

                # GET THE CLASS OF SOMETHING:
                try:
                    # TODO: If CUISINES is not found then we don't extract anything. Find a more robust way
                    details_top = soup.find("div", text="CUISINES")  # the class name is not the same in every web page
                    # get the class name
                    detail_category_class = details_top.attrs['class'][0]
                    # get the price value class name
                    detail_category_values_class = details_top.find_next_sibling("div").attrs['class'][0]
                except AttributeError:
                    print(f"[scrape] {link}: Could not fetch the details. \n")
                    detail_category_class = detail_category_values_class = ''

                if detail_category_class != detail_category_values_class:
                    values = soup.find_all('div', class_=detail_category_values_class)
                    for i, item in enumerate(soup.find_all('div', class_=detail_category_class)):
                        ### To get a number for the price do values[i].text.strip(euro symbol)
                        venue_data[item.text.lower()] = values[i].text

                # add the venue data to the general data set
                data.append(venue_data)
            if vb == 1:
                print(f'Scraped batch {batch} out of {total_batches} batches.')
        return data

            #################################
            # CHECK OUT THE SCREENSHOTS
            # data to get:: column name: Entry type

            # DONE 1. restaurant name: str
            # DONE 2. address: str  (street, postcode, city, country)
            # DONE 3. cuisine: List[str]

            # Find in the details page:
            # DONE 1. cuisine: List[str]. Or in the main page (see screenshots)
            # 2. about: str (raw text). <div class="restaurants-detail-overview-cards-DetailsSectionOverviewCard__desktopAboutText--VY6hs"> </div>

            # Find in the location page:
            # DONE 1. address: str. Or in the main page (see screenshots)

            # Find in the reviews page:
            # page url = https://www.tripadvisor.com/Restaurant_Review-g187323-d8025081-Reviews-Happies-Berlin.html
            # review page url = https://www.tripadvisor.com/Restaurant_Review-g187323-d8025081-Reviews-Happies-Berlin.html#REVIEWS
            # DONE 1. price_range: str (symbols?)
            # 2. ratings: np.float, (all languages or english only?)
            #     or individual columns as: Excellent, Very good, Average, Poor, Terrible
            # 3. number_of_reviews: np.float
            # 4. text_reviews: List[str] (all languages or english only?)
            #################################

        # convert to pandas dataFrame with index a unique id (ta_01, ta_02 ...)
        # df = pd.DataFrame(data=data)
        # save as h5 or pickle or csv

    @staticmethod
    def _check_not_none(bs4out: list) -> Tuple[list, list]:
        out = list()
        text = list()
        for item in bs4out:
            try:
                text.append(item.text)
                out.append(True)
            except AttributeError:
                out.append(False)
                text.append([''])
        return out, text

    def _crawler(self, soup) -> List[str]:
        """Finds all urls from a Trip Advisor search page.

        Arguments:
        ----------
        soup: object,
            The bs4.BeautifulSoup object.

        Returns:
        --------
        urls: List[str],
            The urls of all the search pages.
        """
        results2 = soup.find(id='EATERY_LIST_CONTENTS').find_all('a', class_='pageNum taLnk')

        if not results2:
            warn("Couldn't find class 'pageNum taLnk'. Make sure you passed the correct url.")
            return []

        a = 'data-offset="'  # denotes the list items per page
        data_offsets = list()
        for item in results2:
            s = str(item)
            dummyvar = s.find(a)
            data_offsets.append(int(s[dummyvar + len(a): s.find('"', dummyvar + len(a))]))

        # get an example url to extract the url parts to append later
        b = 'href="'
        dummyvar = s.find(b)
        url = s[dummyvar + len(b): s.find('"', dummyvar + len(b))]
        url_parts = url.split(f'-oa{data_offsets[-1]}-')

        # get the difference between elements
        element_diff = [j - i for i, j in zip(data_offsets[:-1], data_offsets[1:])]

        # get mode of data_offsets
        offset = max(set(element_diff), key=element_diff.count)

        # use the offset to get all the urls
        urls = list()
        for i in range(0, data_offsets[-1], offset):
            urls.append(self.base_url + url_parts[0] + f'-oa{i + offset}-' + url_parts[1])
        print('Finished crawling\n')
        return urls

    def _get_page_listings(self, soup) -> List[str]:
        """Get all restaurants from 1 page.

        Arguments:
        ----------
        soup: object,
            The bs4.BeautifulSoup object.

        Returns:
        --------
        links: List[str],
            The restaurant web pages to scrape the data from.
        """
        results = soup.find(id='EATERY_SEARCH_RESULTS')

        # get the restaurant list
        # only the numbered ones (avoid the sponsored listings: 'data-test': 'SL_list_item')
        restaurant_elems = results.find_all('div',
                                            {'class': '_1llCuDZj',
                                             'data-test': re.compile(r"([0-9]+)(_list_item)")})
        # iterate through all elements
        links = list()
        for r in restaurant_elems:
            page_url = r.find('a', href=True)['href']  # the url to the restaurant page
            links.append(self.base_url + page_url)
        return links

    @staticmethod
    def _get_soup(url: str):
        """Returns the bs4.BeautifulSoup object."""
        page = requests.get(url)
        return BeautifulSoup(page.content, 'html.parser')


def main():
    # read command line arguments (the url)
    pass
    #URL = 'https://www.tripadvisor.com/Restaurants-g187323-Berlin.html'
    #soup = get_soup(URL)


if __name__ == '__main__':
    main()
