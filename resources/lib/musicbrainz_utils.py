from musicbrainz2.webservice import Query, ArtistFilter, WebServiceError, ReleaseFilter
import xbmc

def get_musicbrainz_album( album_title, artist ):
    album = {}
    artist=artist.replace(" ", "+")
    try:
        # The result should include all official albums.
        #
        inc = ReleaseFilter(artistName=artist, title=album_title )
        album_result = Query().getReleases( inc )
    except WebServiceError, e:
        xbmc.log( "[script.cdartmanager] - Error: %s" % e, xbmc.LOGERROR )
    
    if len( album_result ) == 0:
        xbmc.log( "[script.cdartmanager] - No releases found on MusicBrainz.", xbmc.LOGNOTICE
    else:
        album["artist"] = album_result[ 0 ].release.artist.name
        album["artist_id"] = album_result[ 0 ].release.artist.id
        album["id"] = album_result[ 0 ].release.id
        album["title"] = album_result[ 0 ].release.title
    return album

def get_musicbrainz_artist_id( artist ):
    try:
        # Search for all artists matching the given name. Retrieve the Best Result
        #
        # replace spaces with plus sign
        artist=artist.replace(" ", "+")  
        f = ArtistFilter( name=artist, limit=1 )
        artistResults = Query().getArtists(f)
        for result in artistResults:
            artist = result.artist
            xbmc.log( "[script.cdartmanager] - Score     : %s" % result.score, xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Id        : %s" % artist.id, xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Name      : %s" % repr( artist.name ), xbmc.LOGDEBUG )
            xbmc.log( "[script.cdartmanager] - Sort Name : %s" % repr( artist.sortName ), xbmc.LOGDEBUG )
            id = ( artist.id ).replace( "http://musicbrainz.org/artist/", "" )
            name = artist.name
            sortname = artist.sortName
        return name, id, sortname
    except WebServiceError, e:
        xbmc.log( "[script.cdartmanager] - Error: %s" % e, xbmc.LOGERROR )
        return "", "", ""