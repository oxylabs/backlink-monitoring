# Backlink checker
[<img src="https://img.shields.io/static/v1?label=&message=Python&color=brightgreen" />](https://github.com/topics/python) [<img src="https://img.shields.io/static/v1?label=&message=web%20scraping&color=important" />](https://github.com/topics/web-scraping)

## Table of Contents

- [Packages Required](#packages-required)
- [Checking backlinks](#checking-backlinks)
  - [STEP 1: Check if backlink is reachable](#step-1-check-if-backlink-is-reachable)
  - [STEP 2: Check if backlink HTML has noindex element](#step-2-check-if-backlink-html-has-noindex-element)
  - [STEP 3: Check if backlink HTML contains a link to a referent page](#step-3-check-if-backlink-html-contains-a-link-to-a-referent-page)
  - [STEP 4: Check if referent page is marked as "nofollow"](#step-4-check-if-referent-page-is-marked-as-nofollow)
- [Assigning results to Pandas DataFrame](#assigning-results-to-pandas-dataframe)
- [Pushing results to Slack](#pushing-results-to-slack)


Backlink checker is a simple tool, which checks backlink quality, identifies problematic backlinks, and outputs them to a specific [Slack](https://slack.com/) channel.

The tool tries to reach a backlink, which is supposed to contain a referent link, and checks if it indeed does. If a backlink contains a referent link, the tool retrieves the HTML of that backlink and checks for certain HTML elements, which indicate good quality of backlink.

## Packages Required

The first step is to prepare the environment. The backlink checker is written in Python. The most common Python packages for creating any web crawling tool are Requests and Beautiful Soup 4 - a library needed for pulling data out of HTML. Also, make sure you have Pandas package installed, as it will be used for some simple data wrangling.

These packages can be installed using the `pip install` command. 
<!-- Open the terminal, and create a virtual environment (optional but recommended). You can use [virtualenv package](https://pypi.org/project/virtualenv/) ,  [Anaconda distribution](https://docs.anaconda.com/anaconda/navigator/tutorials/manage-environments/), or Python's [venv module](https://docs.python.org/3/tutorial/venv.html) to create virtual environments.

Activate the virtual environment and run the following command. Note that if you are not working with a virtual environment, add `--user` to the following command. -->

```python
pip install beautifulsoup4 requests pandas
```

This will install all the three needed packages. 

Important: Note that version 4 of [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) is being installed here. Earlier versions are now obsolete. 

## Checking backlinks

The script scrapes backlink websites and checks for several backlink quality signs:
- if backlink is reachable
- if backlink contains _noindex_ element or not
- if backlink contains a link to a referent page
- if link to referent's page is marked as _nofollow_

### STEP 1: Check if backlink is reachable

The first step is to try to reach the backlink. This can be done using the Requests library's `get()` method.

```python
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
```

If a request returns an error (such as `404 Not Found`) or backlink cannot be reached, backlink is assigned _Backlink not reachable_ status. 

### STEP 2: Check if backlink HTML has `noindex` element

To be able to navigate in the HTML of a backlink, a Beautiful soup object needs to be created.

```python
bsObj = BeautifulSoup(resp.content, 'lxml', from_encoding=encoding)
```

Note that if you do not have lxml installed already, you can do that by running `pip install lxml`.

Beautiful Soup's `find_all()` method can be used to find if there are `<meta>` tags with `noindex` attributes in HTML. If that's true, let's assign _Noindex_ status to that backlink.

```python
if len(bsObj.findAll('meta', content=re.compile("noindex"))) > 0:
    return('Noindex', response_code)
```

### STEP 3: Check if backlink HTML contains a link to a referent page

Next, it can be found if HTML contains an anchor tag (marked as `a`) with a referent link. If there was no referent link found, let's assign _Link was not found_ status to that particular backlink.

```python
elements = bsObj.findAll('a', href=re.compile(our_link))
if elements == []:
    return ('Link was not found', response_code)
```

### STEP 4: Check if referent page is marked as `nofollow`

Finally, let's check if an HTML element, containing a link to a referent page, has a `nofollow` tag. This tag can be found in the `rel` attribute.

```python
try:
    if 'nofollow' in element['rel']:
        return ('Link found, nofollow', response_code)
except KeyError:
    return ('Link found, dofollow', response_code)
```

Based on the result, let's assign either _Link found, nofollow_ or _Link found, dofollow_ status.


## Assigning results to Pandas DataFrame

After getting status for each backlink and referent link pair, let's append this information (along with the response code from a backlink) to pandas DataFrame.

```python
df = None
for backlink, referent_link in zip(backlinks_list, referent_links_list):
    (status, response_code) = get_page(backlink, referent_link)
    if df is not None:
        df = df.append([[backlink, status, response_code]])
    else:
        df = pd.DataFrame(data=[[backlink, status, response_code]])
df.columns = ['Backlink', 'Status', 'Response code']
```

`get_page()` function refers to the 4-step process that was described above (please see the complete code for the better understanding).


## Pushing results to Slack

In order to be able to automatically report backlinks and their statuses in a convenient way, a Slack app could be used. You will need to create an app in Slack and assign incoming webhook to connect it and Slack's channel you would like to post notifications to. More on Slack apps and webhooks: https://api.slack.com/messaging/webhooks

```python
SLACK_WEBHOOK = "YOUR_SLACK_CHANNEL_WEBHOOK"
```

Although the following piece of code could look a bit complicated, all that it does is formatting data into a readable format and pushing that data to Slack channel via POST request to Slack webhook.

```python
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

requests.post(webhook_url = SLACK_WEBHOOK, json = slack_data)
```


That's it! In this example, Slack was used for reporting purposes, but it is possible to adjust the code so that backlinks and their statuses would be exported to a .csv file, google spreadsheets, or database. 

Please see [backlink_monitoring_oxylabs.py](/backlink_monitoring_oxylabs.py) for the complete code.

