# Overwatch Counter Picker

A web app that helps Overwatch 2 players find effective counter picks against enemy heroes.

## Deployment Instructions

### Prerequisites
- Your Excel file named `Overwatch Counters.xlsx` with the required columns
- A free Render.com account (or similar platform)
- Git installed on your computer

### Local Testing

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the app locally:
   ```
   python app.py
   ```

3. Visit `http://localhost:5000` in your web browser

### Deploying to Render

1. Push your code to a GitHub repository

2. Log in to Render.com

3. Create a new Web Service:
   - Connect to your GitHub repository
   - Select "Python" as the runtime
   - Set the build command: `pip install -r requirements.txt`
   - Set the start command: `gunicorn app:app`
   - Choose a free or paid plan based on your needs

4. Add environment variables (if needed)

5. Upload your Excel file:
   - After deployment, go to your Render dashboard
   - Select your web service
   - Go to the "Shell" tab
   - Upload your `Overwatch Counters.xlsx` file using the file uploader

### File Structure

Make sure your deployment includes:
- `app.py` - The main Flask application
- `requirements.txt` - Dependencies
- `Procfile` - Instructions for the web server
- `static/` - Folder containing your hero images
- `Overwatch Counters.xlsx` - Data file

### Static Files

Ensure your static file structure includes:
```
/static/images/heroes/tank/     (for tank hero images)
/static/images/heroes/damage/   (for damage hero images)
/static/images/heroes/support/  (for support hero images)
/static/images/heroes/unknown/  (for unknown role hero images)
```

Each hero image should be named according to the pattern:
`Icon-Hero_Name.webp`

## Troubleshooting

If you encounter errors during deployment:

1. Check the application logs in your Render dashboard
2. Verify that your Excel file is correctly uploaded
3. Ensure all hero images are in the correct folders with proper naming
4. Check that the Procfile is in the root directory of your project
