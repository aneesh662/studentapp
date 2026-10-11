import os
from flask import Flask, render_template, request, redirect, url_for
import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    return psycopg.connect(db_url, row_factory=dict_row)


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                course VARCHAR(100) NOT NULL
            )
        """)


@app.route("/")
def home():
    with get_db() as conn:
        students = conn.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()
    return render_template("index.html", students=students)


@app.route("/add", methods=["POST"])
def add_student():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    course = request.form.get("course", "").strip()

    if not name or not phone or not course:
        return "Please fill in every field.", 400

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO students (name, phone, course)
            VALUES (%s, %s, %s)
            """,
            (name, phone, course),
        )
    return redirect(url_for("home"))


@app.route("/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM students WHERE id = %s",
            (student_id,),
        )
    return redirect(url_for("home"))


@app.route("/health")
def health():
    with get_db() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "database": "connected"}


# The table is created automatically when the application starts.
init_db()

if __name__ == "__main__":
    app.run(debug=True)
