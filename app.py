import os
from io import BytesIO
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")

database_url = os.environ.get("DATABASE_URL", "").strip()
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url:
    # Allow the app to start locally, but Render should have DATABASE_URL set.
    database_url = "sqlite:///students_local.db"
    print("WARNING: DATABASE_URL is not set; using local SQLite for development.")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db = SQLAlchemy(app)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    place = db.Column(db.String(120), nullable=True)
    course = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(160), nullable=True)
    joined_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def filtered_students():
    query = Student.query
    search = request.args.get("q", "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(or_(
            Student.name.ilike(like),
            Student.phone.ilike(like),
            Student.place.ilike(like),
            Student.course.ilike(like),
            Student.email.ilike(like),
        ))
    return query.order_by(Student.id.desc()), search


def read_student_form(student=None):
    name = request.form.get("name", "").strip()
    if not name:
        flash("Student name is required.", "error")
        return None

    joined_text = request.form.get("joined_date", "").strip()
    joined_date = None
    if joined_text:
        try:
            joined_date = datetime.strptime(joined_text, "%Y-%m-%d").date()
        except ValueError:
            flash("Please enter a valid joining date.", "error")
            return None

    values = {
        "name": name,
        "phone": request.form.get("phone", "").strip() or None,
        "place": request.form.get("place", "").strip() or None,
        "course": request.form.get("course", "").strip() or None,
        "email": request.form.get("email", "").strip() or None,
        "joined_date": joined_date,
    }
    if student is not None:
        for key, value in values.items():
            setattr(student, key, value)
    else:
        student = Student(**values)
        db.session.add(student)
    return student


@app.get("/")
def index():
    query, search = filtered_students()
    students = query.all()
    return render_template("index.html", students=students, search=search, total=Student.query.count())


@app.post("/students/add")
def add_student():
    student = read_student_form()
    if student is not None:
        try:
            db.session.commit()
            flash("Student added successfully.", "success")
        except Exception:
            db.session.rollback()
            app.logger.exception("Could not add student")
            flash("Could not save the student. Check the server logs.", "error")
    return redirect(url_for("index"))


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        updated = read_student_form(student)
        if updated is not None:
            try:
                db.session.commit()
                flash("Student details updated successfully.", "success")
                return redirect(url_for("index"))
            except Exception:
                db.session.rollback()
                app.logger.exception("Could not update student")
                flash("Could not update the student. Check the server logs.", "error")
    return render_template("edit.html", student=student)


@app.get("/students/export.xlsx")
def export_students():
    query, search = filtered_students()
    students = query.all()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Students"
    headers = ["ID", "Name", "Phone", "Place", "Course", "Email", "Joined Date"]
    sheet.append(headers)

    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="234E70")
        cell.alignment = Alignment(horizontal="center")

    for student in students:
        sheet.append([
            student.id,
            student.name,
            student.phone or "",
            student.place or "",
            student.course or "",
            student.email or "",
            student.joined_date.isoformat() if student.joined_date else "",
        ])

    for column_cells in sheet.columns:
        max_len = max((len(str(c.value or "")) for c in column_cells), default=10)
        sheet.column_dimensions[get_column_letter(column_cells[0].column)].width = min(max_len + 3, 40)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    filename = "students_filtered.xlsx" if search else "students.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/health")
def health():
    # Lightweight health endpoint; verifies that the database can be reached.
    try:
        db.session.execute(db.text("SELECT 1"))
        return {"status": "ok", "database": "connected"}, 200
    except Exception:
        app.logger.exception("Database health check failed")
        return {"status": "error", "database": "unavailable"}, 503


with app.app_context():
    # Creates missing tables without deleting existing records.
    # For larger production apps, use Flask-Migrate/Alembic for schema changes.
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
