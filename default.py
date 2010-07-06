__scriptname__    = "CDArt Manager Script"
__scriptID__      = "script.cdartmanager"
__author__        = "Giftie"
__version__       = "0.8.0"
__XBMC_Revision__ = "30001"
__date__          = "05-06-10"
import sys
import os
import xbmcgui
import xbmcaddon
import xbmc


BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'lib' ) )

sys.path.append (BASE_RESOURCE_PATH)

print BASE_RESOURCE_PATH

__settings__ = xbmcaddon.Addon(__scriptID__)
__language__ = __settings__.getLocalizedString

if ( __name__ == "__main__" ):          
    import gui
    ui = gui.GUI( "script-cdartmanager.xml" , os.getcwd(), "Default")
    ui.doModal()
    del ui
    sys.modules.clear()
