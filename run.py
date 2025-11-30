# File: run.py
"""
/run.py
Application entry point
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Build SSL context if both cert and key are provided
    ssl_context = None
    ssl_cert = app.config.get("SSL_CERT")
    ssl_key = app.config.get("SSL_KEY")
    if ssl_cert and ssl_key:
        ssl_context = (ssl_cert, ssl_key)

    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
        ssl_context=ssl_context,
    )
