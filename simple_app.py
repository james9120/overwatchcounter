from flask import Flask, render_template_string, jsonify
import os

# Initialize Flask app
app = Flask(__name__)

# Sample hero data
heroes = {
    "D.Va": "Tank",
    "Reinhardt": "Tank",
    "Zarya": "Tank",
    "Genji": "Damage",
    "Tracer": "Damage",
    "Widowmaker": "Damage",
    "Mercy": "Support",
    "Ana": "Support",
    "Lucio": "Support"
}

@app.route('/')
def index():
    return render_template_string("""
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
            .hero-item {
                margin-bottom: 10px;
                padding: 10px;
                border-radius: 5px;
                background-color: rgba(0, 0, 0, 0.5);
            }
            .tank {
                border-left: 4px solid #2980b9;
            }
            .damage {
                border-left: 4px solid #c0392b;
            }
            .support {
                border-left: 4px solid #27ae60;
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
                            Your app is now running correctly on Render!
                        </p>
                        
                        <h3 class="mt-4">Sample Heroes:</h3>
                        <div class="row">
                            {% for hero, role in heroes.items() %}
                                <div class="col-md-4">
                                    <div class="hero-item {{ role.lower() }}">
                                        <strong>{{ hero }}</strong>
                                        <div><small>{{ role }}</small></div>
                                    </div>
                                </div>
                            {% endfor %}
                        </div>
                        
                        <div class="text-center mt-4">
                            <p>
                                This is a simplified version of your app that's guaranteed to work 
                                on Render. Once this is working, you can gradually add your full 
                                functionality.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """, heroes=heroes)

@app.route('/status')
def status():
    return jsonify({
        "status": "ok",
        "message": "App is running correctly",
        "hero_count": len(heroes)
    })

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
