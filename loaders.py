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
import neo4j_credentials as nc
graph = Graph("bolt://localhost:7687", auth=(nc.user, nc.password))


client = Client() 
sci_name = client.get('P225')
im_prop = client.get('P18')
vernacular = pandas.read_csv('vernacular_en.csv')
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
def get_backbone(search=''):
    if search and len(search)>2:
        backbone = species.name_backbone(name=search, kingdom='animals')
        return backbone
    else:
        return ''

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

def draw_doc_graph(docs):
    if len(docs)>0:
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
        return True
    else:
        return False

def get_cyto_backbone(backbone):
    nodes,edges = [],[]
    last_node = ''
    for o in app_order:
        if o in backbone:
            name = backbone[o].lower().capitalize()
            nodes += [{'data': { 'id': name, 'label': backbone[o.lower()+'Key'], 'rank':o.upper() }}]
            if last_node:
                edges += [{'data': { 'source': name, 'target': last_node}}]
            last_node = name
    return nodes+edges

def get_children(backbone, this_session, limit):
    if this_session.tree_selected in this_session.tree_offset:
        offset = this_session.tree_offset[this_session.tree_selected]
    else:
        offset = 0
    children = species.name_usage(key=this_session.tree_selected, data='children', limit=limit,offset=offset)['results']
    children = pandas.DataFrame(children)
    if 'canonicalName' in children.columns:
        children = children[['canonicalName','rank','taxonID']].dropna()
    nodes,edges = [],[]
    base_name = [g['data']['id'] for g in this_session.tree_graph if (g['data'].get('label')==this_session.tree_selected)][0]
    for _,row in children.iterrows():
        taxon = int(row['taxonID'].replace('gbif:',''))
        name = row['canonicalName'].lower().capitalize()
        nodes += [{'data': { 'id': name, 'label': taxon, 'rank':row['rank']}}]
        edges += [{'data': { 'source': name, 'target': base_name}}]
    return nodes+edges

def get_neo_papers(taxon, limit=20, offset=0):
    query = """
    match (t:Taxon {{id:{}}})<-[:MENTIONS]-(p:Paper)
    return t,p
    skip {}
    limit {};
    """.format(taxon, offset, limit)

    paper_q = lambda x: """
    match (:Paper {{id:'{}'}})-[:MENTIONS]->(t)
    return t
    """.format(x)

    nodes, edges, ctr = [],[], 0
    results = graph.run(query).data()
    paper_dict = {}
    papers = []
    for res in results:
        nodes += [{'data': { 'id': res['t']['name'], 'label': taxon, 'rank':res['t']['rank'].upper()}}]
        nodes += [{'data': { 'id': 'Paper '+str(ctr), 'label': res['p']['id'], 'rank':'PAPER'}}]
        edges += [{'data': { 'source': res['t']['name'], 'target': 'Paper '+str(ctr)}}]
        paper_dict.update({res['p']['id']:'Paper '+str(ctr)})
        ctr += 1
        papers.append(res['p'])
        mentions = graph.run(paper_q(res['p']['id'])).data()
        for men in mentions:
            if 'rank' in men['t']:
                nodes += [{'data': { 'id': men['t']['name'], 'label': men['t']['id'], 'rank':men['t']['rank'].upper()}}]  
            else:
                nodes += [{'data': { 'id': men['t']['name'], 'label': men['t']['name'], 'rank':'FUNCTION'}}]  
            edges += [{'data': { 'source': men['t']['name'], 'target': paper_dict[res['p']['id']]}}]
    return nodes+edges, papers