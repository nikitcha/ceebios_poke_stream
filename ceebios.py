import streamlit
import pandas
import numpy
import requests
import urllib
from scholarly import scholarly
from scholarly import scholarly, ProxyGenerator
#from bokeh.models.widgets import Div
import wiki
import webbrowser
# import wikidata
# Wikispecies
from pygbif import species, occurrences, maps
import gdelt_api

CORE_API = "https://core.ac.uk:443/api-v2"
API_KEY = "cJmoVEila3gB0zCIM2q1vpZnsKjr9XdG"

#pg = ProxyGenerator()
#pg.FreeProxies()
#pg.Tor_External(tor_sock_port=9050, tor_control_port=9051, tor_password="scholarly_password")
#scholarly.use_proxy(pg)

streamlit.set_page_config(page_title="Ceebios Species Explorer", page_icon='icon.png',layout="wide")
streamlit.image('https://ceebios.com/wp-content/uploads/2017/06/ceebios-logo-06-167x92.png')
streamlit.subheader('Open source project to help bio-mimicry research for Data Scientists and Engineers.')

streamlit.subheader('Search')
search = streamlit.text_input(label='Filter Species',value='')

@streamlit.cache
def get_species(search):
    suggests = species.name_suggest(search)
    name = [s.get('canonicalName') for s in suggests]
    name = set(name)
    return [n for n in name]

species_list = get_species(search)

name = streamlit.multiselect(label='Select Species', options=species_list)
if len(name)>1:
    streamlit.text('More than one species is selected!')
    streamlit.stop()
if len(name)==0 or not name[0]:
    streamlit.text('No species is selected!')
    streamlit.stop()
name = name[0]

def search_google(search_query, cnt = 30):
    pubs = []
    fields = {'title', 'author', 'abstract'} #
    while True:        
        pub = next(search_query)
        if not pub:
            break        
        bib = pub.get('bib')
        if not bib:
            break
        pubs.append({f:bib.get(f) for f in fields})
        if len(pubs)==cnt:
            break
    return pandas.DataFrame(pubs)

@streamlit.cache
def search_core(query, page,lang, cnt = 30):
    params = {"page": page, "pageSize": cnt, "apiKey": API_KEY, "language.name":lang}
    #core_query = " ".join((urllib.parse.quote(query), "biomimetism"))
    search_url = "/".join((CORE_API, "articles", "search", query))
    response = requests.get(search_url, params).json()
    info = response['data']
    fields = {'title', 'authors'}
    pubs = [{f:inf.get(f) for f in fields} for inf in info]
    return pandas.DataFrame(pubs)

@streamlit.cache
def get_google_queries(name):
    query = scholarly.search_pubs(name)
    pubs = search_google(query)
    return query, pubs

@streamlit.cache(allow_output_mutation=True)
def get_wiki(lang, name):
    wikiext = wiki.WikipediaExtractor(lang=lang)
    return wikiext.search_pages(name, best_match=True)

def open_page(url):    
    #js = "window.open('{}')".format(url)  # New tab or window
    #html = '<img src onerror="{}">'.format(js)
    #div = Div(text=html)
    #streamlit.bokeh_chart(div)
    webbrowser.open(url)

@streamlit.cache()
def get_gdelt(name):
    words = name.split(' ')
    url = gdelt_api.get_keywrods_url(words)
    data = requests.get(url)
    articles = data.json()
    if any(articles):
        out = [{'title':A['title'], 'url':A['url']} for A in articles['articles']]
    else: 
        out = []
    return pandas.DataFrame(out)


@streamlit.cache
def get_gbif(api, name):
    url = "https://api.gbif.org/v1/species/suggest?q="+urllib.parse.quote(name)
    data = requests.get(url)
    info = data.json()[0]
    if api=='Species':
        fields = ['kingdom','phylum','order','family', 'genus', 'species', 'scientificName','canonicalName']
        return {k:info[k] for k in fields}
    if api=='Maps':
        ans = occurrences.search(scientificName=info['scientificName'], hasCoordinate=True)
        if ans['count']>0:
            coords = [(float(res['decimalLongitude']), float(res['decimalLatitude'])) for res in ans['results']]
            coords = pandas.DataFrame(numpy.stack(coords))
            coords.columns = ['lon','lat']
            return coords
        else:
            return pandas.DataFrame()

    if api=='Literature':
        url = "https://api.gbif.org/v1/literature/search?q="+urllib.parse.quote(name)
        data = requests.get(url)
        info = data.json()
        return pandas.DataFrame(info['results'])


engine = streamlit.radio("Search Engine",('GBIF','CORE','Google Scholar', 'Wikipedia','Semantic Scholar')) #'World News (GDELT)')

streamlit.subheader('Results')
if engine=='GBIF':
    api = streamlit.radio("GBIF",('Species','Maps','Literature'))
    data = get_gbif(api, name)
    if api in ['Species', 'Literature']:
        streamlit.write(data)
    if api=='Maps':
        streamlit.map(data)
elif engine=='Google Scholar':
    try:
        query, pubs = get_google_queries(name)
        c1,c2 = streamlit.beta_columns((1,1))
        with c1:
            if streamlit.button(label='More Publications'):
                pubs = search_google(query)
        with c2:
            if streamlit.button(label='Open in Browser'):
                val = name.replace(' ','+')
                url = "https://scholar.google.com/scholar?as_vis=0&q={}&hl=en&as_sdt=0,5".format(val)
                open_page(url)
        streamlit.table(pubs)
    except:
        streamlit.text('IP is getting Captcha. Opening in seperate tab.')
        val = name.replace(' ','+')
        url = "https://scholar.google.com/scholar?as_vis=0&q={}&hl=en&as_sdt=0,5".format(val)
        open_page(url)
elif engine=='CORE':
    c1,c2,c3 = streamlit.beta_columns((1,1,1))
    with c1:
        corepage = streamlit.number_input(label='Page', min_value=1,value=1)
    with c2:
        corelang = streamlit.radio("CORE Language",('English','French'))
    with c3:
        if streamlit.button(label='Open in Browser'):
            url = "https://core.ac.uk/search?q="+name.replace(' ','+')
            open_page(url)
    pubs = search_core(name,corepage,corelang)
    streamlit.table(pubs)
elif engine=='Wikipedia':
    lang = streamlit.radio("Wiki Language",('en','fr'))
    page = get_wiki(lang, name)
    streamlit.markdown(page.summary)
    #streamlit.image(page.get_species_image())
    if streamlit.button(label='Open Wikipedia'):
        page.open()
elif engine=='World News (GDELT)':
    articles = get_gdelt(name)
    streamlit.write(articles)
elif engine=='Semantic Scholar':
    streamlit.text('Opening SemanticScholar in seperate tab.')
    val = name.replace(' ','%20')
    url = "https://www.semanticscholar.org/search?q={}&sort=relevance".format(val)
    open_page(url)


