from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
import sqlite3
import csv
import io
import json
import urllib.request
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            reviewer_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id)
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
    sort_by = request.args.get("sort", "newest").strip()

    conn = get_db_connection()

    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if search_query:
        query += " AND (title LIKE ? OR author LIKE ? OR category LIKE ? OR isbn LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    if sort_by == "title_asc":
        query += " ORDER BY title ASC"
    elif sort_by == "title_desc":
        query += " ORDER BY title DESC"
    elif sort_by == "author_asc":
        query += " ORDER BY author ASC"
    elif sort_by == "category_asc":
        query += " ORDER BY category ASC"
    else:
        query += " ORDER BY id DESC"

    books = conn.execute(query, params).fetchall()

    categories = conn.execute(
        "SELECT DISTINCT category FROM books ORDER BY category"
    ).fetchall()

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
        selected_status=status_filter,
        selected_sort=sort_by
    )


@app.route("/api/isbn/<isbn>")
def api_fetch_isbn(isbn):
    clean_isbn = isbn.strip().replace("-", "").replace(" ", "")
    try:
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{clean_isbn}&format=json&jscmd=data"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            key = f"ISBN:{clean_isbn}"
            if key in data:
                info = data[key]
                title = info.get("title", "")
                authors = ", ".join([a.get("name", "") for a in info.get("authors", [])])
                cover = info.get("cover", {}).get("medium", "") or info.get("cover", {}).get("large", "")
                subjects = info.get("subjects", [])
                category = subjects[0].get("name") if subjects else "General"
                return jsonify({
                    "success": True,
                    "title": title,
                    "author": authors,
                    "category": category,
                    "cover_url": cover
                })
    except Exception as e:
        pass
    return jsonify({"success": False, "message": "ISBN details not found"}), 404


@app.route("/add", methods=["POST"])
def add_book():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    category = request.form.get("category", "").strip()
    status = request.form.get("status", "Available").strip()
    isbn = request.form.get("isbn", "").strip()
    cover_url = request.form.get("cover_url", "").strip()
    try:
        total_copies = max(1, int(request.form.get("total_copies", 1)))
    except (ValueError, TypeError):
        total_copies = 1

    available_copies = total_copies if status == "Available" else 0

    if title and author and category:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO books (title, author, category, status, isbn, cover_url, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, author, category, status, isbn if isbn else None, cover_url if cover_url else None, total_copies, available_copies)
        )
        conn.commit()
        conn.close()
        flash(f'Book "{title}" added successfully with {total_copies} copies!', "success")
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
        isbn = request.form.get("isbn", "").strip()
        cover_url = request.form.get("cover_url", "").strip()
        try:
            total_copies = max(1, int(request.form.get("total_copies", book["total_copies"] or 1)))
        except (ValueError, TypeError):
            total_copies = book["total_copies"] or 1

        curr_avail = book["available_copies"] if book["available_copies"] is not None else 1
        diff = total_copies - (book["total_copies"] or 1)
        new_avail = max(0, curr_avail + diff)

        if title and author and category:
            conn.execute(
                """
                UPDATE books
                SET title = ?, author = ?, category = ?, status = ?, isbn = ?, cover_url = ?, total_copies = ?, available_copies = ?
                WHERE id = ?
                """,
                (title, author, category, status, isbn if isbn else None, cover_url if cover_url else None, total_copies, new_avail, id)
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
        tot = book["total_copies"] or 1
        avail = book["available_copies"] if book["available_copies"] is not None else (1 if book["status"] == "Available" else 0)
        
        if book["status"] == "Available":
            new_status = "Borrowed"
            new_avail = max(0, avail - 1)
        else:
            new_status = "Available"
            new_avail = min(tot, avail + 1)

        conn.execute("UPDATE books SET status = ?, available_copies = ? WHERE id = ?", (new_status, new_avail, id))
        conn.commit()
        flash(f'Status for "{book["title"]}" updated.', "info")

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


@app.route("/analytics")
def analytics_page():
    conn = get_db_connection()
    
    # Category statistics
    cat_rows = conn.execute("SELECT category, COUNT(*) as count FROM books GROUP BY category ORDER BY count DESC").fetchall()
    categories = [r["category"] for r in cat_rows]
    category_counts = [r["count"] for r in cat_rows]

    # Status distribution
    total_avail = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'Available'").fetchone()[0]
    total_borrowed = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'Borrowed'").fetchone()[0]

    # Member type distribution
    mem_rows = conn.execute("SELECT member_type, COUNT(*) as count FROM members GROUP BY member_type").fetchall()
    member_types = [r["member_type"] for r in mem_rows]
    member_counts = [r["count"] for r in mem_rows]

    conn.close()

    return render_template(
        "analytics.html",
        categories_json=json.dumps(categories),
        cat_counts_json=json.dumps(category_counts),
        status_json=json.dumps({"Available": total_avail, "Borrowed": total_borrowed}),
        members_json=json.dumps({"labels": member_types, "data": member_counts})
    )


@app.route("/borrow/receipt/<int:id>")
def borrow_receipt(id):
    conn = get_db_connection()
    record = conn.execute("""
        SELECT r.id, r.book_id, r.member_id, r.issue_date, r.due_date, r.return_date, r.fine_amount, r.status,
               b.title as book_title, b.author as book_author, b.category as book_category, b.isbn,
               m.name as member_name, m.email as member_email, m.phone as member_phone, m.member_type
        FROM borrow_records r
        JOIN books b ON r.book_id = b.id
        JOIN members m ON r.member_id = m.id
        WHERE r.id = ?
    """, (id,)).fetchone()
    conn.close()

    if not record:
        flash("Borrow record not found.", "danger")
        return redirect(url_for("borrow_page"))

    return render_template("receipt.html", record=record)


@app.route("/reservations")
def reservations_page():
    conn = get_db_connection()
    reservations = conn.execute("""
        SELECT res.id, res.book_id, res.member_id, res.request_date, res.status,
               b.title as book_title, b.author as book_author, b.status as book_status,
               m.name as member_name, m.email as member_email
        FROM reservations res
        JOIN books b ON res.book_id = b.id
        JOIN members m ON res.member_id = m.id
        ORDER BY res.id DESC
    """).fetchall()

    borrowed_books = conn.execute("SELECT id, title, author FROM books WHERE status = 'Borrowed'").fetchall()
    members = conn.execute("SELECT id, name FROM members ORDER BY name").fetchall()
    conn.close()

    return render_template(
        "reservations.html",
        reservations=reservations,
        borrowed_books=borrowed_books,
        members=members
    )


@app.route("/reservations/create", methods=["POST"])
def create_reservation():
    book_id = request.form.get("book_id")
    member_id = request.form.get("member_id")

    if book_id and member_id:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO reservations (book_id, member_id, status) VALUES (?, ?, 'Pending')",
            (book_id, member_id)
        )
        conn.commit()
        conn.close()
        flash("Reservation request placed successfully!", "success")
    else:
        flash("Please select both a book and a member.", "danger")

    return redirect(url_for("reservations_page"))


@app.route("/reservations/cancel/<int:id>")
def cancel_reservation(id):
    conn = get_db_connection()
    conn.execute("UPDATE reservations SET status = 'Cancelled' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Reservation request cancelled.", "warning")
    return redirect(url_for("reservations_page"))


@app.route("/reviews/<int:book_id>", methods=["GET", "POST"])
def book_reviews(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if not book:
        conn.close()
        flash("Book not found!", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        reviewer_name = request.form.get("reviewer_name", "").strip()
        rating = request.form.get("rating", 5)
        comment = request.form.get("comment", "").strip()

        try:
            rating_val = max(1, min(5, int(rating)))
        except (ValueError, TypeError):
            rating_val = 5

        if reviewer_name:
            conn.execute(
                "INSERT INTO reviews (book_id, reviewer_name, rating, comment) VALUES (?, ?, ?, ?)",
                (book_id, reviewer_name, rating_val, comment)
            )
            conn.commit()
            flash("Thank you for your book review & rating!", "success")
        else:
            flash("Reviewer name is required.", "danger")

    reviews = conn.execute("SELECT * FROM reviews WHERE book_id = ? ORDER BY id DESC", (book_id,)).fetchall()
    avg_rating_row = conn.execute("SELECT AVG(rating) as avg_rating, COUNT(*) as count FROM reviews WHERE book_id = ?", (book_id,)).fetchone()
    conn.close()

    avg_rating = round(avg_rating_row["avg_rating"], 1) if avg_rating_row["avg_rating"] else None
    review_count = avg_rating_row["count"]

    return render_template(
        "reviews.html",
        book=book,
        reviews=reviews,
        avg_rating=avg_rating,
        review_count=review_count
    )


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/about")
def about_page():
    return render_template("about.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)