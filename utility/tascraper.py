"""Web scraper for the Trip Advisor website.

This class module is built primarily to extract data from Berlin restaurant pages.
Although it hasn't been tested, it should work without any changes for other cities as well.

Dependencies:
-------------
* bs4 - BeautifulSoup, a library to parse HTML documents and navigate the element tree
* requests - to make HTTP requests from code
* re - Regex library, to search for more complex strings
* warnings - to issue useful user warnings
* selenium - to interact with the web page and uncover hidden data
"""
import requests
import re
from bs4 import BeautifulSoup
from typing import List, Tuple
from warnings import warn
from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException
from selenium.webdriver.support.ui import WebDriverWait


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
    >>> URL = 'https://www.tripadvisor.com/Restaurant_Review-g187323-d2047693-Reviews-Ga_Ya_Ya-Berlin.html'
    >>> scraper = Scraper()
    >>> data, sess = scraper.parse_page(scraper.get_soup(URL))
    >>> if sess:
    >>>     sess.close()
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
        soup = self.get_soup(url)
        print('[crawl] Retrieving restaurant listings...\n')
        if all_pgs:
            # get sub-pages with restaurants
            all_pages = [url] + self._crawler(soup)
            links = list()
            # slow due to get_soup()
            for page in all_pages:
                links.append(self._get_page_listings(self.get_soup(page)))
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
        session = None  # for selenium web driver session
        for search_page in links:
            batch += 1
            for link in search_page:
                if vb == 2:
                    print(f"Scraping {link}")
                # apply the language filter and get the soup
                soup = self.get_soup(f"{link}?filterLang={lang}")

                try:
                    # get the venue_data
                    venue_data, session = self.parse_page(soup, url=link, session=session)

                    # add the url
                    venue_data['url'] = link

                    # assign a unique id
                    venue_data['venue_id'] = f'id_{v_id}'
                    v_id += 1

                    # add it to the data set
                    data.append(venue_data)
                except:
                    print(f'[scrape] Could not scrape {link}\n')

            if (vb == 1) & (len(links) != 0):
                print(f'Scraped batch {batch} out of {total_batches} batches.')
        # close the session
        self._webdriversession(mode='close', wbdriver=session)
        return data

    def parse_page(self, soup, url='', session=None) -> Tuple:
        """Parses the HTML and scrapes page data.

        Arguments:
        ----------
        soup: object,
            The bs4.BeautifulSoup object.

        url: str, (optional; default='')
            The web page url must correspond to the soup object for the data
            to make sense.

        session: object, (selenium.webdriver when created) (optional; default=None)
            The web driver session created if needed.

        Returns:
        --------
        venue_data: dict,
            The scraped restaurant data.

        session: object, (selenium.webdriver when created)
            The web driver session.
        """

        # data_names = ['name', 'address', 'postcode', 'city', 'country',
        #               'price range symbol', 'price range', 'cuisines',
        #               'meals', 'features', 'special diets', 'about']
        # # initialise the output
        # venue_data = {item:'' for item in data_names}

        # fixed parameters for searching the html
        search_class_params = {'about_text_class': 'restaurants-details-card-DesktopView__desktopAboutText--1VvQH',
                               'hidden_details_titles_class': 'restaurants-details-card-TagCategories__categoryTitle--28rB6',
                               'hidden_details_values_class': 'restaurants-details-card-TagCategories__tagText--Yt3iG'
                               }
        # declare the output
        venue_data = dict()

        # ======== Get the info at the top of the page ========
        top_info = soup.find(id='taplc_resp_rr_top_info_rr_resp_0')
        name = top_info.find(class_='ui_header h1')
        addr_street = top_info.find('div', class_='businessListingContainer').find('span',
                                                                                   class_='street-address')
        addr_extended = top_info.find('div', class_='businessListingContainer').find('span',
                                                                                     class_='extended-address')
        locality = top_info.find('div', class_='businessListingContainer').find('span', class_='locality')
        country = top_info.find('div', class_='businessListingContainer').find('span', class_='country-name')

        try:
            city = soup.select("span[class='header_popularity popIndexValidation']")[0].a.text
            dm = 'Restaurants in '  # should be the same in all web pages
            city = city[city.find(dm)+len(dm):]
        except IndexError:
            try:
                city = soup.title.text.split(',')[1].strip().split()[0]  # example: restaurant name, city - Address
            except Exception as e:
                print('\t[parse page] Unable to extract city')
                print(f'Error details: {repr(e)}')
                city = None

        # check for NoneTypes and get the text for each variable
        checks, texts = self._check_not_none([name, addr_street, addr_extended, locality, country])
        #name, [postcode, city], country = texts[0], texts[3].strip(', ').split(), texts[4]
        name, postcode_city, country = texts[0], texts[3], texts[4]
        if city:
            postcode = postcode_city.replace(',', '').strip().strip(city).strip()
        else:
            postcode = postcode_city  # for manual processing

        # concatenate the addresses to get the full address
        if sum(checks[1:3]) == 2:
            addr_street = texts[1] + f', {texts[2]}'
        else:
            addr_street = texts[1]

        # get the symbol based price range
        try:
            price_symbols = soup.select('.header_links a')[0].text
            venue_data['price range symbol'] = price_symbols if '$' in price_symbols else None
        except:
            pass

        # populate with the restaurant data
        venue_data['name'] = name
        venue_data['address'] = addr_street
        venue_data['postcode'] = postcode
        venue_data['city'] = city
        venue_data['country'] = country

        # ======== Get the details ========
        try:
            # # the class name is not the same in every web page so we choose by the text
            # details_top = soup.find("div", text="CUISINES")
            #
            # # get the class name
            # detail_category_class = details_top.attrs['class'][0]
            #
            # # get the price value class name
            # detail_category_values_class = details_top.find_next_sibling("div").attrs['class'][0]

            items = soup.find('div',
                              class_='restaurants-details-card-DetailsCard__innerDiv--1Imq5').div.next_sibling.div
            try:
                about_text = items.find('div', class_=search_class_params['about_text_class']).text
                venue_data['about'] = about_text
            except AttributeError:
                pass

            details_titles = items.select(f".{search_class_params['hidden_details_titles_class']}")
            details_values = items.select(f".{search_class_params['hidden_details_values_class']}")
            for i, item in enumerate(details_titles):
                venue_data[item.text.lower()] = details_values[i].text

        except AttributeError:
            try:
                # create a session if it does not already exist
                if not session:
                    session = self._webdriversession(mode='create', wbdriver=None)

                # wait until the page opens completely
                session.get(url)
                session.implicitly_wait(100)

                # interact with the web page to get the data and update the venue_data dictionary
                venue_data.update(self.find_details(session, url=url))
            except Exception as e:
                print("[parse page] Could not fetch the details.")
                print(f'Error details: {repr(e)}\n')
            finally:
                detail_category_class = detail_category_values_class = ''

        # if detail_category_class != detail_category_values_class:
        #     values = soup.find_all('div', class_=detail_category_values_class)
        #     for i, item in enumerate(soup.find_all('div', class_=detail_category_class)):
        #         venue_data[item.text.lower()] = values[i].text

        # ======== get the ratings ========
        # find the 'Traveler rating' section
        b = soup.select("div[class='node-preserve'][data-ajax-preserve='preserved-filters_detail_checkbox_trating_true']")

        # contents[0] is always the section title (e.g. "Traveler rating")
        try:
            label_elems = b[0].contents[1].select('div')[0].select('label')
            label_elems_values = b[0].contents[1].select('div')[0].select("span[class='row_num is-shown-at-tablet']")
            for i, item in enumerate(label_elems):
                # convert to integer and add it to the dictionary
                venue_data['rating_'+item.text] = int(label_elems_values[i].text.replace(',', '').replace('.', ''))
        except IndexError as e:
            # print('[parse page]: No ratings found')
            pass
        return venue_data, session

    def find_details(self, session, url) -> dict:
        """Returns the details section data by using the session.

        Arguments:
        ----------
        session: object, (selenium.webdriver)
            The web driver session.

        url: str,
            The web page url. The current session must be open at this url.

        Returns:
        --------
        data: dict(),
            The extracted data from the details section pop up window.
        """
        # fixed parameters
        hidden_params = {'hidden_class': 'restaurants-detail-overview-cards-DetailsSectionOverviewCard__detailsContent--1hucM',
                         'hidden_about_class': 'restaurants-detail-overview-cards-DetailsSectionOverviewCard__desktopAboutText--VY6hs',
                         'hidden_details_titles_class': 'restaurants-detail-overview-cards-DetailsSectionOverviewCard__categoryTitle--2RJP_',
                         'hidden_details_values_class': 'restaurants-detail-overview-cards-DetailsSectionOverviewCard__tagText--1OH6h'
                         }

        details_button = session.find_elements_by_link_text('View all details')
        if len(details_button) > 1:
            print("More than one 'View all details' button")
        elif len(details_button) == 0:
            print("Didn't find 'View all details' button")

        data = dict()
        for button in details_button:
            # button.click()  # does not work
            session.execute_script('arguments[0].click();', button)  # this one works

            # get soup
            element = WebDriverWait(session, 10).until(lambda x: x.find_element_by_class_name('_1Hzf3Xci'))
            soup = BeautifulSoup(session.page_source, 'html.parser')

            # get the about section
            try:
                # about_text = soup.select(f'.{hidden_class}')[0].div.contents[0].find('div', text='About').next_sibling.next_sibling.text
                about_text = soup.select(f".{hidden_params['hidden_class']}")[0].div.contents[0].find('div', class_= hidden_params['hidden_about_class']).text
                data['about'] = about_text
            except AttributeError:
                pass

            # get the details
            details_titles = soup.select(f".{hidden_params['hidden_class']}")[0].div.contents[1].div.select(
                f".{hidden_params['hidden_details_titles_class']}")
            details_values = soup.select(f".{hidden_params['hidden_class']}")[0].div.contents[1].div.select(
                f".{hidden_params['hidden_details_values_class']}")
            for i, item in enumerate(details_titles):
                data[item.text.lower()] = details_values[i].text
        return data

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
        print('\t[_crawler] Finished crawling.\n')
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
    def get_soup(url: str):
        """Returns the bs4.BeautifulSoup object."""
        page = requests.get(url)
        return BeautifulSoup(page.content, 'html.parser')

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
    def _webdriversession(mode='create', wbdriver=None):
        """Creates or closes a web driver session.

        Arguments:
        ----------
        mode: str,
            The mode: 'create' to create a new driver session if one
            doesn't already exist or 'close' to close the current
            session defined by wbdriver.

        wbdriver: object (selenium.webdriver),
            The web driver created. Only used when mode='close' to close
            the driver session.

        Returns:
        --------
        session: object (selenium.webdriver),
            The web driver session created.
        """
        if mode not in ['create', 'close']:
            raise ValueError(f"mode='{mode}' is invalid. Valid values are ['create', 'close']")

        try:
            if mode == 'create':
                session = webdriver.Safari()  # can use Chrome() or Firefox() as alternatives
                return session
            elif mode == 'close':
                wbdriver.close()
                print('Web driver session closed.')
        except (NameError, AttributeError, SessionNotCreatedException) as e:
            print('In _webdriversession: ' + repr(e))
        return

def main():
    # read command line arguments (the url)
    pass


if __name__ == '__main__':
    main()
