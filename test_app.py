from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test App</title>
        <style>body { background-color: green; color: white; }</style>
    </head>
    <body>
        <h1>Test App</h1>
        <p>This is a completely separate Flask application.</p>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
