import numpy as np
import streamlit
import loaders
import urllib
import os
import session
import pandas
import userdata as db
import streamlit.components.v1 as components
import streamlit.report_thread as ReportThread
import re 
streamlit.set_page_config(page_title="Ceebios Explorer", page_icon='icon.png',layout="wide")

this_session = session.get(tree_graph=[], tree_selected=0, tree_offset={}, paper_offset=0, last_search='')

# Define location of the packaged frontend build
parent_dir = os.path.dirname(os.path.abspath(__file__))

_autosuggest = components.declare_component(
    "autosuggest",
    path=os.path.join(parent_dir, "build_autosuggest")
)

def autosuggest(key=None):
    value = _autosuggest(key=key)
    return value


_cytoscape = components.declare_component(
    "custom_dot",
    path=os.path.join(parent_dir, "build_cytoscape")
)

# Edit arguments sent and result received from React component, so the initial input is converted to an array and returned value extracted from the component
def cytoscape(elements,  key=None) -> str:
    component_value = _cytoscape(elements=elements,  key=key)
    return component_value


def open_page(url, label=''):    
    if url:
        if not label:
            link = '[Open in Browser]({})'.format(url)
        else:
            link = '[{}]({})'.format(label, url)
        streamlit.write(link)

conn = db.get_connection()
db.init_db(conn)
streamlit.markdown("""
                    <style>
                    .small-font {font-size:10px} 
                    [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
                        width: 400px;
                    }
                    [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
                        width: 400px;
                        margin-left: -400px;
                    }
                    </style>
                    """, unsafe_allow_html=True)

with streamlit.sidebar:
    streamlit.write('Search for Species')
    streamlit.markdown('<p class="small-font">Source: GBIF</p>', unsafe_allow_html=True)
    suggest = autosuggest(key="suggest")

with streamlit.sidebar.beta_expander('See my search history'):
    username = streamlit.text_input(label='User Name', value='anonymous')
    if username=='admin':
        history = db.get_alldata(conn)
    else:
        history = db.get_userdata(conn,username)
    streamlit.write(history)


streamlit.image('https://ceebios.com/wp-content/uploads/2017/06/ceebios-logo-06-167x92.png')
streamlit.subheader('Open source project to help bio-mimicry research for Data Scientists and Engineers.')

with streamlit.beta_expander('Common Name Search'):
    streamlit.markdown('<p class="small-font">Source: GBIF</p>', unsafe_allow_html=True)
    query = streamlit.text_input('Name',value="")
    if query:
        streamlit.write(loaders.get_canonical_name(query))

if suggest:
    backbone = loaders.get_backbone(suggest)
else:
    streamlit.stop()

taxon = backbone['usageKey']
name = backbone['canonicalName']

if this_session.last_search != suggest:   
    db.add_userdata(conn, username, suggest)
    this_session.tree_graph = loaders.get_cyto_backbone(backbone)
    this_session.tree_offset = {}
    this_session.tree_selected = 0
    this_session.last_search = suggest
    this_session.paper_offset = 0



with streamlit.form(key='graph'):
    c1, c2,c3 = streamlit.beta_columns((1,1,2))
    children = []
    with c3:
        nchild = streamlit.slider(label='Number of Children',min_value=0,max_value=50,value=10)
    with c1:
        if streamlit.form_submit_button('Get Children'):
            if this_session.tree_selected:
                children = loaders.get_children(backbone, this_session, limit=nchild)
                this_session.tree_graph = this_session.tree_graph+children
                if this_session.tree_selected in this_session.tree_offset:
                    this_session.tree_offset[this_session.tree_selected] += nchild
                else:
                    this_session.tree_offset.update({this_session.tree_selected:nchild})
            else:
                streamlit.warning('No Node Selected')
    with c2:
        if streamlit.form_submit_button('Reset'):
            this_session.tree_graph = loaders.get_cyto_backbone(backbone)
            this_session.tree_selected = 0 
            this_session.tree_offset = {}

out = cytoscape(this_session.tree_graph)
if out:
    selected, graph = out
    this_session.tree_graph = graph
    this_session.tree_selected = selected    
    taxon = selected
    name = [g['data']['id'] for g in this_session.tree_graph if (g['data'].get('label')==taxon)][0]
    streamlit.write('Selected: Taxon={}, Name={}'.format(taxon, name))

with streamlit.beta_expander('Images'):
    streamlit.markdown('<p class="small-font">Source: GBIF</p>', unsafe_allow_html=True)
    cs = streamlit.beta_columns(6)
    for c,im in zip(cs,loaders.get_images(taxon, 6, True)):
        with c:
            streamlit.image(im, output_format='jpeg')

with streamlit.beta_expander(label='Wikipedia'):
    streamlit.markdown('<p class="small-font">Source: Wikidata & Wikipedia</p>', unsafe_allow_html=True)
    try:
        res = loaders.get_wiki_info(taxon)
        if res:
            if res['label']:
                streamlit.subheader(res['label'].capitalize())
            if res['description']:
                streamlit.write(res['description'].capitalize())
            c1,c2 = streamlit.beta_columns(2)
            with c1:
                if res['image']:
                    streamlit.image(res['image'])
            with c2:
                if res['range']:
                    if 'svg' in res['range']:
                        #streamlit.components.v1.iframe(res['range'])
                        streamlit.components.v1.html(f"""<img src="{res['range']}" alt="" width="100%" height="100%">""", height = 400)
                    else:
                        streamlit.image(res['range'])    
            if res['page']                  :
                streamlit.markdown(res['page'].summary)
            c1,c2 = streamlit.beta_columns(2)
            with c1:
                if res['wikipedia']:
                    open_page(url=res['wikipedia'], label='Wikipedia')
            with c2:
                if res['wikidata']:
                    open_page(url=res['wikidata'], label='Wikidata')
    except:
        page, image_url = loaders.get_wiki(name)
        if image_url:
            streamlit.image(image_url)
        if page:
            streamlit.write(page.summary)


with streamlit.beta_expander(label='Articles', expanded=False):
    streamlit.markdown('<p class="small-font">Source: Semantic Scholar, Wikidata, GBIF</p>', unsafe_allow_html=True)
    if False:
        docs = loaders.get_documents(name)
        if loaders.draw_doc_graph(docs):
            HtmlFile = open("graph.html", 'r', encoding='utf-8')
            source_code = HtmlFile.read() 
            streamlit.components.v1.html(source_code, height = 800)       
        cs = streamlit.beta_columns((1,2,4,1,1,1))
        labels = ['id','Title','Abstract','Field','Year', 'URL']
        for c,l in zip(cs,labels):
            with c:
                streamlit.write(l)
        for i, row in docs.iterrows():
            c1,c2,c3,c4,c5,c6 = streamlit.beta_columns((1,2,4,1,1,1))                    
            with c1:
                streamlit.write(i)
            with c2:
                streamlit.write(row['title'])
            with c3:
                streamlit.write(row['abstract'])
            with c4:
                streamlit.write(','.join(row['scientific_fields']))
            with c5:
                streamlit.write(row['publication_year'])
            with c6:
                streamlit.write('[Link]({})'.format(row['url']))
    else:
        with streamlit.form(key='graph paper'):
            c1, c2, c3 = streamlit.beta_columns((1,1,2))
            with c3:
                npapers = streamlit.slider(label='Number of Papers',min_value=0,max_value=50,value=10)
            with c2:
                if streamlit.form_submit_button('Reset'):
                    this_session.paper_offset = 0
            with c1:
                if streamlit.form_submit_button('Next'):
                    this_session.paper_offset = this_session.paper_offset + npapers

        paper_graph, papers = loaders.get_neo_papers(taxon, name, limit=npapers, offset=this_session.paper_offset)
        out_paper = cytoscape(paper_graph)
        if out_paper:
            selected = out_paper[0]
            paper = [p for p in papers if p['id']==selected]
            if paper:
                streamlit.write(paper[0])
            else:
                streamlit.write(papers)
        else:
            streamlit.write(papers)



with streamlit.beta_expander(label='Smart Links'):
    url = "https://www.gbif.org/species/"+str(taxon)
    open_page(url, 'GBIF')

    url = "https://search.crossref.org/?q={}&from_ui=yes".format(name.replace(' ','+'))
    open_page(url, 'CrossRef')

    url = 'https://academic.microsoft.com/search?q={}&f=&orderBy=0&skip=0&take=10'.format(urllib.parse.quote(name))
    open_page(url, 'Microsoft Academic')

    val = name.replace(' ','%20')
    url = "https://www.semanticscholar.org/search?q={}&sort=relevance".format(val)
    open_page(url, 'Semantic Scholar')

    val = name.replace(' ','%20')
    url = "https://www.lens.org/lens/search/scholar/list?q={}".format(val)
    open_page(url, 'Lens')

    val = name.replace(' ','+')
    url = "https://scholar.google.com/scholar?as_vis=0&q={}&hl=en&as_sdt=0,5".format(val)
    open_page(url, 'Google Scholar')

    url = "https://www.base-search.net/Search/Results?lookfor={}&name=&oaboost=1&newsearch=1&refid=dcbasen".format(name.replace(' ','+'))
    open_page(url, 'BASE')

    url = "https://app.dimensions.ai/discover/publication?search_mode=content&search_text={}&search_type=kws&search_field=full_search".format(urllib.parse.quote(name))
    open_page(url, 'Dimensions')

if streamlit.checkbox('Maps'):
    data = loaders.get_coords(taxon, 300)
    streamlit.map(data)   

if streamlit.checkbox(label='Other Resources'):
    engine = streamlit.radio("Engine",('Open Knowledge Map','Tree of Life','EOL','OneZoom')) #'World News (GDELT)')
    if engine=='Tree of Life':
        url = "https://tree.opentreeoflife.org/"
        open_page(url)
        streamlit.components.v1.iframe(url, height=800, scrolling=True)
    elif engine=='EOL':
        url = "https://eol.org/search?q={}".format(name.replace(' ','+'))
        open_page(url)
        streamlit.components.v1.iframe(url, height=800, scrolling=True)
    elif engine=='OneZoom':
        url = "https://www.onezoom.org/AT/@biota=93302?img=best_any&anim=jump#x775,y1113,w1.4450"
        open_page(url)        
        streamlit.components.v1.iframe(url, height=800, scrolling=True)
    elif engine == 'Open Knowledge Map':
        streamlit.components.v1.iframe("https://openknowledgemaps.org/", height=800, scrolling=True)