from flask import request, make_response, g
from flask import current_app, send_from_directory
import json
import time
import requests
import os
import pandas as pd
import networkx as nx

__api_versions__ = [0]
auth_token_file = open(os.path.join(os.path.expanduser("~"), ".cloudvolume/secrets/chunkedgraph-secret.json"))
auth_token_json = json.loads(auth_token_file.read())
auth_token = auth_token_json["token"]

# -------------------------------
# ------ Access control and index
# -------------------------------

def query():
    return send_from_directory('.', 'query.html')

def user():
    return send_from_directory('.', 'user.html')

def getScripts(name):
    return send_from_directory('.', name)

def getStyles(name):
    return send_from_directory('.', name)

def home():
    resp = make_response()
    resp.headers['Access-Control-Allow-Origin'] = '*'
    acah = "Origin, X-Requested-With, Content-Type, Accept"
    resp.headers["Access-Control-Allow-Headers"] = acah
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Connection"] = "keep-alive"
    return resp


# -------------------------------
# ------ Measurements and Logging
# -------------------------------

def before_request():
    g.request_start_time = time.time()


def after_request(response):
    dt = (time.time() - g.request_start_time) * 1000

    url_split = request.url.split("/")
    current_app.logger.info("%s - %s - %s - %s - %f.3" %
                            (request.path.split("/")[-1], "1",
                             "".join([url_split[-2], "/", url_split[-1]]),
                             str(request.data), dt))

    print("Response time: %.3fms" % (dt))
    return response


def internal_server_error(error):
    dt = (time.time() - g.request_start_time) * 1000

    url_split = request.url.split("/")
    current_app.logger.error("%s - %s - %s - %s - %f.3" %
                             (request.path.split("/")[-1],
                              "Server Error: " + error,
                              "".join([url_split[-2], "/", url_split[-1]]),
                              str(request.data), dt))
    return 500


def unhandled_exception(e):
    dt = (time.time() - g.request_start_time) * 1000

    url_split = request.url.split("/")
    current_app.logger.error("%s - %s - %s - %s - %f.3" %
                             (request.path.split("/")[-1],
                              "Exception: " + str(e),
                              "".join([url_split[-2], "/", url_split[-1]]),
                              str(request.data), dt))
    return 500

# -------------------
# ------ Applications
# -------------------
def getPublished(): 
    publishedData = pd.read_csv("./proofreadingprogress/app/cell_temp.csv", header=0, names=['dataset', 'rootid', 'published'])
    published = list(publishedData['rootid'].to_dict().values())
    return ' '.join([str(id) for id in published])

def apiRequest(args):
    auth_header = {"Authorization": f"Bearer {auth_token}"}
    isLineage = args.get('lineage', 'false') == "true"
    aggregate = args.get('queries')
    query = args.get('query')
    dataset = args.get('dataset')
    params = args.get('params')
    reqs = []
    graph = None
    graphable = True
    if aggregate:
        queryIds = aggregate.split()
        rootQuery = json.dumps({"root_ids": queryIds})
        fullURL = f"{dataset}tabular_change_log_many{params}"
        r = requests.get(fullURL, headers=auth_header, data=rootQuery)
        results = json.loads(r.content)
        if (isLineage):
            lineURL = f"{dataset}lineage_graph_multiple"
            g = requests.post(lineURL, headers=auth_header, 
                    data=rootQuery)
            try:
                graph = nx.node_link_graph(json.loads(g.content))
            except:
                graph = None
                graphable = False

        '''for query in queryIds:
            fullURL = f"https://minnie.microns-daf.com/segmentation/api/v1/table/fly_training_v2/root/{query}/tabular_change_log?{isRootIds}&{isFiltered}"
            r = requests.get(fullURL, headers=auth_header)
            dataframe = pd.read_json(r.content, 'columns')
            #json.loads(
            reqs.append(dataframe.to_json(orient='records', date_format='iso'))'''

        for key in results.keys():
            dataframe = pd.DataFrame.from_dict(json.loads(results[key]))
            jsonData = {
                'key': key,
                'edits': json.loads(dataframe.to_json(orient='records', date_format='iso')),
                'lineage' : list(nx.ancestors(graph, int(key))) if graph != None else list()
            }
            reqs.append(jsonData)
    else:
        fullURL = f"{dataset}root/{query}/tabular_change_log{params}"
        r = requests.get(fullURL, headers=auth_header)
        results = json.loads(r.content)
        if (isLineage):
            lineURL = f"{dataset}root/{query}/lineage_graph"
            g = requests.get(lineURL, headers=auth_header)
            try:
                graph = nx.node_link_graph(json.loads(g.content))
            except:
                graph = None
                graphable = False

        dataframe = pd.read_json(r.content, 'columns')
        jsonData = {
            'key': query,
            'edits': json.loads(dataframe.to_json(orient='records', date_format='iso')),
            'lineage' : list(nx.ancestors(graph, int(query))) if graph != None else list()
        }
        reqs.append(jsonData)
        csv = dataframe.to_csv()
        
    content = {
        'json': reqs,
        'csv': '' if aggregate else csv,
        'graph': graphable
    }
    return content