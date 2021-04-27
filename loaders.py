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
from pyvis import network as net
import sqlite3
from matplotlib import cm
import matplotlib

client = Client() 
sci_name = client.get('P225')
im_prop = client.get('P18')

CORE_API = "https://core.ac.uk:443/api-v2"
API_KEY = "cJmoVEila3gB0zCIM2q1vpZnsKjr9XdG"

MIC_KEY = "c12b79e8d175478db89dea3d70dd2e56" #"7edb2076d56b40eba66f8d5f23e0385a"
MIC_API = "https://api.labs.cognitive.microsoft.com/academic/v1.0/interpret?query="
order = {'species':0,'genus':1,'family':2,'order':3,'phylum':4,'kingdom':5}

cmap = cm.get_cmap('Pastel1', 8)  
app_order = ['kingdom','phylum','class','order','family','genus','species', 'else']
palette = {o:matplotlib.colors.rgb2hex(cmap(i)) for i,o in enumerate(app_order)}


def deep_get(_dict, prop, default=None):
    if prop in _dict:
        return _dict.get(prop, default)
    else:
        for key in _dict:
            if isinstance(_dict.get(key), dict):
                return deep_get(_dict.get(key), prop, default)  

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


#@streamlit.cache
def get_graph_app(result, parent, children):
    g=net.Network(height='500px', width='50%',heading='')
    rnode =  result.iloc[0]['taxonRank']+':'+result.iloc[0]['canonicalName']
    g.add_node(rnode)

    if parent.shape[0]>0:
        res = parent.iloc[0]
        for i,rank in enumerate(app_order):
            if rank==res['taxonRank'] or rank=='species':
                node = res['taxonRank']+':'+res['canonicalName']
            else:
                node = rank+':'+res[rank] if res[rank] else 'None'
            g.add_node(node, color=palette[rank])
            if i>0:
                prev = res[app_order[i-1]] if res[app_order[i-1]] else 'None'
                prev = app_order[i-1]+':'+prev
                g.add_edge(prev, node)
            if rank==res['taxonRank'] or rank=='species':
                break
        g.add_edge(rnode, node)

    for i in range(children.shape[0]):
        cnode = children.iloc[i]['taxonRank']+':'+children.iloc[i]['canonicalName']
        if children.iloc[i]['taxonRank'] in palette:
            g.add_node(cnode, color=palette[children.iloc[i]['taxonRank']])
        else:
            g.add_node(cnode, color=palette['else'])
        g.add_edge(cnode, rnode)
    g.write_html('test.html')


@streamlit.cache(hash_funcs={sqlite3.Connection: id})
def suggest(query, lang, conn):
    df1 = pandas.read_sql(f"select taxonID,vernacularName from vernacular where language='{lang}' and vernacularName like '%{query}%' limit 1000", con=conn)
    sql = "select taxonID, canonicalName, taxonRank, kingdom, phylum, [class], [order], family, genus from taxon where taxonID in ("
    sql += ",".join([str(v) for v in df1['taxonID'].values])+")"
    df2 = pandas.read_sql(sql, con=conn)
    return df1.set_index('taxonID').join(df2.set_index('taxonID'), how='inner').reset_index()

@streamlit.cache(hash_funcs={sqlite3.Connection: id})
def search(query, conn):
    return pandas.read_sql(f"select taxonID, scientificName, canonicalName, genericName, taxonRank, kingdom, phylum, [class], [order], family, genus from taxon where canonicalName like '%{query}%' limit 1000", con=conn)

@streamlit.cache(hash_funcs={sqlite3.Connection: id})
def browse(query,conn):
    result = pandas.read_sql(f"select taxonID, parentNameUsageID, scientificName, canonicalName, genericName, taxonRank, kingdom, phylum, [class], [order], family, genus from taxon where taxonID={query} limit 1", con=conn)
    sql = f"""select taxonID, parentNameUsageID, scientificName, canonicalName, genericName, taxonRank, kingdom, phylum, [class], [order], family, genus 
                from taxon where parentNameUsageID={query} and canonicalName is not NULL limit 10000"""
    children = pandas.read_sql(sql, con=conn)
    parent_id = result.iloc[0]['parentNameUsageID']
    if parent_id is not None:
        parent = pandas.read_sql(f"select taxonID, parentNameUsageID, scientificName, canonicalName, genericName, taxonRank, kingdom, phylum, [class], [order], family, genus from taxon where taxonID={parent_id} limit 1", con=conn)
    else:
        parent = pandas.DataFrame()
    return result, parent, children

@streamlit.cache(hash_funcs={sqlite3.Connection: id})
def wrap(query, conn):
    return pandas.read_sql(query, con=conn)

@streamlit.cache
def get_images(taxon, limit=4):
    res = occurrences.search(taxonKey=taxon,mediatype='stillimage',limit=limit)['results']
    images = [r['media'][0]['identifier'] for r in res]
    return images

@streamlit.cache
def get_coords(taxon, limit=100):
    res = occurrences.search(taxonKey=taxon,hasCoordinate=True,limit=limit)
    if res['count']>0:
        coords = [(float(res['decimalLongitude']), float(res['decimalLatitude'])) for res in res['results']]
        coords = pandas.DataFrame(numpy.stack(coords))
        coords.columns = ['lon','lat']
        return coords
    else:
        return pandas.DataFrame()    
