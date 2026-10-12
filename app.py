import os
import uuid
import logging
from pathlib import Path
from io import BytesIO
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_ROOT = Path(os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "uploads")))
PHOTO_DIR = UPLOAD_ROOT / "photos"
PDF_DIR = UPLOAD_ROOT / "documents"
PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
PDF_EXTENSIONS = {"pdf"}
MAX_CONTENT_LENGTH = 8 * 1024 * 1024

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-key-change-me")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

# Render provides DATABASE_URL in Environment. SQLite fallback is for local testing only.
database_url = os.environ.get("DATABASE_URL", "").strip()
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(BASE_DIR / "students_local.db")
    app.logger.warning("DATABASE_URL is not set; using local SQLite. Set DATABASE_URL on Render.")

db = SQLAlchemy(app)


class Student(db.Model):
    __tablename__ = "student"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40))
    place = db.Column(db.String(120))
    course = db.Column(db.String(120))
    email = db.Column(db.String(160))
    joined_date = db.Column(db.Date)
    photo_filename = db.Column(db.String(255))
    document_filename = db.Column(db.String(255))
    document_original_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def initialize_database():
    """Create a missing table and safely add upload columns to the existing student table."""
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        if Student.__tablename__ not in table_names:
            return
        existing_columns = {column["name"] for column in inspector.get_columns(Student.__tablename__)}
        new_columns = {
            "photo_filename": "VARCHAR(255)",
            "document_filename": "VARCHAR(255)",
            "document_original_name": "VARCHAR(255)",
        }
        # Names and SQL types here are fixed constants, not user-provided input.
        with db.engine.begin() as connection:
            for column_name, sql_type in new_columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(
                        f'ALTER TABLE "{Student.__tablename__}" ADD COLUMN "{column_name}" {sql_type}'
                    ))
                    app.logger.info("Added missing database column: %s", column_name)


def ensure_upload_dirs():
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)


def get_extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def store_upload(file_obj, allowed_extensions, folder, label):
    if not file_obj or not file_obj.filename:
        return None
    safe_original = secure_filename(file_obj.filename)
    ext = get_extension(safe_original)
    if not safe_original or ext not in allowed_extensions:
        raise ValueError(f"Invalid {label} file. Please use an allowed file type.")
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_obj.save(folder / stored_name)
    return stored_name


def delete_upload(folder, filename):
    if not filename:
        return
    try:
        (folder / Path(filename).name).unlink(missing_ok=True)
    except OSError:
        app.logger.exception("Could not remove uploaded file")


def find_students():
    query = Student.query
    search_term = request.args.get("q", "").strip()
    if search_term:
        pattern = f"%{search_term}%"
        query = query.filter(or_(
            Student.name.ilike(pattern),
            Student.phone.ilike(pattern),
            Student.place.ilike(pattern),
            Student.course.ilike(pattern),
            Student.email.ilike(pattern),
        ))
    return query.order_by(Student.id.desc()), search_term


def form_data():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Student name is required.", "error")
        return None
    date_text = request.form.get("joined_date", "").strip()
    try:
        joined_date = datetime.strptime(date_text, "%Y-%m-%d").date() if date_text else None
    except ValueError:
        flash("Enter a valid joining date.", "error")
        return None
    email = request.form.get("email", "").strip() or None
    return {
        "name": name,
        "phone": request.form.get("phone", "").strip() or None,
        "place": request.form.get("place", "").strip() or None,
        "course": request.form.get("course", "").strip() or None,
        "email": email,
        "joined_date": joined_date,
    }


def process_uploads(student):
    """Save new uploads; leave current files unchanged when fields are empty."""
    photo_obj = request.files.get("photo")
    pdf_obj = request.files.get("document")
    new_photo = None
    new_pdf = None
    try:
        if photo_obj and photo_obj.filename:
            new_photo = store_upload(photo_obj, PHOTO_EXTENSIONS, PHOTO_DIR, "photo")
        if pdf_obj and pdf_obj.filename:
            new_pdf = store_upload(pdf_obj, PDF_EXTENSIONS, PDF_DIR, "PDF document")
    except ValueError as error:
        delete_upload(PHOTO_DIR, new_photo)
        delete_upload(PDF_DIR, new_pdf)
        flash(f"{error} Photo types: JPG, JPEG, PNG, WEBP. Document type: PDF.", "error")
        return False

    if new_photo:
        delete_upload(PHOTO_DIR, student.photo_filename)
        student.photo_filename = new_photo
    if new_pdf:
        delete_upload(PDF_DIR, student.document_filename)
        student.document_filename = new_pdf
        pdf_obj_name = secure_filename(pdf_obj.filename)
        student.document_original_name = pdf_obj_name or "document.pdf"
    return True


@app.get("/")
def index():
    try:
        query, search_term = find_students()
        students = query.all()
        total = Student.query.count()
        return render_template("index.html", students=students, search=search_term, total=total)
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not load student records")
        return "Database error while loading students. Check Render runtime logs.", 500


@app.post("/students/add")
def add_student():
    values = form_data()
    if values is None:
        return redirect(url_for("index"))
    student = Student(**values)
    saved_file_names = []
    try:
        db.session.add(student)
        db.session.flush()
        if not process_uploads(student):
            db.session.rollback()
            return redirect(url_for("index"))
        db.session.commit()
        flash("Student added successfully.", "success")
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not add student")
        flash("Could not save student. Check Render runtime logs.", "error")
    return redirect(url_for("index"))


@app.get("/students/<int:student_id>")
def student_profile(student_id):
    student = db.get_or_404(Student, student_id)
    return render_template("profile.html", student=student)


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student(student_id):
    student = db.get_or_404(Student, student_id)
    if request.method == "POST":
        values = form_data()
        if values is None:
            return redirect(url_for("edit_student", student_id=student.id))
        for key, value in values.items():
            setattr(student, key, value)
        if not process_uploads(student):
            db.session.rollback()
            return redirect(url_for("edit_student", student_id=student.id))
        try:
            db.session.commit()
            flash("Student details updated.", "success")
            return redirect(url_for("index"))
        except Exception:
            db.session.rollback()
            app.logger.exception("Could not update student")
            flash("Could not update student. Check Render runtime logs.", "error")
    return render_template("edit.html", student=student)


@app.post("/students/<int:student_id>/delete")
def delete_student(student_id):
    student = db.get_or_404(Student, student_id)
    photo_name = student.photo_filename
    pdf_name = student.document_filename
    try:
        db.session.delete(student)
        db.session.commit()
        delete_upload(PHOTO_DIR, photo_name)
        delete_upload(PDF_DIR, pdf_name)
        flash("Student deleted.", "success")
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not delete student")
        flash("Could not delete student. Check Render runtime logs.", "error")
    return redirect(url_for("index", q=request.form.get("q", "").strip()))


@app.get("/students/<int:student_id>/photo")
def student_photo(student_id):
    student = db.get_or_404(Student, student_id)
    if not student.photo_filename:
        abort(404)
    path = PHOTO_DIR / Path(student.photo_filename).name
    if not path.is_file():
        abort(404)
    return send_file(path, conditional=True)


@app.get("/students/<int:student_id>/document")
def view_document(student_id):
    student = db.get_or_404(Student, student_id)
    if not student.document_filename:
        abort(404)
    path = PDF_DIR / Path(student.document_filename).name
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype="application/pdf", as_attachment=False,
                     download_name=student.document_original_name or "student-document.pdf")


@app.get("/students/export.xlsx")
def export_students():
    try:
        query, search_term = find_students()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Students"
        sheet.append(["ID", "Name", "Phone", "Place", "Course", "Email", "Joined Date", "Photo Uploaded", "PDF Document"])
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="234E70")
            cell.alignment = Alignment(horizontal="center")
        for student in query.all():
            sheet.append([
                student.id, student.name, student.phone or "", student.place or "",
                student.course or "", student.email or "",
                student.joined_date.isoformat() if student.joined_date else "",
                "Yes" if student.photo_filename else "No",
                student.document_original_name or ("Yes" if student.document_filename else "No"),
            ])
        for column in sheet.columns:
            max_length = max((len(str(cell.value or "")) for cell in column), default=10)
            sheet.column_dimensions[get_column_letter(column[0].column)].width = min(max_length + 3, 40)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return send_file(output, as_attachment=True,
            download_name="students_filtered.xlsx" if search_term else "students.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not export students")
        return "Database error while exporting. Check Render runtime logs.", 500


@app.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}, 200
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Database health check failed")
        return {"status": "error", "database": "unavailable"}, 503


ensure_upload_dirs()
initialize_database()

if __name__ == "__main__":
    app.run(debug=True)
