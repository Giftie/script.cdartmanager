import xbmc
import urllib
from traceback import print_exc

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
            xbmc.log( "[script.cdartmanager] - # !!Unable to open page %s" % url, xbmc.LOGDEBUG )
            error = True
    if error:
        return ""
    else:
        xbmc.log( "[script.cdartmanager] - HTML Source:\n%s" % htmlsource, xbmc.LOGDEBUG )
        return htmlsource  