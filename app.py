import streamlit
import loaders
import urllib

import userdata as db
import streamlit.report_thread as ReportThread
streamlit.set_page_config(page_title="Ceebios Explorer", page_icon='icon.png',layout="wide")
session_id = ReportThread.get_report_ctx().session_id

def open_page(url):    
    link = '[Open in Browser]({})'.format(url)
    streamlit.write(link)

connuser = db.get_connection()
conn = db.get_connection('gbif.db')
db.init_db(connuser)
username = streamlit.sidebar.text_input(label='User Name', value='anonymous')
with streamlit.sidebar.beta_expander('See my search history'):
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

with streamlit.beta_expander('Canonical Search', expanded=True):
    query = streamlit.text_input('Keywords',value="")
    if query:
        streamlit.dataframe(loaders.search(query, conn))

query = streamlit.text_input('Taxon',value="")

c1,c2 = streamlit.beta_columns((1,1))
with c1:
    if query:
        streamlit.write('Result')
        result, parent, children = loaders.browse(query, conn)
        streamlit.dataframe(result)  
        streamlit.write('Parent')
        streamlit.dataframe(parent)    
        streamlit.write('Children')
        streamlit.dataframe(children)          
with c2:
    if query:
        loaders.get_graph_app(result, parent, children)
        HtmlFile = open("test.html", 'r', encoding='utf-8')
        source_code = HtmlFile.read() 
        streamlit.components.v1.html(source_code, height = 550,width=1600)

if query:
    name = result.iloc[0]['canonicalName']
else:
    streamlit.stop()

cs = streamlit.beta_columns(6)
for c,im in zip(cs,loaders.get_images(query, 6)):
    with c:
        streamlit.image(im, output_format='jpeg')

streamlit.write('Selected: '+name)
db.add_userdata(connuser, username, name)

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

with streamlit.beta_expander(label='Academic Portal'):
    engine = streamlit.radio("Search Engine",('Microsoft Academic', 'Semantic Scholar','Google Scholar', 'CORE','BASE','Dimensions','CrossRef','Open Knowledge Map','Tree of Life','EOL','OneZoom')) #'World News (GDELT)')

    streamlit.subheader('Results')
    if engine=='CrossRef':
        url = "https://search.crossref.org/?q={}&from_ui=yes".format(name.replace(' ','+'))
        open_page(url)
    elif engine=='Tree of Life':
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
    elif engine=='BASE':
        url = "https://www.base-search.net/Search/Results?lookfor={}&name=&oaboost=1&newsearch=1&refid=dcbasen".format(name.replace(' ','+'))
        open_page(url)
    elif engine == 'Microsoft Academic':
        #pubs = loaders.get_microsoft(name,1)
        url = 'https://academic.microsoft.com/search?q={}&f=&orderBy=0&skip=0&take=10'.format(urllib.parse.quote(name))
        open_page(url)
    elif engine == 'Dimensions':
        url = "https://app.dimensions.ai/discover/publication?search_mode=content&search_text={}&search_type=kws&search_field=full_search".format(urllib.parse.quote(name))
        open_page(url)
    elif engine == 'Open Knowledge Map':
        streamlit.components.v1.iframe("https://openknowledgemaps.org/", height=800, scrolling=True)
    elif engine=='Google Scholar':
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
            #if streamlit.button(label='Open in Browser'):
            url = "https://core.ac.uk/search?q="+name.replace(' ','+')
            open_page(url)
        pubs = loaders.search_core(name,corepage,corelang)
        streamlit.table(pubs)
    elif engine=='World News (GDELT)':
        articles = loaders.get_gdelt(name)
        streamlit.write(articles)
    elif engine=='Semantic Scholar':
        val = name.replace(' ','%20')
        url = "https://www.semanticscholar.org/search?q={}&sort=relevance".format(val)
        open_page(url)



with streamlit.beta_expander('GBIF Taxonomy SQL Wrapper'):
    query = streamlit.text_input('SQL Query',value="select * from taxon where canonicalName like '%vespa ducalis%' limit 5")
    if query:
        streamlit.dataframe(loaders.wrap(query, conn))