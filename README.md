# Flask Student Management App

Features:
- Search students by name, phone, place, course, or email.
- Add and edit student records.
- Export all records or search-filtered records to Excel (.xlsx).
- Print the visible student table.
- PostgreSQL support through `DATABASE_URL`.
- `/health` endpoint for a basic database connectivity check.

## Files
- `app.py`: Flask routes, SQLAlchemy model, Excel export.
- `templates/index.html`: Student list, search, add form, export and print.
- `templates/edit.html`: Edit student details.
- `static/style.css`: Responsive styling and print stylesheet.
- `requirements.txt`: Python dependencies.
- `render.yaml`: Optional Render Blueprint configuration.

## Run locally
1. Create a virtual environment.
2. Install packages: `pip install -r requirements.txt`
3. Set `SECRET_KEY` and optionally `DATABASE_URL`.
4. Run: `python app.py`
5. Open `http://127.0.0.1:5000`.

If `DATABASE_URL` is not set locally, the app uses `students_local.db` for development only.

## Deploy to Render
1. Push this project to a GitHub repository.
2. In Render, create a PostgreSQL database and a Web Service in the same region.
3. Set `DATABASE_URL` on the Web Service to the database's Internal Database URL.
4. Set a strong `SECRET_KEY` environment variable.
5. Build command: `pip install -r requirements.txt`
6. Start command: `gunicorn app:app`
7. Deploy and check `/health`.

Alternatively, use `render.yaml` as a Render Blueprint. If a database with the same name already exists, link the existing database rather than creating a duplicate.

## Important database notes
- The app calls `db.create_all()` at startup. It creates missing tables and does not intentionally delete existing records.
- For future schema changes in a production app, use migrations (for example Flask-Migrate/Alembic); `create_all()` does not update existing tables.
- Keep database URLs and secrets out of GitHub. Set them in Render Environment.
- This starter app has no login/role-based access control. Add authentication and authorization before exposing student personal information publicly.
