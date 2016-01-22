import cherrypy, json
from endpoint_query import *

ENDPOINT_URI = "localhost"
PORT = 3030
DATASET = "mood"

class MoodService:

    def __init__(self):
        self.endpoint = SparqlEndpoint(ENDPOINT_URI, PORT, DATASET)

    def coordinateLimits(self, configNumber):
        params = { "@configNumber": configNumber }
        jsonstr = self.endpoint.executeQuery("coord_limits", params, DATASET)
        data = json.loads(jsonstr)
        return json.dumps(data['results']['bindings'])
    coordinateLimits.exposed = True

    def findNearestMoodTrack(self, valence, arousal):
        params = { "@valence": valence, "@arousal": arousal }
        jsonstr = self.endpoint.executeQuery( "find_nearest_mbid", params, DATASET)
        data = json.loads(jsonstr)
        return json.dumps(data['results']['bindings'])
    findNearestMoodTrack.exposed = True

    def getvalue(self, data, key):
        return data['results']['bindings'][0][key.encode('UTF-8')]['value']

import os.path
conf = os.path.join(os.path.dirname(__file__), 'mood.conf')

if __name__ == '__main__':
    cherrypy.quickstart(MoodService(), config=conf)
else:
    cherrypy.tree.mount(MoodService(), config=conf)
