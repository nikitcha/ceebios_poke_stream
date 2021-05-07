import streamlit
import loaders
import urllib
import os
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

connuser = db.get_connection()
conn = db.get_connection('gbif.db')
db.init_db(connuser)

with streamlit.sidebar:
    streamlit.write('Search for Species')
    react_search = autosuggest(key="suggest")

with streamlit.sidebar.beta_expander('See my search history'):
    username = streamlit.text_input(label='User Name', value='anonymous')
    if username=='admin':
        history = db.get_alldata(connuser)
    else:
        history = db.get_userdata(connuser,username)
    streamlit.write(history)


streamlit.image('https://ceebios.com/wp-content/uploads/2017/06/ceebios-logo-06-167x92.png')
streamlit.subheader('Open source project to help bio-mimicry research for Data Scientists and Engineers.')

with streamlit.beta_expander('Common Name Search'):
    lang = streamlit.radio('Language',['en','fr'])
    query = streamlit.text_input('Name',value="")
    if query:
        # Try local first
        canonical = loaders.suggest(query, lang, conn)        
        # Try wikipedia
        if canonical.shape[0]<1:
            canonical = loaders.get_cannonical_name(query, lang)
            streamlit.write('Canonical Name: '+canonical)
        else:
            streamlit.dataframe(canonical)

backbone, _ = loaders.get_backbone(react_search)
if not backbone:
    streamlit.stop()
db.add_userdata(connuser, username, react_search)

c1, c2 = streamlit.beta_columns((1,1))
children = []
with c2:
    nchild = streamlit.slider(label='Number of Children',min_value=0,max_value=20,value=5)
with c1:
    if streamlit.button('Get Children'):
        children = loaders.get_children(backbone, limit=nchild, offset=0)
        streamlit.dataframe(children)

loaders.get_backbone_graph(backbone, children)
HtmlFile = open("example.html", 'r', encoding='utf-8')
source_code = HtmlFile.read() 
streamlit.components.v1.html(source_code, height = 400, width = 1600)
        

with streamlit.beta_expander('Images'):
    cs = streamlit.beta_columns(6)
    for c,im in zip(cs,loaders.get_images(react_search, 6, False)):
        with c:
            streamlit.image(im, output_format='jpeg')


with streamlit.beta_expander(label='Articles', expanded=True):
    streamlit.write(loaders.get_documents(react_search))

streamlit.stop()
with streamlit.beta_expander(label='Smart Links'):
    url = "https://www.gbif.org/species/"+taxon
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
    data = loaders.get_coords(query, 300)
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

with streamlit.beta_expander('GBIF Taxonomy SQL Wrapper'):
    query = streamlit.text_input('SQL Query',value="select * from taxon where canonicalName like '%vespa ducalis%' limit 5")
    if query:
        streamlit.dataframe(loaders.wrap(query, conn))