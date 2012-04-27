# -*- coding: utf-8 -*-

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
    
# pull information from default.py
_                 = sys.modules[ "__main__" ].__language__
__scriptname__    = sys.modules[ "__main__" ].__scriptname__
__scriptID__      = sys.modules[ "__main__" ].__scriptID__
__author__        = sys.modules[ "__main__" ].__author__
__credits__       = sys.modules[ "__main__" ].__credits__
__credits2__      = sys.modules[ "__main__" ].__credits2__
__version__       = sys.modules[ "__main__" ].__version__
__addon__         = sys.modules[ "__main__" ].__addon__
__dbversion__     = sys.modules[ "__main__" ].__dbversion__
addon_db          = sys.modules[ "__main__" ].addon_db
addon_db_backup   = sys.modules[ "__main__" ].addon_db_backup
addon_work_folder = sys.modules[ "__main__" ].addon_work_folder
__useragent__     = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"
image             = sys.modules[ "__main__" ].image

#time socket out at 30 seconds
socket.setdefaulttimeout(30)

KEY_BUTTON_BACK  = 275
KEY_KEYBOARD_ESC = 61467

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo( 'path' ), 'resources' ) )
skin_art_path      = os.path.join( BASE_RESOURCE_PATH, "skins", "Default", "media" )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

from convert import set_entity_or_charref
from folder import dirEntries
from fanarttv_scraper import get_distant_artists, retrieve_fanarttv_xml, get_recognized, remote_cdart_list, remote_fanart_list, remote_clearlogo_list, remote_coverart_list
from utils import get_html_source, clear_image_cache, empty_tempxml_folder, get_unicode
from download import download_art, auto_download
from database import backup_database, store_alblist, store_lalist, retrieve_distinct_album_artists, store_counts, new_database_setup, get_local_albums_db, get_local_artists_db, new_local_count, refresh_db, artwork_search, update_database
from musicbrainz_utils import get_musicbrainz_artist_id, get_musicbrainz_album, update_musicbrainzid
from file_item import Thumbnails

#variables
download_temp_folder = os.path.join( addon_work_folder, "temp" )
addon_image_path     = os.path.join( BASE_RESOURCE_PATH, "skins", "Default", "media")
addon_img            = os.path.join( addon_image_path, "cdart-icon.png" )
missing_cdart_image  = os.path.join( addon_image_path, "missing_cdart.png" )
missing_cover_image  = os.path.join( addon_image_path, "missing_cover.png" )
pDialog              = xbmcgui.DialogProgress()
safe_db_version      = __dbversion__

from pre_eden_code import get_all_local_artists, retrieve_album_list, retrieve_album_details, get_album_path
from xbmcvfs import delete as delete_file
from xbmcvfs import exists as exists
from xbmcvfs import copy as file_copy

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
            print_exc()
            try:
                pDialog.close()
            except:
                pass            

    def retrieve_settings( self ):
        backup_path  = __addon__.getSetting( "backup_path" )
        unique_path  = __addon__.getSetting( "unique_path" )
        enableresize = __addon__.getSetting( "enableresize" )
        folder       = __addon__.getSetting( "folder" )
        enablecustom = __addon__.getSetting( "enablecustom" )
        xbmc.log( "[script.cdartmanager] - # Settings                                                 #", xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #                                                          #", xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Backup Folder: %-35s    #" % backup_path, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Unique Folder: %-35s    #" % unique_path, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Resize Enabled: %-34s    #" % enableresize, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Saving format: %-35s    #" % folder, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #    Enable Custom Colours: %-27s    #" % enablecustom, xbmc.LOGDEBUG )
        xbmc.log( "[script.cdartmanager] - #                                                          #", xbmc.LOGDEBUG )
        
    def setup_colors( self ):
        if __addon__.getSetting( "enablecustom" ) == "true":
            self.recognized_color   = str.lower( __addon__.getSetting( "recognized" ) )
            self.unrecognized_color = str.lower( __addon__.getSetting( "unrecognized" ) )
            self.remote_color       = str.lower( __addon__.getSetting( "remote" ) )
            self.local_color        = str.lower( __addon__.getSetting( "local" ) )
            self.remotelocal_color  = str.lower( __addon__.getSetting( "remotelocal" ) )
            self.unmatched_color    = str.lower( __addon__.getSetting( "unmatched" ) )
            self.localcdart_color   = str.lower( __addon__.getSetting( "localcdart" ) )
        else:
            self.recognized_color   = "green"
            self.unrecognized_color = "white"
            self.remote_color       = "green"
            self.local_color        = "orange"
            self.remotelocal_color  = "yellow"
            self.unmatched_color    = "white"
            self.localcdart_color   = "orange"
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
            color = "FFFFFFFF"
        if color == "blue":
            color = "FF0000FF"
        if color == "cyan":
            color = "FF00FFFF"
        if color == "violet":
            color = "FFEE82EE"
        if color == "pink":
            color = "FFFF1493"
        if color == "red":
            color = "FFFF0000"
        if color == "green":
            color = "FF00FF00"
        if color == "yellow":
            color = "FFFFFF00"
        if color == "orange":
            color = "FFFF4500"
        colored_text = text.replace( colorword , "[COLOR=%s]%s[/COLOR]" % ( color , colorword ) )
        return colored_text

    def remove_color( self, text ):
        clean_text = text.replace( "[/COLOR]","" ).replace( "[COLOR=FFFFFFFF]","" ).replace( "[COLOR=FF0000FF]","" ).replace( "[COLOR=FF00FFFF]","" ).replace( "[COLOR=FFEE82EE]","" ).replace( "[COLOR=FFFF1493]","" ).replace( "[COLOR=FFFF0000]","" ).replace( "[COLOR=FF00FF00]","" ).replace( "[COLOR=FFFFFF00]","" ).replace( "[COLOR=FFFF4500]","" )
        return clean_text

    #Local vs. XBMCSTUFF.COM cdART list maker
    def local_vs_distant( self ):
        xbmc.log( "[script.cdartmanager] - Local vs. FanArt.TV cdART", xbmc.LOGNOTICE )
        pDialog.create( _(32065) )
        #xbmc.sleep( 1000 )
        #Onscreen Dialog - Comparing Local and Online cdARTs...
        local_count = 0
        distant_count = 0
        cdart_difference = 0
        album_count = 0
        artist_count = 0
        temp_album = {}
        cdart_lvd = []
        local_artist = get_local_artists_db()
        count_artist_local = len( local_artist )
        for artist in local_artist:
            artist_count += 1
            percent = int( ( artist_count / float( count_artist_local ) ) * 100 )
            xbmc.log( "[script.cdartmanager] - Artist: %-40s Local ID: %s" % ( repr( artist["name"] ), artist["local_id"] ), xbmc.LOGNOTICE )
            local_album_list = get_local_albums_db( artist["name"], self.background )
            for album in local_album_list:
                temp_album = {}
                album_count += 1
                temp_album["artist"] = artist["name"]
                temp_album["title"] = album["title"]
                temp_album["path"] = album["path"]
                name = artist["name"]
                title = album["title"]
                pDialog.update( percent , "%s%s" % ( _(32038) , repr( artist["name"] ) )  , "%s%s" % ( _(32039) , repr( album["title"] ) ) )
                test_album = self.find_cdart2( name , title )
                xbmc.log( "[script.cdartmanager] - Album: %s" % repr( album["title"] ), xbmc.LOGNOTICE )
                if not test_album == [] : 
                    xbmc.log( "[script.cdartmanager] - ALBUM MATCH FOUND", xbmc.LOGNOTICE )
                    temp_album["distant"] = True
                    distant_count += 1
                    if album["cdart"] == True :
                        temp_album["local"] = True
                        local_count += 1
                        xbmc.log( "[script.cdartmanager] - Local & Distant cdART image exists...", xbmc.LOGNOTICE )
                    else:
                        temp_album["local"] = False
                        xbmc.log( "[script.cdartmanager] - No local cdART image exists", xbmc.LOGNOTICE )
                else :
                    xbmc.log( "[script.cdartmanager] - ALBUM MATCH NOT FOUND", xbmc.LOGNOTICE )
                    temp_album["distant"] = False
                    if album["cdart"] == False :
                        local_count += 1
                        temp_album["local"] = True
                        xbmc.log( "[script.cdartmanager] - Local cdART image exists...", xbmc.LOGNOTICE )
                    else:
                        temp_album["local"] = False
                        xbmc.log( "[script.cdartmanager] - No local cdART image exists", xbmc.LOGNOTICE )
                cdart_lvd.append(temp_album)
                #xbmc.log( temp_album, xbmc.LOGNOTICE )
                #xbmc.log( cdart_lvd                , xbmc.LOGNOTICE )
                if ( pDialog.iscanceled() ):
                    break
            if ( pDialog.iscanceled() ):
                    break    
        pDialog.close()
        if (local_count - distant_count) > 0:
            xbmcgui.Dialog().ok( "There are %s cdARTs that only exist locally" % ( local_count - distant_count ), "Local cdARTs: %s" % local_count, "Distant cdARTs: %s" % distant_count )
            difference = 1
        else:
            xbmcgui.Dialog().ok( "There are %s new cdARTs on FanArt.TV" % ( distant_count - local_count ), "Local cdARTs: %s" % local_count, "Distant cdARTs: %s" % distant_count )
            differnece = 0
        return cdart_lvd, difference

    #creates the album list on the skin
    def populate_album_list( self, artist_menu, art_url, focus_item, type ):
        xbmc.log( "[script.cdartmanager] - Populating Album List", xbmc.LOGNOTICE )
        self.getControl( 122 ).reset()
        if not art_url:
            #no cdart found
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            xbmcgui.Window(10001).clearProperty( "artwork" )
            xbmcgui.Dialog().ok( _(32033), _(32030), _(32031) )
            #Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
            #return
        else:
            local_album_list = get_local_albums_db( art_url[0]["local_name"], self.background )
            label1 = ""
            label2 = ""
            album_list= {}
            xbmc.log( "[script.cdartmanager] - Building album list", xbmc.LOGNOTICE )
            empty_list = False
            check = False
            try:
                for album in local_album_list:
                    if type == "cdart":
                        art_image = missing_cdart_image
                        filename = "cdart.png"
                    else:
                        art_image = missing_cover_image
                        filename = "folder.jpg"
                    empty_list = False
                    if album["disc"] > 1:
                        label1 = "%s - %s %s" % ( album["title"], _(32016), album["disc"] )
                    else:
                        label1 = album["title"]
                    name = art_url[0]["artist"]
                    musicbrainz_albumid = album["musicbrainz_albumid"]
                    if not musicbrainz_albumid:
                        empty_list = True
                        continue
                    else:
                        check = True
                    #check to see if there is a thumb
                    artwork = artwork_search( art_url, musicbrainz_albumid, album["disc"], type )
                    if not artwork:
                        temp_path = os.path.join( album["path"], filename ).replace( "\\\\", "\\" )
                        if exists( temp_path ):
                            url = art_image = temp_path
                            color = self.local_color
                        else:
                            url = art_image
                            color = self.unrecognized_color
                    else:
                        if artwork["picture"]:
                            #check to see if artwork already exists
                            # set the matched colour local and distant colour
                            #colour the label to the matched colour if not
                            url = artwork["picture"]
                            if album[type]:
                                art_image = os.path.join( album["path"], filename ).replace( "\\\\", "\\" )
                                color = self.remotelocal_color
                            else:
                                art_image=url
                                color = self.remote_color                          
                        else:
                            url = ""
                            if album[type]:
                                art_image = os.path.join( album["path"], filename ).replace( "\\\\", "\\" )
                                color = self.local_color
                            else:
                                art_image = url
                                color = self.unmatched_color
                    label2 = "%s&&%s&&&&%s" % (url, album["path"] , art_image)
                    listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage = art_image )
                    self.getControl( 122 ).addItem( listitem )
                    listitem.setLabel( self.coloring( label1 , color , label1 ) )
                    listitem.setLabel2( label2 )                        
                    listitem.setThumbnailImage( art_image )            
                    self.cdart_url = art_url
                    clear_image_cache( art_image )
            except:
                print_exc()
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            if ( not empty_list ) or check:
                self.setFocus( self.getControl( 122 ) )
                self.getControl( 122 ).selectItem( focus_item )
            else:
                xbmcgui.Window(10001).clearProperty( "artwork" )
                xbmcgui.Dialog().ok( _(32033), _(32030), _(32031) )
                #Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
        return
       
    #creates the artist list on the skin        
    def populate_artist_list( self, local_artist_list):
        xbmc.log( "[script.cdartmanager] - Populating Artist List", xbmc.LOGNOTICE )
        if not local_artist_list:
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            return
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

    def populate_fanarts( self, artist_menu, focus_item ):
        xbmc.log( "[script.cdartmanager] - Populating Fanart List", xbmc.LOGNOTICE )
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        self.getControl( 160 ).reset()
        try:
            fanart = remote_fanart_list( artist_menu )
            if fanart:
                for artwork in fanart:
                    listitem = xbmcgui.ListItem( label = os.path.basename( artwork ), label2 = artist_menu["name"] + "&&&&" + artwork, thumbnailImage = artwork + "/preview" )
                    self.getControl( 160 ).addItem( listitem )
                    listitem.setLabel( os.path.basename( artwork ) )
                    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
                    self.setFocus( self.getControl( 160 ) )
                    self.getControl( 160 ).selectItem( focus_item )
            else:
                xbmc.log( "[script.cdartmanager - No Fanart for this artist", xbmc.LOGNOTICE )
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )
                xbmcgui.Window(10001).clearProperty( "artwork" )
                xbmcgui.Dialog().ok( _(32033), _(32030), _(32031) )
                #Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
                return
        except:
            print_exc()
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        
    def populate_clearlogos( self, artist_menu, focus_item ):
        xbmc.log( "[script.cdartmanager] - Populating ClearLOGO List", xbmc.LOGNOTICE )
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        self.getControl( 167 ).reset()
        try:
            clearlogo = remote_clearlogo_list( artist_menu )
            if clearlogo:
                for artwork in clearlogo:
                    clear_image_cache( artwork )
                    listitem = xbmcgui.ListItem( label = os.path.basename( artwork ), label2 = artist_menu["name"] + "&&&&" + artwork, thumbnailImage = artwork + "/preview" )
                    self.getControl( 167 ).addItem( listitem )
                    listitem.setLabel( os.path.basename( artwork ) )
                    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
                    self.setFocus( self.getControl( 167 ) )
                    self.getControl( 167 ).selectItem( focus_item )
            else:
                xbmc.log( "[script.cdartmanager - No ClearLOGO for this artist", xbmc.LOGNOTICE )
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )
                xbmcgui.Window(10001).clearProperty( "artwork" )
                xbmcgui.Dialog().ok( _(32033), _(32030), _(32031) )
                #Onscreen Dialog - Not Found on Fanart.tv, Please contribute! Upload your cdARTs, On fanart.tv
                return
        except:
            print_exc()
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )

    def populate_downloaded( self, successfully_downloaded, type ):
        xbmc.log( "[script.cdartmanager] - Populating ClearLOGO List", xbmc.LOGNOTICE )
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        self.getControl( 404 ).reset()
        xbmcgui.Window(10001).setProperty( "artwork", type )
        for item in successfully_downloaded:
            try:
                try:
                    listitem = xbmcgui.ListItem( label = item["artist"], label2 = item["title"], thumbnailImage = item["path"] )
                except:
                    listitem = xbmcgui.ListItem( label = item["artist"], label2 = "", thumbnailImage = item["path"] )
                self.getControl( 404 ).addItem( listitem )
                listitem.setLabel( item["artist"] )
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )
                self.setFocus( self.getControl( 404 ) )
                self.getControl( 404 ).selectItem( 0 )
            except:
                print_exc()
                xbmc.executebuiltin( "Dialog.Close(busydialog)" )

    def populate_local_cdarts( self, focus_item ):
        xbmc.log( "[script.cdartmanager] - Populating Local cdARTS", xbmc.LOGNOTICE )
        label2= ""
        cdart_img=""
        url = ""
        work_temp = []
        l_artist = get_local_albums_db( "all artists", self.background )
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        self.getControl( 140 ).reset()
        for album in l_artist:
            if album["cdart"]:
                cdart_img = os.path.join( album["path"], "cdart.png" )
                label2 = "%s&&%s&&&&%s" % ( url, album["path"], cdart_img )
                label1 = "%s * %s" % ( album["artist"] , album["title"] )
                listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                self.getControl( 140 ).addItem( listitem )
                listitem.setLabel( self.coloring( label1 , "orange" , label1 ) )
                listitem.setLabel2( label2 )
                work_temp.append( album )
            else:
                pass
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        self.setFocus( self.getControl( 140 ) )
        self.getControl( 140 ).selectItem( focus_item )
        return work_temp

    def single_unique_copy(self, artist, album, source):
        xbmc.log( "[script.cdartmanager] - Copying to Unique Folder: %s - %s" % (artist,album) , xbmc.LOGNOTICE )
        destination = ""
        fn_format = int( __addon__.getSetting( "folder" ) )
        unique_folder = __addon__.getSetting( "unique_path" )
        if unique_folder =="":
            __addon__.openSettings()
            unique_folder = __addon__.getSetting( "unique_path" )
        resize = __addon__.getSetting( "enableresize" )
        xbmc.log( "[script.cdartmanager] - Resize: %s" % resize, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - Unique Folder: %s" % unique_folder, xbmc.LOGNOTICE )
        if exists(source):
            xbmc.log( "[script.cdartmanager] - source: %s" % source, xbmc.LOGNOTICE )
            if fn_format == 0:
                destination=os.path.join( unique_folder, ( artist.replace( "/","" ) ).replace( "'","" ) ) #to fix AC/DC
                fn = os.path.join( destination, ( ( ( album.replace( "/","" ) ).replace( "'","" ) ) + ".png" ) )
            else:
                destination=unique_folder
                fn = os.path.join( destination, ( ( ( (artist.replace( "/", "" ) ).replace( "'","" ) ) + " - " + ( ( album.replace( "/","" ) ).replace( "'","" ) ) + ".png" ).lower() ) )
            xbmc.log( "[script.cdartmanager] - destination: %s" % destination, xbmc.LOGNOTICE )
            if not exists(destination):
                #pass
                os.makedirs(destination)
            else:
                pass
            try:
                xbmc.log( "[script.cdartmanager] - Saving: %s" % fn, xbmc.LOGNOTICE )
                file_copy(source, fn)
            except:
                xbmc.log( "[script.cdartmanager] - Copying error, check path and file permissions", xbmc.LOGNOTICE )
        else:
            xbmc.log( "[script.cdartmanager] - Error: cdART file does not exist..  Please check...", xbmc.LOGNOTICE )
        return

    def single_backup_copy(self, artist, album, source):
        xbmc.log( "[script.cdartmanager] - Copying To Backup Folder: %s - %s" % (artist,album) , xbmc.LOGNOTICE )
        destination = ""
        fn_format = int(__addon__.getSetting("folder"))
        backup_folder = __addon__.getSetting("backup_path")
        if backup_folder =="":
            __addon__.openSettings()
            backup_folder = __addon__.getSetting("backup_path")
        xbmc.log( "[script.cdartmanager] - source: %s" % source, xbmc.LOGNOTICE )
        if exists(source):
            xbmc.log( "[script.cdartmanager] - source: %s" % source, xbmc.LOGNOTICE )
            if fn_format == 0:
                destination=os.path.join(backup_folder, (artist.replace("/","")).replace("'","")) #to fix AC/DC
                fn = os.path.join(destination, ( ((album.replace("/","")).replace("'","")) + ".png"))
            else:
                destination=backup_folder
                fn = os.path.join(destination, ((((artist.replace("/", "")).replace("'","")) + " - " + ((album.replace("/","")).replace("'","")) + ".png").lower()))
            xbmc.log( "[script.cdartmanager] - destination: %s" % destination, xbmc.LOGNOTICE )
            if not exists(destination):
                #pass
                os.makedirs(destination)
            else:
                pass
            xbmc.log( "[script.cdartmanager] - filename: %s" % fn, xbmc.LOGNOTICE )
            try:
                file_copy(source, fn)
            except:
                xbmc.log( "[script.cdartmanager] - copying error, check path and file permissions", xbmc.LOGNOTICE )
        else:
            xbmc.log( "[script.cdartmanager] - Error: cdART file does not exist..  Please check...", xbmc.LOGNOTICE )
        return

    def single_cdart_delete(self, source, album):
        xbmc.log( "[script.cdartmanager] - Deleting: %s" % source, xbmc.LOGNOTICE )
        conn = sqlite3.connect(addon_db)
        c = conn.cursor()
        cdart = False
        if exists(source):
            try:
                delete_file( source )
                c.execute("""UPDATE alblist SET cdart=%s WHERE title='%s'""" % ( cdart, album ) )
                conn.commit()
            except:
                xbmc.log( "[script.cdartmanager] - Deleteing error, check path and file permissions", xbmc.LOGNOTICE )
        else:
            xbmc.log( "[script.cdartmanager] - Error: cdART file does not exist..  Please check...", xbmc.LOGNOTICE )
        c.close()
        return
    
    # Copy's all the local unique cdARTs to a folder specified by the user
    def unique_cdart_copy( self, unique ):
        xbmc.log( "[script.cdartmanager] - Copying Unique cdARTs...", xbmc.LOGNOTICE )
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
        xbmc.log( "[script.cdartmanager] - Unique Folder: %s" % unique_folder, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - Resize: %s" % resize, xbmc.LOGNOTICE )
        pDialog.create( _(32060) )
        #xbmc.sleep( 1000 )
        for album in unique:
            percent = int((count/len(unique))*100)
            xbmc.log( "[script.cdartmanager] - Artist: %-30s    ##    Album:%s" % (album["artist"], album["title"]), xbmc.LOGNOTICE )
            if (pDialog.iscanceled()):
                break
            if album["local"] == "TRUE" and album["distant"] == "FALSE":
                source=os.path.join(album["path"].replace("\\\\" , "\\"), "cdart.png")
                xbmc.log( "[script.cdartmanager] - Source: %s" % repr(source), xbmc.LOGNOTICE )
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
                    xbmc.log( "[script.cdartmanager] - Destination: %s" % repr(fn), xbmc.LOGNOTICE )
                    if exists(fn):
                        xbmc.log( "[script.cdartmanager] - ################## cdART Not being copied, File exists: %s" % repr(fn), xbmc.LOGNOTICE )
                        duplicates += 1
                    else:
                        try:
                            xbmc.log( "[script.cdartmanager] - Saving: %s" % repr(fn)                                    , xbmc.LOGNOTICE )
                            file_copy(source, fn)
                            conn = sqlite3.connect(addon_db)
                            c = conn.cursor()
                            c.execute("insert into unqlist(title, artist, path, cdart) values (?, ?, ?, ?)", ( unicode(album["title"], 'utf-8'), unicode(album["artist"], 'utf-8'), repr(album["path"]), album["local"]))
                            c.commit
                            count += 1
                        except:
                            xbmc.log( "[script.cdartmanager] - Copying error, check path and file permissions", xbmc.LOGNOTICE )
                            count += 1
                        c.close()
                        pDialog.update( percent, _(32064) % unique_folder , "Filename: %s" % fn, "%s: %s" % ( _(32056) , count ) )
                else:
                    xbmc.log( "[script.cdartmanager] - Error: cdART file does not exist..  Please check...", xbmc.LOGNOTICE )
            else:
                if album["local"] and album["distant"]:
                    xbmc.log( "[script.cdartmanager] - Local and Distant cdART exists", xbmc.LOGNOTICE )
                else:
                    xbmc.log( "[script.cdartmanager] - Local cdART does not exists", xbmc.LOGNOTICE )
        pDialog.close()
        xbmcgui.Dialog().ok( _(32057), "%s: %s" % ( _(32058), unique_folder), "%s %s" % ( count , _(32059)))
        # uncomment the next line when website is ready
        #self.compress_cdarts( unique_folder )
        return

    def restore_from_backup( self ):
        xbmc.log( "[script.cdartmanager] - Restoring cdARTs from backup folder", xbmc.LOGNOTICE )
        pDialog.create( _(32069) )
        #xbmc.sleep( 1000 )
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
        xbmc.log( "[script.cdartmanager] - Copying cdARTs from: %s" % repr(from_folder), xbmc.LOGNOTICE )
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
        xbmc.log( "[script.cdartmanager] - Filename format: %s" % fn_format, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - From Folder: %s" % from_folder, xbmc.LOGNOTICE )
        local_db = get_local_albums_db( "all artists", self.background )
        total_albums=len(local_db)
        xbmc.log( "[script.cdartmanager] - total albums: %s" % total_albums, xbmc.LOGNOTICE )
        pDialog.create( _(32069) )
        #xbmc.sleep( 1000 )
        for album in local_db:
            if (pDialog.iscanceled()):
                break
            xbmc.log( "[script.cdartmanager] - Artist: %-30s  ##  Album: %s" % (repr(album["artist"]), repr(album["title"])), xbmc.LOGNOTICE )
            xbmc.log( "[script.cdartmanager] - Album Path: %s" % repr(album["path"]), xbmc.LOGNOTICE )
            percent = int(total_count/float(total_albums))*100
            if fn_format == 0:
                source=os.path.join( from_folder, (album["artist"].replace("/","").replace("'","") ) )#to fix AC/DC and other artists with a / in the name
                if album["disc"] > 1:
                    fn = os.path.join( source, ( ( album["title"].replace("/","").replace("'","") ) + "_disc_" + str( album["disc"] ) + ".png") )
                else:
                    fn = os.path.join( source, ( ( album["title"].replace("/","").replace("'","") ) + ".png") )
                if not exists(fn):
                    source=os.path.join( from_folder )
                    if album["disc"] > 1:
                        fn = os.path.join(source, ( ( ( album["artist"].replace("/", "").replace("'","") ) + " - " + ( album["title"].replace("/","").replace("'","") ) + "_disc_" + str( album["disc"] ) + ".png").lower() ) )
                    else:
                        fn = os.path.join(source, ( ( ( album["artist"].replace("/", "").replace("'","") ) + " - " + ( album["title"].replace("/","").replace("'","") ) + ".png").lower() ) )
            else:
                source=os.path.join( from_folder ) #to fix AC/DC
                if album["disc"] > 1:
                    fn = os.path.join(source, ( ( ( album["artist"].replace("/", "").replace("'","") ) + " - " + ( album["title"].replace("/","").replace("'","") ) + "_disc_" + str( album["disc"] ) + ".png").lower() ) )
                else:
                    fn = os.path.join(source, ( ( ( album["artist"].replace("/", "").replace("'","") ) + " - " + ( album["title"].replace("/","").replace("'","") ) + ".png").lower() ) )
                if not exists(fn):
                    source=os.path.join( from_folder, (album["artist"].replace("/","").replace("'","") ) )#to fix AC/DC and other artists with a / in the name
                    fn = os.path.join(source, ( ( album["title"].replace("/","").replace("'","") ) + ".png") )
            xbmc.log( "[script.cdartmanager] - Source folder: %s" % repr(source), xbmc.LOGNOTICE )
            xbmc.log( "[script.cdartmanager] - Source filename: %s" % repr(fn), xbmc.LOGNOTICE )
            if exists(fn):
                destination = os.path.join(album["path"], "cdart.png")
                xbmc.log( "[script.cdartmanager] - Destination: %s" % repr(destination), xbmc.LOGNOTICE )
                try:
                    file_copy(fn, destination)
                    if not from_folder == __addon__.getSetting("backup_path"):
                        delete_file( fn )  # remove file
                    count += 1
                except:
                    xbmc.log( "[script.cdartmanager] - ######  Copying error, check path and file permissions", xbmc.LOGNOTICE )
                try:
                    c.execute("""UPDATE alblist SET cdart=%s WHERE title='%s'""" % ( True, album["title"] ) )
                except:
                    xbmc.log( "[script.cdartmanager] - ######  Problem modifying Database!!  Artist: %s   Album: %s" % (repr(album["artist"]), repr(album["title"])), xbmc.LOGNOTICE )
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
        xbmc.log( "[script.cdartmanager] - Copying cdARTs to Backup folder", xbmc.LOGNOTICE )
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
        albums = get_local_albums_db( "all artists", self.background )
        pDialog.create( _(32060) )
        #xbmc.sleep( 1000 )
        for album in albums:
            if (pDialog.iscanceled()):
                break
            if album["cdart"]:
                source=os.path.join(album["path"].replace("\\\\" , "\\"), "cdart.png")
                xbmc.log( "[script.cdartmanager] - cdART #: %s" % count, xbmc.LOGNOTICE )
                xbmc.log( "[script.cdartmanager] - Artist: %-30s  Album: %s" % (repr(album["artist"]), repr(album["title"])), xbmc.LOGNOTICE )
                xbmc.log( "[script.cdartmanager] - Album Path: %s" % source, xbmc.LOGNOTICE )
                if exists(source):
                    if fn_format == 0:
                        destination=os.path.join( bkup_folder, ( album["artist"].replace("/","").replace("'","") ) ) #to fix AC/DC
                        if album["disc"] > 1:
                            fn = os.path.join( destination, ( ( album["title"].replace("/","").replace("'","") ) + "_disc_" + str( album["disc"] ) + ".png") )
                        else:
                            fn = os.path.join( destination, ( ( album["title"].replace("/","").replace("'","") ) + ".png") )
                    elif fn_format == 1:
                        destination=os.path.join( bkup_folder ) #to fix AC/DC
                        if album["disc"] > 1:
                            fn = os.path.join( destination, (  ( album["artist"].replace("/", "").replace("'","") ) + " - " + ( album["title"].replace("/","").replace("'","") ) + "_disc_" + str( album["disc"] ) + ".png").lower())
                        else:
                            fn = os.path.join( destination, (  ( album["artist"].replace("/", "").replace("'","") ) + " - " + ( album["title"].replace("/","").replace("'","") ) + ".png").lower())
                    xbmc.log( "[script.cdartmanager] - Destination Path: %s" % destination, xbmc.LOGNOTICE )
                    if not exists(destination):
                        os.makedirs(destination)
                    xbmc.log( "[script.cdartmanager] - Filename: %s" % fn, xbmc.LOGNOTICE )
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
        xbmc.log( "[script.cdartmanager] - Duplicate cdARTs: %s" % duplicates, xbmc.LOGNOTICE )
        xbmcgui.Dialog().ok( _(32057), "%s: %s" % ( _(32058), bkup_folder), "%s %s" % ( count , _(32059)), "%s Duplicates Found" % duplicates)
        return        
        
# Search for missing cdARTs and save to missing.txt in backup folder
    def missing_list( self ):
        xbmc.log( "[script.cdartmanager] - Saving Missing cdART list to backup folder", xbmc.LOGNOTICE )
        count = 0
        percent = 0
        line = ""
        albums = get_local_albums_db("all artists", self.background)
        bkup_folder = __addon__.getSetting("backup_path")
        pDialog.create( _(32103), _(20186) )
        #xbmc.sleep( 1000 )
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
                if not album["cdart"]:
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
                if not album["cdart"]:
                    artist = repr( album["artist"] ) 
                    title = repr( album["title"] )
                    line = artist + " * " + title + "\n"
                    missing.write( line )
            missing.close()
        except:
            xbmc.log( "[script.cdartmanager] - Error saving missing.txt file", xbmc.LOGNOTICE )
        pDialog.close()
                    
    def refresh_counts( self, local_album_count, local_artist_count, local_cdart_count ):
        xbmc.log( "[script.cdartmanager] - Refreshing Counts", xbmc.LOGNOTICE )
        self.getControl( 109 ).setLabel( _(32007) % local_artist_count)
        self.getControl( 110 ).setLabel( _(32010) % local_album_count)
        self.getControl( 112 ).setLabel( _(32008) % local_cdart_count)
        self.missing_list()

    # This selects which cdART image shows up in the display box (image id 210) 
    def cdart_icon( self ):
        blank_art = os.path.join( skin_art_path, "blank_artwork.png")
        image = blank_art
        cdart_path = {}
        try: # If there is information in label 2 of list id 140(local album list)
            local_cdart = ( self.getControl(140).getSelectedItem().getLabel2() ).split("&&&&")[1]
            url = (( self.getControl( 140 ).getSelectedItem().getLabel2() ).split("&&&&")[0]).split("&&")[1]
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
            print_exc()
            image = blank_art
        self.getControl( 210 ).setImage( image )

    def clear_artwork( self ):
        self.getControl( 211 ).setImage( addon_img )
        self.getControl( 210 ).setImage( addon_img )
            
    def popup(self, header, line1, line2, line3):        
        #self.getControl( 400 ).setLabel( header )
        #self.getControl( 401 ).setLabel( line1 )
        #self.getControl( 402 ).setLabel( line2 )
        #self.getControl( 403 ).setLabel( line3 )
        #self.getControl( 9012 ).setVisible( True )
        pDialog.create( header, line1, line2, line3 )
        #xbmc.sleep( 1000 )
        xbmc.sleep(2000)
        pDialog.close()
        #self.getControl( 9012 ).setVisible( False ) 

    # setup self. strings and initial local counts
    def setup_all( self ):
        self.background = False
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
        self.artwork_type = ""
        listitem = xbmcgui.ListItem( label=self.label_1, label2=self.label_2, thumbnailImage=self.cdartimg )
        self.getControl( 122 ).addItem( listitem )
        listitem.setLabel2(self.label_2)
        #checking to see if addon_db exists, if not, run database_setup()
        if exists( (addon_db).replace("\\\\" , "\\").encode("utf-8") ):
            xbmc.log( "[script.cdartmanager] - Addon Db found - Loading Counts", xbmc.LOGNOTICE )
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
        else:
            xbmc.log( "[script.cdartmanager] - Addon Db Not Found - Building New Addon Db", xbmc.LOGNOTICE )
            local_album_count, local_artist_count, local_cdart_count = new_database_setup( self.background )
        self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        self.local_artists = get_local_artists_db() # retrieve data from addon's database
        self.setFocusId( 100 ) # set menu selection to the first option(cdARTs)

    def onClick( self, controlId ):
        #print controlId
        if controlId == 105 : #cdARTs Search Artists 
            self.menu_mode = 1
            self.artwork_type = "cdart"
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            self.getControl( 120 ).reset()
            self.getControl( 140 ).reset()
            distant_artist = get_distant_artists()
            local_artists = get_local_artists_db( mode="album_artists" )
            if distant_artist:
                self.recognized_artists, self.local_artists = get_recognized( distant_artist , local_artists )
            self.populate_artist_list( self.recognized_artists )
        if controlId == 120 : #Retrieving information from Artists List
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            #self.clear_artwork()
            self.artist_menu = {}
            self.artist_menu["local_id"] = ( self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["local_id"] )
            self.artist_menu["name"] = get_unicode( self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["name"] )
            self.artist_menu["musicbrainz_artistid"] = get_unicode( self.local_artists[self.getControl( 120 ).getSelectedPosition()]["musicbrainz_artistid"] )
            self.artist_menu["distant_id"] = get_unicode( self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["distant_id"] )
            if not self.artist_menu["musicbrainz_artistid"]:
                self.artist_menu["musicbrainz_artistid"] = update_musicbrainzid( "artist", self.artist_menu )
            artist_name = get_unicode( self.artist_menu["name"] )
            self.getControl( 204 ).setLabel( _(32038) + "[CR]%s" % artist_name )
            if self.menu_mode == 1:
                self.remote_cdart_url = remote_cdart_list( self.artist_menu )
                xbmcgui.Window(10001).setProperty( "artwork", "cdart" )
                self.populate_album_list( self.artist_menu, self.remote_cdart_url, 0, "cdart" )
            elif self.menu_mode == 3:
                self.remote_cdart_url = remote_coverart_list( self.artist_menu )
                xbmcgui.Window(10001).setProperty( "artwork", "cover" )
                self.populate_album_list( self.artist_menu, self.remote_cdart_url, 0, "cover" )
            elif self.menu_mode == 6:
                xbmcgui.Window(10001).setProperty( "artwork", "fanart" )
                self.populate_fanarts( self.artist_menu, 0 )
            elif self.menu_mode == 7:
                xbmcgui.Window(10001).setProperty( "artwork", "clearlogo" )
                self.populate_clearlogos( self.artist_menu, 0 )
        if controlId == 122 : #Retrieving information from Album List
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
            try:
                cdart_path["artist"] = ( self.getControl( 204 ).getLabel().encode('utf-8') ).replace( _(32038) + "[CR]","")
            except:
                cdart_path["artist"] = ( self.getControl( 204 ).getLabel().decode('utf-8') ).replace( _(32038) + "[CR]","")
            cdart_path["title"] = self.getControl( 122 ).getSelectedItem().getLabel()
            cdart_path["title"] = self.remove_color(cdart_path["title"])
            selected_item = self.getControl( 122 ).getSelectedPosition()
            if not url =="" : # If it is a recognized Album...
                if self.menu_mode == 1:
                    message, d_success = download_art( url, cdart_path, "cdart", "manual", 0 )
                elif self.menu_mode == 3:
                    message, d_success = download_art( url, cdart_path, "cover", "manual", 0 )
                try:
                    pDialog.close()
                except:
                    pass # pDialog not open anyways
                xbmcgui.Dialog().ok(message[0] ,message[1] ,message[2] ,message[3])
            else : # If it is not a recognized Album...
                xbmc.log( "[script.cdartmanager] - Oops --  Some how I got here... - ControlID(122)", xbmc.LOGDEBUG )
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
            artist_name = self.artist_menu["name"].decode("utf-8")
            self.getControl( 204 ).setLabel( _(32038) + "[CR]%s" % artist_name )
            if self.menu_mode == 1:
                self.remote_cdart_url = remote_cdart_list( self.artist_menu )
                xbmcgui.Window(10001).setProperty( "artwork", "cdart" )
                self.populate_album_list( self.artist_menu, self.remote_cdart_url, selected_item )
            elif self.menu_mode == 3:
                self.remote_cdart_url = remote_coverart_list( self.artist_menu, selected_item )
                xbmcgui.Window(10001).setProperty( "artwork", "cover" )
                self.populate_coverarts( self.artist_menu, self.remote_cdart_url )
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
        if controlId == 131 : #Modify Local Database
            self.setFocusId( 190 ) # change when other options 
        if controlId == 190 : # backup database
            backup_database()
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ( _(32042), _(32139), 2000, image) )
        if controlId == 191 : #Refresh Local database selected from Advanced Menu
            refresh_db( False )
            pDialog.close()
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        if controlId == 192: #Update database
            update_database( False )
            pDialog.close()
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        if controlId == 136 : #Restore from Backup
            self.restore_from_backup()
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        if controlId == 137 : #Local cdART List
            self.getControl( 122 ).reset()
            self.menu_mode = 8
            xbmcgui.Window(10001).setProperty( "artwork", "cdart" )
            self.populate_local_cdarts( 0 )
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
            self.getControl( 300 ).setLabel( self.getControl(140).getSelectedItem().getLabel() )
        if controlId in ( 142, 143, 144 ):
            path = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[1])
            artist_album = self.getControl(140).getSelectedItem().getLabel()
            artist_album = self.remove_color(artist_album)
            artist = artist_album.split(" * ")[0]
            album_title = artist_album.split(" * ")[1]
            if controlId == 143:  #Delete cdART
                self.single_cdart_delete( path, album_title )
                local_album_count, local_artist_count, local_cdart_count = new_local_count()
                self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
                popup_label = _( 32075 )
            elif controlId == 142: #Backup to backup folder
                self.single_backup_copy( artist, album_title, path )
                popup_label = _( 32074 )
            else: #Copy to Unique folder
                self.single_unique_copy( artist, album_title, path )
                popup_label = _( 32076 )
            self.popup( popup_label, self.getControl(140).getSelectedItem().getLabel(),"", "")
            self.setFocusId( 140 )            
            self.populate_local_cdarts()
        if controlId == 100 : #cdARTS
            self.artwork_type = "cdart"
            self.setFocusId( 105 )
        if controlId == 101 : #Cover Arts
            self.artwork_type = "cover"
            self.setFocusId( 150 )
        if controlId == 103 : #Advanced
            self.setFocusId( 130 )
        if controlId == 104 : #Settings
            self.menu_mode = 5
            __addon__.openSettings()
            self.setup_colors()
        if controlId == 111 : #Exit
            self.menu_mode = 0
            empty_tempxml_folder()
            self.close()
        if controlId == 150 : #Cover Art Search Artists 
            self.menu_mode = 3
            self.artwork_type = "cover"
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            self.getControl( 120 ).reset()
            self.getControl( 140 ).reset()
            distant_artist = get_distant_artists()
            local_artists = get_local_artists_db( mode="album_artists" )
            if distant_artist:
                self.recognized_artists, self.local_artists = get_recognized( distant_artist , local_artists )
            self.populate_artist_list( self.recognized_artists )
        if controlId in ( 180, 181 ): # fanart Search Album Artists
            self.menu_mode = 6
        if controlId in ( 184, 185 ): # Clear Logo Search Artists
            self.menu_mode = 7
        if controlId == 102:
            self.artwork_type = "fanart"
            self.setFocusId( 170 )
        if controlId == 170:
            self.setFocusId( 180 )
        if controlId == 171:
            self.setFocusId( 181 )
        if controlId == 168:
            self.setFocusId( 184 )
        if controlId == 169:
            self.setFocusId( 186 )
        if controlId == 152:
            self.artwork_type = "clearlogo"
            self.setFocusId( 168 )
        if controlId in ( 180, 181, 184, 185 ):
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            self.getControl( 120 ).reset()
            distant_artist = get_distant_artists()
            if controlId in ( 180, 184):
                local_artists = get_local_artists_db( mode="album_artists" )
            else:
                local_artists = get_local_artists_db( mode="local_artists" )
            if distant_artist:
                self.recognized_artists, self.local_artists = get_recognized( distant_artist , local_artists )
            self.populate_artist_list( self.recognized_artists )
        if controlId == 167:
            artist = {}
            if self.menu_mode == 7:
                url = ( self.getControl( 167 ).getSelectedItem().getLabel2() ).split("&&&&")[ 1 ]
                artist["artist"] = ( self.getControl( 167 ).getSelectedItem().getLabel2() ).split("&&&&")[ 0 ]
                artist["path"] = os.path.join( __addon__.getSetting("music_path"), artist["artist"] )
                selected_item = self.getControl( 167 ).getSelectedPosition()
                if url:
                    download_art( url, artist, "clearlogo", "manual", 0 )
                    try:
                        pDialog.close()
                    except:
                        pass
                else:
                    xbmc.log( "[script.cdartmanager] - Nothing to download", xbmc.LOGDEBUG )
                xbmcgui.Window(10001).setProperty( "artwork", "clearlogo" )
                self.populate_clearlogos( self.artist_menu, selected_item )
        if controlId == 160:
            artist = {}
            if self.menu_mode == 6:
                url = ( self.getControl( 160 ).getSelectedItem().getLabel2() ).split("&&&&")[ 1 ]
                artist["artist"] = ( self.getControl( 160 ).getSelectedItem().getLabel2() ).split("&&&&")[ 0 ]
                artist["path"] =  os.path.join( __addon__.getSetting("music_path"), artist["artist"] )
                selected_item = self.getControl( 160 ).getSelectedPosition()
                if url:
                    download_art( url, artist, "fanart", "manual", 0 )
                    try:
                        pDialog.close()
                    except:
                        pass
                else:
                    xbmc.log( "[script.cdartmanager] - Nothing to download", xbmc.LOGDEBUG )
                xbmcgui.Window(10001).setProperty( "artwork", "fanart" )
                self.populate_fanarts( self.artist_menu, selected_item )  
        if controlId in ( 182, 186, 187, 183, 106, 151 ): # Automatic Download
            self.artwork_type = ""
            if controlId == 106: #cdARTs
                self.menu_mode = 2
                self.artwork_type = "cdart"
            if controlId == 151: #cover arts
                self.menu_mode = 4
                self.artwork_type = "cover"
            if controlId == 186:# ClearLOGOs
                self.artwork_type = "clearlogo"
            if controlId == 182:# Fanarts
                self.artwork_type = "fanart"
            if controlId == 187:# ClearLOGOs All Artists
                self.artwork_type = "clearlogo_allartists"
            if controlId == 183:# Fanarts All Artists
                self.artwork_type = "fanart_allartists"
            download_count, successfully_downloaded = auto_download( self.artwork_type )
            local_album_count, local_artist_count, local_cdart_count = new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
            if successfully_downloaded:
                self.populate_downloaded( successfully_downloaded, self.artwork_type )

    def onFocus( self, controlId ):
        if not ( controlId == 122 or controlId == 140 or controlId == 160 ):
            xbmcgui.Window(10001).clearProperty( "artwork" )
        if controlId == 140:
            self.cdart_icon()
        if controlId in ( 100, 101, 152, 103, 104, 111):
            xbmcgui.Window(10001).clearProperty( "artwork" )
            self.menu_mode = 0

    def onAction( self, action ):
        if self.menu_mode == 8:
            self.cdart_icon()
        buttonCode =  action.getButtonCode()
        actionID   =  action.getId()
        #xbmc.log( "[script.cdartmanager] - onAction(): actionID=%i buttonCode=%i" % (actionID,buttonCode), xbmc.LOGNOTICE )
        if (buttonCode == KEY_BUTTON_BACK or buttonCode == KEY_KEYBOARD_ESC):
            self.close()
            empty_tempxml_folder()
        if actionID == 10:
            xbmc.log( "[script.cdartmanager] - Closing", xbmc.LOGNOTICE )
            try:
                pDialog.close()
            except:
                pass
            empty_tempxml_folder()
            self.close()

def onAction( self, action ):
    #xbmc.log( action, xbmc.LOGNOTICE )
    if (buttonCode == KEY_BUTTON_BACK or buttonCode == KEY_KEYBOARD_ESC):
            empty_tempxml_folder()
            self.close()
    if ( action.getButtonCode() in CANCEL_DIALOG ):
        xbmc.log( "[script.cdartmanager] - Closing", xbmc.LOGNOTICE )
        empty_tempxml_folder()
        self.close()
