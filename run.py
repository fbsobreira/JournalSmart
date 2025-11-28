
# File: run.py
"""
/run.py
Application entry point
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=443,
        debug=True,
        ssl_context=('qbo.journalsmart.app+2.pem', 'qbo.journalsmart.app+2-key.pem')
    )