#!/usr/bin/env python3

###############################
# This script scrapes backlink websites and checks if it:
#     a) gives a valid response
#     b) its HTML contains a link to our websites
#     c) it has no "noindex" element in HTML
#     d) there is no "noffolow" tag in our link's element in HTML
# Info about backlinks is then saved to local .csv file. Also, a notication is pushed to a Slack channel with potentially problematic backlinks and their statuses
###############################

# Import BeautifulSoup - library for puling data out of HTML
from bs4 import BeautifulSoup
from bs4.dammit import EncodingDetector

# Import other standart Python libraries, that will be used later
import requests
import json
import pandas as pd
import random
from datetime import datetime
import traceback
import re
import os

# More on Slack apps and webhooks: https://api.slack.com/messaging/webhooks
SLACK_WEBHOOK = "YOUR_SLACK_CHANNEL_WEBHOOK"


def get_page(website, our_link):
    # Add "http://" prefix to website if there is no protocol defined for a backlink
    if website.startswith('http') is not True:
        website = 'http://' + website

    # Get contents of a website
    try:
        resp = requests.get(
            website,
            allow_redirects=True
        )
    except Exception as e:
        return ("Website not reachable", "None")

    # Check if a website is reachable
    response_code = resp.status_code
    if response_code != 200:
        return ("Website not reachable", response_code)

    # Try to find encoding, decode content and load it to BeautifulSoup object
    http_encoding = resp.encoding if 'charset' in resp.headers.get(
        'content-type', '').lower() else None
    html_encoding = EncodingDetector.find_declared_encoding(
        resp.content, is_html=True)
    encoding = html_encoding or http_encoding
    bsObj = BeautifulSoup(resp.content, 'lxml', from_encoding=encoding)

    # Check if website's HTML contains "noindex" element
    if len(bsObj.findAll('meta', content=re.compile("noindex"))) > 0:
        return('Noindex', response_code)

    # Check if HTML contains a link to your page
    our_link = our_link.lstrip('https:').rstrip('/')
    elements = bsObj.findAll('a', href=re.compile(our_link))
    if elements == []:
        return ('Link was not found', response_code)
    else:
        element = elements[0]

    # Find your link and check if its element contains a "nofollow" tag
    try:
        if 'nofollow' in element['rel']:
            return ('Link found, nofollow', response_code)
    except KeyError:
        return ('Link found, dofollow', response_code)

    # If every check is passed, return "Link found, dofollow" status
    return ('Link found, dofollow', response_code)


def push_to_slack(df, webhook_url=SLACK_WEBHOOK):
    df.reset_index(drop=True, inplace=True)

    # Align text beautifully
    for col in df.columns.tolist():
        max_len = len(max(df[col].astype(str).tolist(), key=len))
        for value in df[col].tolist():
            df.loc[df[col].astype(str) == str(value), col] = str(
                value) + (max_len - len(str(value)))*" "

    cols = df.columns.tolist()
    dict_df = df.to_dict()
    header = ''
    rows = []

    for i in range(len(df)):
        row = ''
        for col in cols:
            row += "`" + str(dict_df[col][i]) + "` "
        row = ':black_small_square:' + row
        rows.append(row)

    if rows == []:
        rows = ['\n' + "`" + "No problematic backlinks were found" + "`"]

    data = ["*" + "Problematic backlinks" "*\n"] + rows

    slack_data = {
        "text": '\n'.join(data)
    }

    response = requests.post(webhook_url, json=slack_data)

    return df


def main():
    # Wrap everything in try-except clause in order to catch all errors
    try:
        # 1) Get backlinks and our links
        websites = ['https://example.com', 'www.example.co.uk',
                    'http://www.geekscab.com/2019/07/how-much-information-can-ip-address.html']  # A LIST OF BACKLINKS
        our_links = ['https://oxylabs.io/blog/what-is-web-scraping', 'https://oxylabs.io/blog/the-difference-between-data-center-and-residential-proxies',
                     'https://oxylabs.io/blog/what-is-proxy']  # A LIST OF YOUR LINKS

        # 2) Scrape a website and check if:
        #  a) gives a valid response (not a blank / error)
        #  b) its HTML contains a link to our websites
        #  c) there is no "noffolow" tag in our link's element

        df = None
        print('Scraping and parsing data from websites...')
        for website, our_link in zip(websites, our_links):
            (status, response_code) = get_page(website, our_link)
            if df is not None:
                df = df.append([[website, status, response_code]])
            else:
                df = pd.DataFrame(data=[[website, status, response_code]])
        df.columns = ['Website', 'Status', 'Response code']
        df.reset_index(inplace=True, drop=True)

        # Save to .csv file locally
        df.to_csv('statuses.csv', index=None)

        # 3) Push notication to Slack
        print('Pushing notification to Slack...')
        df_to_push = df.loc[df['Status'] !=
                            'Link found, dofollow'][['Website', 'Status']]
        push_to_slack(df_to_push)

    except:
        tb = traceback.format_exc()
        print(str(datetime.now()) + '\n' + tb + '\n')
        return -1

    return 1


if __name__ == '__main__':
    main()
