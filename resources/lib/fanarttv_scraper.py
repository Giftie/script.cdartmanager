# fanart.tv artist artwork scraper
 
import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import os, sys, traceback, re
import urllib
from traceback import print_exc
from urllib import quote_plus, unquote_plus

_                 = sys.modules[ "__main__" ].__language__
__scriptname__    = sys.modules[ "__main__" ].__scriptname__
__scriptID__      = sys.modules[ "__main__" ].__scriptID__
__author__        = sys.modules[ "__main__" ].__author__
__credits__       = sys.modules[ "__main__" ].__credits__
__credits2__      = sys.modules[ "__main__" ].__credits2__
__version__       = sys.modules[ "__main__" ].__version__
__addon__         = sys.modules[ "__main__" ].__addon__
addon_db          = sys.modules[ "__main__" ].addon_db
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from utils import get_html_source, unescape
from musicbrainz_utils import get_musicbrainz_album, get_musicbrainz_artist_id, update_musicbrainzid
from utils import unescape

music_url = "http://fanart.tv/api/music.php?id="
artist_url = "http://fanart.tv/api/music.php?all=true"
lookup_id = False

pDialog = xbmcgui.DialogProgress()

def retrieve_fanarttv_xml( id ):
    xbmc.log( "[script.cdartmanager] - Retrieving artwork for artist id: %s" % id, xbmc.LOGDEBUG )
    url = music_url + id
    htmlsource = get_html_source( url )
    music_id = '<music id="' + id + '" name="(.*?)">'
    match = re.search( music_id, htmlsource )
    artist_artwork = []
    blank = {}
    back = {}
    album_art = {}
    try:
        if match:
            backgrounds = re.search( """<backgrounds>(.*?)</backgrounds>""" , htmlsource )
            if backgrounds:
                xbmc.log( "[script.cdartmanager] - Found FanART", xbmc.LOGDEBUG )
                _background = re.findall('<background>(.*?)</background>' , htmlsource )
                back["backgrounds"] = _background
                artist_artwork.append( back )
            else:
                xbmc.log( "[script.cdartmanager] - No FanART found", xbmc.LOGDEBUG )
                back["backgrounds"] = blank
                artist_artwork.append( back )
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
                        cdart_match = re.search( '<cdart>(.*?)</cdart>' , album_sort[ 1 ] )
                        cover_match = re.search( '<cover>(.*?)</cover>' , album_sort[ 1 ] )
                        cdart_multi_match = re.findall( '<cdart disc=(.*?)>(.*?)</cdart>' , album_sort[ 1 ] )
                        if cdart_match:
                            cdart = {}
                            cdart["disc"] = 1
                            cdart["cdart"] = cdart_match.group( 1 )
                            album_artwork["cdart"].append(cdart)
                            xbmc.log( "[script.cdartmanager] - cdart: %s" % cdart_match.group( 1 ), xbmc.LOGDEBUG )
                        else:
			    for disc in cdart_multi_match:
		                cdart = {}
			        cdart["disc"] = int(disc[0])
			        cdart["cdart"] = disc[1]
			        album_artwork["cdart"].append(cdart)
                        if cover_match:
                            album_artwork["cover"] = cover_match.group( 1 )
                            xbmc.log( "[script.cdartmanager] - cover: %s" % cover_match.group( 1 ), xbmc.LOGDEBUG )
                        
                    except:
                        print "No Album Artwork found"
                        print_exc()
                    print album_artwork
                    a_art.append(album_artwork)
                album_art["artwork"] = a_art
                artist_artwork.append(album_art)
            else:
                xbmc.log( "[script.cdartmanager] - No artwork found for artist_id: %s" % id, xbmc.LOGDEBUG )
                artist_artwork.append( blank )
    except:
        print_exc()
    return artist_artwork

def get_distant_artists():
    """ This retrieve the distant artist list from fanart.tv """
    xbmc.log( "[script.cdartmanager] - Retrieving Distant Artists", xbmc.LOGDEBUG )
    distant_artists = []
    htmlsource = get_html_source( artist_url )
    match = re.compile( '<artist id="(.*?)" name="(.*?)"/>', re.DOTALL )
    for item in match.finditer( htmlsource ):
        distant = {}
        distant["name"] = unescape( ( item.group(2).replace("&amp;", "&") ) )
        distant["id"] = ( item.group(1) )
        distant_artists.append(distant)
    return distant_artists
    
def get_recognized( distant, local ):
    xbmc.log( "[script.cdartmanager] - #  Retrieving Recognized Artists from fanart.tv", xbmc.LOGDEBUG )
    true = 0
    count = 0
    name = ""
    artist_list = []
    recognized = []
    #percent = 0
    pDialog.create( _(32048) )
    #Onscreen dialog - Retrieving Recognized Artist List....
    for artist in local:
        percent = int((float(count)/len(local))*100)
        if ( pDialog.iscanceled() ):
            break
        if not artist["musicbrainz_artistid"] and lookup_id:
            artist["musicbrainz_artistid"] = update_musicbrainzid( "artist", artist )
        for d_artist in distant:
            if ( pDialog.iscanceled() ):
                break
            if artist["musicbrainz_artistid"] == d_artist["id"]:
                true += 1
                artist["distant_id"] = d_artist["id"]
                break                
            else:
                artist["distant_id"] = ""
        recognized.append(artist)
        artist_list.append(artist)
        pDialog.update(percent, (_(32049) % true))
        #Onscreen Dialog - Artists Matched: %
        count += 1
    xbmc.log( "[script.cdartmanager] - #  Total Artists Matched: %s" % true, xbmc.LOGDEBUG )
    if true == 0:
        xbmc.log( "[script.cdartmanager] - #  No Matches found.  Compare Artist and Album names with xbmcstuff.com", xbmc.LOGDEBUG )
    pDialog.close()   
    return recognized, artist_list
    
    
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
                    xbmc.log( "[script.cdartmanager] - Unable to match artist on fanart.tv: %s" % repr( artist["name"] ), xbmc.LOGDEBUG )
            else:
                xbmc.log( "[script.cdartmanager] - Unable to match artist on Musicbrainz: %s" % repr( artist["name"] ), xbmc.LOGDEBUG )
    except:
        print_exc()
    return available_artwork