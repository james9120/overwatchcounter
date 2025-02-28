from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Overwatch Counter Picker</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
        <style>
            body {
                background-color: #405275;
                color: #f0edf2;
                font-family: Arial, sans-serif;
                padding: 20px;
            }
            .card {
                background-color: rgba(0, 0, 0, 0.6);
                border: 2px solid #f99e1a;
                border-radius: 10px;
                padding: 20px;
                margin-top: 30px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card">
                        <h1 class="text-center" style="color: #f99e1a;">Overwatch Counter Picker</h1>
                        <p class="text-center mt-4">
                            The app is running! This is a minimal test page.
                        </p>
                        <div class="text-center mt-4">
                            <p>Server is operational. If you're seeing this page, your Flask app is working correctly.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/status')
def status():
    return "App is running"

# Run the app (this will be ignored by Gunicorn, but useful for local testing)
if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app with production settings
    app.run(host='0.0.0.0', port=port)
