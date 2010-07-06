#to do:
# -  add skin folder storage.  right now only albumfolder storage is working
# -  add comments showing what local strings are being displayed   _(32002) = Search Artist
# -  add log printing
# -  insure mouse use works properly - at the moment it seems to break everything!
# -  add save local cdart list, showing which album have or don't have cdarts
# -  add user input(ie keyboard) to get more advanced searches
# -  add database update for any downloads
#        many need to read local database(l_cdart - lalist) to find local id #'s
#        then write to l_cdart - alblist with the important information
#
import platform
import urllib
import sys
import os
import unicodedata
import re
from traceback import print_exc
import xbmcgui
import xbmcaddon
import xbmc

# pull information from default.py
_              = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__scriptID__   = sys.modules[ "__main__" ].__scriptID__
__version__    = sys.modules[ "__main__" ].__version__
__settings__   = sys.modules[ "__main__" ].__settings__
__useragent__  = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources' ) )

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

# Find the proper platforms and append to our path, xbox is the same as win32
env = ( os.environ.get( "OS", "win32" ), "win32", )[ os.environ.get( "OS", "win32" ) == "xbox" ]

# Check to see if using a 64bit version of Linux
env2 = platform.machine()
if re.match("Linux", env) and env2 == "x86_64" :
   env = "Linux_x86_64"
  
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "platform_libraries", env ) )

#import platform's librairies
from pysqlite2 import dbapi2 as sqlite3
from convert import set_entity_or_charref
from convert import translate_string

#variables
OK = True
db_path = os.path.join(xbmc.translatePath( "special://profile/Database/" ), "MyMusic7.db")
xmlfile = os.path.join( BASE_RESOURCE_PATH , "temp.xml" )
artist_url = "http://www.xbmcstuff.com/music_scraper.php?&id_scraper=OIBNYbNUYBCezub&t=artists"
album_url = "http://www.xbmcstuff.com/music_scraper.php?&id_scraper=OIBNYbNUYBCezub&t=cdarts"
cross_url = "http://www.xbmcstuff.com/music_scraper.php?&id_scraper=OIBNYbNUYBCezub&t=cross"
addon_db = os.path.join(xbmc.translatePath( "special://profile/addon_data/" ), __scriptID__, "l_cdart.db")
addon_image_path = os.path.join( BASE_RESOURCE_PATH, "skins", "Default", "media")
addon_img = os.path.join( addon_image_path , "cdart-icon.png" )
pDialog = xbmcgui.DialogProgress()
nDialog = xbmcgui.Dialog()

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):    	
        pass


    def onInit( self ):    	
	self.setup_all()
    
    # sets the colours for the lists
    def coloring( self , text , color , colorword ):
        if color == "red":
            color="FFFF0000"
        if color == "green":
            color="ff00FF00"
        if color == "yellow":
            color="ffFFFF00"
        colored_text = text.replace( colorword , "[COLOR=%s]%s[/COLOR]" % ( color , colorword ) )
        return colored_text


    def set_cdart_folder( self ):
        

    def get_html_source( self , url ):
        """ fetch the html source """
        class AppURLopener(urllib.FancyURLopener):
            version = __useragent__
        urllib._urlopener = AppURLopener()

        try:
            if os.path.isfile( url ):
                sock = open( url, "r" )
            else:
                urllib.urlcleanup()
                sock = urllib.urlopen( url )

            htmlsource = sock.read()
            sock.close()
            return htmlsource
        except:
            print_exc()
            print "# !!Unable to open page %s" % url
            return ""
        
    #not sure this is even being used
    def save_xml( self , data ):
        file( xmlfile , "w" ).write( repr( data ) )
        
    #not sure this is even being used    
    def load_data( self , file_path ):
        try:
            temp_data = eval( file( file_path, "r" ).read() )
        except:
            print_exc()
            print "# !!Unable to open file: %s" % xmlfile
            temp_data = ""
        return temp_data
    
    #retrieve local artist list from xbmc's music db
    def get_local_artist( self ):
        conn_b = sqlite3.connect(db_path)
        d = conn_b.cursor()
        d.execute('SELECT strArtist , idArtist FROM artist ')
        count = 1
        artist_list = []
        for item in d:
            artist = {}
            artist["name"]= translate_string( item[0].encode("utf-8") )
            artist["local_id"]= item[1]
            artist_list.append(artist)
            count = count + 1
        d.close
        count = count - 1
        print "# Total Local Artists: %s" % count
        return artist_list, count
    
    #retrieve local albums based on artist's name from xbmc's db
    def get_local_album( self , artist_name):
        local_album_list = []    
        conn_b = sqlite3.connect(db_path)
        d = conn_b.cursor()
        d.execute("""SELECT DISTINCT strArtist , idArtist, strPath, strAlbum FROM songview Where strArtist LIKE "%s" AND strAlbum != ''""" % artist_name )
        for item in d:
            album = {}
            album["artist"] = translate_string( repr(item[0]).strip("'u") )
            album["artist_id"] = repr(item[1]).strip("'u")
            album["path"] = repr(item[2]).strip("'u")
            album["title"] = translate_string( repr(item[3]).strip("'u").strip('"') )
            if os.path.isfile(os.path.join( album["path"] , "cdart.png").replace("\\\\" , "\\").encode("utf-8")):
                album["cdart"] = "TRUE"
            else :
                album["cdart"] = "FALSE"
            local_album_list.append(album)
            d.close
        return local_album_list
    
    #match artists on xbmcstuff.com with local database    
    def get_recognized( self , distant_artist , l_artist  ):
        true = 0
        artist_list = []
        recognized = []
        pDialog.create( _(32048) )
        #Onscreen dialog - Retrieving Recognized Artist List....
        for artist in l_artist:
            match = re.search('<artist id="(.*?)">%s</artist>' % str.lower( re.escape(artist["name"]) ), distant_artist )
            if match: 
                true = true + 1
                artist["distant_id"] = match.group(1)
                recognized.append(artist)
                artist_list.append(artist)
            else:
                artist["distant_id"] = ""
                artist_list.append(artist)
            pDialog.update(true, (_(32049) % true))
            #Onscreen Dialog - Artists Matched: %
            if ( pDialog.iscanceled() ):
                break
        print "# Total Artists Matched: %s" % true
        if true == 0:
            print "# No Matches found.  Compare Artist and Album names with xbmcstuff.com"
        pDialog.close()
        return recognized, artist_list
    
    #search xbmcstuff.com for similar artists if an artist match is not made
    #between local artist and distant artist
    def search( self , name):
        artist_album_list = []
        search_list = []
        search_dialog = []
        search_name = str.lower(name)
        if re.search("/", search_name):
            search_name=search_name.replace("/", "")
        for part in search_name.split(" "):
            search_xml = str.lower(self.get_html_source( cross_url + "&artist=%s" % urllib.quote_plus(part)) )
            #print cross_url + cross_url + "&artist=%s" % part 
            #print search_xml
            #self.save_xml(search_xml)
            match = re.search('<message>(.*?)</message>', search_xml )    
            if match:
                print "# not found on xbmcstuff.com"
            elif len(part) == 1 or part in ["the","le","de"]:
                pass
            else: 
                raw = re.compile( "<cdart>(.*?)</cdart>", re.DOTALL ).findall(search_xml)
                for i in raw:
                    album = {}
                    album["local_name"] = name
                    match = re.search( "<artist>(.*?)</artist>", i )
                    if match:
                        album["artist"] = set_entity_or_charref(match.group(1))
                    else:
                        album["artist"] = ""
                    if not album["artist"] in search_dialog:
                        search_dialog.append(album["artist"])
                    
                    match = re.search( "<album>(.*?)</album>", i )
                    if match:
                        album["title"] = (match.group(1))
                    else:
                        album["title"] = ""
                    
                    match = re.search( "<thumb>(.*?)</thumb>", i )
                    if match:
                        album["thumb"] = (match.group(1))
                    else:
                        album["thumb"] = ""
                    
                    match = re.search( "<picture>(.*?)</picture>", i )
                    if match:
                        album["picture"] = (match.group(1))
                    else:
                        album["picture"] = ""
                    
                    print album["artist"]
                    search_list.append(album)
            
        if search_dialog: 
            select = None
            select = nDialog().select( _(32032), search_dialog)
            #Onscreen Select Menu
            print select
            if not select == -1:
                for item in search_list : 
                    if item["artist"] == search_list[select]["artist"]:
                        artist_album_list.append(item)
        
        else:
            nDialog(().ok( _(32033), "%s %s" % ( _(32034), name) )
            #Onscreen Dialog - Not Found on XBMCSTUFF.COM, No CDArt found for 
        return artist_album_list
    
    # finds the cdart for the album list    
    def find_cdart( self , album , artist_album_list):
        xml = self.get_html_source( cross_url + "&album=%s&artist=%s" % (urllib.quote_plus(album["title"].replace("&", "&amp;")) , urllib.quote_plus(artist_album_list[0]["artist"])))
        # the .replace("&", "&amp;") is in place to correctly match the albums with & in them
        match = re.findall( "<picture>(.*?)</picture>", xml )
        return match
    
    #finds the cdart for auto download
    def find_cdart2(self , album):
        xml = self.get_html_source( cross_url + "&album=%s&artist=%s" % (urllib.quote_plus((album["title"].replace(",","")).replace("&", "&amp;")) , urllib.quote_plus(album["artist"])))
        # the .replace("&", "&amp;") is in place to correctly match the albums containing '&'
        match = re.findall( "<picture>(.*?)</picture>", xml )
        return match
        
    # downloads the cdart.  used from album list selections
    def download_cdart( self, url_cdart , album ):
	destination = os.path.join( album["path"] , "cdart.png").replace('/"/cdart.png','/cdart.png"')
	#print url_cdart
	#print destination
        pDialog.create( _(32047) )
        #Onscreen Dialog - "Downloading...."
        #
        #conn = sqlite3.connect(addon_db)
        #c = conn.cursor()
        try:
            #this give the ability to use the progress bar by retrieving the downloading information
            #and calculating the percentage
            def _report_hook( count, blocksize, totalsize ):
                percent = int( float( count * blocksize * 100 ) / totalsize )
                strProgressBar = str( percent )
                #print "percent: %s:" % percent
                pDialog.update( percent, _(32035) )
                #Onscreen Dialog - *DOWNLOADING CDART*
                if ( pDialog.iscanceled() ):
                    pass
                
            if os.path.exists(album["path"]):
                fp, h = urllib.urlretrieve(url_cdart, destination, _report_hook)
                print fp, h
                message = [_(32023), _(32024), "File: %s" % album["path"] , "Url: %s" % url_cdart]
                #message = ["Download Sucessful!"]
                #
                #album["cdart"] = "TRUE"  #for storage in the database update
                #album["artist_id] = output from l_cdart database artist id
                #c.execute("insert into alblist(cdart, path, artist_id, title, artist) values (?, ?, ?, ?, ?)", (album["cdart"], album["path"], album["artist_id"], album["title"], album["artist"]))

            else:
                message = [ _(32026), ( _(32025), _(32027) ), "File: %s" % album["path"] , "Url: %s" % url_cdart]
                #message = Download Problem, Check file paths - CDArt Not Downloaded]           
            if ( pDialog.iscanceled() ):
                pass
            
        except:
            message = [ _(32026), _(32025), "File: %s" % album["path"] , "Url: %s" % url_cdart]
            #message = [Download Problem, Check file paths - CDArt Not Downloaded]           
            print_exc()
        #conn.commit()
        #c.close()
        pDialog.close()
        return message  # returns one of the messages built based on success or lack of

    #Automatically downloads non existing cdarts and refreshes addon's db
    def auto_download( self ):
        pDialog.create( _(32046) )
        #Onscreen Dialog - Automatically Downloading CDArt
        count_artist_local = len(local_artist)
        artist_count = 0
        download_count = 0
        cdart_existing = 0
        album_count = 0
        conn = sqlite3.connect(addon_db)
        c = conn.cursor()
        for artist in local_artist:
            artist_count = artist_count + 1
            percent = int((artist_count / float(count_artist_local)) * 100)
            print "#    Artist: %s" % artist["name"] 
            local_album_list = self.get_local_album( artist["name"] )
            for album in local_album_list:
                album_count = album_count + 1
                pDialog.update( percent , "%s%s" % (_(32038) , artist["name"] )  , "%s%s" % (_(32039) , album["title"] ) )
                test_album = self.find_cdart2(album)
                print "#        %s" % album["title"]
                if not test_album == [] : 
                    print "#            ALBUM MATCH FOUND"
                    if album["cdart"] == "FALSE" :
                        print "test_album[0]: %s" % test_album[0]
                        self.download_cdart( test_album[0] , album )
                        download_count = download_count + 1
                        album["cdart"] = "TRUE"
                        c.execute("insert into alblist(cdart, path, artist_id, title, artist) values (?, ?, ?, ?, ?)", (album["cdart"], album["path"], album["artist_id"], album["title"], album["artist"]))

                    else :
                        cdart_existing = cdart_existing + 1
                        print "#            CDArt file already exists, skipped..."
                else :
                    print "#            ALBUM MATCH NOT FOUND"

                if ( pDialog.iscanceled() ):
                    break
            if ( pDialog.iscanceled() ):
                    break    
        conn.commit()
        c.close()
        pDialog.close()
        valid = nDialog(().ok( _(32040), "%s: %s" % (_(32041) , download_count ) )
        print valid
        return

    #creates the album list on the skin
    def populate_album_list(self, artist_menu):
        cdart_url = []
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        self.getControl( 122 ).reset()
        #If there is something in artist_menu["distant_id"] build cdart_url
        print "# distant id: %s" % artist_menu["distant_id"]
        if artist_menu["distant_id"] :
            artist_xml = self.get_html_source( album_url + "&id_artist=%s" % artist_menu["distant_id"] )
            raw = re.compile( "<cdart (.*?)</cdart>", re.DOTALL ).findall(artist_xml)
            for i in raw:
                album = {}            
                album["local_name"] = album["artist"] = artist_menu["name"]
                match = re.search('album="(.*?)">', i )
                #search for album title match, if found, store in album["title"], if not found store empty space
                if match:
                    album["title"] = match.group(1)               
                    #print "album title before: %s" % album["title"]
                    album["title"] = album["title"].replace("&amp;", "&")
                    #print "album title before: %s" % album["title"]
                    
                else:
                    album["title"] = ""
                #search for album thumb match, if found, store in album["thumb"], if not found store empty space
                match = re.search( "<thumb>(.*?)</thumb>", i )
                if match:
                    album["thumb"] = (match.group(1))
                
                else:
                    album["thumb"] = ""
                match = re.search( "<picture>(.*?)</picture>", i )
                #search for album cdart match, if found, store in album["picture"], if not found store empty space
                if match:
                    album["picture"] = (match.group(1))
                
                else:
                    album["picture"] = ""
                cdart_url.append(album)
            print "cdart_url: %s " % cdart_url
        #If artist_menu["distant_id"] is empty, search for name match
        else :
            cdart_url = self.search( artist_menu["name"] )
            
        if not cdart_url:
            #no cdart found
            nDialog(().ok( _(32033), _(32030), _(32031) )
            #Onscreen Dialog - Not Found on XBMCSTUFF.COM, Please contribute! Upload your CDArts, On www.xbmcstuff.com
        else:
            local_album_list = self.get_local_album(cdart_url[0]["local_name"])
            cdart_img = ""
            label1 = ""
            label2 = ""
            album_list= {}
            for album in local_album_list:
                cdart = self.find_cdart(album, cdart_url)
                #check to see if there is a thumb
                if len(cdart) == 1: 
                    label1 = "%s - %s" % (album["artist"] , album["title"])
                    cdart_img = cdart[0]
                    #check to see if cdart already exists
                    #colour the label yellow if found
                    #colour the label green if not
                    label2 = "%s&&%s" % (album["path"], cdart_img)
                    if album["cdart"] == "TRUE":
                        label1 = "%s - %s     ***CDArt Exists***" % (album["artist"] , album["title"])
                        listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                        self.getControl( 122 ).addItem( listitem )
                        listitem.setLabel( self.coloring( label1 , "yellow" , label1 ) )
                        listitem.setLabel2( label2 )                        
                    else :
                        listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                        self.getControl( 122 ).addItem( listitem )
                        listitem.setLabel( self.coloring( label1 , "green" , label1 ) )
                        listitem.setLabel2( label2 )
                    listitem.setThumbnailImage( cdart_img )
                                   
                else :
                    label1 = "choose for %s - %s" % (album["artist"] , album["title"] )
                    cdart_img = ""
                    label2 = "%s&&%s" % (album["path"], cdart_img)
                    listitem = xbmcgui.ListItem( label=label1, label2=cdart_img, thumbnailImage=cdart_img )
                    self.getControl( 122 ).addItem( listitem )
                    listitem.setLabel( label1 )
                    listitem.setLabel2( label2 )
                    listitem.setThumbnailImage( cdart_img )
            
                self.cdart_url=cdart_url
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        self.setFocus( self.getControl( 122 ) )
        self.getControl( 122 ).selectItem( 0 )
        
    #creates the artist list on the skin        
    def populate_artist_list( self, local_artist_list):
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        for artist in local_artist_list:
                if not artist["distant_id"] == "":
                    listitem = xbmcgui.ListItem( label=self.coloring( artist["name"] , "green" , artist["name"] ) )
                    self.getControl( 120 ).addItem( listitem )
                    listitem.setLabel( self.coloring( artist["name"] , "green" , artist["name"] ) )
                else :
                    listitem = xbmcgui.ListItem( label=artist["name"] )
                    self.getControl( 120 ).addItem( listitem )
                    listitem.setLabel( artist["name"] )
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        self.setFocus( self.getControl( 120 ) )
        self.getControl( 120 ).selectItem( 0 )
        
    #create the addon's database
    def database_setup( self ):
        global local_artist
        local_artist, count_artist_local = self.get_local_artist()
        artist_count = 0
        download_count = 0
        cdart_existing = 0
        album_count = 0
        percent=0
        pDialog.create( _(32021), _(32016) )
        #Onscreen Dialog - Creating Addon Database
        #                      Please Wait....
        print addon_db
        conn = sqlite3.connect(addon_db)
        c = conn.cursor()
        c.execute('''create table lalist(local_id, name)''')
        c.execute('''create table alblist(cdart, path, artist_id, title, artist)''')
        for artist in local_artist:
            c.execute("insert into lalist(local_id, name) values (?, ?)", (artist["local_id"], artist["name"]))
            artist_count = artist_count + 1
            percent = int((artist_count / float(count_artist_local)) * 100) 
            local_album_list = self.get_local_album( artist["name"] )
            for album in local_album_list:
                pDialog.update( percent, _(32016), "" , "%s - %s" % ( artist["name"] , album["title"] ) )
                album_count = album_count + 1               
                if album["cdart"] == "TRUE" :
                   cdart_existing = cdart_existing + 1
                c.execute("insert into alblist(cdart, path, artist_id, title, artist) values (?, ?, ?, ?, ?)", (album["cdart"], album["path"], album["artist_id"], album["title"], album["artist"]))
                if (pDialog.iscanceled()):
                    break
            if (pDialog.iscanceled()):
                break
        if (pDialog.iscanceled()):
            pDialog.close()
            nDialog(().ok(_(32050), _(32051), _(32052), _(32053))
        pDialog.close()
        conn.commit()
        c.close()
        return album_count, artist_count, cdart_existing
    
    #retrieve the addon's database - saves time by no needing to search system for infomation on every addon access
    def get_local_db( self ):
        local_album_list = []    
        conn_l = sqlite3.connect(addon_db)
        c = conn_l.cursor()
        c.execute("""SELECT DISTINCT cdart, path, artist_id, title, artist FROM alblist""")
        db=c.fetchall()
        for item in db:
            album = {}
            album["cdart"] = translate_string( item[0].encode("utf-8"))
            album["path"] = repr(item[1])
            album["artist_id"] = repr(item[2])
            album["title"] = translate_string( item[3].encode("utf-8"))
            album["artist"] = translate_string( item[4].encode("utf-8"))
            local_album_list.append(album)
            c.close
        return local_album_list
    
    #retrieves counts for local album, artist and cdarts
    def new_local_count( self ):
        pDialog.create( _(32020), _(32016) )
        #Onscreen Dialog - Retrieving Local Music Database, Please Wait....
        global local_artist
        local_artist, count_artist_local = self.get_local_artist()
        artist_count = 0
        download_count = 0
        cdart_existing = 0
        album_count = 0
        percent=0
        local_album_list = self.get_local_db( )
        for album in local_album_list:
            pDialog.update( percent, _(32016), "" , "%s - %s" % ( album["artist"] , album["title"] ) )
            album_count = album_count + 1               
            if album["cdart"] == "TRUE" :
               cdart_existing = cdart_existing + 1

        pDialog.close()
        return album_count, count_artist_local, cdart_existing
    
    #user call from Advanced menu to refresh the addon's database
    def refresh_db( self ):
        if os.path.isfile((addon_db).replace("\\\\" , "\\").encode("utf-8")):
            #File exists needs to be deleted
            db_delete = nDialog.yesno( _(32042) , _(32015) )
            if db_delete :
                os.remove(addon_db)
                
            else:
                pass
            self.local_album_count, self.local_artist_count, self.local_cdart_count = self.database_setup()
            
        else :
            #If file does not exist and some how the program got here, create new database
            self.local_album_count, self.local_artist_count, self.local_cdart_count = self.database_setup()
        #update counts
        self.getControl( 109 ).setLabel( _(32007) % self.local_artist_count)
        self.getControl( 110 ).setLabel( _(32010) % self.local_album_count)
        self.getControl( 112 ).setLabel( _(32008) % self.local_cdart_count)
        
    # setup self. strings and initial local counts
    def setup_all( self ):
        self.menu_mode = 0
        self.recognized_artists = []
        self.all_artists = []
        self.cdart_url = []
        self.local_artists = []
        self.label_1 = ""
        self.label_2 = addon_img
        self.cdartimg = ""
        self.local_artist_count = 0
        self.local_album_count = 0
        self.local_cdart_count = 0
        #check settings to see if storage location has been set, open settings if not.
        try:
            storage=( "skin", "albumfolder" )[ int( __settings__.getSetting("folder") ) ]
        except:
            __settings__.openSettings()
            storage=( "skin", "albumfolder" )[ int( __settings__.getSetting("folder") ) ]
        #if skin storage has been selected, check to see if cdart directory exists
        #if not, create one.
        if storage == "skin":
            cdart_path = os.path.join(xbmc.translatePath("special://skin\media"),"backdrops","artist_fanart","cd")
            if not os.path.exists(cdart_path):
            os.makedirs(cdart_path)
            
        listitem = xbmcgui.ListItem( label=self.label_1, label2=self.label_2, thumbnailImage=self.cdartimg )
        self.getControl( 122 ).addItem( listitem )
        listitem.setLabel2(self.label_2)
        #checking to see if addon_db exists, if not, run database_setup()
        if not os.path.isfile((addon_db).replace("\\\\" , "\\").encode("utf-8")):
            self.local_album_count, self.local_artist_count, self.local_cdart_count = self.database_setup()
        else:
            self.local_album_count, self.local_artist_count, self.local_cdart_count = self.new_local_count()
        self.getControl( 109 ).setLabel( _(32007) % self.local_artist_count)
        self.getControl( 110 ).setLabel( _(32010) % self.local_album_count)
        self.getControl( 112 ).setLabel( _(32008) % self.local_cdart_count)
        self.setFocusId( 100 ) # set menu selection to the first option(Search Artists)

                    
    def onClick( self, controlId ):
        #print "Control ID: %s " % controlId
        if controlId == 100 : #Search Artist
            self.setFocusId( 105 )
        if controlId == 102 : #Automatic Download
            self.menu_mode = 3
            download_count = self.auto_download()
            self.local_album_count, self.local_artist_count, self.local_cdart_count = self.new_local_count()
            self.getControl( 109 ).setLabel( _(32007) % self.local_artist_count)
            self.getControl( 110 ).setLabel( _(32010) % self.local_album_count)
            self.getControl( 112 ).setLabel( _(32008) % self.local_cdart_count)
        if controlId == 103 : #Advanced
            self.setFocusId( 130 )
        if controlId in [105, 106]:
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            self.getControl( 120 ).reset()
            distant_artist = str.lower(self.get_html_source( artist_url ))
            self.recognized_artists, self.local_artists = self.get_recognized( distant_artist , local_artist )
        
        if controlId == 105 : #Recognized Artists
            self.menu_mode = 1
            self.populate_artist_list( self.recognized_artists )
        if controlId == 106 : #All Artists
            self.menu_mode = 2
            self.populate_artist_list( self.local_artists )
        #if controlId == 107 :
        #    self.setFocusId( 200 )
        #if controlId == 108 :
        #    self.setFocusId( 200 )    
        if controlId == 120 : #Retrieving information from Artists List
            if self.menu_mode == 1: #information pulled from recognized list
                artist_menu = {}
                artist_menu["local_id"] = str(self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["local_id"])
                artist_menu["name"] = str(self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["name"])
                artist_menu["distant_id"] = str(self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["distant_id"])
            elif self.menu_mode == 2: #information pulled from All Artist List
                artist_menu = {}
                artist_menu["local_id"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["local_id"])
                artist_menu["name"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["name"])
                artist_menu["distant_id"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["distant_id"])
            print artist_menu
            self.populate_album_list( artist_menu )
            self.setFocus( self.getControl( 122 ) )
            self.getControl( 122 ).selectItem( 0 )    
        if controlId == 122 : #Retrieving information from Album List
            local = ""
            url = ""
            album = {}
            album_search=[]
            album_selection=[]
            cdart_path = {}
            count = 0
            url = (self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&")[1]
            cdart_path["path"] = (self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&")[0]
            local = ((self.getControl( 122 ).getSelectedItem().getLabel()).replace("choose for ", "")).replace("     ***CDArt Exists***", "")
            cdart_path["artist"]=local.split(" - ")[0]
            cdart_path["title"]=local.split(" - ")[1]
            print "# artist: %s" % cdart_path["artist"]
            print "# album title: %s" % cdart_path["title"]
            print "# cdart_path: %s" % cdart_path["path"]
            print "# url: %s" % url
            if not url =="" : # If it is a recognized Album...
                message = self.download_cdart( url, cdart_path )
            else : # If it is not a recognized Album...
                for elem in self.cdart_url:
                    album["search_name"] = elem["title"]
                    album["search_url"] = elem["picture"]
                    album_search.append(album["search_name"])
                    album_selection.append(album["search_url"])
                    count=count+1
                select = nDialog(().select(_(32022), album_search)
                #print select
                cdart_url = album_selection[select]
                message = self.download_cdart( cdart_url, cdart_path )
            nDialog(().ok(message[0] ,message[1] ,message[2] ,message[3])
            
        if controlId == 132 : #Clean Music database selected from Advanced Menu
            xbmc.executebuiltin( "CleanLibrary(music)") 
        if controlId == 133 : #Update Music database selected from Advanced Menu
            xbmc.executebuiltin( "UpdateLibrary(music)")
        if controlId == 130 : #Save Local CDArt List selected from Advanced Menu
            pass
        if controlId == 131 : #Refresh Local database selected from Advanced Menu
            self.refresh_db()
        if controlId == 104 : #Settings
            self.menu_mode = 5
            __settings__.openSettings()
        if controlId == 111 : #Exit
            self.menu_mode = 0
            self.close()
            	

    def onFocus( self, controlId ):
        if controlId == 122 :
            if re.search("&&", self.getControl( 122 ).getSelectedItem().getLabel2()):
                image=(self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&")[1]
            else:
                image=addon_img
            self.getControl( 210 ).setImage( image )
            
        	
    def onAction( self, action ):
        print action
        if re.search("&&", self.getControl( 122 ).getSelectedItem().getLabel2()):
            image=(self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&")[1]
        else:
            image=addon_img
        self.getControl( 210 ).setImage( image )
            
        #if action == 10:
        #    print "Closing"
        #    pDialog.close()
        #    self.close()
   
def onAction( self, action ):
    print action
    if ( action.getButtonCode() in CANCEL_DIALOG ):
	print "# Closing"
	self.close()
