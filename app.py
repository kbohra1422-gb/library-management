from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
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


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/about")
def about_page():
    return render_template("about.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)