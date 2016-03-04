import cherrypy, json
from endpoint_query import *
import couchdb, httplib2, ConfigParser
import os.path

confpath = os.path.join(os.path.dirname(__file__), 'dynamic.conf')

class MoodService:

    def __init__(self):
        self.unpackConfig()
        self.endpointConnection = SparqlHttpConnection(self.getConf('fuseki','uri'), self.getConf('fuseki','port'), self.getConf('fuseki','querydir'))
        self.couchServer = couchdb.Server(self.getConf('couchdb','uri'))
        self.couchdb = self.couchServer[self.getConf('couchdb','database')]

    def unpackConfig(self):
        config = ConfigParser.ConfigParser()
        config.read(confpath)
        self.config = {
            'fuseki': { 
                'uri': config.get('fuseki','uri').replace("\"", ""), 
                'port': int(config.get('fuseki','port')),  
                'dataset': config.get('fuseki','dataset').replace("\"", ""),
                'querydir': config.get('fuseki','querydir').replace("\"", "")
            },
            'couchdb': {
                'uri': config.get('couchdb','uri').replace("\"", ""),
                'database': config.get('couchdb','database').replace("\"", "")
            },
            'musicbrainz': {
                'recordingService': config.get('musicbrainz','recordingService').replace("\"", "")
            }
        }

    def getConf(self, section, key):
        return self.config[section][key]

    # MOODPLAY

    def getFeaturesByFilenames(self, filenames, feature):
        tracks = []
        for fname in eval(filenames):
            track = { "filename": fname }
            mdata = self.getTrackGuidByFilename(track["filename"])
            track["_id"] = json.loads(mdata)
            features = self.getFeatureByTrackGuid(track["_id"], feature)
            track[feature] = json.loads(features)
            tracks.append(track)
        return json.dumps(tracks)
    getFeaturesByFilenames.exposed = True

    def getFeaturesByCoordinates(self, valence, arousal, limit, feature):
        tracks = []
        re = self.findNearestTracks(valence, arousal, limit)
        for result in json.loads(re):
            track = { 
                "valence": float(result["valence"]["value"]), 
                "arousal": float(result["arousal"]["value"]),
                "filename": result["path"]["value"]
            }
            print track["filename"]
            mdata = self.getTrackGuidByFilename(track["filename"])
            track["_id"] = json.loads(mdata)
            features = self.getFeatureByTrackGuid(track["_id"], feature)
            track[feature] = features
            tracks.append(track)
        return json.dumps(tracks)
    getFeaturesByCoordinates.exposed = True

    # SPARQL ENDPOINT ACCESS 

    def coordinateLimits(self, configNumber):
        params = { "@configNumber": configNumber }
        return self.executeQuery("coord_limits", params)
    coordinateLimits.exposed = True

    def findNearestTrack(self, valence, arousal):
        params = { "@valence": valence, "@arousal": arousal }
        return self.executeQuery( "find_nearest_mbid", params)
    findNearestTrack.exposed = True

    def findNearestTracks(self, valence, arousal, limit):
        params = { "@valence": valence, "@arousal": arousal, "@limit": limit }
        return self.executeQuery( "find_n_nearest_mbid", params)
    findNearestTracks.exposed = True

    def getLocalMetadata(self, filename):
        params = { "@filename": filename }
        return self.executeQuery("metadata_by_filename", params)
    getLocalMetadata.exposed = True

    def getTrackUriByFilename(self, filename):
        params = { "@filename": filename }
        return self.executeQuery("trackuri_by_filename", params)
    getTrackUriByFilename.exposed = True

    def getCoordinatesForConfig(self, configNumber):
        params = { "@config": configNumber }
        return self.executeQuery("coords_for_config", params)
    getCoordinatesForConfig.exposed = True

    def executeQuery(self, queryname, params):
        jsonstr = self.endpointConnection.executeQuery(queryname, params, self.getConf('fuseki','dataset'))
        data = json.loads(jsonstr)
        return json.dumps(data['results']['bindings'])

    # COUCHDB FEATURE DB ACCESS

    def getTrackByTitleAndArtist(self, title, artist):
        return self.getSingleDocument('getTrackByTitleAndArtist', [title, artist])
    getTrackByTitleAndArtist.exposed = True
    
    def getTrackByMusicBrainzGuid(self, mbid):
        return self.getSingleDocument('getTrackByMusicBrainzGuid', mbid)
    getTrackByMusicBrainzGuid.exposed = True

    def getTrackByGuid(self, trackid):
        return self.getSingleDocument('getTrackByGuid', trackid)
    getTrackByGuid.exposed = True

    def getTrackGuidByFilename(self, filename):
        return self.getSingleDocument('getTrackGuidByFilename', filename)
    getTrackGuidByFilename.exposed = True
    
    def getFeatureByTrackGuid(self, trackid, feature):
        return self.getSingleDocument('getFeatureByTrackGuid', [trackid, feature])
    getFeatureByTrackGuid.exposed = True

    def saveDymo(self, data):
        return self.saveDocument(data)
    saveDymo.exposed = True

    def getSingleDocument(self, viewname, key):
        doc = None
        for row in self.couchdb.view("views/" + viewname, key=key):
            doc = row.value
        return json.dumps(doc)

    def saveDocument(self, json):
        return self.couchdb.save(json)

    # MUSICBRAINZ WEBSERVICE ACCESS

    def getMusicbrainzMetadata(self, mbid):
        uri = self.getConf('musicbrainz','recordingService')
        re, co = httplib2.Http().request(uri + mbid + "?inc=artist-credits+releases&fmt=json")
        if re.status == 200:
            return co
        else:
            return json.dumps(re)
    getMusicbrainzMetadata.exposed = True

if __name__ == '__main__':
    cherrypy.quickstart(MoodService(), config=confpath)
else:
    cherrypy.tree.mount(MoodService(), config=confpath)
