# -*- coding: utf-8 -*-

import xbmc
import sys, os
from traceback import print_exc

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3
    
_                 = sys.modules[ "__main__" ].__language__
__scriptname__    = sys.modules[ "__main__" ].__scriptname__
__scriptID__      = sys.modules[ "__main__" ].__scriptID__
__version__       = sys.modules[ "__main__" ].__version__
__addon__         = sys.modules[ "__main__" ].__addon__
addon_db          = sys.modules[ "__main__" ].addon_db
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo( 'path' ), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from musicbrainz2.webservice import Query, ArtistFilter, WebServiceError, ReleaseFilter, ReleaseGroupFilter, ReleaseGroupIncludes
from musicbrainz2.model import Release

def split_album_info( album_result, index ):
    album = {}
    try:
        album["artist"] = album_result[ index ].releaseGroup.artist.name
        album["artist_id"] = ( album_result[ index ].releaseGroup.artist.id ).replace( "http://musicbrainz.org/artist/", "" )
        album["id"] = ( album_result[ index ].releaseGroup.id ).replace( "http://musicbrainz.org/release-group/", "" )
        album["title"] = album_result[ index ].releaseGroup.title
    except:
        album["artist"] = ""
        album["artist_id"] = ""
        album["id"] = ""
        album["title"] = ""
    return album

def get_musicbrainz_album( album_title, artist, e_count, limit=1, with_singles=False ):
    """ Retrieves information for Album from MusicBrainz using provided Album title and Artist name. 
        
        Use:
            album, albums = get_musicbrainz_album( album_title, artist, e_count, limit, with_singles )
        
        album_title  - the album title(must be unicode)
        artist       - the artist's name(must be unicode)
        e_count      - used internally(should be set to 0)
        limit        - limit the number of responses
        with_singles - set to True to look up single releases at the same time
    """
    album = {}
    albums = []
    count = e_count
    album["artist"] = ""
    album["artist_id"] = ""
    album["id"] = ""
    album["title"] = ""
    xbmc.log( "[script.cdartmanager] - Retieving MusicBrainz Info", xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Artist: %s" % repr(artist), xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Album: %s" % repr(album_title), xbmc.LOGDEBUG )
    artist = artist.replace( " ", "+" ).replace( " & ","+" ).replace('"','?')
    #artist = artist.replace('"','?')
    album_title = album_title.replace( " ", "+" ).replace( " & ","+" ).replace('"','?')
    #album_title = album_title.replace('"','?')
    try:
        if with_singles:
            q = """'"%s" AND artist:"%s"'""" % ( album_title, artist )
        else:
            q = """'"%s" AND artist:"%s" NOT type:"Single"'""" % (album_title, artist)
        filter = ReleaseGroupFilter( query=q, limit=limit )
        #filter = ReleaseGroupFilter( artistName=artist, title=album_title, releaseTypes=Release.TYPE_ALBUM)
        album_result = Query().getReleaseGroups( filter )
        if len( album_result ) == 0 and with_singles:
            xbmc.log( "[script.cdartmanager] - No releases found on MusicBrainz.", xbmc.LOGDEBUG )
            name, album["artist_id"], sort_name = get_musicbrainz_artist_id( artist )
        elif len( album_result ) == 0 and not with_singles:
            xbmc.log( "[script.cdartmanager] - No releases found on MusicBrainz. Trying singles", xbmc.LOGDEBUG )
            album, albums = get_musicbrainz_album( album_title, artist, 0, limit, True ) # try again with singles
        else:
            for i in range( len( album_result ) ):
                album = split_album_info( album_result, i )
                if len( album_result ) >= 1:
                    albums.append( album )
    except WebServiceError, e:
        xbmc.log( "[script.cdartmanager] - Error: %s" % e, xbmc.LOGERROR )
        web_error = "%s" % e
        try:
            if int( web_error.replace( "HTTP Error ", "").replace( ":", "") ) == 503 and count < 5:
                xbmc.log( "[script.cdartmanager] - Script being blocked - Waiting 2 seconds". xbmc.LOGDEBUG )
                xbmc.sleep( 2000 ) # give the musicbrainz server a 2 second break hopefully it will recover
                count += 1
                album, albums = get_musicbrainz_album( album_title, artist, count, limit, with_singles ) # try again
            elif int( web_error.replace( "HTTP Error ", "").replace( ":", "") ) == 503 and count > 5:
                xbmc.log( "[script.cdartmanager] - Script being blocked, attempted 5 tries with 2 second pauses", xbmc.LOGDEBUG )
                count = 0
            elif int( web_error.replace( "HTTP Error ", "").replace( ":", "") ) == 400 and not with_singles:
                xbmc.log( "[script.cdartmanager] - Match not found, trying again matching singles", xbmc.LOGDEBUG )
                xbmc.sleep( 1000 ) # sleep for allowing proper use of webserver
                album, albums = get_musicbrainz_album( album_title, artist, 0, limit, True ) # try again with singles
        except:
            pass            
    count = 0
    xbmc.sleep( 1000 ) # sleep for allowing proper use of webserver
    return album, albums

def update_musicbrainzid( type, info ):
    xbmc.log( "[script.cdartmanager] - Updating MusicBrainz ID", xbmc.LOGDEBUG )
    artist_id = ""
    try:
        if type == "artist":  # available data info["local_id"], info["name"], info["distant_id"]
            name, artist_id, sortname = get_musicbrainz_artist_id( info["name"] )
            conn = sqlite3.connect(addon_db)
            c = conn.cursor()
            c.execute('UPDATE alblist SET musicbrainz_artistid="%s" WHERE artist="%s"' % (artist_id, info["name"]) )
            try:
                c.execute('UPDATE lalist SET musicbrainz_artistid="%s" WHERE name="%s"' % (artist_id, info["name"]) )
            except:
                pass
            conn.commit
            c.close()
        if type == "album":
            album_id = get_musicbrainz_album( info["title"], info["artist"], 0 )["id"] 
            conn = sqlite3.connect(addon_db)
            c = conn.cursor()
            c.execute("""UPDATE alblist SET musicbrainz_albumid='%s' WHERE title='%s'""" % (album_id, info["title"]) )
            conn.commit
            c.close()
    except:
        print_exc()
    return artist_id
        
def get_musicbrainz_artist_id( artist, limit=1 ):
    name = ""
    id = ""
    sortname = ""
    try:
        # Search for all artists matching the given name. Retrieve the Best Result
        #
        # replace spaces with plus sign
        artist=artist.replace( " ", "+" ).replace( " & ","+" ).replace('"','?')
        f = ArtistFilter( name=artist, limit=limit )
        q_result = Query().getArtists(f)
        if not len(q_result) == 0:
            result = q_result[0]
            artist = result.artist
            xbmc.log( "[script.cdartmanager] - Score     : %s" % result.score, xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Id        : %s" % artist.id, xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Name      : %s" % repr( artist.name ), xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Sort Name : %s" % repr( artist.sortName ), xbmc.LOGDEBUG )
            id = ( artist.id ).replace( "http://musicbrainz.org/artist/", "" )
            name = artist.name
            sortname = artist.sortName
        else: 
            xbmc.log( "[script.cdartmanager] - No Artist ID found for Artist: %s" % repr( artist ), xbmc.LOGDEBUG )
        xbmc.sleep( 1000 ) # sleep for allowing proper use of webserver
    except WebServiceError, e:
        xbmc.log( "[script.cdartmanager] - Error: %s" % e, xbmc.LOGERROR )
    return name, id, sortname