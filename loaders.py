import streamlit
import wikipedia
import pandas
import numpy
import requests
import urllib
#from scholarly import scholarly
from wikidata.client import Client
from pygbif import species, occurrences, maps
import weakref
from pyvis import network as net
import sqlite3

client = Client() 
sci_name = client.get('P225')
im_prop = client.get('P18')

CORE_API = "https://core.ac.uk:443/api-v2"
API_KEY = "cJmoVEila3gB0zCIM2q1vpZnsKjr9XdG"

app_order = ['kingdom','phylum','class','order','family','genus','species']
palette = {'species':'#FB2056','genus':'#FC8F5B','family':'#FFD055','order':'#8DD58C','class':'#38C9B1','phylum':'#1798C3','kingdom':'#182573'}

def deep_get(_dict, prop, default=None):
    if prop in _dict:
        return _dict.get(prop, default)
    else:
        for key in _dict:
            if isinstance(_dict.get(key), dict):
                return deep_get(_dict.get(key), prop, default)  

docurl = "http://165.22.121.95/documents/search/"
def make_url(species):
    return f"{docurl}{species}"

@streamlit.cache()
def get_documents(search):
    try:
        res = requests.get(make_url(search))
        df = pandas.DataFrame(res.json()) #[['title','abstract', 'url','authors','publication_year']]
        return df 
    except:
        return pandas.DataFrame()

@streamlit.cache(hash_funcs={weakref.KeyedRef: hash})
def get_cannonical_name(search, lang='en'):
    if not search:
        return ''
    wikipedia.set_lang(lang)
    page = wikipedia.WikipediaPage(wikipedia.search(search, results=1, suggestion=True))
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageprops&titles={page.title}&format=json"
    result = requests.get(url).json()
    entity = client.get(deep_get(result,'wikibase_item'), load=True)  
    if sci_name in entity:
        return entity[sci_name]
    else:
        return ''

@streamlit.cache(hash_funcs={weakref.KeyedRef: hash}, allow_output_mutation=True)
def get_wiki(name, lang):
    wikipedia.set_lang(lang)
    try:
        page = wikipedia.WikipediaPage(wikipedia.search(name, results=1))
        url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageprops&titles={page.title}&format=json"
        result = requests.get(url).json()
        entity = client.get(deep_get(result,'wikibase_item'), load=True)
        image_url = '' if im_prop not in entity else entity[im_prop].image_url
        return page, image_url
    except:
        return None,None

@streamlit.cache
def search_core(query, page,lang, cnt = 10):
    try:
        params = {"page": page, "pageSize": cnt, "apiKey": API_KEY, "language.name":lang}
        core_query = urllib.parse.quote(query)
        search_url = "/".join((CORE_API, "articles", "search", core_query))
        response = requests.get(search_url, params).json()
        info = response['data']
        fields = {'title', 'authors'}
        pubs = [{f:inf.get(f) for f in fields} for inf in info]
        return pandas.DataFrame(pubs)
    except:
        return ''

@streamlit.cache
def get_backbone(search=''):
    if search and len(search)>2:
        backbone = species.name_backbone(name=search, kingdom='animals')
        return backbone
    else:
        return ''

@streamlit.cache
def get_backbone_graph(backbone, children):
    g=net.Network(height='400px', width='100%',heading='')
    last_node, node = '',''
    for o in app_order:
        if o in backbone:
            g.add_node(backbone[o], color=palette[o])
            node = backbone[o]                    
            if last_node and node:
                g.add_edge(node,last_node)
        last_node = node

    if last_node and len(children)>0:
        for index, row in children.iterrows():
            rank = row['rank'].lower()
            if rank in palette:
                g.add_node(row['canonicalName'], color=palette[rank])
            else:
                g.add_node(row['canonicalName'])
            g.add_edge(last_node,row['canonicalName'])        
    g.write_html('example.html')


@streamlit.cache
def get_images(search, limit=4, istaxon=True):
    if istaxon:
        res = occurrences.search(taxonKey=search,mediatype='stillimage',limit=limit)['results']
    else:
        res = occurrences.search(q=search,mediatype='stillimage',limit=limit)['results']
    images = [r['media'][0]['identifier'] for r in res]
    return images

@streamlit.cache
def get_coords(taxon, limit=100, istaxon=True):
    if istaxon:
        res = occurrences.search(taxonKey=taxon,hasCoordinate=True,limit=limit)
    else:
        res = occurrences.search(q=taxon,hasCoordinate=True,limit=limit)
    if res['count']>0:
        coords = [(float(res['decimalLongitude']), float(res['decimalLatitude'])) for res in res['results']]
        coords = pandas.DataFrame(numpy.stack(coords))
        coords.columns = ['lon','lat']
        return coords
    else:
        return pandas.DataFrame()    

@streamlit.cache
def get_children(backbone, limit=5, offset=0):
    children = species.name_usage(key=backbone['usageKey'], data='children', limit=limit,offset=offset)['results']
    children = pandas.DataFrame(children)
    if 'canonicalName' in children.columns:
        children = children[['canonicalName','rank']].dropna()
    else:
        children = []
    return children