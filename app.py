from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sqlite3
import csv
import io
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = "library_secret_key_super_secure"

# Database file location
DATABASE = "library.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            isbn TEXT,
            cover_url TEXT,
            total_copies INTEGER DEFAULT 1,
            available_copies INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            member_type TEXT DEFAULT 'Student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            issue_date DATE DEFAULT (date('now')),
            due_date DATE NOT NULL,
            return_date DATE,
            fine_amount REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Issued',
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(books)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "isbn" not in existing_cols:
        cursor.execute("ALTER TABLE books ADD COLUMN isbn TEXT")
    if "cover_url" not in existing_cols:
        cursor.execute("ALTER TABLE books ADD COLUMN cover_url TEXT")
    if "total_copies" not in existing_cols:
        cursor.execute("ALTER TABLE books ADD COLUMN total_copies INTEGER DEFAULT 1")
    if "available_copies" not in existing_cols:
        cursor.execute("ALTER TABLE books ADD COLUMN available_copies INTEGER DEFAULT 1")

    conn.commit()
    conn.close()


@app.route("/")
def home():
    search_query = request.args.get("q", "").strip()
    category_filter = request.args.get("category", "").strip()
    status_filter = request.args.get("status", "").strip()

    conn = get_db_connection()

    # Build SQL query based on filters
    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if search_query:
        query += " AND (title LIKE ? OR author LIKE ? OR category LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard])

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY id DESC"

    books = conn.execute(query, params).fetchall()

    # Get distinct categories for filter dropdown
    categories = conn.execute(
        "SELECT DISTINCT category FROM books ORDER BY category"
    ).fetchall()

    # Calculate statistics
    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    available_books = conn.execute(
        "SELECT COUNT(*) FROM books WHERE status = 'Available'"
    ).fetchone()[0]
    borrowed_books = conn.execute(
        "SELECT COUNT(*) FROM books WHERE status = 'Borrowed'"
    ).fetchone()[0]
    categories_count = conn.execute(
        "SELECT COUNT(DISTINCT category) FROM books"
    ).fetchone()[0]

    conn.close()

    stats = {
        "total": total_books,
        "available": available_books,
        "borrowed": borrowed_books,
        "categories": categories_count
    }

    return render_template(
        "index.html",
        books=books,
        categories=[c["category"] for c in categories],
        stats=stats,
        search_query=search_query,
        selected_category=category_filter,
        selected_status=status_filter
    )


@app.route("/add", methods=["POST"])
def add_book():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    category = request.form.get("category", "").strip()
    status = request.form.get("status", "Available").strip()

    if title and author and category:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO books (title, author, category, status)
            VALUES (?, ?, ?, ?)
            """,
            (title, author, category, status)
        )
        conn.commit()
        conn.close()
        flash(f'Book "{title}" added successfully!', "success")
    else:
        flash("Please fill in all required fields.", "danger")

    return redirect(url_for("home"))


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_book(id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (id,)).fetchone()

    if not book:
        conn.close()
        flash("Book not found!", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()
        status = request.form.get("status", "Available").strip()

        if title and author and category:
            conn.execute(
                """
                UPDATE books
                SET title = ?, author = ?, category = ?, status = ?
                WHERE id = ?
                """,
                (title, author, category, status, id)
            )
            conn.commit()
            conn.close()
            flash(f'Book "{title}" updated successfully!', "success")
            return redirect(url_for("home"))
        else:
            flash("All fields are required.", "danger")

    conn.close()
    return render_template("edit.html", book=book)


@app.route("/toggle/<int:id>")
def toggle_status(id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (id,)).fetchone()

    if book:
        new_status = "Borrowed" if book["status"] == "Available" else "Available"
        conn.execute("UPDATE books SET status = ? WHERE id = ?", (new_status, id))
        conn.commit()
        flash(f'Status for "{book["title"]}" changed to {new_status}.', "info")

    conn.close()
    return redirect(url_for("home"))


@app.route("/delete/<int:id>")
def delete_book(id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (id,)).fetchone()

    if book:
        conn.execute("DELETE FROM books WHERE id = ?", (id,))
        conn.commit()
        flash(f'Book "{book["title"]}" deleted successfully!', "warning")

    conn.close()
    return redirect(url_for("home"))


@app.route("/export/csv")
def export_csv():
    search_query = request.args.get("q", "").strip()
    category_filter = request.args.get("category", "").strip()
    status_filter = request.args.get("status", "").strip()

    conn = get_db_connection()
    query = "SELECT id, title, author, category, status, created_at FROM books WHERE 1=1"
    params = []

    if search_query:
        query += " AND (title LIKE ? OR author LIKE ? OR category LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard])

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY id DESC"

    books = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Author", "Category", "Status", "Date Added"])

    for book in books:
        writer.writerow([
            book["id"],
            book["title"],
            book["author"],
            book["category"],
            book["status"],
            book["created_at"]
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=library_books.csv"}
    )


@app.route("/members")
def members_page():
    search_query = request.args.get("q", "").strip()
    conn = get_db_connection()
    query = "SELECT * FROM members WHERE 1=1"
    params = []
    if search_query:
        query += " AND (name LIKE ? OR email LIKE ? OR phone LIKE ? OR member_type LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])
    query += " ORDER BY id DESC"
    members = conn.execute(query, params).fetchall()
    
    total_members = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    students_count = conn.execute("SELECT COUNT(*) FROM members WHERE member_type = 'Student'").fetchone()[0]
    faculty_count = conn.execute("SELECT COUNT(*) FROM members WHERE member_type = 'Faculty'").fetchone()[0]
    conn.close()
    
    return render_template(
        "members.html",
        members=members,
        search_query=search_query,
        stats={"total": total_members, "students": students_count, "faculty": faculty_count}
    )


@app.route("/members/add", methods=["POST"])
def add_member():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    member_type = request.form.get("member_type", "Student").strip()

    if name:
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO members (name, email, phone, member_type) VALUES (?, ?, ?, ?)",
                (name, email if email else None, phone, member_type)
            )
            conn.commit()
            flash(f'Member "{name}" registered successfully!', "success")
        except sqlite3.IntegrityError:
            flash("Email already registered for another member.", "danger")
        finally:
            conn.close()
    else:
        flash("Member name is required.", "danger")

    return redirect(url_for("members_page"))


@app.route("/members/edit/<int:id>", methods=["POST"])
def edit_member(id):
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    member_type = request.form.get("member_type", "Student").strip()

    if name:
        conn = get_db_connection()
        try:
            conn.execute(
                "UPDATE members SET name=?, email=?, phone=?, member_type=? WHERE id=?",
                (name, email if email else None, phone, member_type, id)
            )
            conn.commit()
            flash(f'Member record updated successfully!', "success")
        except sqlite3.IntegrityError:
            flash("Email already in use by another member.", "danger")
        finally:
            conn.close()

    return redirect(url_for("members_page"))


@app.route("/members/delete/<int:id>")
def delete_member(id):
    conn = get_db_connection()
    member = conn.execute("SELECT * FROM members WHERE id = ?", (id,)).fetchone()
    if member:
        conn.execute("DELETE FROM members WHERE id = ?", (id,))
        conn.commit()
        flash(f'Member "{member["name"]}" deleted.', "warning")
    conn.close()
    return redirect(url_for("members_page"))


@app.route("/borrow")
def borrow_page():
    search_query = request.args.get("q", "").strip()
    conn = get_db_connection()
    
    query = """
        SELECT r.id, r.book_id, r.member_id, r.issue_date, r.due_date, r.return_date, r.fine_amount, r.status,
               b.title as book_title, b.author as book_author,
               m.name as member_name, m.email as member_email
        FROM borrow_records r
        JOIN books b ON r.book_id = b.id
        JOIN members m ON r.member_id = m.id
        WHERE 1=1
    """
    params = []
    if search_query:
        query += " AND (b.title LIKE ? OR m.name LIKE ? OR r.status LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard])
    query += " ORDER BY r.id DESC"
    
    records = conn.execute(query, params).fetchall()
    
    today_str = date.today().isoformat()
    enriched_records = []
    for r in records:
        r_dict = dict(r)
        if r_dict["status"] == "Issued" and r_dict["due_date"] < today_str:
            due_dt = datetime.strptime(r_dict["due_date"], "%Y-%m-%d").date()
            overdue_days = (date.today() - due_dt).days
            r_dict["calculated_fine"] = max(0, overdue_days * 5.0)
            r_dict["overdue_days"] = overdue_days
        else:
            r_dict["calculated_fine"] = r_dict["fine_amount"] or 0.0
            r_dict["overdue_days"] = 0
        enriched_records.append(r_dict)

    available_books = conn.execute("SELECT id, title, author FROM books WHERE status = 'Available'").fetchall()
    members = conn.execute("SELECT id, name, member_type FROM members ORDER BY name").fetchall()
    
    issued_count = conn.execute("SELECT COUNT(*) FROM borrow_records WHERE status = 'Issued'").fetchone()[0]
    total_fines = conn.execute("SELECT SUM(fine_amount) FROM borrow_records").fetchone()[0] or 0.0

    conn.close()

    return render_template(
        "borrow.html",
        records=enriched_records,
        available_books=available_books,
        members=members,
        search_query=search_query,
        stats={"issued": issued_count, "total_fines": total_fines},
        today_date=today_str,
        default_due_date=(date.today() + timedelta(days=14)).isoformat()
    )


@app.route("/borrow/issue", methods=["POST"])
def issue_book():
    book_id = request.form.get("book_id")
    member_id = request.form.get("member_id")
    due_date = request.form.get("due_date")

    if not due_date:
        due_date = (date.today() + timedelta(days=14)).isoformat()

    if book_id and member_id:
        conn = get_db_connection()
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        member = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()

        if book and member:
            conn.execute(
                """
                INSERT INTO borrow_records (book_id, member_id, issue_date, due_date, status)
                VALUES (?, ?, date('now'), ?, 'Issued')
                """,
                (book_id, member_id, due_date)
            )
            conn.execute("UPDATE books SET status = 'Borrowed' WHERE id = ?", (book_id,))
            conn.commit()
            flash(f'Book "{book["title"]}" issued to {member["name"]} successfully!', "success")
        else:
            flash("Invalid book or member selection.", "danger")
        conn.close()
    else:
        flash("Please select both a book and a member.", "danger")

    return redirect(url_for("borrow_page"))


@app.route("/borrow/return/<int:id>")
def return_book(id):
    conn = get_db_connection()
    record = conn.execute("SELECT * FROM borrow_records WHERE id = ?", (id,)).fetchone()

    if record and record["status"] == "Issued":
        due_dt = datetime.strptime(record["due_date"], "%Y-%m-%d").date()
        today_dt = date.today()
        fine = 0.0
        if today_dt > due_dt:
            overdue_days = (today_dt - due_dt).days
            fine = overdue_days * 5.0

        conn.execute(
            """
            UPDATE borrow_records
            SET status = 'Returned', return_date = date('now'), fine_amount = ?
            WHERE id = ?
            """,
            (fine, id)
        )
        conn.execute("UPDATE books SET status = 'Available' WHERE id = ?", (record["book_id"],))
        conn.commit()
        if fine > 0:
            flash(f"Book returned! Late fine calculated: ₹{fine:.2f}", "warning")
        else:
            flash("Book returned on time! No fine incurred.", "success")
    else:
        flash("Record not found or already returned.", "danger")

    conn.close()
    return redirect(url_for("borrow_page"))


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/about")
def about_page():
    return render_template("about.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)