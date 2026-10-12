# Flask Student Management — Stable Package

## Included
- Search, add, edit, delete student records
- Student photo upload (JPG/JPEG/PNG/WEBP)
- PDF upload and browser viewing
- Excel export and print layout
- PostgreSQL support through `DATABASE_URL`
- Startup compatibility migration for three optional upload columns

## Deploy on Render
Build command: `pip install -r requirements.txt`
Start command: `gunicorn app:app`
Set `DATABASE_URL` to the PostgreSQL Internal Database URL and set a strong `SECRET_KEY`.

## Database compatibility
At startup, the app creates missing tables and adds only the missing upload metadata columns to the `student` table. It does not delete rows. Back up your database before deploying. If your existing table has a different name or a different schema, this automatic compatibility step may not fit your database; check Render logs before making schema changes.

## File persistence
Render web-service filesystems are ephemeral unless a persistent disk is configured. Set `UPLOAD_FOLDER` to a persistent disk mount (if available on your plan) or use external object storage to preserve uploaded photos/PDFs across redeploys.

## Security
This starter does not include authentication. Add login and role permissions before exposing student records publicly. Uploads are limited to 8 MB per request; production should also validate file contents and scan uploads.


## Professional student profile

Use **View** beside any student to open a dedicated profile page. The profile includes the student's photo, contact details, course, joining date, and uploaded PDF link. Select **Print profile** to print it or choose **Save as PDF** in the browser print dialog. The dashboard also has improved responsive styling, search, summary cards, and a clearer action layout.
