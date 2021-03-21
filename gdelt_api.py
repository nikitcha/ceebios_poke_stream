import collections.abc

config =    {'query':
                {
                'keywords':{
                    'in':[],
                    'out':[],
                    'or':[]
                },
                'domain':{
                    'in':[],
                    'out':[]
                },
                'domainis':{
                    'in':[],
                    'out':[]
                },
                'imagefacetone':[],
                'imagenumfaces':[],
                'imageocrmeta':[],
                'imagetag':[],  #http://data.gdeltproject.org/api/v2/guides/LOOKUP-IMAGETAGS.TXT
                'imagewebcount':[],
                'imagewebtag':[],  #http://data.gdeltproject.org/api/v2/guides/LOOKUP-IMAGEWEBTAGS.TXT
                'near':[],  # near20:"trump putin"
                'repeat':[],  # repeat3:"trump"
                'sourcecountry':{
                    'in':[], #http://data.gdeltproject.org/api/v2/guides/LOOKUP-COUNTRIES.TXT
                    'out':[]
                },
                'sourcelang':{
                    'in':[], #http://data.gdeltproject.org/api/v2/guides/LOOKUP-LANGUAGES.TXT
                    'out':[]
                },
                'theme':{
                    'in':[], #http://data.gdeltproject.org/api/v2/guides/LOOKUP-GKGTHEMES.TXT
                    'out':[]
                },
                'tone':[],
                'toneabs':[]  
                },
            'mode': [],  # 'artlist','artgallery','imagecollage','imagecollageinfo','imagegallery','imagecollageshare','timelinevol','timelinevolraw','timelinevolinfo','timelinetone','timelinelang','timelinesourcecountry','tonechart','wordcloudimagetags','wordcloudimagewebtags'
            'format':[],  # 'html','csv','rss','rssarchive','json','jsonp','jsonfeed'
            'timespan':[], # 1m, 1w, 1d, 1h, 1min
            'startdatetime':[],
            'enddatetime':[],
            'maxrecords':[],
            'timelinesmooth':[],
            'trans':[], #googtrans
            'sort':[],
            'timezoom':[],
            }

def safe_update(old,new):
    d = old.copy()
    for k,v in new.items():
        if isinstance(v,collections.abc.Mapping):
            d[k] = safe_update(d.get(k,{}),v)
        else:
            d[k] = v
    return d


def get_url(subconf={'query':{
                        'keywords':{
                            'in':['trump', 'biden', 'election'],
                            'or':['refuse','civil','war','senate'],
                            'out':[]},
                        'sourcelang':{
                            'in':['eng']}
                    },
                    'maxrecords':'50',
                    'timespan':'1d'
                    }):
    thisconf = safe_update(config,subconf)
    url = 'https://api.gdeltproject.org/api/v2/doc/doc?'
    for k,v in thisconf.items():
        if len(v)>0:
            suburl = '&'+k+'='
            if isinstance(v,collections.abc.Mapping):
                for qk,qv in v.items():
                    if len(qv)>0:
                        if isinstance(qv,collections.abc.Mapping):
                            if qk=='keywords':
                                if len(qv['in'])>0: suburl += '%20AND%20'.join(qv['in'])
                                if len(qv['out'])>0: suburl += '%20AND%20'+'%20AND%20'.join(['-'+s for s in qv['out']])
                                if len(qv['or'])>0: suburl += '%20AND%20('+'%20OR%20'.join(qv['or'])+')'
                            else:
                                if len(qv['in'])==1: 
                                    suburl += '%20'+qk+':'+qv['in'][0]
                                elif len(qv['in'])>1:
                                    suburl += '%20'+'('+'%20OR%20'.join([qk+':'+s for s in qv['in']])+')'
                                if len(qv['out'])==1: 
                                    suburl += '%20-'+qk+':'+qv['out'][0]
                                elif len(qv['out'])>1:
                                    suburl += '%20'+'%20AND%20'.join(['-'+qk+':'+s for s in qv['out']])
                        else:
                            suburl += '%20'+qk+':'+qv
            else:
                suburl += v
        else:
            suburl = ''
        url += suburl
    return url

def get_keywrods_url(kwrds, request = {
        'query':{
            'sourcelang':{'in':['french','english']}
         },
        'format':'json',
        'maxrecords':'50',
        'timespan':'3months'
        }):
        request = safe_update(request,{'query':{'keywords':{'in':kwrds}}})
        return get_url(request)    

