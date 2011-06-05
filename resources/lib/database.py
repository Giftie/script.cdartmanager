import xbmc, xbmcgui
import sys, os, re
from traceback import print_exc

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3

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


safe_db_version = "1.3.2"
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
pDialog = xbmcgui.DialogProgress()
from musicbrainz_utils import get_musicbrainz_artist_id, get_musicbrainz_album, update_musicbrainzid
from fanarttv_scraper import retrieve_fanarttv_xml, remote_cdart_list

from pre_eden_code import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
from xbmcvfs import delete as delete_file
from xbmcvfs import exists as exists
from xbmcvfs import copy as file_copy

# remove comments to save as dharma
#from dharma_code import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
#from os import remove as delete_file
#exists = os.path.exists
#from shutil import copy as file_copy



def artwork_search( cdart_url, id, disc, type ):
    xbmc.log( "[script.cdartmanager] - #  Finding Artwork", xbmc.LOGNOTICE )
    art = {}
    for item in cdart_url:
        if item["musicbrainz_albumid"] == id and item["disc"] == disc and type == "cdart":
            art = item
            break
        elif item["musicbrainz_albumid"] == id and type == "cover":
            art = item
            break
    return art

def get_xbmc_database_info():
    xbmc.log( "[script.cdartmanager] - #  Retrieving Album Info from XBMC's Music DB", xbmc.LOGDEBUG )
    pDialog.create( _(32021), _(32105) )
    album_list, total = retrieve_album_list()
    album_detail_list = retrieve_album_details_full( album_list, total )
    pDialog.close()
    return album_detail_list 

def retrieve_album_details_full( album_list, total ):
    xbmc.log( "[script.cdartmanager] - # Retrieving Album Details", xbmc.LOGDEBUG )
    album_detail_list = []
    album_count = 0
    percent = 0
    try:
        for detail in album_list:
            if (pDialog.iscanceled()):
                break
            album_count += 1
            percent = int((album_count/float(total)) * 100)
            pDialog.update( percent, _(20186), "Album: %s" % detail['title'] , "%s #:%6s      %s:%6s" % ( _(32039), album_count, _(32045), total ) )
            album_id = detail['albumid']
            albumdetails = retrieve_album_details( album_id )
            for albums in albumdetails:
                if (pDialog.iscanceled()):
                    break
                album_artist = {}
                previous_path = ""
                paths = get_album_path( album_id )
                for path in paths:
                    if (pDialog.iscanceled()):
                        break
                    album_artist = {}
                    if not path == previous_path:
                        if exists(path):
                            xbmc.log( "[script.cdartmanager] - Path Exists", xbmc.LOGDEBUG )
                            album_artist["local_id"] = detail['albumid']
                            title = detail['title']
                            try:
                                a_title = albums['artist'].encode("utf-8")
                                album_artist["artist"] = a_title
                            except:
                                print_exc()
                                album_artist["artist"] = albums['artist'].decode("utf-8")
                            album_artist["path"] = path
                            album_artist["cdart"] = exists( os.path.join( path , "cdart.png").replace("\\\\" , "\\") )
                            album_artist["cover"] = exists( os.path.join( path , "folder.jpg").replace("\\\\" , "\\") )
                            previous_path = path
                            path_match = re.search( "(.*?)(?:[\s]|[\(]|[\s][\(])(?:disc|part|cd)(?:[\s]|)([0-9]{0,3})(?:[\)]?.*?)." , path, re.I)
                            title_match = re.search( "(.*?)(?:[\s]|[\(]|[\s][\(])(?:disc|part|cd)(?:[\s]|)([0-9]{0,3})(?:[\)]?.*?)" , title, re.I)
                            if title_match:
                                if title_match.group(2):
                                    xbmc.log( "[script.cdartmanager] - #     Title has CD count", xbmc.LOGDEBUG )
                                    xbmc.log( "[script.cdartmanager] - #        Disc %s" % title_match.group( 2 ), xbmc.LOGDEBUG )
                                    album_artist["disc"] = int( title_match.group(2) )
                                    album_artist["title"] = ( title_match.group( 1 ).replace(" -", "") ).rstrip()
                                else:
                                    if path_match:
                                        if path_match.group(2):
                                            xbmc.log( "[script.cdartmanager] - #     Path has CD count", xbmc.LOGDEBUG )
                                            xbmc.log( "[script.cdartmanager] - #        Disc %s" % path_match.group( 2 ), xbmc.LOGDEBUG )
                                            album_artist["disc"] = int( path_match.group(2) )
                                        else:
                                            album_artist["disc"] = 1
                                    else:
                                        album_artist["disc"] = 1
                                    album_artist["title"] = ( title.replace(" -", "") ).rstrip()
                            else:
                                if path_match:
                                    if path_match.group(2):
                                        xbmc.log( "[script.cdartmanager] - #     Path has CD count", xbmc.LOGDEBUG )
                                        xbmc.log( "[script.cdartmanager] - #        Disc %s" % path_match.group( 2 ), xbmc.LOGDEBUG )
                                        album_artist["disc"] = int( path_match.group(2) )
                                    else:
                                        album_artist["disc"] = 1
                                else:
                                    album_artist["disc"] = 1
                                album_artist["title"] = ( title.replace(" -", "") ).rstrip()
                            try:
                                album_artist["title"] = ( album_artist["title"].encode("utf-8") )
                            except:
                                album_artist["title"] = ( album_artist["title"].decode("utf-8") )
                            musicbrainz_albuminfo = get_musicbrainz_album( album_artist["title"], album_artist["artist"] )
                            album_artist["musicbrainz_albumid"] = musicbrainz_albuminfo["id"]
                            album_artist["musicbrainz_artistid"] = musicbrainz_albuminfo["artist_id"]
                            xbmc.log( "[script.cdartmanager] - Album Title: %s" % repr(album_artist["title"]), xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Album Artist: %s" % repr(album_artist["artist"]), xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Album ID: %s" % album_artist["local_id"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Album Path: %s" % repr(album_artist["path"]), xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - cdART Exists?: %s" % album_artist["cdart"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Cover Art Exists?: %s" % album_artist["cover"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - Disc #: %s" % album_artist["disc"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - MusicBrainz AlbumId: %s" % album_artist["musicbrainz_albumid"], xbmc.LOGDEBUG )
                            xbmc.log( "[script.cdartmanager] - MusicBrainz ArtistId: %s" % album_artist["musicbrainz_artistid"], xbmc.LOGDEBUG )
                            album_detail_list.append(album_artist)
                        else:
                            break
    except:
        xbmc.log( "[script.cdartmanager] - Error Occured", xbmc.LOGNOTICE )
        print_exc()
        pDialog.close()
    return album_detail_list
    
def get_album_cdart( album_path ):
    xbmc.log( "[script.cdartmanager] - ## Retrieving cdART status", xbmc.LOGNOTICE )
    if exists( os.path.join( album_path , "cdart.png").replace("\\\\" , "\\") ):
        return "TRUE"
    else:
        return "FALSE"
        
def get_album_coverart( album_path ):
    xbmc.log( "[script.cdartmanager] - ## Retrieving cdART status", xbmc.LOGNOTICE )
    if exists( os.path.join( album_path , "folder.jpg").replace("\\\\" , "\\") ):
        return "TRUE"
    else:
        return "FALSE"
    
def store_alblist( local_album_list ):
    xbmc.log( "[script.cdartmanager] - #  Storing alblist", xbmc.LOGDEBUG )
    album_count = 0
    cdart_existing = 0
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    percent = 0 
    try:
        for album in local_album_list:
            pDialog.update( percent, _(20186), "" , "%s:%6s" % ( _(32100), album_count ) )
            album_count += 1
            if not album["musicbrainz_artistid"]:
                try:
                    album["artist"] = ( album["artist"].encode("utf-8") )
                    name, album["musicbrainz_artistid"], sort_name = get_musicbrainz_artist_id( album["artist"] )
                except:
                    album["artist"] = ( album["artist"].decode("utf-8") )
                    name, album["musicbrainz_artistid"], sort_name = get_musicbrainz_artist_id( album["artist"] )
            xbmc.log( "[script.cdartmanager] - Album Count: %s" % album_count, xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Album ID: %s" % album["local_id"], xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Album Title: %s" % repr(album["title"]), xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Album Artist: %s" % repr(album["artist"]), xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Album Path: %s" % repr(album["path"]).replace("\\\\" , "\\"), xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - cdART Exist?: %s" % album["cdart"], xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Cover Art Exist?: %s" % album["cover"], xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Disc #: %s" % album["disc"], xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - MusicBrainz AlbumId: %s" % album["musicbrainz_albumid"], xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - MusicBrainz ArtistId: %s" % album["musicbrainz_artistid"], xbmc.LOGDEBUG )
            if album["cdart"]:
                cdart_existing += 1
            try:
                c.execute("insert into alblist(album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid) values (?, ?, ?, ?, ?, ?, ?, ?, ?)", ( album["local_id"], album["title"], album["artist"], album["path"].replace("\\\\" , "\\"), ("False","True")[album["cdart"]], ("False","True")[album["cover"]], album["disc"], album["musicbrainz_albumid"], album["musicbrainz_artistid"] ))
            except UnicodeDecodeError:
                try:
                    temp_title = album["title"].decode('latin-1')
                    album["title"] = temp_title.encode('utf-8')
                    c.execute("insert into alblist(album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid) values (?, ?, ?, ?, ?, ?, ?, ?, ?)", ( album["local_id"], album["title"], album["artist"], album["path"].replace("\\\\" , "\\"), ("False","True")[album["cdart"]], ("False","True")[album["cover"]], album["disc"], album["musicbrainz_albumid"], album["musicbrainz_artistid"] ))
                except UnicodeDecodeError:
                    try:
                        temp_title = album["title"].decode('cp850')
                        album["title"] = temp_title.encode('utf-8')
                        c.execute("insert into alblist(album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid) values (?, ?, ?, ?, ?, ?, ?, ?, ?)", ( album["local_id"], album["title"], album["artist"], album["path"].replace("\\\\" , "\\"), ("False","True")[album["cdart"]], ("False","True")[album["cover"]], album["disc"], album["musicbrainz_albumid"], album["musicbrainz_artistid"] ))
                    except:
                        xbmc.log( "[script.cdartmanager] - # Error Saving to Database"            , xbmc.LOGNOTICE )
            except StandardError, e:
                xbmc.log( "[script.cdartmanager] - # Error Saving to Database", xbmc.LOGNOTICE )
                print_exc()
            if (pDialog.iscanceled()):
                break
    except:
        xbmc.log( "[script.cdartmanager] - # Error Saving to Database", xbmc.LOGNOTICE )
        print_exc()
    conn.commit()
    c.close()
    xbmc.log( "[script.cdartmanager] - # Finished Storing ablist", xbmc.LOGDEBUG )
    return album_count, cdart_existing
    
def recount_cdarts():
    xbmc.log( "[script.cdartmanager] - #  Recounting cdARTS", xbmc.LOGDEBUG )
    cdart_existing = 0
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    c.execute("""SELECT title, cdart FROM alblist""")
    db=c.fetchall()
    for item in db:
        if eval( item[1] ):
            cdart_existing += 1
    c.close()
    return cdart_existing
        
def store_lalist( local_artist_list, count_artist_local ):
    xbmc.log( "[script.cdartmanager] - #  Storing lalist", xbmc.LOGNOTICE )
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    artist_count = 0
    for artist in local_artist_list:
        try:
            c.execute("insert into lalist(local_id, name, musicbrainz_artistid) values (?, ?, ?)", (artist["local_id"], unicode(artist["name"], 'utf-8', ), artist["musicbrainz_artistid"]))
            artist_count += 1
            percent = int((artist_count / float(count_artist_local)) * 100)
            if (pDialog.iscanceled()):
                break
        except:
            print_exe()
    conn.commit()
    c.close()
    xbmc.log( "[script.cdartmanager] - # Finished Storing lalist", xbmc.LOGDEBUG )
    return artist_count
        
def retrieve_distinct_album_artists():
    xbmc.log( "[script.cdartmanager] - #  Retrieving Distinct Album Artist", xbmc.LOGDEBUG )
    album_artists = []
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    c.execute("""SELECT DISTINCT artist, musicbrainz_artistid FROM alblist""")
    db=c.fetchall()
    #xbmc.log( db, xbmc.LOGNOTICE )
    for item in db:
        artist = {}
        artist["name"] = ( item[0].encode('utf-8') ).lstrip("'u").rstrip("'")
        artist["musicbrainz_artistid"] = item[1]
        xbmc.log( repr(artist["name"]), xbmc.LOGNOTICE )
        album_artists.append(artist)
    #xbmc.log( repr(album_artists), xbmc.LOGNOTICE )
    c.close()
    xbmc.log( "[script.cdartmanager] - # Finished Retrieving Distinct Album Artists", xbmc.LOGNOTICE )
    return album_artists
        
def store_counts( artist_count, album_count, cdart_existing ):
    xbmc.log( "[script.cdartmanager] - #  Storing Counts", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    Album Count: %s" % album_count, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    Artist Count: %s" % artist_count, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    cdARTs Existing Count: %s" % cdart_existing, xbmc.LOGNOTICE )
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    c.execute("insert into counts(artists, albums, cdarts, version) values (?, ?, ?, ?)", (artist_count, album_count, cdart_existing, safe_db_version))
    conn.commit()
    c.close()
    xbmc.log( "[script.cdartmanager] - # Finished Storing Counts", xbmc.LOGNOTICE )
    
def new_database_setup():
    global local_artist
    artist_count = 0
    download_count = 0
    cdart_existing = 0
    album_count = 0
    percent=0
    local_artist_list = []
    local_album_artist_list = []
    count_artist_local = 0
    album_artist = []
    xbmc.log( "[script.cdartmanager] - #  Setting Up Database", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    addon_work_path: %s" % addon_work_folder, xbmc.LOGNOTICE )
    if not exists( os.path.join( addon_work_folder, "settings.xml") ):
        xbmcgui.Dialog().ok( _(32071), _(32072), _(32073) )
        xbmc.log( "[script.cdartmanager] - #  Settings not set, aborting database creation", xbmc.LOGNOTICE )
        return album_count, artist_count, cdart_existing
    local_album_list = get_xbmc_database_info()
    #xbmc.log( local_album_list, xbmc.LOGNOTICE )
    pDialog.create( _(32021), _(20186) )
    #Onscreen Dialog - Creating Addon Database
    #                      Please Wait....
    xbmc.log( addon_db, xbmc.LOGNOTICE )
    conn = sqlite3.connect(addon_db)
    c = conn.cursor()
    c.execute('''create table counts(artists, albums, cdarts, version)''') 
    c.execute('''create table lalist(local_id, name, musicbrainz_artistid)''')   # create local album artists database
    c.execute('''create table alblist(album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid)''')  # create local album database
    c.execute('''create table unqlist(title, disc, artist, path, cdart)''')  # create unique database
    conn.commit()
    c.close()
    album_count, cdart_existing = store_alblist( local_album_list ) # store album details first
    album_artist = retrieve_distinct_album_artists()               # then retrieve distinct album artists
    local_artist_list = get_all_local_artists()         # retrieve local artists(to get idArtist)
    percent = 0
    found = False
    for artist in album_artist:        # match album artist to local artist id
        pDialog.update( percent, _(20186), "%s"  % _(32101) , "%s:%s" % ( _(32038), repr(artist["name"]) ) )
        if (pDialog.iscanceled()):
            break
        #xbmc.log( artist, xbmc.LOGNOTICE )
        album_artist_1 = {}
        name = ""
        name = artist["name"]
        artist_count += 1
        for local in local_artist_list:
            if name == local["artist"]:
                id = local["artistid"]
                found = True
                break
        if found:
            album_artist_1["name"] = name                                   # store name and
            album_artist_1["local_id"] = id                                 # local id
            album_artist_1["musicbrainz_artistid"] = artist["musicbrainz_artistid"]
            local_album_artist_list.append(album_artist_1)
        else:
            try:
                print artist["name"]
            except:
                print_exc()
            
    #xbmc.log( local_album_artist_list, xbmc.LOGNOTICE )
    count = store_lalist( local_album_artist_list, artist_count )         # then store in database
    if (pDialog.iscanceled()):
        pDialog.close()
        ok=xbmcgui.Dialog().ok(_(32050), _(32051), _(32052), _(32053))
        xbmc.log( ok, xbmc.LOGNOTICE )
    store_counts( artist_count, album_count, cdart_existing )
    xbmc.log( "[script.cdartmanager] - # Finished Storing Database", xbmc.LOGNOTICE )
    pDialog.close()
    return album_count, artist_count, cdart_existing
    
#retrieve the addon's database - saves time by no needing to search system for infomation on every addon access
def get_local_albums_db( artist_name ):
    xbmc.log( "[script.cdartmanager] - #  Retrieving Local Albums Database", xbmc.LOGNOTICE )
    local_album_list = []
    query = ""
    conn_l = sqlite3.connect(addon_db)
    c = conn_l.cursor()
    try:
        if artist_name == "all artists":
            pDialog.create( _(32102), _(20186) )
            query="SELECT DISTINCT album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid FROM alblist ORDER BY artist"
        else:
            query='SELECT DISTINCT album_id, title, artist, path, cdart, cover, disc, musicbrainz_albumid, musicbrainz_artistid FROM alblist WHERE artist="%s"' % artist_name
        c.execute(query)
        db=c.fetchall()
        for item in db:
            #xbmc.log( item, xbmc.LOGNOTICE )
            album = {}
            album["local_id"] = ( item[0] )
            album["title"] = ( item[1].encode("utf-8") ).lstrip("'u")
            album["artist"] = ( item[2].encode("utf-8") ).lstrip("'u")
            album["path"] = ( (item[3]).encode("utf-8") ).replace('"','').lstrip("'u").rstrip("'")
            album["cdart"] = eval( ( item[4].encode("utf-8") ).lstrip("'u") )
            album["cover"] = eval( ( item[5].encode("utf-8") ).lstrip("'u") )
            album["disc"] = ( item[6] )
            album["musicbrainz_albumid"] = item[7]
            album["musicbrainz_artistid"] = item[8]
            #xbmc.log( repr(album), xbmc.LOGNOTICE )
            local_album_list.append(album)
        c.close
    except:
        print_exc()
        c.close
    #xbmc.log( local_album_list, xbmc.LOGNOTICE )
    if artist_name == "all artists":
        pDialog.close()
    xbmc.log( "[script.cdartmanager] - #  Finished Retrieving Local Albums Database", xbmc.LOGNOTICE )
    return local_album_list
        
def get_local_artists_db():
    xbmc.log( "[script.cdartmanager] - #  Retrieving Local Artists Database", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #", xbmc.LOGNOTICE )
    local_artist_list = []    
    query = "SELECT DISTINCT local_id, name, musicbrainz_artistid FROM lalist ORDER BY name"
    conn_l = sqlite3.connect(addon_db)
    c = conn_l.cursor()
    try:
        c.execute(query)
        db=c.fetchall()
        count = 0
        for item in db:
            count += 1
            #print item
            artists = {}
            artists["local_id"] = ( item[0] )
            artists["name"] = ( item[1].encode("utf-8")).lstrip("'u")
            artists["musicbrainz_artistid"] = item[2]
            #xbmc.log( repr(artists), xbmc.LOGNOTICE )
            local_artist_list.append(artists)
    except:
        print_exc()
    c.close
    #xbmc.log( local_artist_list, xbmc.LOGNOTICE )
    return local_artist_list
    
#retrieves counts for local album, artist and cdarts
def new_local_count():
    xbmc.log( "[script.cdartmanager] - #  Counting Local Artists, Albums and cdARTs", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #", xbmc.LOGNOTICE )
    conn_l = sqlite3.connect(addon_db)
    c = conn_l.cursor()
    try:
        query = "SELECT artists, albums, cdarts FROM counts"
        pDialog.create( _(32020), _(20186) )
        #Onscreen Dialog - Retrieving Local Music Database, Please Wait....
        c.execute(query)
        counts=c.fetchall()
        for item in counts:
            local_artist = item[0]
            album_count = item[1]
            cdart_existing = item[2]
        cdart_existing = recount_cdarts()
        pDialog.close()
        c.close
        return album_count, local_artist, cdart_existing
    except UnboundLocalError:
        xbmc.log( "[script.cdartmanager] - #  Counts Not Available in Local DB, Rebuilding DB", xbmc.LOGNOTICE )
        c.close
        refresh_db()
    
#user call from Advanced menu to refresh the addon's database
def refresh_db():
    xbmc.log( "[script.cdartmanager] - #  Refreshing Local Database", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #", xbmc.LOGNOTICE )
    local_album_count = 0
    local_artist_count = 0
    local_cdart_count = 0
    if exists((addon_db).replace("\\\\" , "\\").encode("utf-8")):
        #File exists needs to be deleted
        db_delete = xbmcgui.Dialog().yesno( _(32042) , _(32015) )
        if db_delete :
            xbmc.log( "[script.cdartmanager] - #    Deleting Local Database", xbmc.LOGNOTICE )
            try:
                delete_file(addon_db)
            except:
                xbmc.log( "[script.cdartmanager] - Unable to delete Database", xbmc.LOGNOTICE )
            if exists((addon_db).replace("\\\\" , "\\").encode("utf-8")): # if database file still exists even after trying to delete it.
                conn = sqlite3.connect(addon_db)
                c = conn.cursor()
                c.execute('''DROP table counts''') 
                c.execute('''DROP table lalist''')   # create local album artists database
                c.execute('''DROP table alblist''')  # create local album database
                c.execute('''DROP table unqlist''')  # create unique database
                conn.commit()
                c.close()
            local_album_count, local_artist_count, local_cdart_count = new_database_setup()
        else:
            pass            
    else :
        #If file does not exist and some how the program got here, create new database
        local_album_count, local_artist_count, local_cdart_count = new_database_setup()
    #update counts
    xbmc.log( "[script.cdartmanager] - # Finished Refeshing Database", xbmc.LOGNOTICE )
    return local_album_count, local_artist_count, local_cdart_count
   
    