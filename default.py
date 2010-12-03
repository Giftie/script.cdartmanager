__scriptname__    = "CDArt Manager Script"
__scriptID__      = "script.cdartmanager"
__author__        = "Giftie"
__version__       = "1.1.3"
__credits__       = "Ppic, Reaven, Imaginos, redje, Jair"
__XBMC_Revision__ = "35415"
__date__          = "12-02-10"
import sys
import os
import xbmcaddon
import xbmc

__settings__ = xbmcaddon.Addon(__scriptID__)
__language__ = __settings__.getLocalizedString

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __settings__.getAddonInfo('path'), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "skins", "Default" ) )

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ))

print BASE_RESOURCE_PATH


addon_work_folder = os.path.join(xbmc.translatePath( "special://profile/addon_data/" ), __scriptID__)

if ( __name__ == "__main__" ):
    print "############################################################"
    print "#    %-50s    #" % __scriptname__
    print "#        default.py module                                 #"
    print "#    %-50s    #" % __scriptID__
    print "#    %-50s    #" % __author__
    print "#    %-50s    #" % __version__
    print "#    %-50s    #" % __credits__
    print "#    Thanks the the help guys...                           #"
    print "############################################################"
    path = __settings__.getAddonInfo('path')
    if not os.path.exists(addon_work_folder):
        __settings__.openSettings()
    import gui
    ui = gui.GUI( "script-cdartmanager.xml" , __settings__.getAddonInfo('path'), "Default")
    ui.doModal()
    del ui
    sys.modules.clear()
