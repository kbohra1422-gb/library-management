from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify, session
import sqlite3
import csv
import io
import json
import os
import urllib.request
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "library_secret_key_super_secure"

UPLOAD_FOLDER = os.path.join("static", "uploads", "pdfs")
ALLOWED_EXTENSIONS = {"pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Database file location
DATABASE = "library.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'Admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, book_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
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
    if "pdf_url" not in existing_cols:
        cursor.execute("ALTER TABLE books ADD COLUMN pdf_url TEXT")
    if "icon" not in existing_cols:
        cursor.execute("ALTER TABLE books ADD COLUMN icon TEXT")
    if "created_at" not in existing_cols:
        cursor.execute("ALTER TABLE books ADD COLUMN created_at TIMESTAMP")
    cursor.execute("UPDATE books SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

    # Ensure all books in the catalog have tailored icons assigned
    cursor.execute("SELECT id, title, category, icon FROM books")
    for b_row in cursor.fetchall():
        if not b_row["icon"]:
            matched = get_book_icon(b_row["title"], b_row["category"])
            cursor.execute("UPDATE books SET icon = ? WHERE id = ?", (matched, b_row["id"]))

    # Seed Default Demo Accounts if users table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_hash = generate_password_hash("admin123")
        student_hash = generate_password_hash("student123")
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", "admin@library.local", admin_hash, "System Administrator", "Admin"))
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        """, ("student", "student@library.local", student_hash, "Rahul Student", "Student"))

    # Seed sample 3 "Want to Read" books for users if wishlist is empty
    cursor.execute("SELECT COUNT(*) FROM wishlist")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM books ORDER BY id ASC LIMIT 3")
        top_books = cursor.fetchall()
        cursor.execute("SELECT id FROM users")
        all_users = cursor.fetchall()
        for u in all_users:
            for b in top_books:
                cursor.execute("INSERT OR IGNORE INTO wishlist (user_id, book_id) VALUES (?, ?)", (u["id"], b["id"]))

    # Seed representative sample borrow loans for due date countdown testing if <= 1 record
    cursor.execute("SELECT COUNT(*) FROM borrow_records")
    if cursor.fetchone()[0] <= 1:
        cursor.execute("SELECT id FROM members LIMIT 2")
        member_rows = cursor.fetchall()
        cursor.execute("SELECT id FROM books WHERE status = 'Available' LIMIT 2")
        avail_books = cursor.fetchall()
        if member_rows and len(avail_books) >= 2:
            m_id = member_rows[0]["id"]
            b_overdue = avail_books[0]["id"]
            b_due_soon = avail_books[1]["id"]
            # Overdue loan (issued 17 days ago, due 3 days ago)
            cursor.execute("""
                INSERT INTO borrow_records (book_id, member_id, issue_date, due_date, status, fine_amount)
                VALUES (?, ?, date('now', '-17 days'), date('now', '-3 days'), 'Issued', 15.0)
            """, (b_overdue, m_id))
            cursor.execute("UPDATE books SET status = 'Borrowed' WHERE id = ?", (b_overdue,))

            # Due soon loan (issued 12 days ago, due in 2 days)
            cursor.execute("""
                INSERT INTO borrow_records (book_id, member_id, issue_date, due_date, status, fine_amount)
                VALUES (?, ?, date('now', '-12 days'), date('now', '+2 days'), 'Issued', 0.0)
            """, (b_due_soon, m_id))
            cursor.execute("UPDATE books SET status = 'Borrowed' WHERE id = ?", (b_due_soon,))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    conn.commit()
    conn.close()


def get_book_icon(title="", category="", custom_icon=None):
    """Returns a tailored, expressive emoji icon according to the book title and genre."""
    if custom_icon and str(custom_icon).strip():
        return str(custom_icon).strip()
    text = f"{title or ''} {category or ''}".lower()
    if any(k in text for k in ["clean code", "code", "software", "program", "python", "java", "developer", "tech", "computer", "web", "html", "css", "c++", "linux"]):
        return "💻"
    if any(k in text for k in ["atomic", "habit", "routine", "discipline", "productivity", "focus", "power"]):
        return "🎯"
    if any(k in text for k in ["alchemist", "coelho", "magic", "spirit", "alchemy", "soul", "destiny"]):
        return "✨"
    if any(k in text for k in ["wings of fire", "fire", "kalam", "rocket", "space", "biography", "autobiography", "leader", "apj"]):
        return "🚀"
    if any(k in text for k in ["hobbit", "lord of the rings", "ring", "fantasy", "dragon", "tolkien", "wizard", "sorcery", "quest"]):
        return "🧙"
    if any(k in text for k in ["think and grow", "rich", "wealth", "money", "invest", "finance", "business", "dollar", "stock", "startup"]):
        return "💡"
    if any(k in text for k in ["science", "physics", "chemistry", "biology", "astronomy", "cosmos", "quantum"]):
        return "🔬"
    if any(k in text for k in ["history", "war", "ancient", "civilization", "empire", "revolution", "historical"]):
        return "📜"
    if any(k in text for k in ["psychology", "mind", "mental", "brain", "behavior", "cognitive", "personal development"]):
        return "🧠"
    if any(k in text for k in ["novel", "story", "fiction", "literature", "classic"]):
        return "📚"
    if any(k in text for k in ["art", "design", "paint", "draw", "photo", "music", "cinema"]):
        return "🎨"
    if any(k in text for k in ["math", "data", "algorithm", "statistic", "calculus", "geometry"]):
        return "🔢"
    if any(k in text for k in ["mystery", "thriller", "crime", "detective", "sherlock", "secret"]):
        return "🕵️"
    if any(k in text for k in ["philosophy", "meditation", "zen", "stoic", "peace", "wisdom"]):
        return "🧭"
    if any(k in text for k in ["health", "fitness", "yoga", "nutrition", "medicine", "doctor"]):
        return "🌿"
    if any(k in text for k in ["love", "romance", "heart", "poem", "poetry"]):
        return "💖"
    if any(k in text for k in ["travel", "geography", "world", "journey", "adventure", "explore"]):
        return "🗺️"
    return "📖"


def get_due_countdown(due_date_str, status="Issued"):
    """
    Computes a structured countdown dictionary for due dates with color coding,
    badge classes, human-readable labels, and urgency levels.
    """
    if status != "Issued":
        return {
            "status": "returned",
            "days_left": None,
            "badge_class": "badge-success",
            "badge_text": "Returned",
            "countdown_text": "Completed",
            "is_overdue": False,
            "urgency": "success",
            "icon": "✅"
        }

    try:
        due_dt = datetime.strptime(str(due_date_str).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return {
            "status": "issued",
            "days_left": None,
            "badge_class": "badge-neutral",
            "badge_text": "Active Loan",
            "countdown_text": str(due_date_str),
            "is_overdue": False,
            "urgency": "normal",
            "icon": "📅"
        }

    today = date.today()
    days_left = (due_dt - today).days

    if days_left < 0:
        overdue_days = abs(days_left)
        day_str = "day" if overdue_days == 1 else "days"
        return {
            "status": "overdue",
            "days_left": days_left,
            "overdue_days": overdue_days,
            "badge_class": "badge-danger",
            "badge_text": f"Overdue ({overdue_days}d)",
            "countdown_text": f"⚠️ Overdue by {overdue_days} {day_str}",
            "is_overdue": True,
            "urgency": "critical",
            "icon": "⚠️",
            "fine_preview": overdue_days * 5.0
        }
    elif days_left == 0:
        return {
            "status": "due_today",
            "days_left": 0,
            "overdue_days": 0,
            "badge_class": "badge-danger",
            "badge_text": "Due Today",
            "countdown_text": "🚨 Due Today!",
            "is_overdue": False,
            "urgency": "critical",
            "icon": "🚨",
            "fine_preview": 0.0
        }
    elif days_left == 1:
        return {
            "status": "due_tomorrow",
            "days_left": 1,
            "overdue_days": 0,
            "badge_class": "badge-warning",
            "badge_text": "Due Tomorrow",
            "countdown_text": "⏳ 1 day left",
            "is_overdue": False,
            "urgency": "warning",
            "icon": "⏳",
            "fine_preview": 0.0
        }
    elif days_left <= 3:
        return {
            "status": "due_soon",
            "days_left": days_left,
            "overdue_days": 0,
            "badge_class": "badge-warning",
            "badge_text": f"{days_left} days left",
            "countdown_text": f"⏳ {days_left} days left",
            "is_overdue": False,
            "urgency": "warning",
            "icon": "⏳",
            "fine_preview": 0.0
        }
    else:
        return {
            "status": "on_track",
            "days_left": days_left,
            "overdue_days": 0,
            "badge_class": "badge-info",
            "badge_text": f"{days_left} days left",
            "countdown_text": f"⏱️ {days_left} days left",
            "is_overdue": False,
            "urgency": "normal",
            "icon": "⏱️",
            "fine_preview": 0.0
        }


@app.context_processor
def inject_user():
    """Injects current_user dictionary, user_wishlist set, wishlist_count, get_book_icon, and get_due_countdown into all templates."""
    user_data = None
    user_wishlist = set()
    if "user_id" in session:
        user_data = {
            "id": session.get("user_id"),
            "username": session.get("username"),
            "email": session.get("email"),
            "full_name": session.get("full_name"),
            "role": session.get("role", "Member")
        }
        try:
            conn = get_db_connection()
            rows = conn.execute("SELECT book_id FROM wishlist WHERE user_id = ?", (session["user_id"],)).fetchall()
            user_wishlist = {r["book_id"] for r in rows}
            conn.close()
        except Exception:
            user_wishlist = set()
    return {
        "current_user": user_data,
        "user_wishlist": user_wishlist,
        "wishlist_count": len(user_wishlist),
        "get_book_icon": get_book_icon,
        "get_due_countdown": get_due_countdown
    }


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access your library account.", "warning")
            return redirect(url_for("login_page", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in with admin privileges.", "warning")
            return redirect(url_for("login_page", next=request.url))
        if session.get("role") not in ["Admin", "Librarian"]:
            flash("Access restricted: Administrator or Librarian role required.", "danger")
            return redirect(url_for("home_page"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    """Initial landing: direct guests to login, or logged-in users to home."""
    if "user_id" in session:
        return redirect(url_for("home_page"))
    return redirect(url_for("login_page"))


@app.route("/home")
@login_required
def home_page():
    """Modern Library Landing & Overview Home Page."""
    conn = get_db_connection()

    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    available_books = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'Available'").fetchone()[0]
    borrowed_books = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'Borrowed'").fetchone()[0]
    total_members = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    total_reservations = conn.execute("SELECT COUNT(*) FROM reservations WHERE status = 'Pending'").fetchone()[0]
    total_ebooks = conn.execute("SELECT COUNT(*) FROM books WHERE pdf_url IS NOT NULL AND pdf_url != ''").fetchone()[0]

    # Recent featured books
    recent_books = conn.execute("SELECT * FROM books ORDER BY id DESC LIMIT 8").fetchall()

    # Categories list
    categories = conn.execute("SELECT DISTINCT category FROM books ORDER BY category").fetchall()

    # Recent Reviews (up to 4)
    recent_reviews = conn.execute("""
        SELECT r.reviewer_name, r.rating, r.comment, r.created_at, b.title as book_title, b.id as book_id
        FROM reviews r
        JOIN books b ON r.book_id = b.id
        ORDER BY r.id DESC LIMIT 4
    """).fetchall()

    # User active borrows & reservations if logged in
    user_borrows = []
    user_overdue_count = 0
    user_due_soon_count = 0
    if "user_id" in session:
        user_email = session.get("email")
        member_row = conn.execute("SELECT id FROM members WHERE email = ?", (user_email,)).fetchone()
        if member_row:
            member_id = member_row["id"]
            raw_borrows = conn.execute("""
                SELECT br.*, b.title as book_title, b.author as book_author
                FROM borrow_records br
                JOIN books b ON br.book_id = b.id
                WHERE br.member_id = ? AND br.status = 'Issued'
                ORDER BY br.id DESC
            """, (member_id,)).fetchall()
            for b in raw_borrows:
                b_dict = dict(b)
                cd = get_due_countdown(b_dict["due_date"], b_dict["status"])
                b_dict["countdown"] = cd
                if cd["is_overdue"]:
                    user_overdue_count += 1
                elif cd["urgency"] == "warning":
                    user_due_soon_count += 1
                user_borrows.append(b_dict)

    conn.close()

    stats = {
        "total": total_books,
        "available": available_books,
        "borrowed": borrowed_books,
        "members": total_members,
        "reservations": total_reservations,
        "ebooks": total_ebooks
    }

    return render_template(
        "home.html",
        stats=stats,
        recent_books=recent_books,
        categories=[c["category"] for c in categories],
        recent_reviews=recent_reviews,
        user_borrows=user_borrows,
        user_overdue_count=user_overdue_count,
        user_due_soon_count=user_due_soon_count,
        active_page="home"
    )


@app.route("/books")
@app.route("/catalog")
@login_required
def books_catalog():
    """Full Books Catalog with Search, Filters, and Management."""
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
        selected_sort=sort_by,
        active_page="books"
    )


@app.route("/wishlist")
@login_required
def wishlist_page():
    """Personal 'Want to Read' Reading Wishlist Collection."""
    user_id = session["user_id"]
    conn = get_db_connection()
    wishlist_books = conn.execute("""
        SELECT b.*, w.created_at as saved_at
        FROM wishlist w
        JOIN books b ON w.book_id = b.id
        WHERE w.user_id = ?
        ORDER BY w.id DESC
    """, (user_id,)).fetchall()

    total_count = len(wishlist_books)
    available_count = sum(1 for b in wishlist_books if b["status"] == "Available")
    ebooks_count = sum(1 for b in wishlist_books if b["pdf_url"])
    conn.close()

    return render_template(
        "wishlist.html",
        books=wishlist_books,
        total_count=total_count,
        available_count=available_count,
        ebooks_count=ebooks_count,
        active_page="wishlist"
    )


@app.route("/wishlist/toggle/<int:book_id>", methods=["GET", "POST"])
@login_required
def toggle_wishlist(book_id):
    """Toggles a book in/out of the user's 'Want to Read' list."""
    user_id = session["user_id"]
    conn = get_db_connection()
    book = conn.execute("SELECT id, title FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        conn.close()
        flash("Book record not found.", "danger")
        return redirect(request.referrer or url_for("books_catalog"))

    existing = conn.execute(
        "SELECT id FROM wishlist WHERE user_id = ? AND book_id = ?",
        (user_id, book_id)
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM wishlist WHERE id = ?", (existing["id"],))
        conn.commit()
        is_saved = False
        message = f"Removed '{book['title']}' from your 'Want to Read' list."
        flash(message, "info")
    else:
        conn.execute(
            "INSERT INTO wishlist (user_id, book_id) VALUES (?, ?)",
            (user_id, book_id)
        )
        conn.commit()
        is_saved = True
        message = f"Added '{book['title']}' to your 'Want to Read' list! 🔖"
        flash(message, "success")

    count_row = conn.execute(
        "SELECT COUNT(*) FROM wishlist WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    new_count = count_row[0] if count_row else 0
    conn.close()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({
            "success": True,
            "book_id": book_id,
            "saved": is_saved,
            "count": new_count,
            "message": message
        })

    return redirect(request.referrer or url_for("books_catalog"))


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


def handle_pdf_upload(req, default_url=None):
    pdf_url = req.form.get("pdf_url", "").strip()
    if "pdf_file" in req.files:
        file = req.files["pdf_file"]
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            if filename.lower().endswith(".pdf"):
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(save_path)
                return f"/static/uploads/pdfs/{filename}"
    return pdf_url if pdf_url else default_url


@app.route("/add", methods=["POST"])
@login_required
def add_book():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    category = request.form.get("category", "").strip()
    status = request.form.get("status", "Available").strip()
    isbn = request.form.get("isbn", "").strip()
    cover_url = request.form.get("cover_url", "").strip()
    pdf_url = handle_pdf_upload(request)
    icon = request.form.get("icon", "").strip()
    if not icon:
        icon = get_book_icon(title, category)

    try:
        total_copies = max(1, int(request.form.get("total_copies", 1)))
    except (ValueError, TypeError):
        total_copies = 1

    available_copies = total_copies if status == "Available" else 0

    if title and author and category:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO books (title, author, category, status, isbn, cover_url, total_copies, available_copies, pdf_url, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, author, category, status, isbn if isbn else None, cover_url if cover_url else None, total_copies, available_copies, pdf_url, icon)
        )
        conn.commit()
        conn.close()
        flash(f'Book "{title}" added successfully with E-Book support!', "success")
    else:
        flash("Please fill in all required fields.", "danger")

    return redirect(url_for("books_catalog"))


@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_book(id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (id,)).fetchone()

    if not book:
        conn.close()
        flash("Book not found!", "danger")
        return redirect(url_for("books_catalog"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()
        status = request.form.get("status", "Available").strip()
        isbn = request.form.get("isbn", "").strip()
        cover_url = request.form.get("cover_url", "").strip()
        pdf_url = handle_pdf_upload(request, book["pdf_url"])
        icon = request.form.get("icon", "").strip()
        if not icon:
            icon = get_book_icon(title, category)

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
                SET title = ?, author = ?, category = ?, status = ?, isbn = ?, cover_url = ?, total_copies = ?, available_copies = ?, pdf_url = ?, icon = ?
                WHERE id = ?
                """,
                (title, author, category, status, isbn if isbn else None, cover_url if cover_url else None, total_copies, new_avail, pdf_url, icon, id)
            )
            conn.commit()
            conn.close()
            flash(f'Book "{title}" updated successfully!', "success")
            return redirect(url_for("books_catalog"))
        else:
            flash("All fields are required.", "danger")

    conn.close()
    return render_template("edit.html", book=book)


@app.route("/reader/<int:book_id>")
def e_book_reader(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()

    if not book or not book["pdf_url"]:
        flash("E-Book PDF not available for this title.", "warning")
        return redirect(url_for("books_catalog"))

    return render_template("reader.html", book=book)


@app.route("/toggle/<int:id>")
@login_required
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
    return redirect(url_for("books_catalog"))


@app.route("/delete/<int:id>")
@login_required
def delete_book(id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (id,)).fetchone()

    if book:
        conn.execute("DELETE FROM books WHERE id = ?", (id,))
        conn.commit()
        flash(f'Book "{book["title"]}" deleted successfully!', "warning")

    conn.close()
    return redirect(url_for("books_catalog"))


@app.route("/export/csv")
@login_required
def export_csv():
    search_query = request.args.get("q", "").strip()
    category_filter = request.args.get("category", "").strip()
    status_filter = request.args.get("status", "").strip()

    conn = get_db_connection()
    query = "SELECT id, title, author, category, status, total_copies, available_copies FROM books WHERE 1=1"
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
    writer.writerow(["ID", "Title", "Author", "Category", "Status", "Total Copies", "Available Copies"])

    for book in books:
        writer.writerow([
            book["id"],
            book["title"],
            book["author"],
            book["category"],
            book["status"],
            book["total_copies"] or 1,
            book["available_copies"] or 0
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=library_books.csv"}
    )


@app.route("/members")
@login_required
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


@app.route("/members/export/csv")
@login_required
def export_members_csv():
    search_query = request.args.get("q", "").strip()
    conn = get_db_connection()
    query = "SELECT id, name, email, phone, member_type, created_at FROM members WHERE 1=1"
    params = []
    if search_query:
        query += " AND (name LIKE ? OR email LIKE ? OR phone LIKE ? OR member_type LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])
    query += " ORDER BY id DESC"

    members = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Member ID", "Full Name", "Email", "Phone", "Membership Type", "Registration Date"])
    for m in members:
        writer.writerow([
            m["id"],
            m["name"],
            m["email"] or "N/A",
            m["phone"] or "N/A",
            m["member_type"],
            m["created_at"] or "N/A"
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=library_members.csv"}
    )


@app.route("/members/add", methods=["POST"])
@login_required
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
@login_required
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
@login_required
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
@login_required
def borrow_page():
    search_query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
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

    if status_filter == "Issued":
        query += " AND r.status = 'Issued'"
    elif status_filter == "Returned":
        query += " AND r.status = 'Returned'"
    elif status_filter == "Overdue":
        query += " AND r.status = 'Issued' AND date(r.due_date) < date('now')"

    query += " ORDER BY r.id DESC"
    
    records = conn.execute(query, params).fetchall()
    
    today_str = date.today().isoformat()
    enriched_records = []
    overdue_count = 0
    due_soon_count = 0
    calculated_total_fines = 0.0

    for r in records:
        r_dict = dict(r)
        cd = get_due_countdown(r_dict["due_date"], r_dict["status"])
        r_dict["countdown"] = cd
        if r_dict["status"] == "Issued":
            if cd["is_overdue"]:
                overdue_count += 1
                r_dict["calculated_fine"] = max(0.0, cd["fine_preview"])
                r_dict["overdue_days"] = cd["overdue_days"]
                calculated_total_fines += r_dict["calculated_fine"]
            else:
                if cd["urgency"] == "warning":
                    due_soon_count += 1
                r_dict["calculated_fine"] = r_dict["fine_amount"] or 0.0
                r_dict["overdue_days"] = 0
                calculated_total_fines += r_dict["calculated_fine"]
        else:
            r_dict["calculated_fine"] = r_dict["fine_amount"] or 0.0
            r_dict["overdue_days"] = 0
            calculated_total_fines += r_dict["calculated_fine"]
        enriched_records.append(r_dict)

    available_books = conn.execute("SELECT id, title, author, available_copies, total_copies FROM books WHERE status = 'Available' AND (available_copies IS NULL OR available_copies > 0) ORDER BY title").fetchall()
    members = conn.execute("SELECT id, name, member_type FROM members ORDER BY name").fetchall()
    
    issued_count = conn.execute("SELECT COUNT(*) FROM borrow_records WHERE status = 'Issued'").fetchone()[0]

    conn.close()

    stats = {
        "issued": issued_count,
        "overdue": overdue_count,
        "due_soon": due_soon_count,
        "total_fines": calculated_total_fines
    }

    return render_template(
        "borrow.html",
        records=enriched_records,
        available_books=available_books,
        members=members,
        search_query=search_query,
        selected_status=status_filter,
        stats=stats,
        today_date=today_str,
        default_due_date=(date.today() + timedelta(days=14)).isoformat()
    )


@app.route("/borrow/export/csv")
@login_required
def export_borrow_csv():
    search_query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    conn = get_db_connection()
    query = """
        SELECT r.id, b.title as book_title, m.name as member_name, r.issue_date, r.due_date, r.return_date, r.status, r.fine_amount
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

    if status_filter == "Issued":
        query += " AND r.status = 'Issued'"
    elif status_filter == "Returned":
        query += " AND r.status = 'Returned'"
    elif status_filter == "Overdue":
        query += " AND r.status = 'Issued' AND date(r.due_date) < date('now')"

    query += " ORDER BY r.id DESC"
    records = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Loan ID", "Book Title", "Borrower", "Issue Date", "Due Date", "Return Date", "Status", "Fine (INR)"])
    for r in records:
        writer.writerow([
            r["id"],
            r["book_title"],
            r["member_name"],
            r["issue_date"],
            r["due_date"],
            r["return_date"] or "N/A",
            r["status"],
            f"{r['fine_amount'] or 0.0:.2f}"
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=circulation_records.csv"}
    )


@app.route("/borrow/issue", methods=["POST"])
@login_required
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
            avail = book["available_copies"] if book["available_copies"] is not None else 1
            total_c = book["total_copies"] or 1
            if avail <= 0:
                conn.close()
                flash(f'Cannot issue "{book["title"]}": All {total_c} copies are currently on loan.', "warning")
                return redirect(url_for("borrow_page"))

            new_avail = max(0, avail - 1)
            new_status = "Available" if new_avail > 0 else "Borrowed"

            conn.execute(
                """
                INSERT INTO borrow_records (book_id, member_id, issue_date, due_date, status)
                VALUES (?, ?, date('now'), ?, 'Issued')
                """,
                (book_id, member_id, due_date)
            )
            conn.execute(
                "UPDATE books SET available_copies = ?, status = ? WHERE id = ?",
                (new_avail, new_status, book_id)
            )
            conn.commit()
            flash(f'Book "{book["title"]}" issued to {member["name"]} successfully! ({new_avail} of {total_c} copies remaining in stock)', "success")
        else:
            flash("Invalid book or member selection.", "danger")
        conn.close()
    else:
        flash("Please select both a book and a member.", "danger")

    return redirect(url_for("borrow_page"))


@app.route("/borrow/return/<int:id>")
@login_required
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

        book = conn.execute("SELECT * FROM books WHERE id = ?", (record["book_id"],)).fetchone()
        total_c = (book["total_copies"] if book and book["total_copies"] else 1)
        curr_avail = (book["available_copies"] if book and book["available_copies"] is not None else 0)
        new_avail = min(total_c, curr_avail + 1)

        conn.execute(
            """
            UPDATE borrow_records
            SET status = 'Returned', return_date = date('now'), fine_amount = ?
            WHERE id = ?
            """,
            (fine, id)
        )
        conn.execute(
            "UPDATE books SET available_copies = ?, status = 'Available' WHERE id = ?",
            (new_avail, record["book_id"])
        )

        # Check if there is an active reservation waiting for this book
        pending_res = conn.execute("""
            SELECT res.id, m.name as member_name
            FROM reservations res
            JOIN members m ON res.member_id = m.id
            WHERE res.book_id = ? AND res.status = 'Pending'
            ORDER BY res.id ASC LIMIT 1
        """, (record["book_id"],)).fetchone()

        hold_notif = ""
        if pending_res:
            conn.execute("UPDATE reservations SET status = 'Ready' WHERE id = ?", (pending_res["id"],))
            hold_notif = f" Priority hold for patron {pending_res['member_name']} is now Ready for Pickup!"

        conn.commit()
        if fine > 0:
            flash(f"Book returned! Late fine calculated: ₹{fine:.2f}.{hold_notif}", "warning")
        else:
            flash(f"Book returned on time! Stock updated to {new_avail} of {total_c} copies.{hold_notif}", "success")
    else:
        flash("Record not found or already returned.", "danger")

    conn.close()
    return redirect(url_for("borrow_page"))


@app.route("/analytics")
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
def cancel_reservation(id):
    conn = get_db_connection()
    conn.execute("UPDATE reservations SET status = 'Cancelled' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Reservation request cancelled.", "warning")
    return redirect(url_for("reservations_page"))


@app.route("/reviews/<int:book_id>", methods=["GET", "POST"])
@login_required
def book_reviews(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if not book:
        conn.close()
        flash("Book not found!", "danger")
        return redirect(url_for("books_catalog"))

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


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if "user_id" in session:
        return redirect(url_for("home_page"))

    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember")
        next_url = request.form.get("next") or request.args.get("next")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (identifier, identifier)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = user["email"]
            session["full_name"] = user["full_name"] or user["username"]
            session["role"] = user["role"]
            if remember:
                session.permanent = True
            
            flash(f"Welcome back, {session['full_name']}! You have logged in successfully.", "success")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("home_page"))
        else:
            flash("Invalid username/email or password. Please try again.", "danger")
            return render_template("login.html", prefill_user=identifier)

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register_page():
    if "user_id" in session:
        return redirect(url_for("home_page"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "Student").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        prefill_data = {
            "full_name": full_name,
            "username": username,
            "email": email,
            "role": role
        }

        if not full_name or not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html", prefill_data=prefill_data)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", prefill_data=prefill_data)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html", prefill_data=prefill_data)

        conn = get_db_connection()
        existing_user = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("Username or Email already registered. Please sign in or use different details.", "danger")
            return render_template("register.html", prefill_data=prefill_data)

        pw_hash = generate_password_hash(password)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
            (username, email, pw_hash, full_name, role)
        )
        new_user_id = cursor.lastrowid

        # Also register in members table if Student/Faculty
        if role in ["Student", "Faculty"]:
            member_exists = conn.execute("SELECT id FROM members WHERE email = ?", (email,)).fetchone()
            if not member_exists:
                conn.execute(
                    "INSERT INTO members (name, email, member_type) VALUES (?, ?, ?)",
                    (full_name, email, role)
                )

        conn.commit()
        conn.close()

        # Log in automatically upon registration
        session["user_id"] = new_user_id
        session["username"] = username
        session["email"] = email
        session["full_name"] = full_name
        session["role"] = role

        flash(f"Account created successfully! Welcome to LibManager, {full_name}.", "success")
        return redirect(url_for("home_page"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login_page"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile_page():
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()

    if not user:
        conn.close()
        session.clear()
        flash("User session expired. Please log in again.", "warning")
        return redirect(url_for("login_page"))

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_info":
            new_name = request.form.get("full_name", "").strip()
            new_email = request.form.get("email", "").strip().lower()

            if new_name and new_email:
                try:
                    conn.execute(
                        "UPDATE users SET full_name = ?, email = ? WHERE id = ?",
                        (new_name, new_email, session["user_id"])
                    )
                    conn.commit()
                    session["full_name"] = new_name
                    session["email"] = new_email
                    flash("Profile information updated successfully!", "success")
                except sqlite3.IntegrityError:
                    flash("Email address is already in use by another account.", "danger")
            else:
                flash("Full name and email are required.", "danger")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_new_pw = request.form.get("confirm_new_password", "")

            if not check_password_hash(user["password_hash"], current_pw):
                flash("Current password is incorrect.", "danger")
            elif new_pw != confirm_new_pw:
                flash("New passwords do not match.", "danger")
            elif len(new_pw) < 6:
                flash("New password must be at least 6 characters.", "danger")
            else:
                new_hash = generate_password_hash(new_pw)
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (new_hash, session["user_id"])
                )
                conn.commit()
                flash("Password changed successfully!", "success")

        # Refetch updated user record
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()

    # Find borrowing records for this user (if member exists with same email)
    borrows = []
    member_row = conn.execute("SELECT * FROM members WHERE email = ?", (user["email"],)).fetchone()
    active_borrows = 0
    if member_row:
        borrows = conn.execute("""
            SELECT br.*, b.title as book_title
            FROM borrow_records br
            JOIN books b ON br.book_id = b.id
            WHERE br.member_id = ?
            ORDER BY br.id DESC
        """, (member_row["id"],)).fetchall()
        for b in borrows:
            if b["status"] == "Issued":
                active_borrows += 1

    # Find Want to Read books for this user
    wishlist_books = conn.execute("""
        SELECT b.*, w.created_at as saved_at
        FROM wishlist w
        JOIN books b ON w.book_id = b.id
        WHERE w.user_id = ?
        ORDER BY w.id DESC
    """, (session["user_id"],)).fetchall()

    card_data = {
        "id": user["id"],
        "name": user["full_name"] or user["username"],
        "username": user["username"],
        "email": user["email"],
        "phone": (member_row["phone"] if member_row and member_row["phone"] else "Not Provided"),
        "role": user["role"],
        "member_type": (member_row["member_type"] if member_row and member_row["member_type"] else ("Faculty Fellow" if user["role"] == "Admin" else "Student Scholar")),
        "card_no": f"LM-2026-{user['id']:04d}",
        "issue_date": user["created_at"][:10] if user["created_at"] else "2026-01-01",
        "valid_thru": "2028-12-31",
        "active_borrows": active_borrows,
        "max_borrows": 15 if user["role"] == "Admin" else 5,
        "is_owner": True
    }

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        borrows=borrows,
        wishlist_books=wishlist_books,
        card=card_data,
        active_page="profile"
    )


@app.route("/profile/card")
@login_required
def user_library_card():
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not user:
        conn.close()
        flash("User session expired. Please log in again.", "warning")
        return redirect(url_for("login_page"))

    member = conn.execute("SELECT * FROM members WHERE email = ?", (user["email"],)).fetchone()
    active_borrows = 0
    if member:
        active_borrows = conn.execute(
            "SELECT COUNT(*) FROM borrow_records WHERE member_id = ? AND status = 'Issued'",
            (member["id"],)
        ).fetchone()[0]

    conn.close()

    card_data = {
        "id": user["id"],
        "name": user["full_name"] or user["username"],
        "username": user["username"],
        "email": user["email"],
        "phone": (member["phone"] if member and member["phone"] else "Not Provided"),
        "role": user["role"],
        "member_type": (member["member_type"] if member and member["member_type"] else ("Faculty Fellow" if user["role"] == "Admin" else "Student Scholar")),
        "card_no": f"LM-2026-{user['id']:04d}",
        "issue_date": user["created_at"][:10] if user["created_at"] else "2026-01-01",
        "valid_thru": "2028-12-31",
        "active_borrows": active_borrows,
        "max_borrows": 15 if user["role"] == "Admin" else 5,
        "is_owner": True
    }
    return render_template("library_card.html", card=card_data, active_page="profile")


@app.route("/members/card/<int:id>")
@login_required
def member_library_card(id):
    conn = get_db_connection()
    member = conn.execute("SELECT * FROM members WHERE id = ?", (id,)).fetchone()
    if not member:
        conn.close()
        flash("Member record not found.", "danger")
        return redirect(url_for("members_page"))

    active_borrows = conn.execute(
        "SELECT COUNT(*) FROM borrow_records WHERE member_id = ? AND status = 'Issued'",
        (id,)
    ).fetchone()[0]
    conn.close()

    card_data = {
        "id": member["id"],
        "name": member["name"],
        "username": (member["email"].split("@")[0] if member["email"] else f"patron{member['id']}"),
        "email": member["email"] or "N/A",
        "phone": member["phone"] or "Not Provided",
        "role": member["member_type"],
        "member_type": member["member_type"],
        "card_no": f"LM-2026-{member['id']:04d}",
        "issue_date": member["created_at"][:10] if member["created_at"] else "2026-01-01",
        "valid_thru": "2028-12-31",
        "active_borrows": active_borrows,
        "max_borrows": 10 if member["member_type"] == "Faculty" else 5,
        "is_owner": (session.get("email") == member["email"])
    }
    return render_template("library_card.html", card=card_data, active_page="members")



@app.route("/help")
@login_required
def help_page():
    return render_template("help.html", active_page="help")


@app.route("/about")
@login_required
def about_page():
    return render_template("about.html", active_page="about")


# ==========================================================
# RESTful JSON API Endpoints
# ==========================================================

@app.route("/api/v1/stats", methods=["GET"])
def api_stats():
    """Returns library summary statistics in JSON format."""
    conn = get_db_connection()
    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    available_books = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'Available'").fetchone()[0]
    borrowed_books = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'Borrowed'").fetchone()[0]
    total_members = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    pending_reservations = conn.execute("SELECT COUNT(*) FROM reservations WHERE status = 'Pending'").fetchone()[0]
    total_ebooks = conn.execute("SELECT COUNT(*) FROM books WHERE pdf_url IS NOT NULL AND pdf_url != ''").fetchone()[0]
    conn.close()

    return jsonify({
        "status": "success",
        "data": {
            "total_books": total_books,
            "available_books": available_books,
            "borrowed_books": borrowed_books,
            "total_members": total_members,
            "pending_reservations": pending_reservations,
            "total_ebooks": total_ebooks
        }
    })


@app.route("/api/v1/books", methods=["GET"])
def api_books_list():
    """Returns filtered books list in JSON format."""
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()
    limit = request.args.get("limit", 50, type=int)

    sql = "SELECT * FROM books WHERE 1=1"
    params = []

    if query:
        sql += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)"
        pattern = f"%{query}%"
        params.extend([pattern, pattern, pattern])

    if category:
        sql += " AND category = ?"
        params.append(category)

    if status:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY id DESC LIMIT ?"
    params.append(min(limit, 200))

    conn = get_db_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    books_list = [dict(row) for row in rows]
    return jsonify({
        "status": "success",
        "count": len(books_list),
        "data": books_list
    })


@app.route("/api/v1/books/<int:book_id>", methods=["GET"])
def api_book_detail(book_id):
    """Returns a specific book record with review summary in JSON format."""
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        conn.close()
        return jsonify({"status": "error", "message": "Book not found"}), 404

    reviews = conn.execute("SELECT * FROM reviews WHERE book_id = ? ORDER BY id DESC", (book_id,)).fetchall()
    avg_rating_row = conn.execute("SELECT AVG(rating) as avg_rating, COUNT(*) as count FROM reviews WHERE book_id = ?", (book_id,)).fetchone()
    conn.close()

    book_dict = dict(book)
    book_dict["reviews"] = [dict(r) for r in reviews]
    book_dict["avg_rating"] = round(avg_rating_row["avg_rating"], 1) if avg_rating_row["avg_rating"] else None
    book_dict["review_count"] = avg_rating_row["count"]

    return jsonify({
        "status": "success",
        "data": book_dict
    })


@app.route("/api/v1/members", methods=["GET"])
def api_members_list():
    """Returns library members in JSON format."""
    search = request.args.get("q", "").strip()
    conn = get_db_connection()
    if search:
        pattern = f"%{search}%"
        members = conn.execute(
            "SELECT * FROM members WHERE name LIKE ? OR email LIKE ? ORDER BY name ASC",
            (pattern, pattern)
        ).fetchall()
    else:
        members = conn.execute("SELECT * FROM members ORDER BY name ASC").fetchall()
    conn.close()

    return jsonify({
        "status": "success",
        "count": len(members),
        "data": [dict(m) for m in members]
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True)