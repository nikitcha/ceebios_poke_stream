import streamlit
import loaders
import urllib
import userdata as db

streamlit.set_page_config(page_title="Ceebios Explorer", page_icon='icon.png',layout="wide")
def open_page(url):    
    link = '[Open in Browser]({})'.format(url)
    streamlit.write(link)

def main():
    username = streamlit.sidebar.text_input(label='User Name', value='anonymous')

    conn = db.get_connection()
    db.init_db(conn)

    streamlit.image('https://ceebios.com/wp-content/uploads/2017/06/ceebios-logo-06-167x92.png')
    streamlit.subheader('Open source project to help bio-mimicry research for Data Scientists and Engineers.')

    streamlit.subheader('Search')
    common = streamlit.text_input(label='Filter Species by Common Name',value='')
    entity = loaders.get_cannonical_name(common)
    canonical = streamlit.text_input(label='Filter Species by Canonical Name',value=entity)
    species_list = loaders.get_species(canonical)
    name = streamlit.multiselect(label='Select Species', options=species_list)

    with streamlit.beta_expander('See my search history'):
        if username=='admin':
            history = db.get_alldata(conn)
        else:
            history = db.get_userdata(conn,username)
        streamlit.write(history)

    if len(name)>1:
        streamlit.text('More than one species is selected!')
        streamlit.stop()
    if len(name)==0 or not name[0]:
        streamlit.text('No species is selected!')
        streamlit.stop()
    name = name[0]
    streamlit.write('Selected: '+name)

    db.add_userdata(conn, username, name)

    with streamlit.beta_expander(label='Wikipedia'):
        lang = 'en' #streamlit.radio("Wikipedia Language",('en','fr'))
        page, image = loaders.get_wiki(name, lang)
        if image:
            streamlit.image(image)
        if page:            
            streamlit.markdown(page.summary)
            open_page(page.url)
        else:
            streamlit.write('No Wikipedia page found')

    engine = streamlit.radio("Search Engine",('GBIF','CORE','CrossRef','Open Knowledge Map','Tree of Life','EOL','OneZoom','BASE','Google Scholar', 'Semantic Scholar', 'Microsoft Academic','Dimensions')) #'World News (GDELT)')

    streamlit.subheader('Results')
    if engine=='GBIF':
        api = streamlit.radio("GBIF",('Species','Maps'))
        data = loaders.get_gbif(api, name)
        if api=='Species':
            streamlit.write(data)
        elif api=='Maps':
            streamlit.map(data)
        else:
            streamlit.write(data)
    elif engine=='CrossRef':
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

if __name__=='__main__':
    main()