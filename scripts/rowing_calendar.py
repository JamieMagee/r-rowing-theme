import re
import time
import urllib.request as request
from datetime import datetime

import praw
from prawoauth2 import PrawOAuth2Mini
from lxml import html

from tokens import subreddit, app_secret, app_key, access_token, refresh_token
from settings import user_agent, scopes

def parse_british_rowing(webpage):
    global dates, events, web, locations
    tree = html.fromstring(webpage)
    dates.append([datetime.strptime(date, '%d/%m/%Y') for date in
                  tree.xpath(
                      '//*[@id="britishrowing-calendar"]/tbody/tr[*]/td[2]/span[*]/small/text()')])
    events.append(
        tree.xpath('//*[@id="britishrowing-calendar"]/tbody/tr[*]/td[2]/span[*]/a/text()'))
    web.append(['http://www.britishrowing.org' + site for site in
                tree.xpath('//*[@id="britishrowing-calendar"]/tbody/tr[*]/td[2]/span[*]/a/@href')])
    locations.append([''] * len(
        tree.xpath('//*[@id="britishrowing-calendar"]/tbody/tr[*]/td[2]/span[*]/a/text()')))


def parse_regatta_central(webpage):
    global dates, events, web, locations
    tree = html.fromstring(webpage)
    try:
        dates.append([datetime.strptime(date.replace(' \r\n      ', ''), '%A%m/%d/%y') for date in
                      tree.xpath('//*[@id="tableResults"]/tbody/tr[*]/td[2]/text()')])
    except:
        dates.append([datetime.strptime(date.replace(' \n      ', ''), '%A%m/%d/%y') for date in
                      tree.xpath('//*[@id="tableResults"]/tbody/tr[*]/td[2]/text()')])
    events.append(tree.xpath('//*[@id="tableResults"]/tbody/tr[*]/td[4]/a/text()'))
    web.append(['https://www.regattacentral.com' + site for site in
                tree.xpath('//*[@id="tableResults"]/tbody/tr[*]/td[4]/a/@href')])
    locations.append(tree.xpath(
        '//*[@id="tableResults"]/tbody/tr[*]/td[8]/a/text()|//*[@id="tableResults"]/tbody/tr[*]/td[8]/text()'))


def generate_table(dates, events, web, locations):
    out = '|**Race**|**Date**|**Venue**|\n|-|-|-|\n'
    for i in range(len(dates)):
        if (dates[i] - datetime.now()).days >= -1:
            if (dates[i] - datetime.now()).days < 7:
                out += '|[' + events[i] + '](' + web[i] + ')|' + dates[i].strftime(
                    '%d %B') + '|' + locations[i] + '|\n'
            else:
                return out


def set_sidebar(out):
    print('[*] Logging in...')
    r = praw.Reddit(user_agent)
    oauth_helper = PrawOAuth2Mini(r, app_key=app_key, app_secret=app_secret,
                                  access_token=access_token, scopes=scopes,
                                  refresh_token=refresh_token)
    oauth_helper.refresh()
    print('[*] Login successful...')

    settings = r.get_settings(subreddit)
    desc = settings['description']
    table = re.compile('\|.*\|', re.DOTALL)
    desc = (re.sub(table, out, desc))
    r.update_settings(r.get_subreddit(subreddit), description=desc)
    print('[*] Logging out...')
    r.clear_authentication()


def flatten_list(list_of_lists):
    return [item for sublist in list_of_lists for item in sublist]


rc, br = 'https://www.regattacentral.com/regattas/index.jsp?c=', 'http://www.britishrowing.org/competing/calendar'
countries = ['AU', 'CA', 'DE', 'IT', 'US', 'DK', 'HK', 'IE', 'NO']
while True:
    dates, events, web, locations = [], [], [], []

    for country in countries:
        print('[*] Fetching page...')
        page = request.urlopen(rc + country).read().decode('utf-8')
        print('[*] Parsing calendar...')
        parse_regatta_central(page)

    page = request.urlopen(br).read().decode('utf-8')
    print('[*] Parsing calendar...')
    parse_british_rowing(page)

    dates = flatten_list(dates)
    events = flatten_list(events)
    web = flatten_list(web)
    locations = flatten_list(locations)

    events_ = [points[1] for points in sorted(zip(dates, events, web, locations))]
    web_ = [points[2] for points in sorted(zip(dates, events, web, locations))]
    locations_ = [points[3] for points in sorted(zip(dates, events, web, locations))]
    dates_ = sorted(dates)

    print('[*] Generating table...')
    out = generate_table(dates_, events_, web_, locations_)
    print('[*] Updating sidebar...')
    if len(out) <= 5120:
        set_sidebar(out)
    else:
        print('[*] Table too large')

    print('[*] Sleeping...')
    time.sleep(43200)
