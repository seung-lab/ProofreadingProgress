import sys
from werkzeug.serving import WSGIRequestHandler
import os

from proofreadingprogress.app import create_app

# from caveclient import CAVEclient

app = create_app()

os.environ["INFO_URL"] = "global.daf-apis.com/info"
os.environ["AUTH_URL"] = "global.daf-apis.com/auth"
os.environ["STICKY_AUTH_URL"] = "global.daf-apis.com/sticky_auth"

if __name__ == "__main__":
    print(sys.argv)
    assert len(sys.argv) == 2
    HOME = os.path.expanduser("~")

    port = int(sys.argv[1])

    # Set HTTP protocol
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    # WSGIRequestHandler.protocol_version = "HTTP/2.0"

    print("Port: %d" % port)

    app.run(host="localhost", port=port, debug=True, threaded=True, ssl_context="adhoc")
