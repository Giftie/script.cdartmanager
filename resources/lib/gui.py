# -*- coding: utf-8 -*-

#to do:
# -  
# -  *add comments showing what local strings are being displayed   _(32002) = Search Artist
# -  add log xbmc.log(ing, xbmc.LOGNOTICE )
# -  insure mouse use works properly - at the moment it seems to break everything!
# -  add user input(ie keyboard) to get more advanced searches
# -  add bulk uploading and downloading
# -  add website
#

import urllib
import sys
import os
import unicodedata
import re
from traceback import print_exc
import xbmcgui
import xbmcaddon
import xbmc
import socket
import shutil
import tarfile
from PIL import Image
from string import maketrans
from ftplib import FTP
try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3

#time socket out at 30 seconds
socket.setdefaulttimeout(30)

KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467

# pull information from default.py
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
__useragent__     = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

from convert import set_entity_or_charref
from folder import dirEntries
from fanarttv_scraper import match_library, get_distant_artists, retrieve_fanarttv_xml, get_recognized
from utils import get_html_source, download_cdart, auto_download
from database import store_alblist, store_lalist, retrieve_distinct_album_artists, store_counts, new_database_setup, get_local_albums_db, get_local_artists_db, new_local_count, refresh_db
from musicbrainz_utils import get_musicbrainz_artist_id, get_musicbrainz_album, update_musicbrainzid

#variables
intab = ""
outtab = ""
transtab = maketrans(intab, outtab)
musicdb_path = os.path.join(xbmc.translatePath( "special://profile/Database/" ), "MyMusic7.db")
download_temp_folder = os.path.join(addon_work_folder, "temp")
addon_image_path = os.path.join( BASE_RESOURCE_PATH, "skins", "Default", "media")
addon_img = os.path.join( addon_image_path , "cdart-icon.png" )
pDialog = xbmcgui.DialogProgress()
usehttpapi = __addon__.getSetting("usingdharma")
#usehttpapi = "true"
safe_db_version = "1.3.2"

try:
    from pre_eden_code import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
    from xbmcvfs import delete as delete_file
    from xbmcvfs import exists as exists
    from xbmcvfs import copy as file_copy
except:
    from dharma_code import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
    from os import remove as delete_file
    exists = os.path.exists
    from shutil import copy as file_copy

CHAR_REPLACEMENT = {
    # latin-1 characters that don't have a unicode decomposition
    0xc6: u"AE", # LATIN CAPITAL LETTER AE
    0xd0: u"D",  # LATIN CAPITAL LETTER ETH
    0xd8: u"OE", # LATIN CAPITAL LETTER O WITH STROKE
    0xde: u"Th", # LATIN CAPITAL LETTER THORN
    0xdf: u"ss", # LATIN SMALL LETTER SHARP S
    0xe6: u"ae", # LATIN SMALL LETTER AE
    0xf0: u"d",  # LATIN SMALL LETTER ETH
    0xf8: u"oe", # LATIN SMALL LETTER O WITH STROKE
    0xfe: u"th", # LATIN SMALL LETTER THORN
    }

##
# Translation dictionary.  Translation entries are added to this
# dictionary as needed.

class unaccented_map(dict):
    ##
    # Maps a unicode character code (the key) to a replacement code
    # (either a character code or a unicode string).

    def mapchar(self, key):
        ch = self.get(key)
        if ch is not None:
            return ch
        de = unicodedata.decomposition(unichr(key))
        if de:
            try:
                ch = int(de.split(None, 1)[0], 16)
            except (IndexError, ValueError):
                ch = key
        else:
            ch = CHAR_REPLACEMENT.get(key, key)
        self[key] = ch
        return ch

    if sys.version >= "2.5":
        # use __missing__ where available
        __missing__ = mapchar
    else:
        # otherwise, use standard __getitem__ hook (this is slower,
        # since it's called for each character)
        __getitem__ = mapchar



class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):    	
        pass
        
    def onInit( self ):
        xbmc.log( sys.getdefaultencoding(), xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - ############################################################", xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __scriptname__, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #        gui.py module                                     #", xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __scriptID__, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __author__, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __version__, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __credits__, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __credits2__, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    Thanks for the help...                                #", xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - ############################################################", xbmc.LOGNOTICE )
        self.retrieve_settings()
        self.setup_colors()
        try:
            self.setup_all()
        except:
            pDialog.close()
            print_exc()

    def retrieve_settings( self ):
        backup_path = __addon__.getSetting("backup_path")
        unique_path = __addon__.getSetting("unique_path")
        enableresize = __addon__.getSetting("enableresize")
        folder = __addon__.getSetting("folder")
        enablecustom = __addon__.getSetting("enablecustom")
        xbmc.log( "[script.cdartmanager] - # Settings                                                 #", xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #                                                          #", xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Backup Folder: %-35s    #" % backup_path, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Unique Folder: %-35s    #" % unique_path, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Resize Enabled: %-34s    #" % enableresize, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Saving format: %-35s    #" % folder, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Enable Custom Colours: %-27s    #" % enablecustom, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #                                                          #", xbmc.LOGDEBUG )
        
    def setup_colors( self ):
        if __addon__.getSetting("enablecustom")=="true":
            self.recognized_color = str.lower(__addon__.getSetting("recognized"))
            self.unrecognized_color = str.lower(__addon__.getSetting("unrecognized"))
            self.remote_color = str.lower(__addon__.getSetting("remote"))
            self.local_color = str.lower(__addon__.getSetting("local"))
            self.remotelocal_color = str.lower(__addon__.getSetting("remotelocal"))
            self.unmatched_color = str.lower(__addon__.getSetting("unmatched"))
            self.localcdart_color = str.lower(__addon__.getSetting("localcdart"))
        else:
            self.recognized_color = "green"
            self.unrecognized_color = "white"
            self.remote_color = "green"
            self.local_color = "orange"
            self.remotelocal_color = "yellow"
            self.unmatched_color = "white"
            self.localcdart_color = "orange"
        #######000000000111111111122222222223333333333444444444455555555556
        #######123456789012345678901234567890123456789012345678901234567890        
        xbmc.log( "[script.cdartmanager] - ############################################################", xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - # Custom Colours                                           #", xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #                                                          #", xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Recognized: %-38s    #" % self.recognized_color, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Unrecognized: %-36s    #" % self.unrecognized_color, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Remote: %-42s    #" % self.remote_color, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Local: %-43s    #" % self.local_color, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Local & Remote Match: %-28s    #" % self.remotelocal_color, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Unmatched: %-39s    #" % self.unmatched_color, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Local cdART: %-37s    #" % self.localcdart_color, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #                                                          #", xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - ############################################################", xbmc.LOGDEBUG )            

    def remove_special( self, temp ):
        return temp.translate(transtab, "!@#$^*()?[]{}<>',./")
    
    # sets the colours for the lists
    def coloring( self , text , color , colorword ):
        if color == "white":
            color="FFFFFFFF"
        if color == "blue":
            color="FF0000FF"
        if color == "cyan":
            color="FF00FFFF"
        if color == "violet":
            color="FFEE82EE"
        if color == "pink":
            color="FFFF1493"
        if color == "red":
            color="FFFF0000"
        if color == "green":
            color="FF00FF00"
        if color == "yellow":
            color="FFFFFF00"
        if color == "orange":
            color="FFFF4500"
        colored_text = text.replace( colorword , "[COLOR=%s]%s[/COLOR]" % ( color , colorword ) )
        return colored_text

    def remove_color( self, text ):
        clean_text = (((text.replace("[/COLOR]","")).replace("[COLOR=FFFFFFFF]","")).replace("[COLOR=FF0000FF]","")).replace("[COLOR=FF00FFFF]","")
        clean_text = ((clean_text.replace("[COLOR=FFEE82EE]","")).replace("[COLOR=FFFF1493]","")).replace("[COLOR=FFFF0000]","")
        clean_text = ((clean_text.replace("[COLOR=FF00FF00]","")).replace("[COLOR=FFFFFF00]","")).replace("[COLOR=FFFF4500]","")
        return clean_text
        
###### Remove
    def cdart_search( self, cdart_url, title ):
        s_title = ""
        rms_title = ""
        s_title = self.remove_special( title )
        cdart_find = {}
        for album in cdart_url:
            r_title1 = str.lower( album["title"] )
            r_title2 = str.lower( album["title"].split(" (")[0] )
            r_title3 = str.lower(self.remove_special( album["title"] ))
            r_title4 = str.lower(self.remove_special( album["title"].split(" (")[0] ))
            if title == r_title1 or title == r_title2 or title == r_title3 or title == r_title4 or s_title == r_title1 or s_title == r_title2 or s_title == r_title3 or s_title == r_title4:
                cdart_find = album
                break
            else:
                cdart_find["picture"]=""
                cdart_find["thumb"]=""
                cdart_find["title"]=""
                cdart_find["artistd_id"]=""
                cdart_find["artistl_id"]=""
                cdart_find["local_name"]=""
                cdart_find["artist_name"]=""
        return cdart_find        
#####   Remove 
    # finds the cdart for the album list    
    def find_cdart( self , aname , atitle, remote_cdart_url ):
        xbmc.log( "[script.cdartmanager] - # Finding cdART for album list", xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #", xbmc.LOGDEBUG )
        match = ""
        s_title = ""
        name = str.lower( aname )
        title = str.lower( atitle )
        s_title = self.remove_special( title )
        for album in remote_cdart_url:
            r_title1 = str.lower( album["title"] )
            r_title2 = str.lower( album["title"].split(" (")[0] )
            r_title3 = str.lower(self.remove_special( album["title"] ))
            r_title4 = str.lower(self.remove_special( album["title"].split(" (")[0] ))
            if title == r_title1 or title == r_title2 or title == r_title3 or title == r_title4 or s_title == r_title1 or s_title == r_title2 or s_title == r_title3 or s_title == r_title4:
                return album["picture"]
        return match
##### remove
    # finds the cdart for the album list    
    def find_cdart2( self , aname , atitle ):
        match = None
        name = str.lower( aname )
        title = str.lower( atitle )
        xml = get_html_source( cross_url + "&album=%s&artist=%s" % (urllib.quote_plus(title.replace("&", "&amp;")) , urllib.quote_plus(name.replace("&", "&amp;"))))
        match = re.search("<no_result", xml)
        if match:
            s_name = self.remove_special( name )
            s_title = self.remove_special( title )
            xml = get_html_source( cross_url + "&album=%s&artist=%s" % (urllib.quote_plus(s_title.replace("&", "&amp;")) , urllib.quote_plus(s_name.replace("&", "&amp;"))))
            if not xml == "":
                match = re.findall( "<picture>(.*?)</picture>", xml )
            else:
                xbmc.log( "[script.cdartmanager] - #### Error, xml= %s" % xml, xbmc.LOGDEBUG )
                match = []
        elif not xml == "":
            match = re.findall( "<picture>(.*?)</picture>", xml )
        else:
            xbmc.log( "[script.cdartmanager] - #### Error, xml= %s" % xml, xbmc.LOGDEBUG )
            match = []
        return match
#####    


    #Local vs. XBMCSTUFF.COM cdART list maker
    def local_vs_distant( self ):
        xbmc.log( "[script.cdartmanager] - #  Local vs. XBMCSTUFF.COM cdART", xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - # ", xbmc.LOGNOTICE )
        pDialog.create( _(32065) )
        #Onscreen Dialog - Comparing Local and Online cdARTs...
        local_count = 0
        distant_count = 0
        cdart_difference = 0
        album_count = 0
        artist_count = 0
        temp_album = {}
        cdart_lvd = []
        local_artist = get_local_artists_db()
        count_artist_local = len(local_artist)
        for artist in local_artist:
            artist_count += 1
            percent = int((artist_count / float(count_artist_local)) * 100)
            xbmc.log( "[script.cdartmanager] - #    Artist: %-40s Local ID: %s" % (repr(artist["name"]), artist["local_id"]), xbmc.LOGNOTICE )
            local_album_list = get_local_albums_db( artist["name"] )
            for album in local_album_list:
                temp_album = {}
                album_count += 1
                temp_album["artist"] = artist["name"]
                temp_album["title"] = album["title"]
                temp_album["path"] = album["path"]
                name = artist["name"]
                title = album["title"]
                pDialog.update( percent , "%s%s" % (_(32038) , repr(artist["name"]) )  , "%s%s" % (_(32039) , repr(album["title"]) ) )
                test_album = self.find_cdart2(name , title)
                xbmc.log( "[script.cdartmanager] - #        Album: %s" % repr(album["title"]), xbmc.LOGNOTICE )
                if not test_album == [] : 
                    xbmc.log( "[script.cdartmanager] - #            ALBUM MATCH FOUND", xbmc.LOGNOTICE )
                    temp_album["distant"] = "TRUE"
                    distant_count += 1
                    if album["cdart"] == "TRUE" :
                        temp_album["local"] = "TRUE"
                        local_count += 1
                        xbmc.log( "[script.cdartmanager] - #                Local & Distant cdART image exists...", xbmc.LOGNOTICE )
                    else:
                        temp_album["local"] = "FALSE"
                        xbmc.log( "[script.cdartmanager] - #                No local cdART image exists", xbmc.LOGNOTICE )
                else :
                    xbmc.log( "[script.cdartmanager] - #            ALBUM MATCH NOT FOUND", xbmc.LOGNOTICE )
                    temp_album["distant"] = "FALSE"
                    if album["cdart"] == "TRUE" :
                        local_count += 1
                        temp_album["local"] = "TRUE"
                        xbmc.log( "[script.cdartmanager] - #                Local cdART image exists...", xbmc.LOGNOTICE )
                    else:
                        temp_album["local"] = "FALSE"
                        xbmc.log( "[script.cdartmanager] - #                No local cdART image exists", xbmc.LOGNOTICE )
                cdart_lvd.append(temp_album)
                #xbmc.log( temp_album, xbmc.LOGNOTICE )
                #xbmc.log( cdart_lvd                , xbmc.LOGNOTICE )
                if ( pDialog.iscanceled() ):
                    break
            if ( pDialog.iscanceled() ):
                    break    
        pDialog.close()
        if (local_count - distant_count) > 0:
            xbmcgui.Dialog().ok( "There are %s cdARTs that only exist locally" % (local_count - distant_count), "Local cdARTs: %s" % local_count, "Distant cdARTs: %s" % distant_count )
            difference = 1
        else:
            xbmcgui.Dialog().ok( "There are %s new cdARTs on XBMCSTUFF.COM" % (distant_count - local_count), "Local cdARTs: %s" % local_count, "Distant cdARTs: %s" % distant_count )
            differnece = 0
        return cdart_lvd, difference

    def remote_cdart_list( self, artist_menu ):
        xbmc.log( "[script.cdartmanager] - #   Finding Remote cdARTs", xbmc.LOGNOTICE )
        cdart_url = []
        #If there is something in artist_menu["distant_id"] build cdart_url
        try:
            album_artwork = retrieve_fanarttv_xml( artist_menu["musicbrainz_artistid"] )[1]["artwork"]
            if album_artwork:
                for artwork in album_artwork:
                    album = {'artistl_id': "", 'artistd_id': "", 'local_name': "", 'musicbrainz_albumid': "", 'picture': {}, 'thumb': {} }
                    album["artistl_id"] = artist_menu["local_id"]
                    album["artistd_id"] = artist_menu["distant_id"]
                    album["local_name"] = album["artist"] = artist_menu["name"]
                    album["musicbrainz_albumid"] = artwork["musicbrainz_albumid"]
                    for cdart in artwork["cdart"]:
                        album["picture"][cdart["disc"]-1] = cdart["cdart"]
                        album["thumb"][cdart["disc"]-1] = cdart["cdart"]
                    cdart_url.append(album)
                    #xbmc.log( "[script.cdartmanager] - cdart_url: %s " % cdart_url, xbmc.LOGNOTICE )
        except:
            print_exc()
        return cdart_url
    
    def cdart_search( self, cdart_url, id ):
        cdart = {}
        #print id
        for item in cdart_url:
            #print item
            if item["musicbrainz_albumid"] == id:
                cdart = item
                break
        return cdart
            
    #creates the album list on the skin
    def populate_album_list(self, artist_menu, cdart_url):
        xbmc.log( "[script.cdartmanager] - #  Populating Album List", xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #", xbmc.LOGNOTICE )
        self.getControl( 122 ).reset()
        if not cdart_url:
            #no cdart found
            xbmcgui.Dialog().ok( _(32033), _(32030), _(32031) )
            #Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            #return
        else:
            #xbmc.log( "[script.cdartmanager] - #  Building album list based on:", xbmc.LOGNOTICE )
            #xbmc.log( "[script.cdartmanager] - #        artist: %s     local_id: %s" % (cdart_url[0]["local_name"], cdart_url[0]["artistl_id"] ), xbmc.LOGNOTICE )
            local_album_list = get_local_albums_db( cdart_url[0]["local_name"] )
            cdart_img = ""
            label1 = ""
            label2 = ""
            album_list= {}
            #xbmc.log( local_album_list, xbmc.LOGNOTICE )
            for album in local_album_list:
                name = cdart_url[0]["artist"]
                musicbrainz_albumid = album["musicbrainz_albumid"]
                cdart = self.cdart_search( cdart_url, musicbrainz_albumid )
                #xbmc.log( album, xbmc.LOGNOTICE )
                #check to see if there is a thumb
                if cdart:
                    label1 = "%s * %s" % (album["artist"] , album["title"])
                    url = cdart[album["disc"]-1]["picture"]
                    #check to see if cdart already exists
                    # set the matched colour local and distant colour
                    #colour the label to the matched colour if not
                    if album["cdart"] == "TRUE":
                        cdart_img = os.path.join(album["path"], "cdart.png")
                        label2 = "%s&&%s&&&&%s" % (url, album["path"] , cdart_img)
                        label1 = "%s * %s     ***Local & fanart.tv cdART Exists***" % (album["artist"] , album["title"])
                        listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=(os.path.join(album["path"], "cdart.png")) )
                        self.getControl( 122 ).addItem( listitem )
                        listitem.setLabel( self.coloring( label1 , self.remotelocal_color , label1 ) )
                        listitem.setLabel2( label2 )                        
                    else :
                        label2 = "%s&&%s&&&&%s" % ( url, album["path"], "")
                        cdart_img=url
                        listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                        self.getControl( 122 ).addItem( listitem )
                        listitem.setLabel( self.coloring( label1 , self.remote_color , label1 ) )
                        listitem.setLabel2( label2 )
                    listitem.setThumbnailImage( cdart_img )                                   
                else :
                    url = ""
                    if album["cdart"] == "TRUE":
                        cdart_img = os.path.join(album["path"] , "cdart.png")
                        label2 = "%s&&%s&&&&%s" % (url, album["path"], cdart_img)
                        label1 = "%s * %s     ***Local only cdART Exists***" % (album["artist"] , album["title"])
                        listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                        self.getControl( 122 ).addItem( listitem )
                        listitem.setLabel( self.coloring( label1 , self.local_color , label1 ) )
                        listitem.setLabel2( label2 )
                        listitem.setThumbnailImage( cdart_img )
                    else:
                        label1 = "choose for %s * %s" % (album["artist"] , album["title"] )
                        cdart_img = ""
                        label2 = "%s&&%s&&&&%s" % (url, album["path"], cdart_img)
                        #xbmc.log( "[script.cdartmanager] - #  labe2: %s" % repr(label2), xbmc.LOGNOTICE )
                        listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                        self.getControl( 122 ).addItem( listitem )
                        listitem.setLabel( self.coloring( label1 , self.unmatched_color , label1 ) )
                        listitem.setLabel2( label2 )
                        listitem.setThumbnailImage( cdart_img )            
                self.cdart_url=cdart_url
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            self.setFocus( self.getControl( 122 ) )
            self.getControl( 122 ).selectItem( 0 )
        return
       
    #creates the artist list on the skin        
    def populate_artist_list( self, local_artist_list):
        xbmc.log( "[script.cdartmanager] - #  Populating Artist List", xbmc.LOGNOTICE )
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        try:
            for artist in local_artist_list:
                if not artist["distant_id"] == "":
                    listitem = xbmcgui.ListItem( label=self.coloring( artist["name"] , "green" , artist["name"] ) )
                    self.getControl( 120 ).addItem( listitem )
                    listitem.setLabel( self.coloring( artist["name"] , self.recognized_color , artist["name"] ) )
                else:
                    listitem = xbmcgui.ListItem( label=artist["name"] )
                    self.getControl( 120 ).addItem( listitem )
                    listitem.setLabel( self.coloring( artist["name"] , self.unrecognized_color , artist["name"] ) )
        except:
            print_exc()
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        self.setFocus( self.getControl( 120 ) )
        self.getControl( 120 ).selectItem( 0 )
        return
        
    def single_unique_copy(self, artist, album, source):
        xbmc.log( "[script.cdartmanager] - ### Copying to Unique Folder: %s - %s" % (artist,album) , xbmc.LOGNOTICE )
        destination = ""
        fn_format = int(__addon__.getSetting("folder"))
        unique_folder = __addon__.getSetting("unique_path")
        if unique_folder =="":
            __addon__.openSettings()
            unique_folder = __addon__.getSetting("unique_path")
        resize = __addon__.getSetting("enableresize")
        xbmc.log( "[script.cdartmanager] - #    Resize: %s" % resize, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    Unique Folder: %s" % unique_folder, xbmc.LOGNOTICE )
        if exists(source):
            xbmc.log( "[script.cdartmanager] - #    source: %s" % source, xbmc.LOGNOTICE )
            if fn_format == 0:
                destination=os.path.join(unique_folder, (artist.replace("/","")).replace("'","")) #to fix AC/DC
                fn = os.path.join(destination, ( ((album.replace("/","")).replace("'","")) + ".png"))
            else:
                destination=unique_folder
                fn = os.path.join(destination, ((((artist.replace("/", "")).replace("'","")) + " - " + ((album.replace("/","")).replace("'","")) + ".png").lower()))
            xbmc.log( "[script.cdartmanager] - #    destination: %s" % destination, xbmc.LOGNOTICE )
            if not exists(destination):
                #pass
                os.makedirs(destination)
            else:
                pass
            try:
                xbmc.log( "[script.cdartmanager] - #    Saving: %s" % fn, xbmc.LOGNOTICE )
                file_copy(source, fn)
            except:
                xbmc.log( "[script.cdartmanager] - #  Copying error, check path and file permissions", xbmc.LOGNOTICE )
        else:
            xbmc.log( "[script.cdartmanager] - #   Error: cdART file does not exist..  Please check...", xbmc.LOGNOTICE )
        return

    def single_backup_copy(self, artist, album, source):
        xbmc.log( "[script.cdartmanager] - ### Copying To Backup Folder: %s - %s" % (artist,album) , xbmc.LOGNOTICE )
        destination = ""
        fn_format = int(__addon__.getSetting("folder"))
        backup_folder = __addon__.getSetting("backup_path")
        if backup_folder =="":
            __addon__.openSettings()
            backup_folder = __addon__.getSetting("backup_path")
        xbmc.log( "[script.cdartmanager] - #    source: %s" % source, xbmc.LOGNOTICE )
        if exists(source):
            xbmc.log( "[script.cdartmanager] - #    source: %s" % source, xbmc.LOGNOTICE )
            if fn_format == 0:
                destination=os.path.join(backup_folder, (artist.replace("/","")).replace("'","")) #to fix AC/DC
                fn = os.path.join(destination, ( ((album.replace("/","")).replace("'","")) + ".png"))
            else:
                destination=backup_folder
                fn = os.path.join(destination, ((((artist.replace("/", "")).replace("'","")) + " - " + ((album.replace("/","")).replace("'","")) + ".png").lower()))
            xbmc.log( "[script.cdartmanager] - #    destination: %s" % destination, xbmc.LOGNOTICE )
            if not exists(destination):
                #pass
                os.makedirs(destination)
            else:
                pass
            xbmc.log( "[script.cdartmanager] - filename: %s" % fn, xbmc.LOGNOTICE )
            try:
                file_copy(source, fn)
            except:
                xbmc.log( "[script.cdartmanager] - #  Copying error, check path and file permissions", xbmc.LOGNOTICE )
        else:
            xbmc.log( "[script.cdartmanager] - #   Error: cdART file does not exist..  Please check...", xbmc.LOGNOTICE )
        return

    def single_cdart_delete(self, source, album):
        xbmc.log( "[script.cdartmanager] - ### Deleting: %s" % source, xbmc.LOGNOTICE )
        conn = sqlite3.connect(addon_db)
        c = conn.cursor()
        if exists(source):
            try:
                delete_file( source )
                c.execute("""UPDATE alblist SET cdart="FALSE" WHERE title='%s'""" % album)
                conn.commit()
            except:
                xbmc.log( "[script.cdartmanager] - #  Deleteing error, check path and file permissions", xbmc.LOGNOTICE )
        else:
            xbmc.log( "[script.cdartmanager] - #   Error: cdART file does not exist..  Please check...", xbmc.LOGNOTICE )
        c.close()
        return
    
    # Copy's all the local unique cdARTs to a folder specified by the user
    def unique_cdart_copy( self, unique ):
        xbmc.log( "[script.cdartmanager] - ### Copying Unique cdARTs...", xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #"        , xbmc.LOGNOTICE )
        percent = 0
        count = 0
        duplicates = 0
        destination = ""
        album = {}
        fn_format = int(__addon__.getSetting("folder"))
        unique_folder = __addon__.getSetting("unique_path")
        if unique_folder =="":
            __addon__.openSettings()
            unique_folder = __addon__.getSetting("unique_path")
        resize = __addon__.getSetting("enableresize")
        xbmc.log( "[script.cdartmanager] - #    Unique Folder: %s" % unique_folder, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    Resize: %s" % resize, xbmc.LOGNOTICE )
        pDialog.create( _(32060) )
        for album in unique:
            #xbmc.log( album, xbmc.LOGNOTICE )
            percent = int((count/len(unique))*100)
            xbmc.log( "[script.cdartmanager] - #    Artist: %-30s    ##    Album:%s" % (album["artist"], album["title"]), xbmc.LOGNOTICE )
            if (pDialog.iscanceled()):
                break
            if album["local"] == "TRUE" and album["distant"] == "FALSE":
                source=os.path.join(album["path"].replace("\\\\" , "\\"), "cdart.png")
                xbmc.log( "[script.cdartmanager] - #        Source: %s" % repr(source), xbmc.LOGNOTICE )
                if exists(source):
                    if fn_format == 0:
                        destination=os.path.join(unique_folder, (album["artist"].replace("/","")).replace("'","")) #to fix AC/DC
                        fn = os.path.join(destination, ( ((album["title"].replace("/","")).replace("'","")) + ".png"))
                    else:
                        destination=unique_folder
                        fn = os.path.join(destination, ((((album["artist"].replace("/", "")).replace("'","")) + " - " + ((album["title"].replace("/","")).replace("'","")) + ".png").lower()))
                    if not exists(destination):
                        #pass
                        os.makedirs(destination)
                    else:
                        pass
                    xbmc.log( "[script.cdartmanager] - #        Destination: %s" % repr(fn), xbmc.LOGNOTICE )
                    if exists(fn):
                        xbmc.log( "[script.cdartmanager] - ################## cdART Not being copied, File exists: %s" % repr(fn), xbmc.LOGNOTICE )
                        duplicates += 1
                    else:
                        try:
                            xbmc.log( "[script.cdartmanager] - #    Saving: %s" % repr(fn)                                    , xbmc.LOGNOTICE )
                            file_copy(source, fn)
                            conn = sqlite3.connect(addon_db)
                            c = conn.cursor()
                            c.execute("insert into unqlist(title, artist, path, cdart) values (?, ?, ?, ?)", ( unicode(album["title"], 'utf-8'), unicode(album["artist"], 'utf-8'), repr(album["path"]), album["local"]))
                            c.commit
                            count += 1
                        except:
                            xbmc.log( "[script.cdartmanager] - #  Copying error, check path and file permissions", xbmc.LOGNOTICE )
                            count += 1
                        c.close()
                        pDialog.update( percent, _(32064) % unique_folder , "Filename: %s" % fn, "%s: %s" % ( _(32056) , count ) )
                else:
                    xbmc.log( "[script.cdartmanager] - #   Error: cdART file does not exist..  Please check...", xbmc.LOGNOTICE )
            else:
                if album["local"] and album["distant"]:
                    xbmc.log( "[script.cdartmanager] - #        Local and Distant cdART exists", xbmc.LOGNOTICE )
                else:
                    xbmc.log( "[script.cdartmanager] - #        Local cdART does not exists", xbmc.LOGNOTICE )
        pDialog.close()
        xbmcgui.Dialog().ok( _(32057), "%s: %s" % ( _(32058), unique_folder), "%s %s" % ( count , _(32059)))
        # uncomment the next line when website is ready
        #self.compress_cdarts( unique_folder )
        return

    def restore_from_backup( self ):
        xbmc.log( "[script.cdartmanager] - ### Restoring cdARTs from backup folder", xbmc.LOGNOTICE )
        pDialog.create( _(32069) )
        #Onscreen Dialog - Restoring cdARTs from backup...
        bkup_folder = __addon__.getSetting("backup_path")
        if bkup_folder =="":
            __addon__.openSettings()
            bkup_folder = __addon__.getSetting("backup_path")
        else:
            pass
        self.copy_cdarts(bkup_folder)
        pDialog.close()
        
    def copy_cdarts( self, from_folder ): 
        xbmc.log( "[script.cdartmanager] - #  Copying cdARTs from: %s" % repr(from_folder), xbmc.LOGNOTICE )
        conn = sqlite3.connect(addon_db)
        c = conn.cursor()
        destination = ""
        source = ""
        fn = ""
        part = {}
        local_db = []
        percent = 0
        count = 0
        total_albums = 0 
        total_count = 0
        fn_format = int(__addon__.getSetting("folder"))
        pDialog.create( _(32069) )
        xbmc.log( "[script.cdartmanager] - #    Filename format: %s" % fn_format, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    From Folder: %s" % from_folder, xbmc.LOGNOTICE )
        local_db = get_local_albums_db("all artists")
        total_albums=len(local_db)
        xbmc.log( "[script.cdartmanager] - #    total albums: %s" % total_albums, xbmc.LOGNOTICE )
        #xbmc.log( "[script.cdartmanager] - #    albums: %s" % albums, xbmc.LOGNOTICE )
        for part in local_db:
            if (pDialog.iscanceled()):
                break
            xbmc.log( "[script.cdartmanager] - #     Artist: %-30s  ##  Album: %s" % (repr(part["artist"]), repr(part["title"])), xbmc.LOGNOTICE )
            xbmc.log( "[script.cdartmanager] - #        Album Path: %s" % repr(part["path"]), xbmc.LOGNOTICE )
            percent = int(total_count/float(total_albums))*100
            if fn_format == 0:
                source=os.path.join( from_folder, (part["artist"].replace("/","").replace("'","") ) )#to fix AC/DC and other artists with a / in the name
                fn = os.path.join(source, ( ( part["title"].replace("/","").replace("'","") ) + ".png") )
                if not exists(fn):
                    source=os.path.join( from_folder ) #to fix AC/DC
                    fn = os.path.join(source, ( ( ( part["artist"].replace("/", "").replace("'","") ) + " - " + ( part["title"].replace("/","").replace("'","") ) + ".png").lower() ) )
            else:
                source=os.path.join( from_folder ) #to fix AC/DC
                fn = os.path.join(source, ( ( ( part["artist"].replace("/", "").replace("'","") ) + " - " + ( part["title"].replace("/","").replace("'","") ) + ".png").lower() ) )
                if not exists(fn):
                    source=os.path.join( from_folder, (part["artist"].replace("/","").replace("'","") ) )#to fix AC/DC and other artists with a / in the name
                    fn = os.path.join(source, ( ( part["title"].replace("/","").replace("'","") ) + ".png") )
            xbmc.log( "[script.cdartmanager] - #        Source folder: %s" % repr(source), xbmc.LOGNOTICE )
            xbmc.log( "[script.cdartmanager] - #        Source filename: %s" % repr(fn), xbmc.LOGNOTICE )
            if exists(fn):
                destination = os.path.join(part["path"], "cdart.png")
                xbmc.log( "[script.cdartmanager] - #        Destination: %s" % repr(destination), xbmc.LOGNOTICE )
                try:
                    file_copy(fn, destination)
                    if not from_folder == __addon__.getSetting("backup_path"):
                        delete_file( fn )  # remove file
                    count += 1
                except:
                    xbmc.log( "[script.cdartmanager] - ######  Copying error, check path and file permissions", xbmc.LOGNOTICE )
                try:
                    c.execute("""UPDATE alblist SET cdart="TRUE" WHERE title='%s'""" % part["title"])
                except:
                    xbmc.log( "[script.cdartmanager] - ######  Problem modifying Database!!  Artist: %s   Album: %s" % (repr(part["artist"]), repr(part["title"])), xbmc.LOGNOTICE )
            else:
                pass
            pDialog.update( percent , "From Folder: %s" % from_folder, "Filename: %s" % fn, "%s: %s" % ( _(32056) , count ) )
            total_count += 1
        pDialog.close()
        conn.commit()
        c.close()
        xbmcgui.Dialog().ok( _(32057),  "%s %s" % ( count , _(32070) ) ) 
        return        
        
    # copy cdarts from music folder to temporary location
    # first step to copy to skin folder
    def cdart_copy( self ):
        xbmc.log( "[script.cdartmanager] - # Copying cdARTs to Backup folder", xbmc.LOGNOTICE )
        destination = ""
        duplicates = 0
        percent = 0
        count = 0
        total = 0
        album = {}
        albums = []
        fn_format = int(__addon__.getSetting("folder"))
        bkup_folder = __addon__.getSetting("backup_path")
        cdart_list_folder = __addon__.getSetting("cdart_path")
        if bkup_folder =="":
            __addon__.openSettings()
            bkup_folder = __addon__.getSetting("backup_path")
            cdart_list_folder = __addon__.getSetting("cdart_path")
        albums = get_local_albums_db("all artists")
        pDialog.create( _(32060) )
        for album in albums:
            if (pDialog.iscanceled()):
                break
            if album["cdart"] == "TRUE":
                source=os.path.join(album["path"].replace("\\\\" , "\\"), "cdart.png")
                xbmc.log( "[script.cdartmanager] - #     cdART #: %s" % count, xbmc.LOGNOTICE )
                xbmc.log( "[script.cdartmanager] - #     Artist: %-30s  Album: %s" % (repr(album["artist"]), repr(album["title"])), xbmc.LOGNOTICE )
                xbmc.log( "[script.cdartmanager] - #        Album Path: %s" % source, xbmc.LOGNOTICE )
                if exists(source):
                    if fn_format == 0:
                        destination=os.path.join( bkup_folder, ( album["artist"].replace("/","").replace("'","") ) ) #to fix AC/DC
                        fn = os.path.join( destination, ( ( album["title"].replace("/","").replace("'","") ) + ".png") )
                    elif fn_format == 1:
                        destination=os.path.join( bkup_folder ) #to fix AC/DC
                        fn = os.path.join( destination, (  ( album["artist"].replace("/", "").replace("'","") ) + " - " + ( album["title"].replace("/","").replace("'","") ) + ".png").lower())
                    xbmc.log( "[script.cdartmanager] - #        Destination Path: %s" % destination, xbmc.LOGNOTICE )
                    if not exists(destination):
                        os.makedirs(destination)
                    xbmc.log( "[script.cdartmanager] - #        Filename: %s" % fn, xbmc.LOGNOTICE )
                    if exists(fn):
                        xbmc.log( "[script.cdartmanager] - ################## cdART Not being copied, File exists: %s" % fn, xbmc.LOGNOTICE )
                        duplicates += 1
                    else:
                        try:
                            file_copy(source, fn)
                            count += 1
                            pDialog.update( percent , "backup folder: %s" % bkup_folder, "Filename: %s" % fn, "%s: %s" % ( _(32056) , count ) )
                        except:
                            xbmc.log( "[script.cdartmanager] - ######  Copying error, check path and file permissions", xbmc.LOGNOTICE )
                else:
                    xbmc.log( "[script.cdartmanager] - ######  Copying error, cdart.png does not exist", xbmc.LOGNOTICE )
            else:
                pass
            percent = int(total/float(len(albums))*100)
            total += 1
        pDialog.close()
        xbmc.log( "[script.cdartmanager] - #     Duplicate cdARTs: %s" % duplicates, xbmc.LOGNOTICE )
        xbmcgui.Dialog().ok( _(32057), "%s: %s" % ( _(32058), bkup_folder), "%s %s" % ( count , _(32059)), "%s Duplicates Found" % duplicates)
        return        
        
# Search for missing cdARTs and save to missing.txt in backup folder
    def missing_list( self ):
        xbmc.log( "[script.cdartmanager] - #    Saving Missing cdART list to backup folder", xbmc.LOGNOTICE )
        count = 0
        percent = 0
        line = ""
        albums = get_local_albums_db("all artists")
        bkup_folder = __addon__.getSetting("backup_path")
        pDialog.create( _(32103), _(20186) )
        if bkup_folder =="":
            __addon__.openSettings()
            bkup_folder = __addon__.getSetting("backup_path")
        filename=os.path.join(bkup_folder, "missing.txt")
        filename2 = os.path.join(addon_work_folder, "missing.txt")
        try:
            missing=open(filename, "wb")
            missing.write("Albums Missing cdARTs\n")
            missing.write("---------------------\n")
            missing.write("\n")
            for album in albums:
                count += 1
                if album["cdart"] == "FALSE":
                    artist = repr(album["artist"]) 
                    title = repr(album["title"])
                    line = artist + " * " + title + "\n"
                    missing.write( line )
            missing.close()
            missing=open(filename2, "wb")
            missing.write("Albums Missing cdARTs\n")
            missing.write("---------------------\n")
            missing.write("\n")
            for album in albums:
                count += 1
                if album["cdart"] == "FALSE":
                    artist = repr(album["artist"]) 
                    title = repr(album["title"])
                    line = artist + " * " + title + "\n"
                    missing.write( line )
            missing.close()
        except:
            xbmc.log( "[script.cdartmanager] - #### Error saving missing.txt file", xbmc.LOGNOTICE )
        pDialog.close()
        
    def upload_missing_list( self ):
        # Nothing here yet.
        # 
        # Here the script will upload the missing list stored in backup folder
        # and wait for a response from the website(a file) that will either initiate 
        # a batch download or a dialog stating that there are not any matches
        xbmc.log( "[script.cdartmanager] - #    Saving Missing cdART list to backup folder", xbmc.LOGNOTICE )
        count = 0
        percent = 0
        line = ""
        zip_filename = ""
        bkup_folder = __addon__.getSetting("backup_path")
        pDialog.create( _(32104), _(20186) )
        if bkup_folder =="":
            __addon__.openSettings()
            bkup_folder = __addon__.getSetting("backup_path")
        filename=os.path.join(addon_work_folder, "missing.txt")
        return zip_filename
        
    def download_from_website( self, zip_filename ):
        # Nothing really here yet
        #
        # Here the script will download the zip file that the website
        # will create which stores the cdARTs matching the missing.txt file
        # The file will be stored in addon_data/script.cdartmanager/temp
        # 
        # 
        zip_file = ""
        
    def extract_zip( self, filename ):
        # Here the script will extract the cdARTs store in the zip file downloaded from
        # the website and delete file after extraction is complete(no wasted space)
        # files will be stored in addon_data/script.cdartmanager/temp/extracted_cdarts
        xbmc.log( "[script.cdartmanager] - #  Decompressing unique cdARTs", xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #", xbmc.LOGNOTICE )
        source = os.path.join(addon_work_folder, 'filename')
        destination = os.path.join(addon_work_folder, 'temp')
        xbmc.log( "[script.cdartmanager] - #    Source: %s ", source, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    Destination: %s ", destination, xbmc.LOGNOTICE )
        output = tarfile.TarFile.open(destination, 'r:gz2')
        try:
            output = tarfile.TarFile.open(destination, 'r:gz2')
            try: 
                file.extractall()
            finally:
                file.close()
        except:
            xbmc.log( "[script.cdartmanager] - # Problem extracting file", xbmc.LOGNOTICE )
            
    def download_missing_cdarts( self ):
        # Nothing really here yet
        #
        # Here the script will call each of the steps for downloading the missing cdARTs
        # and extracting.  It will also recheck the local database and update counts for display
        local_album_count = 0
        local_artist_count = 0
        local_cdart_count = 0
        zip_file = ""
        zip_filename = ""
        zip_file=self.upload_missing_list()
        if zip_file == "":
            xbmc.log( "[script.cdartmanager] - # Sorry no matching cdARTs", xbmc.LOGNOTICE )
        else:
            zip_filename = os.path.join(download_temp_folder, zip_file)
            self.download_from_website(zip_filename)
            self.extract_zip(zip_filename)
            delete_file(zip_filename)
            extracted_cdarts_folder = os.path.join(download_temp_folder, "extracted_cdarts")
            self.copy_cdarts(extracted_cdarts_folder)
            # refresh local database
            delete_file(addon_db)
            local_album_count, local_artist_count, local_cdart_count = new_database_setup()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
            
    def upload_to_website( self ):
        # Nothing really here yet
        # 
        # open ftp and send a zip file to the website
        source = os.path.join(addon_work_folder, 'unique.tar.gz')
        cmd = "STOR unique.tar.gz"
        try:
            ftp_upload = FTP('192.168.2.9')
            ftp_upload.login('giftie61', 'gmracing')
            upload = open(source, 'rb')
            ftp_upload.storbinary(cmd, upload)
            upload.close()
            ftp_upload.close()
        except StandardError, e:
            xbmc.log( "[script.cdartmanager] - Error uploading file: %s" % e, xbmc.LOGNOTICE )

    def compress_cdarts( self, unique_folder ):
        xbmc.log( "[script.cdartmanager] - #  Compressing unique cdARTs", xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #"        , xbmc.LOGNOTICE )
        source = unique_folder
        destination = os.path.join(addon_work_folder, 'unique.tar.gz')
        xbmc.log( "[script.cdartmanager] - #    Source: %s " % source, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - #    Destination: %s " % destination, xbmc.LOGNOTICE )
        fileList = dirEntries(source, media_type="files", recursive="TRUE", contains="")
        try:
            output = tarfile.TarFile.open(destination, 'w:gz')
            for f in fileList:
                xbmc.log( "[script.cdartmanager] - archiving file %s" % (f), xbmc.LOGNOTICE )
                output.add(f)
            output.close()
            self.upload_to_website()
        except:
            xbmc.log( "[script.cdartmanager] - # Problem Compressing Unique cdARTs", xbmc.LOGNOTICE )
    
    def upload_unique_cdarts( self ):
        # Nothing really here yet
        # 
        # Here the script will call each step for uploading unique cdARTs
        zip_file = ""
        unique, difference = self.local_vs_distant()
        if difference == 1:
            self.unique_cdart_copy( unique )
            unique_folder = __addon__.getSetting("unique_path")
            zip_file = self.compress_cdarts( unique_folder )
            self.upload_to_website()
        else:
            xbmcgui.Dialog().ok( "There are no unique local cdARTs")        
        
    def setup_artist_list( self, artist ):
        xbmc.log( "[script.cdartmanager] - ##### Setting up artist list", xbmc.LOGNOTICE )
        self.artist_menu = {}
        self.artist_menu["local_id"] = str(artist[self.getControl( 120 ).getSelectedPosition()]["local_id"])
        self.artist_menu["name"] = str(artist[self.getControl( 120 ).getSelectedPosition()]["name"])
        self.artist_menu["distant_id"] = str(artist[self.getControl( 120 ).getSelectedPosition()]["distant_id"])
        self.populate_album_list( self.artist_menu )
                    
    def refresh_counts( self, local_album_count, local_artist_count, local_cdart_count ):
        xbmc.log( "[script.cdartmanager] - ##### Refreshing Counts", xbmc.LOGNOTICE )
        self.getControl( 109 ).setLabel( _(32007) % local_artist_count)
        self.getControl( 110 ).setLabel( _(32010) % local_album_count)
        self.getControl( 112 ).setLabel( _(32008) % local_cdart_count)
        self.missing_list()

    def populate_local_cdarts( self ):
        xbmc.log( "[script.cdartmanager] - ##### Populating Local cdARTS", xbmc.LOGNOTICE )
        label2= ""
        cdart_img=""
        url = ""
        work_temp = []
        l_artist = get_local_albums_db("all artists")
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        self.getControl( 140 ).reset()
        for album in l_artist:
            if album["cdart"] == "TRUE":
                cdart_img = os.path.join(album["path"], "cdart.png")
                label2 = "%s&&%s&&&&%s" % (url, album["path"], cdart_img)
                label1 = "%s * %s" % (album["artist"] , album["title"])
                listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                self.getControl( 140 ).addItem( listitem )
                listitem.setLabel( self.coloring( label1 , "orange" , label1 ) )
                listitem.setLabel2( label2 )
                work_temp.append(album)
                #xbmc.log( label2, xbmc.LOGNOTICE )
            else:
                pass
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        self.setFocus( self.getControl( 140 ) )
        self.getControl( 140 ).selectItem( 0 )
        return work_temp
  
    # This selects which cdART image shows up in the display box (image id 210) 
    def cdart_icon( self ):
        #xbmc.log( "[script.cdartmanager] - # Displaying cdART icon", xbmc.LOGNOTICE )
        try:   # If there is information in label 2 of list id 122(album list)
            local_cdart = ""
            url = ""
            cdart_path ={}
            local_cdart = (self.getControl(122).getSelectedItem().getLabel2()).split("&&&&")[1]
            url = ((self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[1]
            cdart_path["path"] = ((self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[0]
            #xbmc.log( "[script.cdartmanager] - # cdART url: %s" % repr(url), xbmc.LOGNOTICE )
            #xbmc.log( "[script.cdartmanager] - # cdART path: %s" % repr(cdart_path["path"]), xbmc.LOGNOTICE )
            if not local_cdart == "": #Test to see if there is a path in local_cdart
                image = (local_cdart.replace("\\\\" , "\\"))
                self.getControl( 210 ).setImage( image )
            else:
                if not cdart_path["path"] =="": #Test to see if there is an url in cdart_path["path"]
                    image = (cdart_path["path"].replace("\\\\" , "\\"))
                    self.getControl( 210 ).setImage( image )
                else:
                    image =""                    
        except:  
            try: # If there is information in label 2 of list id 140(local album list)
                local_cdart = (self.getControl(140).getSelectedItem().getLabel2()).split("&&&&")[1]
                url = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[1]
                cdart_path["path"] = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[0]
                xbmc.log( "[script.cdartmanager] - # cdART url: %s" % url, xbmc.LOGNOTICE )
                xbmc.log( "[script.cdartmanager] - # cdART path: %s" % cdart_path["path"], xbmc.LOGNOTICE )
                if not local_cdart == "": #Test to see if there is a path in local_cdart
                    image = (local_cdart.replace("\\\\" , "\\"))
                    self.getControl( 210 ).setImage( image )
                else:
                    if not cdart_path["path"] =="": #Test to see if there is an url in cdart_path["path"]
                        image = (cdart_path["path"].replace("\\\\" , "\\"))
                        self.getControl( 210 ).setImage( image )
                    else:
                        image =""
                        #image = addon_img
            
            except: # If there is not any information in any of those locations, no image.
                image =""
                #image=addon_img
        self.getControl( 210 ).setImage( image )

    def popup(self, header, line1, line2, line3):        
        #self.getControl( 400 ).setLabel( header )
        #self.getControl( 150 ).setLabel( line1 )
        #self.getControl( 151 ).setLabel( line2 )
        #self.getControl( 152 ).setLabel( line3 )
        #self.getControl( 9012 ).setVisible( True )
        pDialog.create( header, line1, line2, line3 )
        xbmc.sleep(2000)
        pDialog.close()
        #self.getControl( 9012 ).setVisible( False ) 

    # setup self. strings and initial local counts
    def setup_all( self ):
        xbmc.log( "[script.cdartmanager] - # Setting up Script", xbmc.LOGNOTICE )
        self.menu_mode = 0
        self.artist_menu = {}
        self.remote_cdart_url =[]
        self.recognized_artists = []
        self.all_artists = []
        self.cdart_url = []
        self.local_artists = []
        self.label_1 = ""
        self.label_2 = addon_img
        self.cdartimg = ""
        listitem = xbmcgui.ListItem( label=self.label_1, label2=self.label_2, thumbnailImage=self.cdartimg )
        self.getControl( 122 ).addItem( listitem )
        listitem.setLabel2(self.label_2)
        #checking to see if addon_db exists, if not, run database_setup()
        if exists( (addon_db).replace("\\\\" , "\\").encode("utf-8") ):
            xbmc.log( "[script.cdartmanager] - Addon Db found - Loading Counts", xbmc.LOGNOTICE )
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
        else:
            xbmc.log( "[script.cdartmanager] - Addon Db Not Found - Building New Addon Db", xbmc.LOGNOTICE )
            local_album_count, local_artist_count, local_cdart_count = new_database_setup()
        self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        self.local_artists = get_local_artists_db() # retrieve data from addon's database
        self.setFocusId( 100 ) # set menu selection to the first option(Search Artists)

    def onClick( self, controlId ):
        #xbmc.log( "[script.cdartmanager] - Control ID: %s " % controlId, xbmc.LOGNOTICE )
        if controlId == 102 : #Automatic Download
            self.menu_mode = 3
            download_count = auto_download()
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        if controlId in [105, 106]: #Get Artists List
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            self.getControl( 120 ).reset()
            distant_artist = get_distant_artists()
            #xbmc.log( "[script.cdartmanager] - Distant Artists:", xbmc.LOGNOTICE )
            #xbmc.log( distant_artist, xbmc.LOGNOTICE )
            local_artists = get_local_artists_db()
            if distant_artist:
                self.recognized_artists, self.local_artists = get_recognized( distant_artist , local_artists )
        if controlId == 105 : #Recognized Artists
            self.menu_mode = 1
            #print self.recognized_artists
            self.populate_artist_list( self.recognized_artists )
        if controlId == 106 : #All Artists
            self.menu_mode = 2
            #print self.local_artists
            self.populate_artist_list( self.local_artists )   
        if controlId == 120 : #Retrieving information from Artists List
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            if self.menu_mode == 1: #information pulled from recognized list
                self.artist_menu = {}
                self.artist_menu["local_id"] = str(self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["local_id"])
                self.artist_menu["name"] = str(self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["name"])
                self.artist_menu["musicbrainz_artistid"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["musicbrainz_artistid"])
                self.artist_menu["distant_id"] = str(self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["distant_id"])
                #xbmc.log( "[script.cdartmanager] - # %s" % self.artist_menu, xbmc.LOGNOTICE )
                #xbmc.log( artist_menu, xbmc.LOGNOTICE )
            elif self.menu_mode == 2: #information pulled from All Artist List
                self.artist_menu = {}
                self.artist_menu["local_id"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["local_id"])
                xbmc.log( self.artist_menu["local_id"], xbmc.LOGNOTICE )
                self.artist_menu["name"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["name"])
                xbmc.log( self.artist_menu["name"], xbmc.LOGNOTICE )
                self.artist_menu["musicbrainz_artistid"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["musicbrainz_artistid"])
                xbmc.log( self.artist_menu["musicbrainz_artistid"], xbmc.LOGNOTICE )
                self.artist_menu["distant_id"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["distant_id"])
                xbmc.log( self.artist_menu["distant_id"], xbmc.LOGNOTICE )
            if not self.artist_menu["musicbrainz_artistid"]:
                self.artist_menu["musicbrainz_artistid"] = update_musicbrainzid( "artist", self.artist_menu )
            xbmc.log( "[script.cdartmanager] - # %s" % self.artist_menu, xbmc.LOGNOTICE )
            self.remote_cdart_url = self.remote_cdart_list( self.artist_menu )
            #xbmc.log( artist_menu, xbmc.LOGNOTICE )
            self.populate_album_list( self.artist_menu, self.remote_cdart_url )
        if controlId == 122 : #Retrieving information from Album List
            #xbmc.log( "[script.cdartmanager] - #  Setting up Album List", xbmc.LOGNOTICE )
            self.getControl( 140 ).reset()
            select = None
            local = ""
            url = ""
            album = {}
            album_search=[]
            album_selection=[]
            cdart_path = {}
            local_cdart = ""
            count = 0
            select=0
            local_cdart = (self.getControl(122).getSelectedItem().getLabel2()).split("&&&&")[1]
            url = ((self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[0]
            cdart_path["path"] = ((self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[1]
            local = (self.getControl( 122 ).getSelectedItem().getLabel()).replace("choose for ", "")
            cdart_path["artist"]=local.split(" * ")[0]
            cdart_path["title"]=(((local.split(" * ")[1]).replace("     ***Local & fanart.tv cdART Exists***","")).replace("     ***Local only cdART Exists***",""))
            cdart_path["title"]= self.remove_color(cdart_path["title"])
            #xbmc.log( "[script.cdartmanager] - #   artist: %s" % cdart_path["artist"], xbmc.LOGNOTICE )
            #xbmc.log( "[script.cdartmanager] - #   album title: %s" % cdart_path["title"], xbmc.LOGNOTICE )
            #xbmc.log( "[script.cdartmanager] - #   cdart_path: %s" % cdart_path["path"], xbmc.LOGNOTICE )
            #xbmc.log( "[script.cdartmanager] - #   url: %s" % url, xbmc.LOGNOTICE )
            #xbmc.log( "[script.cdartmanager] - #   local_cdart: %s" % local_cdart, xbmc.LOGNOTICE )
            if not url =="" : # If it is a recognized Album...
                message, d_success = download_cdart( url, cdart_path )
                xbmcgui.Dialog().ok(message[0] ,message[1] ,message[2] ,message[3])
                pDialog.close()
            else : # If it is not a recognized Album...
                for elem in self.cdart_url:
                    album["search_name"] = elem["title"]
                    album["search_url"] = elem["picture"]
                    album_search.append(album["search_name"])
                    album_selection.append(album["search_url"])
                select = xbmcgui.Dialog().select( _(32022), album_search)
                #xbmc.log( select, xbmc.LOGNOTICE )
                if not select == -1:
                    cdart_url = album_selection[select]
                    message, d_success = download_cdart( cdart_url, cdart_path )
                    xbmcgui.Dialog().ok(message[0] ,message[1] ,message[2] ,message[3])
                    pDialog.close()
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
            self.populate_album_list( self.artist_menu, self.remote_cdart_url )
        if controlId == 132 : #Clean Music database selected from Advanced Menu
            xbmc.log( "[script.cdartmanager] - #  Executing Built-in - CleanLibrary(music)", xbmc.LOGNOTICE )
            xbmc.executebuiltin( "CleanLibrary(music)") 
        if controlId == 133 : #Update Music database selected from Advanced Menu
            xbmc.log( "[script.cdartmanager] - #  Executing Built-in - UpdateLibrary(music)", xbmc.LOGNOTICE )
            xbmc.executebuiltin( "UpdateLibrary(music)")
        if controlId == 135 : #Back up cdART selected from Advanced Menu
            self.cdart_copy()
        if controlId == 134 : #Copy Unique Local cdART selected from Advanced Menu
            unique, difference = self.local_vs_distant()
            if difference == 1:
                self.unique_cdart_copy( unique )
            else:
                xbmcgui.Dialog().ok( "There are no unique local cdARTs")
        if controlId == 131 : #Refresh Local database selected from Advanced Menu
            refresh_db()
            pDialog.close()
        if controlId == 136 : #Restore from Backup
            self.restore_from_backup()
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        if controlId == 137 : #Local cdART List
            self.getControl( 122 ).reset()
            self.populate_local_cdarts()
        if controlId == 104 : #Settings
            self.menu_mode = 5
            __addon__.openSettings()
            self.setup_colors()
        if controlId == 111 : #Exit
            self.menu_mode = 0
            self.close()
        if controlId == 107 :
            self.setFocusId( 200 )
        if controlId == 108 :
            self.setFocusId( 200 ) 
        if controlId == 130 : #cdART Backup Menu
            self.setFocusId( 135 )
        if controlId == 140 : #Local cdART selection
            self.cdart_icon()
            self.setFocusId( 142 )
            artist_album = self.getControl(140).getSelectedItem().getLabel()
            artist_album = self.remove_color(artist_album)
            artist = artist_album.split(" * ")[0]
            album_title = artist_album.split(" * ")[1]
            #xbmc.log( "[script.cdartmanager] - # Album: %s" % album_title, xbmc.LOGNOTICE )
            #xbmc.log( "[script.cdartmanager] - # Artist: %s" % artist, xbmc.LOGNOTICE )
            self.getControl( 300 ).setLabel( self.getControl(140).getSelectedItem().getLabel() )
        if controlId == 143 : #Delete cdART
            path = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[1])
            artist_album = self.getControl(140).getSelectedItem().getLabel()
            artist_album = self.remove_color(artist_album)
            artist = artist_album.split(" * ")[0]
            album_title = artist_album.split(" * ")[1]
            #xbmc.log( "[script.cdartmanager] - # Path: %s" % path, xbmc.LOGNOTICE )
            #xbmc.log( "[script.cdartmanager] - # Album: %s" % album_title, xbmc.LOGNOTICE )
            self.single_cdart_delete( path, album_title )
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
            self.popup( _(32075), self.getControl(140).getSelectedItem().getLabel(),"", "")
            self.setFocusId( 140 )            
            self.populate_local_cdarts()
        if controlId == 142 : #Backup to backup folder
            artist_album = self.getControl(140).getSelectedItem().getLabel()
            artist_album = self.remove_color(artist_album)
            artist = artist_album.split(" * ")[0]
            album_title = artist_album.split(" * ")[1]
            path = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[1])
            #xbmc.log( "[script.cdartmanager] - # Album: %s" % album_title, xbmc.LOGNOTICE )
            #xbmc.log( "[script.cdartmanager] - # Artist: %s" % artist, xbmc.LOGNOTICE )
            self.single_backup_copy( artist, album_title, path )
            self.popup(_(32074),self.getControl(140).getSelectedItem().getLabel(), "", path)
            self.setFocusId( 140 )
            self.populate_local_cdarts()
        if controlId == 144 : #Copy to Unique folder
            artist_album = self.getControl(140).getSelectedItem().getLabel()
            artist_album = self.remove_color(artist_album)
            artist = artist_album.split(" * ")[0]
            album_title = artist_album.split(" * ")[1]
            path = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[1])
            #xbmc.log( "[script.cdartmanager] - # Album: %s" % album_title, xbmc.LOGNOTICE )
            #xbmc.log( "[script.cdartmanager] - # Artist: %s" % artist, xbmc.LOGNOTICE )
            self.single_unique_copy( artist, album_title, path )
            self.popup(_(32076),self.getControl(140).getSelectedItem().getLabel(), "", path)
            self.setFocusId( 140 )
            self.populate_local_cdarts()
        if controlId == 100 : #Search Artist
            self.setFocusId( 105 )
        if controlId == 103 : #Advanced
            self.setFocusId( 130 )
            	

    def onFocus( self, controlId ):
        if controlId == 122 or controlId == 140:
            self.cdart_icon()
            
        	
    def onAction( self, action ):
        self.cdart_icon()
        buttonCode =  action.getButtonCode()
        actionID   =  action.getId()
        #xbmc.log( "[script.cdartmanager] - onAction(): actionID=%i buttonCode=%i" % (actionID,buttonCode), xbmc.LOGNOTICE )
        if (buttonCode == KEY_BUTTON_BACK or buttonCode == KEY_KEYBOARD_ESC):
            self.close()
        if actionID == 10:
            xbmc.log( "[script.cdartmanager] - Closing", xbmc.LOGNOTICE )
            try:
                pDialog.close()
            except:
                pass
            self.close()
   
def onAction( self, action ):
    #xbmc.log( action, xbmc.LOGNOTICE )
    if (buttonCode == KEY_BUTTON_BACK or buttonCode == KEY_KEYBOARD_ESC):
            self.close()
    if ( action.getButtonCode() in CANCEL_DIALOG ):
	    xbmc.log( "[script.cdartmanager] - # Closing", xbmc.LOGNOTICE )
	    self.close()
