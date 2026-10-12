# Flask Student Management — Edit, Delete, Photo and PDF

## Features
- Search students by name, phone, place, course, or email.
- Add and edit records.
- Delete records after a confirmation prompt.
- Upload student photo (JPG/JPEG/PNG/WEBP).
- Upload and view one PDF document per student.
- Export all or filtered results to Excel.
- Print the student table.
- PostgreSQL via `DATABASE_URL`; local SQLite fallback for development.

## Run locally
`pip install -r requirements.txt`, then `python app.py`. Open http://127.0.0.1:5000.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`
Set `DATABASE_URL` to your Render PostgreSQL Internal Database URL and set a strong `SECRET_KEY`.

## IMPORTANT: existing database
The new version adds photo and PDF columns. `db.create_all()` will NOT add columns to an already-existing table. Back up your database and apply a proper migration before upgrading an existing installation. Do not delete the old database.

## IMPORTANT: uploaded-file persistence
Uploaded files are stored on the app filesystem by default. Render web service filesystems are ephemeral unless a persistent disk is configured. To retain photos/PDFs across redeploys, attach a persistent disk and set `UPLOAD_FOLDER` to its mount path (for example `/var/data/uploads`) if your Render plan supports it, or use object storage.

## Security
This starter has no login or access controls. Add authentication and authorization before exposing personal student records. Upload limit is 8 MB per request. Production apps should also validate actual file contents and scan uploads.
