# -*- coding: utf-8 -*-
# fanart.tv artist artwork scraper

import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import os, sys, traceback, re
import urllib
from traceback import print_exc
from urllib import quote_plus, unquote_plus

if sys.version_info < (2, 7):
    import json as simplejson
else:
    import simplejson
    
__language__        = sys.modules[ "__main__" ].__language__
__scriptname__      = sys.modules[ "__main__" ].__scriptname__
__scriptID__        = sys.modules[ "__main__" ].__scriptID__
__author__          = sys.modules[ "__main__" ].__author__
__credits__         = sys.modules[ "__main__" ].__credits__
__credits2__        = sys.modules[ "__main__" ].__credits2__
__version__         = sys.modules[ "__main__" ].__version__
__addon__           = sys.modules[ "__main__" ].__addon__
addon_db            = sys.modules[ "__main__" ].addon_db
addon_work_folder   = sys.modules[ "__main__" ].addon_work_folder
BASE_RESOURCE_PATH  = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
api_key             = sys.modules[ "__main__" ].api_key
enable_all_artists  = sys.modules[ "__main__" ].enable_all_artists

#sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from utils import get_html_source, unescape, log, dialog_msg
from musicbrainz_utils import get_musicbrainz_album, get_musicbrainz_artist_id, update_musicbrainzid
from json_utils import retrieve_json_dict

music_url = "http://api.fanart.tv/webservice/artist/%s/%s/xml/%s/2/2"
single_release_group = "http://api.fanart.tv/webservice/album/%s/%s/xml/%s/2/2"
artist_url = "http://api.fanart.tv/webservice/has-art/%s/"
music_url_json = "http://api.fanart.tv/webservice/artist/%s/%s/json/%s/2/2"
single_release_group_json = "http://api.fanart.tv/webservice/album/%s/%s/json/%s/2/2"
lookup_id = False

def remote_cdart_list( artist_menu ):
    log( "Finding remote cdARTs", xbmc.LOGDEBUG )
    cdart_url = []
    try:
        art = retrieve_fanarttv_json( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 2:
            album_artwork = art[5]["artwork"]
            if album_artwork:
                for artwork in album_artwork:
                    #print artwork
                    for cdart in artwork["cdart"]:
                        #print cdart
                        album = {}
                        album["artistl_id"] = artist_menu["local_id"]
                        album["artistd_id"] = artist_menu["musicbrainz_artistid"]
                        try:
                            album["local_name"] = album["artist"] = artist_menu["name"]
                        except KeyError:
                            album["local_name"] = album["artist"] = artist_menu["artist"]
                        album["musicbrainz_albumid"] = artwork["musicbrainz_albumid"]
                        album["disc"] = cdart["disc"]
                        album["size"] = cdart["size"]
                        album["picture"] = cdart["cdart"]
                        album["thumb_art"] = cdart["cdart"]
                        cdart_url.append(album)
                    #log( "cdart_url: %s " % cdart_url, xbmc.LOGDEBUG )
    except:
        print_exc()
    return cdart_url

def remote_coverart_list( artist_menu ):
    log( "Finding remote Cover ARTs", xbmc.LOGDEBUG )
    coverart_url = []
    try:
        art = retrieve_fanarttv_json( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 2:
            album_artwork = art[5]["artwork"]
            if album_artwork:
                for artwork in album_artwork:
                    if artwork["cover"]:
                        album = {}
                        album["artistl_id"] = artist_menu["local_id"]
                        album["artistd_id"] = artist_menu["distant_id"]
                        album["local_name"] = album["artist"] = artist_menu["name"]
                        album["musicbrainz_albumid"] = artwork["musicbrainz_albumid"]
                        album["size"] = 1000
                        album["picture"] = artwork["cover"]
                        album["thumb_art"] = artwork["cover"]
                        coverart_url.append(album)
                    #log( "cdart_url: %s " % cdart_url, xbmc.LOGDEBUG )
    except:
        print_exc()
    return coverart_url

def remote_fanart_list( artist_menu ):
    log( "Finding remote fanart", xbmc.LOGDEBUG )
    backgrounds = ""
    try:
        art = retrieve_fanarttv_json( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 3:
            backgrounds = art[ 0 ]["backgrounds"]
    except:
        print_exc()
    return backgrounds

def remote_clearlogo_list( artist_menu ):
    log( "Finding remote clearlogo", xbmc.LOGDEBUG )
    clearlogo = ""
    try:
        art = retrieve_fanarttv_json( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 3:
            clearlogo = art[ 1 ]["clearlogo"]
    except:
        print_exc()
    return clearlogo
    
def remote_hdlogo_list( artist_menu ):
    log( "Finding remote hdlogo", xbmc.LOGDEBUG )
    hdlogo = ""
    try:
        art = retrieve_fanarttv_json( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 3:
            hdlogo = art[ 3 ]["hdlogo"]
    except:
        print_exc()
    return hdlogo

def remote_banner_list( artist_menu ):
    log( "Finding remote music banners", xbmc.LOGDEBUG )
    banner = ""
    try:
        art = retrieve_fanarttv_json( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 3:
            banner = art[ 4 ]["banner"]
    except:
        print_exc()
    return banner

def remote_artistthumb_list( artist_menu ):
    log( "Finding remote artistthumb", xbmc.LOGDEBUG )
    artistthumb = ""
    #If there is something in artist_menu["distant_id"] build cdart_url
    try:
        art = retrieve_fanarttv_json( artist_menu["musicbrainz_artistid"] )
        if not len(art) < 3:
            artistthumb = art[ 2 ]["artistthumb"]
    except:
        print_exc()
    return artistthumb
    
def retrieve_fanarttv_json( id ):
    log( "Retrieving artwork for artist id: %s" % id, xbmc.LOGDEBUG )
    url = music_url_json % ( api_key, id, "all" )
    htmlsource = ( get_html_source( url, id ) ).encode( 'utf-8', 'ignore' )
    artist_artwork = []
    backgrounds = []
    musiclogos = []
    artistthumbs = []
    hdlogos = []
    banners = []
    albums = []
    blank = {}
    fanart = {}
    clearlogo = {}
    artistthumb = {}
    album_art = {}
    hdlogo = {}
    banner = {}
    artist = ""
    artist_id = ""
    IMAGE_TYPES = [ 'musiclogo',
                    'artistthumb',
                    'artistbackground',
                    'hdmusiclogo',
                    'musicbanner',
                    'albums' ]
    data = simplejson.loads( htmlsource )
    for artist, value in data.iteritems():
        for art in IMAGE_TYPES:
            if value.has_key(art):
                for item in value[art]:
                    print "item:"
                    print item
                    print value
                    if art == "musiclogo":
                        musiclogos.append( item.get('url') )
                    if art == "hdmusiclogo":
                        hdlogos.append( item.get('url') )
                    if art == "artistbackground":
                        backgrounds.append( item.get('url' ) )
                    if art == "musicbanner":
                        banners.append( item.get('url' ) )
                    if art == "artistthumb":
                        artistthumbs.append( item.get( 'url' ) )
                    if art == "albums" and not albums:
                        for album_id in data[ artist ][ "albums" ]:
                            album_artwork = {}
                            album_artwork["musicbrainz_albumid"] = album_id
                            album_artwork["cdart"] = []
                            album_artwork["cover"] = ""
                            if value[ "albums"][ album_id ].has_key( "cdart" ):
                                for item in value[ "albums" ][ album_id ][ "cdart" ]:
                                    cdart = {}
                                    if item.has_key( "disc" ):
                                        cdart[ "disc" ] = int( item[ "disc" ] )
                                    else:
                                        cdart[ "disc" ] = 1
                                    if item.has_key( "url" ):
                                        cdart["cdart"] = item[ "url" ]
                                    else:
                                        cdart["cdart"] = ""
                                    if item.has_key( "size" ):
                                        cdart["size"] = item[ "size" ]
                                    album_artwork["cdart"].append(cdart)
                                    #print album_artwork
                            try:
                                if value[ "albums" ][ album_id ][ "albumcover" ]:
                                    if len( value[ "albums" ][ album_id ][ "albumcover" ] ) < 2:
                                        album_artwork["cover"] = value[ "albums" ][ album_id ][ "albumcover" ][0][ "url" ]
                            except:
                                album_artwork["cover"] = ""
                            albums.append( album_artwork )
    fanart["backgrounds"] = backgrounds
    clearlogo["clearlogo"] = musiclogos
    hdlogo["hdlogo"] = hdlogos
    banner["banner"] = banners
    artistthumb["artistthumb"] = artistthumbs
    album_art["artwork"] = albums
    #print album_art
    artist_artwork.append(fanart)
    artist_artwork.append(clearlogo)
    artist_artwork.append(artistthumb)
    artist_artwork.append(hdlogo)
    artist_artwork.append(banner)
    artist_artwork.append(album_art)
    return artist_artwork

def retrieve_fanarttv_xml( id ):
    log( "Retrieving artwork for artist id: %s" % id, xbmc.LOGDEBUG )
    url = music_url % ( api_key, id, "all" )
    htmlsource = get_html_source( url, id )
    music_id = '<music id="' + id + '" name="(.*?)">'
    match = re.search( music_id, htmlsource )
    artist_artwork = []
    blank = {}
    back = {}
    clearlogo = {}
    artistthumb = {}
    album_art = {}
    hdlogo = {}
    banner = {}
    try:
        if match:
            backgrounds = re.search( '<artistbackgrounds>(.*?)</artistbackgrounds>', htmlsource )
            if backgrounds:
                log( "Found FanART", xbmc.LOGDEBUG )
                _background = re.findall('<artistbackground id="(?:.*?)" url="(.*?)" likes="(?:.*?)/>' , htmlsource )
                back["backgrounds"] = _background
                artist_artwork.append( back )
            else:
                log( "No FanART found", xbmc.LOGDEBUG )
                back["backgrounds"] = blank
                artist_artwork.append( back )
            clearlogos = re.search( '<musiclogos>(.*?)</musiclogos>', htmlsource )
            if clearlogos:
                log( "Found ClearLOGOs", xbmc.LOGDEBUG )
                _clearlogos = re.findall('<musiclogo id="(?:.*?)" url="(.*?)" likes="(?:.*?)/>' , htmlsource )
                clearlogo["clearlogo"] = _clearlogos
                artist_artwork.append( clearlogo )
            else:
                clearlogo["clearlogo"] = ""
                artist_artwork.append( clearlogo )
                log( "No Artist ClearLOGO found", xbmc.LOGDEBUG )
            artistthumbs = re.search( '<artistthumbs>(.*?)</artistthumbs>', htmlsource )
            if artistthumbs:
                log( "Found artistthumbs", xbmc.LOGDEBUG )
                _artistthumbs = re.findall('<artistthumb id="(?:.*?)" url="(.*?)" likes="(?:.*?)/>' , htmlsource )
                artistthumb["artistthumb"] = _artistthumbs
                artist_artwork.append( artistthumb )
            else:
                artistthumb["artistthumb"] = ""
                artist_artwork.append( artistthumb )
                log( "No Artist artistthumbs found", xbmc.LOGDEBUG )
            albums = re.search( "<albums>(.*?)</albums>", htmlsource )
            if albums:
                album = re.findall( '<album id="(.*?)">(.*?)</album>', albums.group( 1 ) )
                a_art = []
                for album_sort in album:
                    album_artwork = {}
                    album_artwork["musicbrainz_albumid"] = album_sort[ 0 ]
                    album_artwork["cdart"] = []
                    album_artwork["cover"] = ""
                    try:
                        cdart_match = re.findall( '<cdart id="(?:.*?)" url="(.*?)" likes="(?:.*?) disc="(.*?)" size="(.*?)"/>' , album_sort[ 1 ] )
                        cover_match = re.search( '<albumcover id="(?:.*?)" url="(.*?)" likes="(?:.*?)/>' , album_sort[ 1 ] )
                        if cdart_match:
                            for disc in cdart_match:
                                cdart = {}
                                cdart["disc"] = int(disc[1])
                                cdart["cdart"] = disc[0]
                                cdart["size"] = int( disc[2] )
                                album_artwork["cdart"].append(cdart)
                        if cover_match:
                            album_artwork["cover"] = cover_match.group( 1 )
                            #log( "cover: %s" % cover_match.group( 1 ), xbmc.LOGDEBUG )                        
                    except:
                        log( "No Album Artwork found", xbmc.LOGDEBUG )
                        print_exc()
                    a_art.append(album_artwork)
                album_art["artwork"] = a_art
                artist_artwork.append(album_art)
            else:
                log( "No artwork found for artist_id: %s" % id, xbmc.LOGDEBUG )
                album_art["artwork"] = blank
                artist_artwork.append( album_art )
            banners = re.search( '<musicbanners>(.*?)</musicbanners>', htmlsource )
            if banners:
                log( "Found Music Banner", xbmc.LOGDEBUG )
                _banner = re.findall('<musicbanner id="(?:.*?)" url="(.*?)" likes="(?:.*?)/>' , htmlsource )
                banner["banner"] = _banner
                artist_artwork.append( banner )
            else:
                log( "No Music Banner found", xbmc.LOGDEBUG )
                banner["banner"] = ""
                artist_artwork.append( banner )
            hdlogos = re.search( '<hdmusiclogos>(.*?)</hdmusiclogos>', htmlsource )
            if hdlogos:
                log( "Found HD LOGOs", xbmc.LOGDEBUG )
                _hdlogos = re.findall('<hdmusiclogo id="(?:.*?)" url="(.*?)" likes="(?:.*?)/>' , htmlsource )
                hdlogo["hdlogo"] = _hdlogos
                artist_artwork.append( hdlogo )
            else:
                hdlogo["hdlogo"] = ""
                artist_artwork.append( hdlogo )
                log( "No Artist HDLOGO found", xbmc.LOGDEBUG )
    except:
        print_exc()
    return artist_artwork

def get_distant_artists():
    """ This retrieve the distant artist list from fanart.tv """
    log( "Retrieving Distant Artists", xbmc.LOGDEBUG )
    distant_artists = []
    htmlsource = get_html_source( artist_url % api_key, "distant" )
    match = re.compile( '<artist id="(.*?)" name="(.*?)" newimages="(?:.*?)" totalimages="(?:.*?)"/>', re.DOTALL )
    for item in match.finditer( htmlsource ):
        distant = {}
        distant["name"] = unescape( ( item.group(2).replace("&amp;", "&") ) )
        distant["id"] = ( item.group(1) )
        #print distant
        distant_artists.append(distant)
    return distant_artists

def match_artists( distant, artists, background=False ):
    artist_list = []
    recognized = []
    matched = False
    matched_count = 0
    canceled = False
    count = 0
    for artist in artists:
        percent = int((float(count)/len( artists ))*100)
        if canceled == True:
            break
        if not artist["musicbrainz_artistid"] and lookup_id:
            artist["musicbrainz_artistid"] = update_musicbrainzid( "artist", artist )
        for d_artist in distant:
            if dialog_msg( "iscanceled", background = background ):
                canceled = True
                break
            if artist["musicbrainz_artistid"] == d_artist["id"] and d_artist["name"]:
                matched_count += 1
                matched = True
                artist["distant_id"] = d_artist["id"]
                break
            elif artist["musicbrainz_artistid"] == d_artist["id"]:
                #print "name missing, adding anyways"
                matched_count += 1
                matched = True
                artist["distant_id"] = d_artist["id"]
                break
            else:
                artist["distant_id"] = ""
                matched = False
        #print artist
        recognized.append(artist)
        artist_list.append(artist)
        dialog_msg( "update", percent = percent, line1 =  __language__(32049) % matched_count, background = background )
        #Onscreen Dialog - Artists Matched: #
        count += 1
    return recognized, artist_list, matched, canceled
    
def get_recognized( distant, all_artists, album_artists, background=False ):
    log( "Retrieving Recognized Artists from fanart.tv", xbmc.LOGDEBUG )
    true = 0
    count = 0
    name = ""
    artist_list = []
    all_artist_list = []
    recognized = []
    recognized_album = []
    fanart_test = ""
    dialog_msg( "create", heading = __language__(32048), background = background )
    #Onscreen dialog - Retrieving Recognized Artist List....
    recognized, artist_list, matched, canceled = match_artists( distant, album_artists, background )
    if enable_all_artists and all_artists:
        recognized_album, all_artist_list, matched, canceled = match_artists( distant, all_artists, background )
    if not matched and not canceled:
        log( "No Matches found.  Compare Artist and Album names with fanart.tv", xbmc.LOGNOTICE )
    elif canceled:
        log( "Get recognized artists has been canceled", xbmc.LOGNOTICE )
    else:
        log( "Matches found. Completed retrieving recognized artists", xbmc.LOGNOTICE )
    dialog_msg( "close", background = background )
    return recognized, recognized_album, all_artist_list, artist_list    

def match_library( local_artist_list ):
    available_artwork = []
    try:
        for artist in local_artist_list:
            artist_artwork = {}
            if not artist["musicbrainz_artistid"]:
                name, artist["musicbrainz_artistid"], sortname = get_musicbrainz_artist_id( artist["name"] )
            if artist["musicbrainz_artistid"]:
                artwork = retrieve_fanarttv_xml( artist["musicbrainz_artistid"] )
                if artwork:
                    artist_artwork["name"] = artist["name"]
                    artist_artwork["musicbrainz_id"] = artist["musicbrainz_artistid"]
                    artist_artwork["artwork"] = artwork
                    available_artwork.append(artist_artwork)
                else:
                    log( "Unable to match artist on fanart.tv: %s" % artist["name"], xbmc.LOGDEBUG )
            else:
                log( "Unable to match artist on Musicbrainz: %s" % artist["name"], xbmc.LOGDEBUG )
    except:
        print_exc()
    return available_artwork
    
    
def junk_delete():
    match = re.search( '''"musiclogo":\[(.*?)\],''', htmlsource )
    if match:
        musiclogos = match.group( 1 )
        musiclogo = re.findall( '''{"id":"(?:.*?)","url":"(.*?)","likes":"(?:.*?)"}''', musiclogos )
    match = re.search( '''"hdmusiclogo":\[(.*?)\],''', htmlsource )
    if match:
        hdmusiclogos = match.group( 1 )
        hdmusiclogo = re.findall( '''{"id":"(?:.*?)","url":"(.*?)","likes":"(?:.*?)"}''', hdmusiclogos )
    match = re.search( '''"artistthumb":\[(.*?)\],''', htmlsource )
    if match:
        artistthumbs = match.group( 1 )
        artistthumb = re.findall( '''{"id":"(?:.*?)","url":"(.*?)","likes":"(?:.*?)"}''', artistthumbs )
    match = re.search( '''"musicbanner":\[(.*?)\],''', htmlsource )
    if match:
        musicbanners = match.group( 1 )
        musicbanner = re.findall( '''{"id":"(?:.*?)","url":"(.*?)","likes":"(?:.*?)"}''', musicbanners )
    match = re.search( '''"artistbackground":\[(.*?)\],''', htmlsource )
    if match:
        artistbackgrounds = match.group( 1 )
        artistbackground = re.findall( '''{"id":"(?:.*?)","url":"(.*?)","likes":"(?:.*?)"}''', artistbackgrounds )
    if data[ artist ].has_key( "albums" ):
            a_art = []
            for album_id in data[ artist ][ "albums" ]:
                album_artwork = {}
                album_artwork["musicbrainz_albumid"] = album_id
                album_artwork["cdart"] = []
                album_artwork["cover"] = ""
                if data[ artist ][ "albums" ][ album_id ].has_key( "cdart" ):
                    cdart = {}
                    for item in data[ artist ][ "albums" ][ album_id ][ "cdart" ]:
                        cdart = {}
                        if item.has_key( "disc" ):
                            cdart[ "disc" ] = int( item[ "disc" ] )
                        else:
                            cdart[ "disc" ] = 1
                        if item.has_key( "url" ):
                            cdart["cdart"] = item[ "url" ]
                        else:
                            cdart["cdart"] = ""
                        if item.has_key( "size" ):
                            cdart["size"] = item[ "size" ]
                        album_artwork["cdart"].append(cdart)
                try:
                    if data[ artist ][ "albums" ][ album_id ][ "albumcover" ]:
                        if len( data[ artist ][ "albums" ][ album_id ][ "albumcover" ] ) < 2:
                            album_artwork["cover"] = data[ artist ][ "albums" ][ album_id ][ "albumcover" ][0][ "url" ]
                except:
                    album_artwork["cover"] = ""
                a_art.append(album_artwork)
            album_art["artwork"] = a_art
            artist_artwork.append(album_art)
 