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
    isRootIds = 'root_ids=' + args.get('root_ids', 'false')
    isFiltered = 'filtered=' + args.get('filtered', 'true')
    aggregate = args.get('queries')
    query = args.get('query')
    reqs = []
    if aggregate:
        queryIds = aggregate.split()
        fullURL = f"https://prodv1.flywire-daf.com/segmentation/api/v1/table/fly_v31/tabular_change_log_many?{isRootIds}&{isFiltered}"
        r = requests.get(fullURL, headers=auth_header, 
                data=json.dumps({"root_ids": queryIds}))

        lineageURL = f"https://prodv1.flywire-daf.com/segmentation/api/v1/table/fly_v31/lineage_graph_multiple"
        g = requests.post(lineageURL, headers=auth_header, 
                data=json.dumps({"root_ids": queryIds}))

        results = json.loads(r.content)
        graph = nx.node_link_graph(json.loads(g.content))
        for key in results.keys():
            dataframe = pd.DataFrame.from_dict(json.loads(results[key]))
            jsonData = {
                'edits': json.loads(dataframe.to_json(orient='records', date_format='iso')),
                'lineage' : list(nx.ancestors(graph, int(key)))
            }
            reqs.append(jsonData)
    else:
        fullURL = f"https://prodv1.flywire-daf.com/segmentation/api/v1/table/fly_v31/root/{query}/tabular_change_log?{isRootIds}&{isFiltered}"
        lineageURL = f"https://prodv1.flywire-daf.com/segmentation/api/v1/table/fly_v31/root/{query}/lineage_graph"
        r = requests.get(fullURL, headers=auth_header)
        dataframe = pd.read_json(r.content, 'columns')
        g = requests.get(lineageURL, headers=auth_header)
        graph = nx.node_link_graph(json.loads(g.content))
        jsonData = {
            'edits': json.loads(dataframe.to_json(orient='records', date_format='iso')),
            'lineage' : list(nx.ancestors(graph, int(query)))
        }
        reqs.append(jsonData)
        csv = dataframe.to_csv()
        
    if aggregate:
        jsonstr = reqs
        csv = ''
    else:
        jsonstr = reqs[0]
    content = {
        'json': jsonstr,
        'csv': csv
    }
    return content