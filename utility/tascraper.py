"""Web scraper for the trip advisor website.

Dependencies:
-------------
* beautifulsoup4
* requests
* re
* warnings
"""
import requests
import re
from bs4 import BeautifulSoup
from typing import List
from warnings import warn


class Scraper:
    """
    Examples:
    --------
    >>> from tascraper import Scraper
    >>> URL = 'https://www.tripadvisor.com/Restaurants-g187323-Berlin.html'
    >>> scraper = Scraper()
    >>> links = scraper.parse(url=URL)
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

    def parse(self, url: str, all_pgs=False) -> List[List[str]]:
        """Get list of restaurants.

        Arguments:
        ----------
        url: str,
            The original url (the first page when you search for restaurants on Trip Advisor)

        all_pgs: bool, (optional; default=False)
            Set to True to automatically crawl and extract the restaurant listings from subsequent pages.

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
            # VERY SLOW
            # get sub-pages with restaurants
            all_pages = [url] + self._crawler(soup)
            links = list()
            for page in all_pages:
                links.append(self._get_page_listings(self._get_soup(page)))
        else:
            # get the page listings from a single page
            links = [self._get_page_listings(soup)]
        return links

    def scrape(self, links: List[str]):
        for link in links:
            scrape_page(link)
            #################################
            # CHECK OUT THE SCREENSHOTS
            # data to get:: column name: Entry type

            # 1. restaurant name: str
            # 2. address: str or in the main page (see screenshots)
            # 3. cuisine: List[str]or in the main page (see screenshots)

            # Find in the details page:
            # 1. cuisine: List[str]or in the main page (see screenshots)
            # 2. about: str (raw text). <div class="restaurants-detail-overview-cards-DetailsSectionOverviewCard__desktopAboutText--VY6hs"> </div>

            # Find in the location page:
            # 1. address: str or in the main page (see screen shots)

            # Find in the reviews page:
            # page url = https://www.tripadvisor.com/Restaurant_Review-g187323-d8025081-Reviews-Happies-Berlin.html
            # review page url = https://www.tripadvisor.com/Restaurant_Review-g187323-d8025081-Reviews-Happies-Berlin.html#REVIEWS
            # 1. price_range: str (symbols?)
            # 2. ratings: np.float, (all languages or english only?)
            #     or individual columns as: Excellent, Very good, Average, Poor, Terrible
            # 3. number_of_reviews: np.float
            # 4. text_reviews: List[str] (all languages or english only?)
            #################################

        # convert to pandas dataFrame with index a unique id (ta_01, ta_02 ...)
        # save as h5 or pickle

    def scrape_page(self, url: str):
        """Get the data from a specific restaurant page."""
        pass

    def _crawler(self, soup) -> list:
        results2 = soup.find(id='EATERY_LIST_CONTENTS').find_all('a', class_='pageNum taLnk')

        if not results2:
            warn("Couldn't find class 'pageNum taLnk'. Make sure you passed the correct url")
            return []

        a = 'data-offset="'  # denotes the list items per page
        data_offsets = list()
        for item in results2:
            s = str(item)
            data_offsets.append(int(s[s.find(a) + len(a): s.find('"', s.find(a) + len(a))]))

        # get an example url to extract the common web page name
        b = 'href="'
        url = s[s.find(b)+len(b): s.find('"', s.find(b)+len(b))]
        url_parts = url.split(f'-oa{data_offsets[-1]}-')

        # get the difference between elements
        dummy = [j - i for i, j in zip(data_offsets[:-1], data_offsets[1:])]

        # get mode of data_offsets
        offset = max(set(dummy), key=dummy.count)

        # use offset to get all the urls
        urls = list()
        for i in range(0, data_offsets[-1], offset):
            urls.append(self.base_url + url_parts[0] + f'-oa{i + offset}-' + url_parts[1])
            # urls.append(self.base_url + f"/Restaurants-g187323-oa{i + offset}-Berlin.html#EATERY_LIST_CONTENTS")
        print('Finished crawling\n')  # DEBUGGING
        return urls

    def _get_page_listings(self, soup) -> list:
        """Get all restaurants from 1 page.

        Arguments:
        ----------
        soup: object,
            The bs4.BeautifulSoup object.

        Returns:
        --------
        links: list,
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
