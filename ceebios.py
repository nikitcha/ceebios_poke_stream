import streamlit
import loaders
import urllib
import userdata as db
streamlit.set_page_config(page_title="Ceebios Explorer", page_icon='icon.png',layout="wide")

app_state = streamlit.experimental_get_query_params() 
def rerun():
    raise streamlit.script_runner.RerunException(streamlit.script_request_queue.RerunData(None))

def open_page(url):    
    link = '[Open in Browser]({})'.format(url)
    streamlit.write(link)

conn = db.get_connection()
db.init_db(conn)

username = streamlit.sidebar.text_input(label='User Name', value='anonymous')
with streamlit.sidebar.beta_expander('See my search history'):
    if username=='admin':
        history = db.get_alldata(conn)
    else:
        history = db.get_userdata(conn,username)
    streamlit.write(history)


streamlit.image('https://ceebios.com/wp-content/uploads/2017/06/ceebios-logo-06-167x92.png')
streamlit.subheader('Open source project to help bio-mimicry research for Data Scientists and Engineers.')

c1,c2 = streamlit.beta_columns((1,1))
with c1:
    streamlit.subheader('Search')   
    common = streamlit.text_input(label='Filter Species by Common Name',value='')
    entity = loaders.get_cannonical_name(common)
    canonical = streamlit.text_input(label='Filter Species by Canonical Name',value=entity)
    species_list = loaders.get_species(canonical)
    #species_list = loaders.auto_suggest(canonical)
    name = streamlit.multiselect(label='Select Species', options=species_list)
    if len(name)>0:
        if len(name)>1:
            streamlit.write('More than one species selected. Considreing only '+name[0])
        name = name[0]
        streamlit.write(name)
        data = loaders.get_gbif('Species', name)

        streamlit.write(data)
        if (name not in app_state) or (name!=app_state['name'][0]) or ('search' not in app_state):
            streamlit.experimental_set_query_params(search=name, level='species', name=name)
    else:
        #streamlit.experimental_set_query_params(search='', level='', name='')
        streamlit.stop()
with c2:
    streamlit.subheader('Browse')   
    app_state = streamlit.experimental_get_query_params() 
    _search = app_state['search'][0] 
    _level = app_state['level'][0]
    backbone, backbone_order = loaders.get_backbone(_search)

    level_int = [i for i,o in enumerate(backbone_order) if o==_level]
    level = streamlit.selectbox(label='Level', options=backbone_order,index=0 if len(level_int)==0 else level_int[0])

    subnames, level_down = loaders.get_subnames(backbone, level)
    #streamlit.experimental_set_query_params(search=_search, level=level, name=name)
    search = streamlit.multiselect(label='Level Down',options=subnames)
    #if search:
    #    streamlit.experimental_set_query_params(search=search[0], level=level_down, name=name)
    #if streamlit.button('Plot Tree'):
    #    app_state = streamlit.experimental_get_query_params() 
    #    loaders.get_graph(backbone_order, backbone, app_state['level'][0], subnames)
    #    HtmlFile = open("example.html", 'r', encoding='utf-8')
    #    source_code = HtmlFile.read() 
    #    streamlit.components.v1.html(source_code, height = 550,width=1600)


streamlit.write('Selected: '+name)

db.add_userdata(conn, username, name)

if streamlit.checkbox('Maps'):
    data = loaders.get_gbif('Maps', name)
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
    engine = streamlit.radio("Search Engine",('CrossRef','CORE','Open Knowledge Map','Tree of Life','EOL','OneZoom','BASE','Google Scholar', 'Semantic Scholar', 'Microsoft Academic','Dimensions')) #'World News (GDELT)')

    streamlit.subheader('Results')
    if engine=='CrossRef':
        url = "https://search.crossref.org/?q={}&from_ui=yes".format(name.replace(' ','+'))
        streamlit.write('API: To Do')
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
        streamlit.write("API: To Do. Need to whitelist IPs")
        url = "https://www.base-search.net/Search/Results?lookfor={}&name=&oaboost=1&newsearch=1&refid=dcbasen".format(name.replace(' ','+'))
        open_page(url)
    elif engine == 'Microsoft Academic':
        #pubs = loaders.get_microsoft(name,1)
        streamlit.write('API: To Do')
        url = 'https://academic.microsoft.com/search?q={}&f=&orderBy=0&skip=0&take=10'.format(urllib.parse.quote(name))
        open_page(url)
    elif engine == 'Dimensions':
        streamlit.write('API: Maybe - not free.')
        url = "https://app.dimensions.ai/discover/publication?search_mode=content&search_text={}&search_type=kws&search_field=full_search".format(urllib.parse.quote(name))
        open_page(url)
    elif engine == 'Open Knowledge Map':
        streamlit.components.v1.iframe("https://openknowledgemaps.org/", height=800, scrolling=True)
    elif engine=='Google Scholar':
        streamlit.text('Open Google Scholar in a separate tab.')
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
        streamlit.text('Open Semantic Scholar in seperate tab.')
        val = name.replace(' ','%20')
        url = "https://www.semanticscholar.org/search?q={}&sort=relevance".format(val)
        open_page(url)

