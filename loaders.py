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
from qwikidata.sparql import return_sparql_query_results
import urllib
from py2neo import Graph


client = Client() 
sci_name = client.get('P225')
im_prop = client.get('P18')
vernacular = pandas.read_csv('vernacular_en.csv')

CORE_API = "https://core.ac.uk:443/apnamei-v2"
API_KEY = "cJmoVEila3gB0zCIM2q1vpZnsKjr9XdG"
db_params = {
    "uri":"localhost:7474",
    "user":"neo4j",
    "password":"Pokedex"
}
#graph = Graph(db_params['uri'], user=db_params['user'], password=db_params['password'])

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

@streamlit.cache()
def get_canonical_name(search):
    res = vernacular[vernacular['vernacularName'].str.contains(search)]
    return {v:c for v,c in zip(res['vernacularName'],res['canonicalName'])}

def safe_get(dic,fs):
    if len(fs)==0:
        return dic
    if fs[0] in dic:
        return safe_get(dic[fs[0]], fs[1:])
    else:
        return None

def get_wiki_info(taxon):
    query = """SELECT ?item ?itemLabel ?itemDescription ?article ?image ?range
    WHERE 
    {
    ?item wdt:P846 "$gbif$"
    optional {?item wdt:P18 ?image.}
    optional {?item wdt:P181 ?range.}
    OPTIONAL {
        ?article schema:about ?item ;
        schema:isPartOf <https://en.wikipedia.org/> ; 
        schema:name ?sitelink .
    }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }""".replace('$gbif$',str(taxon))
    res = return_sparql_query_results(query)['results']['bindings']
    out = {}
    if len(res)>0:
        out['image'] = safe_get(res[0], ['image','value'])
        out['wikipedia'] = safe_get(res[0], ['article','value'])
        out['wikidata'] = safe_get(res[0], ['item','value'])
        out['range'] = safe_get(res[0], ['range','value'])
        out['description'] = safe_get(res[0], ['itemDescription','value'])
        out['label'] = safe_get(res[0], ['itemLabel','value'])
        if out['wikipedia']:
            url = urllib.parse.unquote(out['wikipedia'])
            out['page'] = wikipedia.WikipediaPage(url.split('/')[-1])
        else:
            out['page'] = ''
    return out


@streamlit.cache(hash_funcs={weakref.KeyedRef: hash}, allow_output_mutation=True)
def get_wiki(name):
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

#@streamlit.cache
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

#@streamlit.cache(hash_funcs={Graph: id})
def get_papers(gbif):
    query = """
    match (:Taxon {{taxonid:{}}})<-[:MENTIONS]-(p:Paper) return p
    """.format(gbif)
    res = graph.query(query)
    return res

#@streamlit.cache(hash_funcs={Graph: id})
def get_mentions(paperid):
    query = """
    match (p:Paper {{id:'{}'}})-[:MENTIONS]->(t:Taxon) return t
    """.format(paperid)
    res = graph.query(query)
    return res

def draw_knowledge_graph(backbone, maxnum = 1000, shift=0):
    gbif = backbone['usageKey']
    name = backbone['canonicalName']
    rank = backbone['rank'].lower()
    if rank not in palette:
        rank = 'species'        
    g=net.Network(height='800px', width='100%',heading='')
    name = name.lower()
    g.add_node(name, color=palette[rank], size=5)
    tnodes = [name]
    papers = {'id':[], 'title':[],'abstract':[],'year':[],'s2url':[],'url':[],'field':[]}
    for i,paper in enumerate(get_papers(gbif)):
        for k in ['title','abstract','year','s2url','url','field']:
            papers[k] += [paper['p'][k]]
        papers['id'] += [i]
        pname = 'Paper {}'.format(str(i))
        g.add_node(pname, size=5)
        g.add_edge(name, pname)
        for j,taxon in enumerate(get_mentions(paper['p']['id'])):
            tname = taxon['t']['name'].lower()
            trank = taxon['t']['rank'].lower()
            if trank not in palette:
                trank = 'species' 
            if tname not in tnodes:
                g.add_node(tname, color=palette[trank], size=5)
                tnodes += [tname]
            g.add_edge(tname, pname)
    g.write_html('papers.html')
    return pandas.DataFrame(papers).iloc[shift:shift+maxnum]

def draw_doc_graph(docs):
    species = docs[['dict_species']]
    g=net.Network(height='800px', width='100%',heading='')

    for i,row in species.iterrows():
        g.add_node('paper '+str(i), size=5)
        names = []
        for gbif in row[0]:
            names.append(gbif['canonical_name'])
            rank = gbif['rank']
            if rank not in palette:
                rank = 'species'        
            g.add_node(names[-1], color=palette[rank], size=5)
            g.add_edge(names[-1], 'paper '+str(i))        
    g.write_html('graph.html')
