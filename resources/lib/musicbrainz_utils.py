import xbmc
import sys, os
from traceback import print_exc
_                 = sys.modules[ "__main__" ].__language__
__scriptname__    = sys.modules[ "__main__" ].__scriptname__
__scriptID__      = sys.modules[ "__main__" ].__scriptID__
__version__       = sys.modules[ "__main__" ].__version__
__addon__         = sys.modules[ "__main__" ].__addon__
addon_db          = sys.modules[ "__main__" ].addon_db
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from musicbrainz2.webservice import Query, ArtistFilter, WebServiceError, ReleaseFilter, ReleaseGroupFilter

def get_musicbrainz_album( album_title, artist ):
    album = {}
    xbmc.log( "[script.cdartmanager] - Artist: %s" % repr(artist), xbmc.LOGDEBUG )
    xbmc.log( "[script.cdartmanager] - Album: %s" % repr(album_title), xbmc.LOGDEBUG )
    artist = artist.replace(" & "," ")
    album_title = album_title.replace(" & "," ")
    try:
        #inc = ReleaseFilter(artistName=artist, title=album_title )
        inc = ReleaseGroupFilter( artistName=artist, title=album_title )
        #album_result = Query().getReleases( inc )
        album_result = Query().getReleaseGroups( inc )
        if len( album_result ) == 0:
            xbmc.log( "[script.cdartmanager] - No releases found on MusicBrainz.", xbmc.LOGNOTICE )
            album["artist"] = ""
            album["artist_id"] = ""
            album["id"] = ""
            album["title"] = ""
        else:
#            album["artist"] = album_result[ 0 ].release.artist.name
#            album["artist_id"] = (album_result[ 0 ].release.artist.id).replace( "http://musicbrainz.org/artist/", "" )
#            album["id"] = (album_result[ 0 ].release.id).replace("http://musicbrainz.org/release/", "")
#            album["title"] = album_result[ 0 ].release.title
            album["artist"] = album_result[ 0 ].releaseGroup.artist.name
            album["artist_id"] = (album_result[ 0 ].releaseGroup.artist.id).replace( "http://musicbrainz.org/artist/", "" )
            album["id"] = (album_result[ 0 ].releaseGroup.id).replace("http://musicbrainz.org/release-group/", "")
            album["title"] = album_result[ 0 ].releaseGroup.title
    except WebServiceError, e:
        xbmc.log( "[script.cdartmanager] - Error: %s" % e, xbmc.LOGERROR )
        album["artist"] = ""
        album["artist_id"] = ""
        album["id"] = ""
        album["title"] = ""
    xbmc.sleep(900) # sleep for allowing proper use of webserver        
    return album

def update_musicbrainzid( type, info ):
    xbmc.log( "[script.cdartmanager] - Updating MusicBrainz ID", xbmc.LOGNOTICE )
    try:
        if type == "artist":  # available data info["local_id"], info["name"], info["distant_id"]
            name, artist_id, sortname = get_musicbrainz_artist_id( info["name"] )
            conn = sqlite3.connect(addon_db)
            c = conn.cursor()
            c.execute('UPDATE alblist SET musicbrainz_artistid="%s" WHERE artist="%s"' % (artist_id, info["name"]) )
            c.execute('UPDATE lalist SET musicbrainz_artistid="%s" WHERE name="%s"' % (artist_id, info["name"]) )
            conn.commit
            c.close()
            return artist_id
        if type == "album":
            album_id = get_musicbrainz_album( info["title"], info["artist"] )["id"] 
            conn = sqlite3.connect(addon_db)
            c = conn.cursor()
            c.execute("""UPDATE alblist SET musicbrainz_albumid='%s' WHERE title='%s'""" % (artist_id, info["title"]) )
            conn.commit
            c.close()
            return album_id
    except:
        print_exc()
        return ""
        
def get_musicbrainz_artist_id( artist ):
    try:
        # Search for all artists matching the given name. Retrieve the Best Result
        #
        # replace spaces with plus sign
        name = ""
        id = ""
        sortname = ""
        try:
            artist = artist.encode("utf-8")
        except:
            artist = artist.decode("utf-8")
        artist=artist.replace(" ", "+").replace(" & "," ")
        f = ArtistFilter( name=artist, limit=1 )
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
        xbmc.sleep(900) # sleep for allowing proper use of webserver
        return name, id, sortname
    except WebServiceError, e:
        xbmc.log( "[script.cdartmanager] - Error: %s" % e, xbmc.LOGERROR )
        return "", "", ""