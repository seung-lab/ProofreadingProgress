from flask import request, make_response, g
from flask import current_app, send_from_directory
import json
import time
import requests
import os
import pandas as pd


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

def apiRequest(args):
    auth_header = {"Authorization": f"Bearer {auth_token}"}
    rootIds = 'root_ids=' + args.get('root_ids', 'false')
    filtered = 'filtered=' + args.get('filtered', 'true')
    aggregate = args.get('agg')
    queryIds = args.get('query').split()
    reqs = []
    for id in queryIds:
        fullURL = f"https://prodv1.flywire-daf.com/segmentation/api/v1/table/fly_v31/root/{id}/tabular_change_log?{rootIds}&{filtered}"
        r = requests.get(fullURL, headers=auth_header)
        dataframe = pd.read_json(r.content, 'columns')
        reqs.append(dataframe.to_json(orient='records', date_format='iso'))
        #dataframe.groupby('user_id').agg(total_edits=pd.NamedAgg(column='total_edits", aggfunc=sum))
        csv = dataframe.to_csv()
    
    if aggregate:
        jsonstr = json.dumps(reqs)
        csv = ''
    else:
        jsonstr = reqs[0]
    content = {
        'json': jsonstr,
        'csv': csv
    }
    return content