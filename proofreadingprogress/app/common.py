from networkx.algorithms.dag import ancestors
from proofreadingprogress.app.sql import (
    connect_db,
    publishRootIds,
    publishedDict,
    tableDump,
    create_table,
    isPublished,
)
from flask import request, make_response, g, Blueprint, render_template
from flask import current_app, send_from_directory
import re
import json
import time
import requests
import os
import pandas as pd
import networkx as nx
from multiprocessing.pool import ThreadPool as Pool
from caveclient import CAVEclient
import numpy as np

__api_versions__ = [0]
__url_prefix__ = os.environ.get("PPROGRESS_URL_PREFIX", "progress")

# auth_token_file = open(
#     os.path.join(
#         os.path.expanduser("~"), ".cloudvolume/secrets/chunkedgraph-secret.json"
#     )
# )
# auth_token_json = json.loads(auth_token_file.read())
# auth_token = auth_token_json["token"]
# retrieved_token = g.get('auth_token', auth_token )
# engine = connect_db()

# -------------------------------
# ------ Access control and index
# -------------------------------


def index():
    from .. import __version__

    return f"ProofreadingProgress v{__version__}"


def query():
    return render_template("query.html", prefix=__url_prefix__)


def user():
    return render_template("user.html", prefix=__url_prefix__)


def publish():
    return render_template("publish.html", prefix=__url_prefix__)


def table():
    return render_template("table.html", prefix=__url_prefix__)


def getScripts(name):
    return send_from_directory(".", name)


def getStyles(name):
    return send_from_directory(".", name)


def home():
    resp = make_response()
    resp.headers["Access-Control-Allow-Origin"] = "*"
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
    current_app.logger.info(
        "%s - %s - %s - %s - %f.3"
        % (
            request.path.split("/")[-1],
            "1",
            "".join([url_split[-2], "/", url_split[-1]]),
            str(request.data),
            dt,
        )
    )

    print("Response time: %.3fms" % (dt))
    return response


def internal_server_error(error):
    dt = (time.time() - g.request_start_time) * 1000

    url_split = request.url.split("/")
    current_app.logger.error(
        "%s - %s - %s - %s - %f.3"
        % (
            request.path.split("/")[-1],
            "Server Error: " + error,
            "".join([url_split[-2], "/", url_split[-1]]),
            str(request.data),
            dt,
        )
    )
    return 500


def unhandled_exception(e):
    dt = (time.time() - g.request_start_time) * 1000

    url_split = request.url.split("/")
    current_app.logger.error(
        "%s - %s - %s - %s - %f.3"
        % (
            request.path.split("/")[-1],
            "Exception: " + str(e),
            "".join([url_split[-2], "/", url_split[-1]]),
            str(request.data),
            dt,
        )
    )
    return 500

# -------------------
# ------ Applications
# -------------------
def dataRequest(r):
    reqs = []
    graph = None
    args = r.args
    raw = json.loads(r.data)
    datastack = {
        "https://prodv1.flywire-daf.com/segmentation/api/v1/table/fly_v31/": "flywire_fafb_production",
        "https://minnie.microns-daf.com/segmentation/api/v1/table/fly_training_v2/": "minnie65_phase3_v0",
        "default": "flywire_fafb_production",
    }
    single = args.get("query")
    isFiltered = args.get("filtered", "false") == "true"
    isLineage = args.get("lineage", "false") == "true"
    dataset = args.get("dataset", "default")
    #use user token, instead of local token
    client = CAVEclient(datastack[dataset], auth_token=g.auth_token)
    #print(f"My current token is: {client.auth.token}")
    str_queries = raw.get("queries", "").split(",")
    queries = list(set(convertValidRootIds([single] if single else str_queries)))
    
    dictsBatched = multiThread(client, queries, isFiltered)
    dfdict = {k: v for d in dictsBatched for k, v in d.items()}
    if (isLineage):
        graphsBatched = multiThread(client, queries, graph=True)
        #graphs = [g for batch in graphsBatched for g in batch]
        batches = [batch for batch in graphsBatched]
        graphs = [g for g in batches]
        graph = nx.compose_all(graphs) if len(graphs) > 1 else graphs[0]

    for key, value in dfdict.items():
        try:
            jsonData = processToJson(str(key), value, graph)
            reqs.append(jsonData)
            csv = value.to_csv()
        except:
            #todo
            pass

    return {
        "json": reqs,
        "csv": csv if single else "",
    }

def multiThread(client, queries, filter = True, graph = False, b_size = 10, p_size = 10):
    bqueries = [(client, queries[i : i + b_size], filter) for i in range(0, len(queries), b_size)]
    p = Pool(p_size)
    results = p.imap(caveGRPH if graph else caveCHLG, bqueries)
    p.close()
    p.join()
    return results

def caveCHLG(args):
    return args[0].chunkedgraph.get_tabular_change_log(args[1], args[2])
#return list of graphs
def caveGRPH(args):
    return args[0].chunkedgraph.get_lineage_graph(root_id=args[1], as_nx_graph=True)

def processToJson(query, dataframe, graph=None):
    pubdict = None
    published = []
    try:
        with engine.connect() as conn:
            if graph != None:
                ancestors = list(nx.ancestors(graph, int(query)))
                existing = publishedDict(conn, ancestors)
                published = []
                for i in ancestors:
                    if existing.get(int(i)) == None:
                        published.append(i)
            pubdict = isPublished(conn, int(query))
    except:
        pass

    return {
        "key": query,
        "edits": json.loads(dataframe.to_json(orient="records", date_format="iso")),
        "lineage": len(published) > 0,
        "published": pubdict,
    }

def publish_neurons(args):
    if (True == True):
        return {}
    auth_header = {"Authorization": f"Bearer {g.auth_token}"}
    mustVerify = args.get("verify", "false") == "true"
    paperName = validPaper(args.get("pname", ""))
    doi = validDOI(args.get("doi", ""))
    aggregate = args.get("queries")
    # Bad Examples
    # paperName = validPaper('10.1101/2020.08.30.274225;')
    # doi = validDOI("10.1101/2020.08.30.274225;'")
    # aggregate = '32489ruiuiju823rq'
    dataset = args.get("dataset")
    rqueries = removeInvalidRootIds(aggregate.split())

    engine = connect_db(True)
    try:
        user = g.auth_user["id"]
    except:
        user = 0
    with engine.connect() as conn:
        # create_table(conn)
        # testInit(conn)
        existing = publishedDict(conn, rqueries)
        unpublished = []
        for i in rqueries:
            if existing.get(int(i)) == None:
                unpublished.append(i)
            else:
                existing[int(i)]["exist"] = True

        if len(unpublished) > 0:
            publishRootIds(conn, dataset, unpublished, doi, paperName, user)
            existing.update(publishedDict(conn, unpublished))

    return existing

def removeInvalidRootIds(ids):
    valid = []
    for id in ids:
        try:
            int(id)
            valid.append(id)
        except:
            pass
    return valid

def convertValidRootIds(ids):
    valid = []
    for id in ids:
        try:
            valid.append(np.uint64(id))
        except:
            pass
    return valid

def validDOI(doi):
    valid = not len(doi) or re.match("^10.\d{4,9}[-._;()/:A-Z0-9]+$", doi)
    return doi if valid else ""

def validPaper(pname):
    valid = not len(pname) or re.match("^[\w\-\s]+$", pname)
    return pname if valid else ""

def publishRequest(args):
    return pd.DataFrame.from_dict(publish_neurons(args), orient="index").to_html()

def publishDump():
    with engine.connect() as conn:
        return tableDump(conn).to_html()
