import sys
from werkzeug.serving import WSGIRequestHandler
import os

from proofreadingprogress.app import create_app
#from caveclient import CAVEclient

app = create_app()

if __name__ == '__main__':
    # client = CAVEclient("flywire_fafb_production", auth_token="4d73dbd6b8cc975c00a35ffa91336431")
    # client = CAVEclient(auth_token="4d73dbd6b8cc975c00a35ffa91336431")
    # client = CAVEclient("flywire_fafb_production")
    # auth = client.auth
    # client.chunkedgraph.get_tabular_change_log([720575940613252063])
    # nfo = auth.get_user_information(user_id=[1, 2])
    # print(nfo)
    # print(f"My current token is: {auth.token}")
    print(sys.argv)
    assert len(sys.argv) == 2
    HOME = os.path.expanduser("~")

    port = int(sys.argv[1])

    # Set HTTP protocol
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    # WSGIRequestHandler.protocol_version = "HTTP/2.0"

    print("Port: %d" % port)


    app.run(host='localhost',
            port=port,
            debug=True,
            threaded=True,
            ssl_context='adhoc')