# fanart.tv artist artwork scraper

import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import os, sys, traceback, re
import urllib
from traceback import print_exc
from urllib import quote_plus, unquote_plus
from musicbrainz2.webservice import Query, ArtistFilter, WebServiceError
from musicbrainz_utils import get_musicbrainz_album, get_musicbrainz_artist_id

__scriptID__ = "script.cdartmanager"
__useragent__ = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"
__Addon__ = xbmcaddon.Addon( __scriptID__ )

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __Addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

music_url = "http://fanart.tv/api/music.php?id="
        
def get_html_source( url ):
    """ fetch the html source """
    error = False
    htmlsource = ""
    class AppURLopener(urllib.FancyURLopener):
        version = __useragent__
    urllib._urlopener = AppURLopener()
    for i in range(0, 4):
        try:
            urllib.urlcleanup()
            sock = urllib.urlopen( url )
            htmlsource = sock.read()
            sock.close()
            break
        except:
            print_exc()
            xbmc.log( "[script.cdartmanager] - # !!Unable to open page %s" % url, xbmc.LOGERROR )
            error = True
            xbmc.log( "[script.cdartmanager] - # get_html_source error: %s" % error, xbmc.LOGERROR )
    if error:
        return ""
    else:
        xbmc.log( "[script.cdartmanager] - HTML Source:\n%s" % htmlsource, xbmc.LOGDEBUG )
        return htmlsource  
        
def retrieve_fanarttv_xml( id ):
    url = music_url + id
    htmlsource = get_html_source( url )
    music_id = '<music id="' + id + '" name="(.*?)">'
    match = re.search( music_id, htmlsource )
    artist_artwork = []
    blank = {}
    if match:
        backgrounds = re.search( """<backgrounds>(.*?)</backgrounds>""" , htmlsource )
        if backgrounds:
            _background = re.findall('<background>(.*?)</background>' , htmlsource )
            artist_artwork.append( _background )
        else:
            artist_artwork.append( blank )
        albums = re.search( "<albums>(.*?)</albums>", htmlsource )
        if albums:
            album = re.findall( '<album id="(.*?)">(.*?)</album>', albums.group( 1 ) )
            for album_sort in album:
                album_artwork = {}
                album_artwork["album_id"] = album_sort[ 0 ]
                album_artwork["cdart"] = ""
                album_artwork["cover"] = ""
                try:
                    cdart_match = re.search( '<cdart>(.*?)</cdart>' , album_sort[ 1 ] )
                    cover_match = re.search( '<cover>(.*?)</cover>' , album_sort[ 1 ] )
                    if cdart_match:
                        album_artwork["cdart"] = cdart_match.group( 1 )
                        xbmc.log( "[script.cdartmanager] - cdart: %s" % cdart_match.group( 1 ), xbmc.LOGDEBUG ) 
                    if cover_match:
                        album_artwork["cover"] = cover_match.group( 1 )
                        xbmc.log( "[script.cdartmanager] - cover: %s" % cover_match.group( 1 ), xbmc.LOGDEBUG )
                except:
                    print "No Album Artwork found"
                artist_artwork.append(album_artwork)
        else:
            artist_artwork.append( blank )
    return artist_artwork
        
def match_library( local_artist_list ):
    available_artwork = []
    try:
        for artist in local_artist_list:
            artist_artwork = {}
            print repr( artist["name"] )
            name, id, sortname = get_musicbrainz_artist_id( artist["name"] )
            if name:
                artwork = retrieve_fanarttv_xml( id )
                if artwork:
                    artist_artwork["name"] = name
                    artist_artwork["musicbrainz_id"] = id
                    artist_artwork["artwork"] = artwork
                    available_artwork.append(artist_artwork)
                else:
                    xbmc.log( "[script.cdartmanager] - Unable to match artist on fanart.tv: %s" % repr( name ), xbmc.LOGDEBUG )
            else:
                xbmc.log( "[script.cdartmanager] - Unable to match artist on Musicbrainz: %s" % repr( artist["name"] ), xbmc.LOGDEBUG )
        print "\n"
        print available_artwork
    except:
        print_exc()
    return available_artwork