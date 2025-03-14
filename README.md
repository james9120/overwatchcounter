# Overwatch Counter Picker

A comprehensive web app that helps Overwatch 2 players find effective counter picks against enemy heroes and track their match performance.

## Features

### Single Hero Counter
- Select an individual enemy hero that's giving you trouble
- Choose your preferred role (Tank, Damage, or Support)
- Get recommended counter picks with effectiveness ratings and tactical tips
- Filter heroes by difficulty level for beginner-friendly options
- View detailed enemy hero weaknesses and counter strategies

### Team Counter Analysis
- Select multiple enemy heroes (up to 5) to analyze an entire enemy team composition
- Find the most effective counter heroes for your selected role against the full team
- View individual matchup ratings for each recommended counter against each enemy
- See detailed weaknesses for all selected enemy heroes
- Get beginner-friendly recommendations for effective counters that are easy to play

### Game Tracker
- Record your match results with detailed information:
  - Hero played, map, and match outcome (win/loss/draw)
  - SR changes for competitive matches
  - Enemy team composition
  - Personal notes about the match
- View stats for individual heroes:
  - Win rates and total games played
  - Map-specific performance metrics
  - Average SR changes
- Track overall performance with summary statistics:
  - Role-based performance comparison
  - SR trend visualization over time
  - Identify your best heroes based on win rate
  - Analyze map-specific strengths and weaknesses

## Account System
- Create a personal account to save your game history
- Secure login with password protection
- All your stats persist between sessions
- Track your competitive progress over time

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
- `templates/` - HTML templates
- `Overwatch Counters.xlsx` - Data file

### Static Files

Ensure your static file structure includes:
```
/static/images/heroes/tank/     (for tank hero images)
/static/images/heroes/damage/   (for damage hero images)
/static/images/heroes/support/  (for support hero images)
/static/images/heroes/unknown/  (for unknown role hero images)
/static/images/roles/           (for role icons)
```

Each hero image should be named according to the pattern:
`Icon-Hero_Name.webp`

## Team Counter Analysis Methodology

The team counter analysis feature calculates the most effective heroes against multiple enemy heroes by:

1. Evaluating how well each potential counter performs against every selected enemy
2. Calculating an average effectiveness score across all matchups
3. Determining which counters provide the most value against the entire enemy team
4. Sorting heroes by their overall effectiveness against the team composition

This is especially useful for:
- Countering enemy team compositions in competitive play
- Finding heroes that counter multiple enemies at once
- Adapting your hero selection when facing coordinated team strategies

## Game Tracker Methodology

The game tracking system offers insights through:

1. Historical match recording with detailed data points
2. Aggregated statistics by hero, role, and map
3. Win rate calculation and performance visualization
4. SR trend analysis to track competitive progress
5. Identifying your strongest heroes and maps based on actual performance

## Troubleshooting

If you encounter errors during deployment:

1. Check the application logs in your Render dashboard
2. Verify that your Excel file is correctly uploaded
3. Ensure all hero images are in the correct folders with proper naming
4. Check that the Procfile is in the root directory of your project
5. If database errors occur, check file permissions for SQLite
