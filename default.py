__scriptname__    = "CDArt Manager Script"
__scriptID__      = "script.cdartmanager"
__author__        = "Giftie"
__version__       = "1.3.6"
__credits__       = "Ppic, Reaven, Imaginos, redje, Jair, "
__credits2__      = "Chaos_666, Magnatism"
__XBMC_Revision__ = "35415"
__date__          = "6-22-11"
__dbversion__     = "1.3.2"
__dbversionold__  = "1.1.8"

import sys
import os, traceback
import xbmcaddon, xbmc, xbmcgui

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3
    
from xbmcvfs import delete as delete_file
from xbmcvfs import exists as exists
# remove comments to save as dharma
#from os import remove as delete_file
#exists = os.path.exists
 
__addon__ = xbmcaddon.Addon(__scriptID__)
__language__ = __addon__.getLocalizedString

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "skins", "Default" ) )

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ))
addon_work_folder = xbmc.translatePath( __addon__.getAddonInfo('profile') )
addon_db = os.path.join(addon_work_folder, "l_cdart.db")
addon_db_backup = os.path.join(addon_work_folder, "l_cdart.db.bak")
addon_db_crash = os.path.join(addon_work_folder, "l_cdart.db-journal")
settings_file = os.path.join(addon_work_folder, "settings.xml")
script_fail = False
first_run = False
rebuild = False
soft_exit = False
image = xbmc.translatePath( os.path.join( __addon__.getAddonInfo("path"), "icon.png") )

from utils import empty_tempxml_folder

if ( __name__ == "__main__" ):
    xbmc.log( "[script.cdartmanager] - ############################################################", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __scriptname__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #        default.py module                                 #", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __scriptID__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __author__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __version__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __credits__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    %-50s    #" % __credits2__, xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - #    Thanks for the help guys...                           #", xbmc.LOGNOTICE )
    xbmc.log( "[script.cdartmanager] - ############################################################", xbmc.LOGNOTICE )
    empty_tempxml_folder()
    try:
        if sys.argv[ 1 ]:
            if sys.argv[ 1 ] == "database":
                from database import refresh_db
                local_album_count, local_artist_count, local_cdart_count = refresh_db( True )
            elif sys.argv[ 1 ] == "autocdart":
                pass
            elif sys.argv[ 1 ] == "autocover":
                pass
            else:
                xbmc.log( "[script.cdartmanager] - Error: Improper sys.argv[ 1 ]: %s" % sys.argv[ 1 ], xbmc.LOGNOTICE )
    except IndexError:
        xbmc.log( "[script.cdartmanager] - Addon Work Folder: %s" % addon_work_folder, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - Addon Database: %s" % addon_db, xbmc.LOGNOTICE )
        xbmc.log( "[script.cdartmanager] - Addon settings: %s" % settings_file, xbmc.LOGNOTICE )
        query = "SELECT version FROM counts"    
        xbmc.log( "[script.cdartmanager] - Looking for settings.xml", xbmc.LOGNOTICE )
        if not exists(settings_file):
            xbmc.log( "[script.cdartmanager] - settings.xml File not found, opening settings", xbmc.LOGNOTICE )
            __addon__.openSettings()
            first_run = True
        else:
            xbmc.log( "[script.cdartmanager] - Addon Work Folder Found, Checking For Database", xbmc.LOGNOTICE )
        if not exists(addon_db):
            xbmc.log( "[script.cdartmanager] - Addon Db not found, Must Be First Run", xbmc.LOGNOTICE )
            first_run = True
        else:
            xbmc.log( "[script.cdartmanager] - Addon Db Found, Checking Database Version", xbmc.LOGNOTICE )
        if exists(addon_db_crash) and not first_run:
            xbmc.log( "[script.cdartmanager] - Detected Database Crash, Trying to delete", xbmc.LOGNOTICE )
            try:
                delete_file(addon_db)
                delete_file(addon_db_crash)
                xbmc.log( "[script.cdartmanager] - Opening Settings" , xbmc.LOGNOTICE )
                __addon__.openSettings()
            except StandardError, e:
                xbmc.log( "[script.cdartmanager] - Error Occurred: %s " % e.__class__.__name__, xbmc.LOGNOTICE )
                traceback.print_exc()
                script_fail = True
        elif not first_run:
            xbmc.log( "[script.cdartmanager] - Looking for database version: %s" % __dbversion__, xbmc.LOGNOTICE )
            try:
                conn_l = sqlite3.connect(addon_db)
                c = conn_l.cursor()
                c.execute(query)
                version=c.fetchall()
                c.close
                for item in version:
                    if item[0] == __dbversion__:
                        xbmc.log( "[script.cdartmanager] - Database matched", xbmc.LOGNOTICE )
                        break
                    else:
                        xbmc.log( "[script.cdartmanager] - Database Not Matched - trying to delete" , xbmc.LOGNOTICE )
                        rebuild = xbmcgui.Dialog().yesno( __language__(32108) , __language__(32109) )
                        soft_exit = True
                        break
            except StandardError, e:
                traceback.print_exc()
                xbmc.log( "[script.cdartmanager] - # Error: %s" % e.__class__.__name__, xbmc.LOGNOTICE )
                try:
                    xbmc.log( "[script.cdartmanager] - Trying To Delete Database" , xbmc.LOGNOTICE )
                    delete_file(addon_db)
                    delete_file(settings_file)
                    xbmc.log( "[script.cdartmanager] - Opening Settings" , xbmc.LOGNOTICE )
                    __addon__.openSettings()
                except StandardError, e:
                    traceback.print_exc()
                    xbmc.log( "[script.cdartmanager] - # unable to remove folder", xbmc.LOGNOTICE )
                    xbmc.log( "[script.cdartmanager] - # Error: %s" % e.__class__.__name__, xbmc.LOGNOTICE )
                    script_fail = True
        path = __addon__.getAddonInfo('path')   
        if not script_fail:
            if rebuild:
                from database import refresh_db
                local_album_count, local_artist_count, local_cdart_count = refresh_db( True )
            elif not rebuild and not soft_exit:
                import gui
                ui = gui.GUI( "script-cdartmanager.xml" , __addon__.getAddonInfo('path'), "Default")
                ui.doModal()
                del ui
        else:
            xbmc.log( "[script.cdartmanager] - Problem accessing folder, exiting script", xbmc.LOGNOTICE )
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ( __language__(32042), __language__(32110), 500, image) )
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise