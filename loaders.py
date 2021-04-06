import streamlit
import wikipedia
import pandas
import numpy
import requests
import urllib
#from scholarly import scholarly
from wikidata.client import Client
import gdelt_api
from pygbif import species, occurrences, maps
import weakref
import crossref
from pyvis import network as net

client = Client() 
sci_name = client.get('P225')
im_prop = client.get('P18')

CORE_API = "https://core.ac.uk:443/api-v2"
API_KEY = "cJmoVEila3gB0zCIM2q1vpZnsKjr9XdG"

MIC_KEY = "c12b79e8d175478db89dea3d70dd2e56" #"7edb2076d56b40eba66f8d5f23e0385a"
MIC_API = "https://api.labs.cognitive.microsoft.com/academic/v1.0/interpret?query="
order = {'species':0,'genus':1,'family':2,'order':3,'phylum':4,'kingdom':5}

def deep_get(_dict, prop, default=None):
    if prop in _dict:
        return _dict.get(prop, default)
    else:
        for key in _dict:
            if isinstance(_dict.get(key), dict):
                return deep_get(_dict.get(key), prop, default)  

@streamlit.cache(hash_funcs={weakref.KeyedRef: hash})
def get_cannonical_name(search):
    if not search:
        return ''
    page = wikipedia.WikipediaPage(wikipedia.search(search, results=1))
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageprops&titles={page.title}&format=json"
    result = requests.get(url).json()
    entity = client.get(deep_get(result,'wikibase_item'), load=True)  
    if sci_name in entity:
        return entity[sci_name]
    else:
        return ''

@streamlit.cache
def auto_suggest(search):
    r = requests.get(f"https://api.gbif.org/v1/species/suggest?q={search}")
    results = r.json()
    return [r['canonicalName'] for r in results]

@streamlit.cache
def get_species(search):
    suggests = species.name_suggest(search)
    name = [s.get('canonicalName') for s in suggests]
    name = set(name)
    return [n for n in name]

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


def search_google(search_query, cnt = 10):
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
def get_microsoft(query, page, cnt=10):
    params = {"subscription-key": MIC_KEY, "offset": (page-1)*cnt, "count": cnt}
    core_query = urllib.parse.quote(query)
    search_url = "".join((MIC_API, core_query))
    response = requests.get(search_url, params).json()


#@streamlit.cache
#def get_google_queries(name):
#    query = scholarly.search_pubs(name)
#    pubs = search_google(query)
#    return query, pubs

@streamlit.cache
def get_backbone(search):
    backbone = species.name_backbone(name=search, kingdom='animals')
    backbone_levels = [o for o in order.keys() if o in backbone]
    return backbone, backbone_levels

@streamlit.cache
def get_subnames(backbone, level):
    try:
        subspecies = species.name_usage(key=backbone[level+'Key'], data='children', limit=1000)['results']
        subnames = [s['canonicalName'] for s in subspecies if 'canonicalName' in s]
        if level=='species':
            level_down = level
        else:
            level_int = order[level]
            level_down = [o for i,o in enumerate(order.keys()) if (o in subspecies[0]) and (i<level_int)][-1]
    except:
        subnames = []
        level_down = level
    return subnames, level_down

@streamlit.cache
def get_graph(backbone_order, backbone, level, subnames):
    g=net.Network(height='500px', width='50%',heading='')
    level_int = [i for i,o in enumerate(backbone_order) if o==level][0]
    thisorder = backbone_order[level_int:]
    for o in thisorder:
        g.add_node(backbone[o])

    for i,o in enumerate(thisorder[:-1]):
        g.add_edge(backbone[o],backbone[thisorder[i+1]])

    for sub in subnames:
        g.add_node(sub)
        g.add_edge(backbone[thisorder[0]],sub)
    g.write_html('example.html')


@streamlit.cache
def get_gbif(api, name):
    info = species.name_suggest(q=name)[0]
    if api=='Species':
        fields = ['kingdom','phylum','order','family', 'genus', 'species', 'scientificName','canonicalName']
        return {k:info.get(k) for k in fields}
    if api=='Maps':
        ans = occurrences.search(taxonKey=info['speciesKey'], hasCoordinate=True, limit=300)
        if ans['count']>0:
            coords = [(float(res['decimalLongitude']), float(res['decimalLatitude'])) for res in ans['results']]
            coords = pandas.DataFrame(numpy.stack(coords))
            coords.columns = ['lon','lat']
            return coords
        else:
            return pandas.DataFrame()    
        #ans = maps.map(taxonKey=info['speciesKey'])
        #return ans.path



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