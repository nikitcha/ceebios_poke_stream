import streamlit
import loaders
import urllib
import os
import pandas
import userdata as db
import streamlit.components.v1 as components
import streamlit.report_thread as ReportThread
streamlit.set_page_config(page_title="Ceebios Explorer", page_icon='icon.png',layout="wide")
session_id = ReportThread.get_report_ctx().session_id

# Define location of the packaged frontend build
parent_dir = os.path.dirname(os.path.abspath(__file__))

_autosuggest = components.declare_component(
    "autosuggest",
    path=os.path.join(parent_dir, "build_autosuggest")
)

# Edit arguments sent and result received from React component, so the initial input is converted to an array and returned value extracted from the component
def autosuggest(key=None):
    value = _autosuggest(key=key)
    return value

def open_page(url, label=''):    
    if not label:
        link = '[Open in Browser]({})'.format(url)
    else:
        link = '[{}]({})'.format(label, url)
    streamlit.write(link)

conn = db.get_connection()
db.init_db(conn)
db.init_session(conn, session_id)

with streamlit.sidebar:
    streamlit.write('Search for Species')
    react_search = autosuggest(key="suggest")

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
    lang = streamlit.radio('Language',['en','fr'])
    query = streamlit.text_input('Name',value="")
    if query:
        canonical = loaders.get_cannonical_name(query, lang)
        streamlit.write('Canonical Name: '+canonical)

backbone = loaders.get_backbone(react_search)
if not backbone or 'usageKey' not in backbone:
    streamlit.stop()
taxon = backbone['usageKey']
react_search = backbone['canonicalName']

last_search = db.get_searchdata(conn, session_id)
if last_search['search'] != react_search:   
    db.add_userdata(conn, username, react_search)
    db.update_search_data(conn, session_id, {'search':react_search, 'offset':0})

c1, c2 = streamlit.beta_columns((1,1))
children = []
with c2:
    nchild = streamlit.slider(label='Number of Children',min_value=0,max_value=20,value=5)
with c1:
    if streamlit.button('Get Children'):
        last_search = db.get_searchdata(conn, session_id)
        children = loaders.get_children(backbone, limit=nchild, offset=last_search['offset'])
        db.update_search_data(conn, session_id, {'offset':last_search['offset']+nchild})
        streamlit.dataframe(children)

loaders.get_backbone_graph(backbone, children)
HtmlFile = open("example.html", 'r', encoding='utf-8')
source_code = HtmlFile.read() 
streamlit.components.v1.html(source_code, height = 400)       

with streamlit.beta_expander('Images'):
    cs = streamlit.beta_columns(6)
    for c,im in zip(cs,loaders.get_images(taxon, 6, True)):
        with c:
            streamlit.image(im, output_format='jpeg')

with streamlit.beta_expander(label='Articles', expanded=True):
    docs = loaders.get_documents(react_search)
    for _, row in docs.iterrows():
        c1,c2,c3 = streamlit.beta_columns((2,4,1))
        with c1:
            streamlit.write(row['title'])
        with c2:
            streamlit.write(row['abstract'])
        with c3:
            streamlit.write(row['publication_year'])

with streamlit.beta_expander(label='Experimental: Related Species', expanded=False):
    df = []
    for _,row in docs.iterrows():
        df.append(pandas.DataFrame(row['dict_species'])['canonical_name','rank','gbif_id'])
    df = pandas.concat(df,axis=0)
    df = df.dropna().drop_duplicates()
    streamlit.dataframe(df)


name = react_search
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

if streamlit.checkbox(label='Wikipedia'):
    lang = 'en' #streamlit.radio("Wikipedia Language",('en','fr'))
    page, image = loaders.get_wiki(name, lang)
    if image:
        streamlit.image(image)
    if page:            
        streamlit.markdown(page.summary)
        open_page(page.url)
    else:
        streamlit.write('No Wikipedia page found')

if streamlit.checkbox(label='Other Resources'):
    engine = streamlit.radio("Engine",('CORE','Open Knowledge Map','Tree of Life','EOL','OneZoom')) #'World News (GDELT)')
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
    elif engine=='CORE':
        c1,c2,c3 = streamlit.beta_columns((1,1,1))
        with c1:
            corepage = streamlit.number_input(label='Page', min_value=1,value=1)
        with c2:
            corelang = streamlit.radio("CORE Language",('English','French'))
        with c3:
            #if streamlit.button(label='Open in Browser'):
            url = "https://core.ac.uk/search?q="+name.replace(' ','+')
            open_page(url)
        pubs = loaders.search_core(name,corepage,corelang)
        streamlit.table(pubs)
    elif engine=='World News (GDELT)':
        articles = loaders.get_gdelt(name)
        streamlit.write(articles)
