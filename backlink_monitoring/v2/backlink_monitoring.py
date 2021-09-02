#!/usr/bin/env python3

from bs4 import BeautifulSoup
from bs4.dammit import EncodingDetector
import requests
import pandas as pd
from datetime import datetime
import traceback
import re

SLACK_WEBHOOK = "YOUR_SLACK_CHANNEL_WEBHOOK" # REPLACE WITH YOUR WEBHOOK

def get_page(backlink, referent_link):
    # Add "http://" prefix to backlink if there is no protocol defined for a backlink
    if backlink.startswith('http') is not True:
        backlink = 'http://' + backlink

    try:
        resp = requests.get(
            backlink,
            allow_redirects=True
        )
    except Exception as e:
        return ("Backlink not reachable", "None")

    response_code = resp.status_code
    if response_code != 200:
        return ("Backlink not reachable", response_code)

    # Try to find encoding, decode content and load it to BeautifulSoup object
    http_encoding = resp.encoding if 'charset' in resp.headers.get('content-type', '').lower() else None
    html_encoding = EncodingDetector.find_declared_encoding(resp.content, is_html=True)
    encoding = html_encoding or http_encoding
    bsObj = BeautifulSoup(resp.content, 'lxml', from_encoding=encoding)

    if len(bsObj.findAll('meta', content=re.compile("noindex"))) > 0:
        return('Noindex', response_code)

    referent_link = referent_link.lstrip('https:').rstrip('/')
    elements = bsObj.findAll('a', href=re.compile(referent_link))
    if elements == []:
        return ('Link was not found', response_code)
    else:
        element = elements[0]

    try:
        if 'nofollow' in element['rel']:
            return ('Link found, nofollow', response_code)
    except KeyError:
        return ('Link found, dofollow', response_code)

    # If every check is passed, return "Link found, dofollow" status
    return ('Link found, dofollow', response_code)


def push_to_slack(df, webhook_url = SLACK_WEBHOOK):
    df.reset_index(drop= True, inplace= True)

    # Align text beautifully
    for col in df.columns.tolist():
        max_len = len(max(df[col].astype(str).tolist(), key=len))
        for value in df[col].tolist():
            df.loc[df[col].astype(str) == str(value), col] = str(value) + (max_len - len(str(value)))*" "

    cols = df.columns.tolist()
    dict_df = df.to_dict()
    header = ''
    rows = []

    for i in range(len(df)):
        row = ''
        for col in cols:
            row +=  "`" + str(dict_df[col][i]) + "` "
        row = ':black_small_square:' + row
        rows.append(row)

    data = ["*" + "Backlinks" "*\n"] + rows

    slack_data = {
        "text": '\n'.join(data)
    }

    requests.post(webhook_url, json = slack_data)

    return df


def main():
    # Wrap everything in try-except clause in order to catch all errors
    try:
        backlinks_list = ['https://example.com', 'www.example.co.uk', 'http://www.test.com'] # REPLACE WITH YOUR BACKLINKS
        referent_links_list = ['https://oxylabs.io/blog/what-is-web-scraping', 'https://oxylabs.io/blog/the-difference-between-data-center-and-residential-proxies', 'https://oxylabs.io/blog/what-is-proxy'] # REPLACE WITH YOUR REFERENT LINKS

        df = None
        print('Scraping and parsing data from backlinks...')
        for backlink, referent_link in zip(backlinks_list, referent_links_list):
            (status, response_code) = get_page(backlink, referent_link)
            if df is not None:
                df = df.append([[backlink, status, response_code]])
            else:
                df = pd.DataFrame(data=[[backlink, status, response_code]])
        df.columns = ['Backlink', 'Status', 'Response code']
        df.reset_index(inplace=True, drop=True)

        print('Pushing notification to Slack...')
        push_to_slack(df)

    except:
        tb = traceback.format_exc()
        print(str(datetime.now()) + '\n' + tb + '\n')
        return -1

    return 1

if __name__ == '__main__':
    main()
