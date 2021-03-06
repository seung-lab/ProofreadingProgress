from werkzeug.serving import WSGIRequestHandler
from proofreadingprogress.app import create_app

application = create_app()

if __name__ == "__main__":

    WSGIRequestHandler.protocol_version = "HTTP/1.1"

    application.run(
        host="0.0.0.0", port=80, debug=False, threaded=True, ssl_context="adhoc"
    )
