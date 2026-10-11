# Flask Student Record Manager

A beginner-friendly Flask + PostgreSQL application with add, list, and delete features.

## Files
- `app.py`: Flask routes and PostgreSQL operations
- `templates/index.html`: web interface
- `requirements.txt`: Python dependencies
- `.gitignore`: excludes secrets and temporary files

## Configure the database safely

The app reads the database connection URL from the environment variable `DATABASE_URL`. Do not hardcode database credentials in `app.py` or commit them to GitHub.

### On Render
1. Open your PostgreSQL database in Render and confirm its connection URL.
2. Open your Flask Web Service.
3. Go to **Environment** and add a variable:
   - Key: `DATABASE_URL`
   - Value: paste your PostgreSQL connection URL
4. Save changes and redeploy if required.

Because the database URL was shared in a chat, rotate/change its database password in Render before using it, then update the `DATABASE_URL` value with the new connection URL. Treat the URL as a password.

## Deploy on Render
1. Create a PostgreSQL database on Render.
2. Create a Render Web Service connected to this GitHub repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add `DATABASE_URL` in the web service's Environment settings. Use the Internal Database URL when both services are in the same Render region.
6. Deploy the web service.

The app creates the `students` table on startup if it does not exist.

## Local development
1. Install Python 3.10+ and PostgreSQL.
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Set `DATABASE_URL` to your PostgreSQL connection URL in your local environment.
5. Run: `python app.py`

Never commit database credentials or `.env` files to GitHub.

## Routes
- `/`: list students and show the form
- `/add`: add a student (POST)
- `/delete/<id>`: delete a student (POST)
- `/health`: check application/database connectivity
