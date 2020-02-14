"""Web scraper for the Trip Advisor website.

This class module is built primarily to extract data from Berlin restaurant pages.
Although it hasn't been tested, it should work without any changes for other cities as well.

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
    >>> links = scraper.crawl(url=URL, all_pgs=False)
    >>> data = scraper.scrape(links, lang='ALL', vb=1)

    To get data from a single page:
    >>> scraper = Scraper()
    >>> data = scraper.parse_page(scraper._get_soup(URL))
    """

    def __init__(self):  # , argv):
        self.base_url = None
        self.domain_name = None
        # self.url = self.parse_arguments(argv)

    # def parse_arguments(self, argv):
    #     assert len(argv) == 2
    #     return argv[0], argv[1]

    def crawl(self, url: str, all_pgs=True) -> List[List[str]]:
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

        print(f'[crawl] From url {url}')
        soup = self._get_soup(url)
        print('[crawl] Retrieving restaurant listings...\n')
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
        print('[crawl] Retrieved all restaurant listings.\n')
        return links

    def scrape(self, links: List[List[str]], lang='ALL', vb=0) -> List[dict]:
        """Extracts data from each restaurant page in links.

        Arguments:
        ----------
        links: List[List[str]],
            The restaurant web pages to scrape the data from.

        lang: str, (optional; default='ALL')
            The language filter to use for getting the reviews. Use 'en' for english.

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

        v_id = 0       # counter for assigning unique venue id
        data = list()  # populate with the individual restaurant data
        batch = 0      # to keep track of the number of link batches scraped
        total_batches = len(links)
        for search_page in links:
            batch += 1
            for link in search_page:
                if vb == 2:
                    print(f"Scraping {link}")

                soup = self._get_soup(f"{link}?filterLang={lang}")  # apply the language filter

                try:
                    # get the venue_data
                    venue_data = self.parse_page(soup)

                    # assign a unique id
                    venue_data['venue_id'] = f'id_{v_id}'
                    v_id += 1

                    # add it to the data set
                    data.append(venue_data)
                except:
                    print(f'[scrape]: Could not scrape {link}\n')

            if (vb == 1) & (len(links) != 0):
                print(f'Scraped batch {batch} out of {total_batches} batches.')
        return data

    def parse_page(self, soup) -> dict:
        """Parses the HTML and scrapes page data.

        Arguments:
        ----------
        soup: object,
            The bs4.BeautifulSoup object.

        Returns:
        --------
        venue_data: dict,
            The scraped restaurant data.
        """
        # ======== Get the info at the top of the page ========
        top_info = soup.find(id='taplc_resp_rr_top_info_rr_resp_0')
        name = top_info.find(class_='ui_header h1')
        addr_street = top_info.find('div', class_='businessListingContainer').find('span',
                                                                                   class_='street-address')
        addr_extended = top_info.find('div', class_='businessListingContainer').find('span',
                                                                                     class_='extended-address')
        locality = top_info.find('div', class_='businessListingContainer').find('span', class_='locality')
        country = top_info.find('div', class_='businessListingContainer').find('span', class_='country-name')

        city = soup.select("span[class='header_popularity popIndexValidation']")[0].a.text
        dm = 'Restaurants in '  # should be the same in all web pages
        city = city[city.find(dm)+len(dm):]

        # check for NoneTypes and get the text for each variable
        checks, texts = self._check_not_none([name, addr_street, addr_extended, locality, country])
        #name, [postcode, city], country = texts[0], texts[3].strip(', ').split(), texts[4]
        name, postcode_city, country = texts[0], texts[3], texts[4]

        postcode = postcode_city.replace(',', '').strip().strip(city).strip()

        # concatenate the addresses to get the full address
        if sum(checks[1:3]) == 2:
            addr_street = texts[1] + f', {texts[2]}'
        else:
            addr_street = texts[1]

        # get the symbol based price range
        try:
            price_range_symbol = soup.select('.header_links a')[0].text
        except:
            price_range_symbol = ''


        # populate with the restaurant data
        venue_data = dict()
        venue_data['name'] = name
        venue_data['address'] = addr_street
        venue_data['postcode'] = postcode
        venue_data['city'] = city
        venue_data['country'] = country
        venue_data['price range symbol'] = price_range_symbol

        # ======== Get the details ========
        try:
            # the class name is not the same in every web page so we choose by the text
            details_top = soup.find("div", text="CUISINES")
            # TODO: If 'CUISINES' is not found then we don't extract anything. Find a more robust method

            # get the class name
            detail_category_class = details_top.attrs['class'][0]

            # get the price value class name
            detail_category_values_class = details_top.find_next_sibling("div").attrs['class'][0]
        except AttributeError:
            print("[parse page] Could not fetch the details.\n")
            detail_category_class = detail_category_values_class = ''

        if detail_category_class != detail_category_values_class:
            values = soup.find_all('div', class_=detail_category_values_class)
            for i, item in enumerate(soup.find_all('div', class_=detail_category_class)):
                venue_data[item.text.lower()] = values[i].text

        # ======== get the ratings ========
        # find the 'Traveler rating' section
        b = soup.select("div[class='node-preserve'][data-ajax-preserve='preserved-filters_detail_checkbox_trating_true']")

        # contents[0] is always the section title (e.g. "Traveler rating")
        label_elems = b[0].contents[1].select('div')[0].select('label')
        label_elems_values = b[0].contents[1].select('div')[0].select("span[class='row_num is-shown-at-tablet']")
        for i, item in enumerate(label_elems):
            # convert to float and add it to the dictionary
            venue_data['rating_'+item.text] = float(label_elems_values[i].text.replace(',', '.'))

        return venue_data

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
        print('Finished crawling.\n')
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
    def _check_not_none(bs4out: list) -> Tuple[list, list]:
        """Checks for NoneTypes and gets the text for each item."""
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

    @staticmethod
    def _get_soup(url: str):
        """Returns the bs4.BeautifulSoup object."""
        page = requests.get(url)
        return BeautifulSoup(page.content, 'html.parser')


def main():
    # read command line arguments (the url)
    pass


if __name__ == '__main__':
    main()
