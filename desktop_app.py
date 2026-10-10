import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import sqlite3
import os
import csv

# Configure CustomTkinter Appearance
ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"

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


class LibraryApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        init_db()

        # Window Setup
        self.title("📚 Library Management System - Desktop Edition")
        self.geometry("1100x700")
        self.minsize(950, 600)

        # Configure Grid Layout (1x2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Build Sidebar & Main Container
        self.create_sidebar()
        self.create_main_content()

        # Initial Load
        self.load_categories_filter()
        self.refresh_dashboard()

    def create_sidebar(self):
        """Creates the left sidebar navigation."""
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # App Title / Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="📚 LibManager",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Navigation Buttons
        self.btn_nav_dashboard = ctk.CTkButton(
            self.sidebar_frame,
            text="🏠 Dashboard",
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.show_dashboard_view
        )
        self.btn_nav_dashboard.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.btn_nav_help = ctk.CTkButton(
            self.sidebar_frame,
            text="❓ Help & FAQ",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=14),
            command=self.show_help_view
        )
        self.btn_nav_help.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.btn_nav_about = ctk.CTkButton(
            self.sidebar_frame,
            text="ℹ️ About Project",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=14),
            command=self.show_about_view
        )
        self.btn_nav_about.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        # Theme Switcher at bottom
        self.appearance_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Appearance Theme:",
            anchor="w",
            font=ctk.CTkFont(size=12)
        )
        self.appearance_label.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="w")

        self.appearance_optionemenu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["System", "Dark", "Light"],
            command=self.change_appearance_mode_event
        )
        self.appearance_optionemenu.grid(row=7, column=0, padx=20, pady=(5, 20), sticky="ew")

    def create_main_content(self):
        """Creates the main content area with tab frames."""
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Header Frame
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        self.header_title = ctk.CTkLabel(
            self.header_frame,
            text="📚 Library Catalog & Dashboard",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.header_title.pack(side="left")

        # Views: Dashboard View, Help View, About View
        self.dashboard_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.help_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.about_view = ctk.CTkFrame(self.main_container, fg_color="transparent")

        self.setup_dashboard_view()
        self.setup_help_view()
        self.setup_about_view()

        # Show default view
        self.show_dashboard_view()

    def setup_dashboard_view(self):
        """Setup stats cards, add book form, search bar, and records table."""
        self.dashboard_view.grid_rowconfigure(2, weight=1)
        self.dashboard_view.grid_columnconfigure(1, weight=1)

        # --- Row 0: Stats Cards ---
        self.stats_frame = ctk.CTkFrame(self.dashboard_view, fg_color="transparent")
        self.stats_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        self.stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Card 1: Total
        self.card_total = self.create_stat_card(self.stats_frame, "📚 Total Books", "0", 0)
        # Card 2: Available
        self.card_available = self.create_stat_card(self.stats_frame, "✅ Available", "0", 1)
        # Card 3: Borrowed
        self.card_borrowed = self.create_stat_card(self.stats_frame, "⏳ Borrowed", "0", 2)
        # Card 4: Categories
        self.card_categories = self.create_stat_card(self.stats_frame, "🏷️ Categories", "0", 3)

        # --- Left Column: Add New Book Form ---
        self.form_frame = ctk.CTkFrame(self.dashboard_view, width=300)
        self.form_frame.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 15))

        form_title = ctk.CTkLabel(
            self.form_frame,
            text="➕ Add New Book",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        form_title.pack(padx=15, pady=(15, 10), anchor="w")

        # Title Input
        ctk.CTkLabel(self.form_frame, text="Book Title *", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, anchor="w")
        self.entry_title = ctk.CTkEntry(self.form_frame, placeholder_text="e.g. Clean Code")
        self.entry_title.pack(padx=15, pady=(0, 10), fill="x")

        # Author Input
        ctk.CTkLabel(self.form_frame, text="Author *", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, anchor="w")
        self.entry_author = ctk.CTkEntry(self.form_frame, placeholder_text="e.g. Robert C. Martin")
        self.entry_author.pack(padx=15, pady=(0, 10), fill="x")

        # Category Input
        ctk.CTkLabel(self.form_frame, text="Category *", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, anchor="w")
        self.entry_category = ctk.CTkEntry(self.form_frame, placeholder_text="e.g. Software Engineering")
        self.entry_category.pack(padx=15, pady=(0, 10), fill="x")

        # Status Option
        ctk.CTkLabel(self.form_frame, text="Status", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, anchor="w")
        self.option_status = ctk.CTkOptionMenu(self.form_frame, values=["Available", "Borrowed"])
        self.option_status.pack(padx=15, pady=(0, 15), fill="x")

        # Submit Button
        self.btn_add = ctk.CTkButton(
            self.form_frame,
            text="Add Book to Library",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.add_book_action
        )
        self.btn_add.pack(padx=15, pady=(0, 15), fill="x")

        # --- Right Column: Search/Filter + Table View ---
        # Search & Filter Bar
        self.filter_frame = ctk.CTkFrame(self.dashboard_view)
        self.filter_frame.grid(row=1, column=1, sticky="ew", pady=(0, 10))

        self.entry_search = ctk.CTkEntry(self.filter_frame, placeholder_text="🔍 Search title, author, category...")
        self.entry_search.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.filter_cat_option = ctk.CTkOptionMenu(self.filter_frame, values=["All Categories"], command=lambda e: self.refresh_dashboard())
        self.filter_cat_option.pack(side="left", padx=5, pady=10)

        self.filter_status_option = ctk.CTkOptionMenu(self.filter_frame, values=["All Statuses", "Available", "Borrowed"], command=lambda e: self.refresh_dashboard())
        self.filter_status_option.pack(side="left", padx=5, pady=10)

        self.btn_filter = ctk.CTkButton(self.filter_frame, text="Filter", width=70, command=self.refresh_dashboard)
        self.btn_filter.pack(side="left", padx=5, pady=10)

        self.btn_reset = ctk.CTkButton(self.filter_frame, text="Reset", width=70, fg_color="gray", hover_color="darkgray", command=self.reset_filters)
        self.btn_reset.pack(side="left", padx=(5, 10), pady=10)

        # Table Container
        self.table_frame = ctk.CTkFrame(self.dashboard_view)
        self.table_frame.grid(row=2, column=1, sticky="nsew")
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        # Modern Treeview Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", font=("Plus Jakarta Sans", 10), rowheight=32, background="#ffffff", fieldbackground="#ffffff", foreground="#0f172a")
        style.configure("Treeview.Heading", font=("Plus Jakarta Sans", 10, "bold"), background="#4f46e5", foreground="#ffffff")
        style.map("Treeview", background=[("selected", "#6366f1")], foreground=[("selected", "#ffffff")])

        columns = ("ID", "Title", "Author", "Category", "Status")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("ID", text="#")
        self.tree.column("ID", width=40, anchor="center")

        self.tree.heading("Title", text="Book Title")
        self.tree.column("Title", width=220, anchor="w")

        self.tree.heading("Author", text="Author")
        self.tree.column("Author", width=160, anchor="w")

        self.tree.heading("Category", text="Category")
        self.tree.column("Category", width=140, anchor="w")

        self.tree.heading("Status", text="Status")
        self.tree.column("Status", width=100, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Scrollbar for Table
        scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=10)

        # Bottom Actions Bar (Toggle Status, Edit, Delete)
        self.actions_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.actions_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        self.btn_toggle = ctk.CTkButton(
            self.actions_frame,
            text="🔄 Issue / Return Toggle",
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self.toggle_status_action
        )
        self.btn_toggle.pack(side="left", padx=5)

        self.btn_edit = ctk.CTkButton(
            self.actions_frame,
            text="✏️ Edit Book",
            fg_color="#d97706",
            hover_color="#b45309",
            command=self.edit_book_dialog
        )
        self.btn_edit.pack(side="left", padx=5)

        self.btn_export = ctk.CTkButton(
            self.actions_frame,
            text="📥 Export CSV",
            fg_color="#10b981",
            hover_color="#059669",
            command=self.export_csv_action
        )
        self.btn_export.pack(side="left", padx=5)

        self.btn_delete = ctk.CTkButton(
            self.actions_frame,
            text="🗑️ Delete Book",
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self.delete_book_action
        )
        self.btn_delete.pack(side="right", padx=5)

    def create_stat_card(self, parent, title, initial_val, col):
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=col, padx=5, pady=5, sticky="ew")

        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12, weight="bold"), text_color="gray70")
        lbl_title.pack(padx=10, pady=(10, 2))

        lbl_val = ctk.CTkLabel(card, text=initial_val, font=ctk.CTkFont(size=22, weight="bold"))
        lbl_val.pack(padx=10, pady=(0, 10))

        return lbl_val

    def setup_help_view(self):
        """Setup Help & FAQ view."""
        title = ctk.CTkLabel(self.help_view, text="❓ Help & Frequently Asked Questions", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(anchor="w", pady=(0, 15))

        textbox = ctk.CTkTextbox(self.help_view, font=ctk.CTkFont(size=13))
        textbox.pack(fill="both", expand=True)

        faq_text = """
1. How do I add a new book?
Fill out the 'Add New Book' form on the left panel of the Dashboard with the Title, Author, and Category. Click 'Add Book to Library'.

2. How do I search and filter?
Use the search bar at the top right of the Dashboard. You can filter by entering keywords or selecting specific Categories and Statuses from the dropdowns.

3. How do I issue or return a book?
Select a book from the table list and click the '🔄 Issue / Return Toggle' button at the bottom of the table.

4. How do I edit or delete a book?
Select a book row from the table and click '✏️ Edit Book' or '🗑️ Delete Book'.

5. Where is data stored?
All records are saved safely in your local SQLite database file (library.db).
        """
        textbox.insert("0.0", faq_text.strip())
        textbox.configure(state="disabled")

    def setup_about_view(self):
        """Setup About view."""
        title = ctk.CTkLabel(self.about_view, text="ℹ️ About Library Management System", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(anchor="w", pady=(0, 15))

        textbox = ctk.CTkTextbox(self.about_view, font=ctk.CTkFont(size=13))
        textbox.pack(fill="both", expand=True)

        about_text = """
📚 Library Management System - Desktop Application Edition

Project Overview:
The Library Management System is a desktop application built to manage library book records with high performance and interactive UI controls.

Quality Goal:
Q10 - Quality Documentation & User Guidance (BBAT104 - Fundamentals of TQM).

Technology Stack:
- Python 3
- CustomTkinter (Desktop GUI Framework)
- SQLite 3 (Embedded Database Engine)
- Pillow (Image Processing)

Key Desktop Features:
- Native Desktop Window with Dark/Light Appearance Mode
- Live Dashboard Metrics (Total, Available, Borrowed, Categories)
- Instant Search & Filter by Category / Status
- Full CRUD Operations (Add, Edit, Delete, Issue/Return Toggle)
- Safe Confirmation Dialogs and Error Validations
        """
        textbox.insert("0.0", about_text.strip())
        textbox.configure(state="disabled")

    # --- View Navigation Handlers ---
    def show_dashboard_view(self):
        self.help_view.grid_forget()
        self.about_view.grid_forget()
        self.dashboard_view.grid(row=0, column=0, sticky="nsew")
        self.header_title.configure(text="📚 Library Catalog & Dashboard")

        self.btn_nav_dashboard.configure(fg_color=["#3a7ebf", "#1f538d"], text_color="white")
        self.btn_nav_help.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_nav_about.configure(fg_color="transparent", text_color=("gray10", "gray90"))

    def show_help_view(self):
        self.dashboard_view.grid_forget()
        self.about_view.grid_forget()
        self.help_view.grid(row=0, column=0, sticky="nsew")
        self.header_title.configure(text="❓ Help & User Guide")

        self.btn_nav_dashboard.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_nav_help.configure(fg_color=["#3a7ebf", "#1f538d"], text_color="white")
        self.btn_nav_about.configure(fg_color="transparent", text_color=("gray10", "gray90"))

    def show_about_view(self):
        self.dashboard_view.grid_forget()
        self.help_view.grid_forget()
        self.about_view.grid(row=0, column=0, sticky="nsew")
        self.header_title.configure(text="ℹ️ About Application")

        self.btn_nav_dashboard.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_nav_help.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_nav_about.configure(fg_color=["#3a7ebf", "#1f538d"], text_color="white")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    # --- Database & UI Logic ---
    def load_categories_filter(self):
        conn = get_db_connection()
        rows = conn.execute("SELECT DISTINCT category FROM books ORDER BY category").fetchall()
        conn.close()

        cats = ["All Categories"] + [r["category"] for r in rows if r["category"]]
        self.filter_cat_option.configure(values=cats)

    def refresh_dashboard(self):
        search_query = self.entry_search.get().strip()
        category_filter = self.filter_cat_option.get()
        status_filter = self.filter_status_option.get()

        conn = get_db_connection()

        # Build Search & Filter SQL Query
        query = "SELECT * FROM books WHERE 1=1"
        params = []

        if search_query:
            query += " AND (title LIKE ? OR author LIKE ? OR category LIKE ?)"
            wildcard = f"%{search_query}%"
            params.extend([wildcard, wildcard, wildcard])

        if category_filter and category_filter != "All Categories":
            query += " AND category = ?"
            params.append(category_filter)

        if status_filter and status_filter != "All Statuses":
            query += " AND status = ?"
            params.append(status_filter)

        query += " ORDER BY id DESC"

        books = conn.execute(query, params).fetchall()

        # Calculate Statistics
        total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        available = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'Available'").fetchone()[0]
        borrowed = conn.execute("SELECT COUNT(*) FROM books WHERE status = 'Borrowed'").fetchone()[0]
        categories_count = conn.execute("SELECT COUNT(DISTINCT category) FROM books").fetchone()[0]

        conn.close()

        # Update Stat Cards
        self.card_total.configure(text=str(total))
        self.card_available.configure(text=str(available))
        self.card_borrowed.configure(text=str(borrowed))
        self.card_categories.configure(text=str(categories_count))

        # Clear and Populate Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        for b in books:
            self.tree.insert("", "end", iid=b["id"], values=(
                b["id"],
                b["title"],
                b["author"],
                b["category"],
                b["status"]
            ))

    def reset_filters(self):
        self.entry_search.delete(0, tk.END)
        self.filter_cat_option.set("All Categories")
        self.filter_status_option.set("All Statuses")
        self.refresh_dashboard()

    def add_book_action(self):
        title = self.entry_title.get().strip()
        author = self.entry_author.get().strip()
        category = self.entry_category.get().strip()
        status = self.option_status.get().strip()

        if not title or not author or not category:
            messagebox.showwarning("Validation Error", "Please fill in all required fields (Title, Author, Category).")
            return

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO books (title, author, category, status) VALUES (?, ?, ?, ?)",
            (title, author, category, status)
        )
        conn.commit()
        conn.close()

        # Reset Form Fields
        self.entry_title.delete(0, tk.END)
        self.entry_author.delete(0, tk.END)
        self.entry_category.delete(0, tk.END)
        self.option_status.set("Available")

        messagebox.showinfo("Success", f'Book "{title}" added successfully!')
        self.load_categories_filter()
        self.refresh_dashboard()

    def toggle_status_action(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a book from the table first.")
            return

        book_id = int(selected[0])
        conn = get_db_connection()
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

        if book:
            new_status = "Borrowed" if book["status"] == "Available" else "Available"
            conn.execute("UPDATE books SET status = ? WHERE id = ?", (new_status, book_id))
            conn.commit()
            messagebox.showinfo("Status Updated", f'Status for "{book["title"]}" changed to {new_status}.')

        conn.close()
        self.refresh_dashboard()

    def delete_book_action(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a book from the table first.")
            return

        book_id = int(selected[0])
        conn = get_db_connection()
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

        if book:
            confirm = messagebox.askyesno("Confirm Delete", f'Are you sure you want to delete "{book["title"]}"?')
            if confirm:
                conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
                conn.commit()
                messagebox.showinfo("Deleted", f'Book "{book["title"]}" removed successfully.')

        conn.close()
        self.load_categories_filter()
        self.refresh_dashboard()

    def export_csv_action(self):
        """Exports currently filtered library records to a CSV file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Books to CSV",
            initialfile="library_books.csv"
        )
        if not file_path:
            return

        search_text = self.search_var.get().strip()
        cat_filter = self.filter_cat_var.get().strip()
        status_filter = self.filter_status_var.get().strip()

        query = "SELECT id, title, author, category, status, created_at FROM books WHERE 1=1"
        params = []

        if search_text:
            query += " AND (title LIKE ? OR author LIKE ? OR category LIKE ?)"
            wildcard = f"%{search_text}%"
            params.extend([wildcard, wildcard, wildcard])

        if cat_filter and cat_filter != "All Categories":
            query += " AND category = ?"
            params.append(cat_filter)

        if status_filter and status_filter != "All Statuses":
            query += " AND status = ?"
            params.append(status_filter)

        query += " ORDER BY id DESC"

        conn = get_db_connection()
        books = conn.execute(query, params).fetchall()
        conn.close()

        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
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
            messagebox.showinfo("Export Successful", f"Successfully exported {len(books)} book record(s) to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"An error occurred while saving the CSV file:\n{str(e)}")

    def edit_book_dialog(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a book from the table first.")
            return

        book_id = int(selected[0])
        conn = get_db_connection()
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        conn.close()

        if not book:
            return

        # Modal Popup Dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Book Record")
        dialog.geometry("400x420")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="✏️ Edit Book Record", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)

        ctk.CTkLabel(dialog, text="Book Title *", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=20, anchor="w")
        edit_title = ctk.CTkEntry(dialog)
        edit_title.pack(padx=20, pady=(0, 10), fill="x")
        edit_title.insert(0, book["title"])

        ctk.CTkLabel(dialog, text="Author *", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=20, anchor="w")
        edit_author = ctk.CTkEntry(dialog)
        edit_author.pack(padx=20, pady=(0, 10), fill="x")
        edit_author.insert(0, book["author"])

        ctk.CTkLabel(dialog, text="Category *", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=20, anchor="w")
        edit_category = ctk.CTkEntry(dialog)
        edit_category.pack(padx=20, pady=(0, 10), fill="x")
        edit_category.insert(0, book["category"])

        ctk.CTkLabel(dialog, text="Status", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=20, anchor="w")
        edit_status = ctk.CTkOptionMenu(dialog, values=["Available", "Borrowed"])
        edit_status.pack(padx=20, pady=(0, 15), fill="x")
        edit_status.set(book["status"])

        def save_changes():
            new_title = edit_title.get().strip()
            new_author = edit_author.get().strip()
            new_category = edit_category.get().strip()
            new_status_val = edit_status.get().strip()

            if not new_title or not new_author or not new_category:
                messagebox.showwarning("Validation Error", "All fields are required.", parent=dialog)
                return

            db_conn = get_db_connection()
            db_conn.execute(
                "UPDATE books SET title = ?, author = ?, category = ?, status = ? WHERE id = ?",
                (new_title, new_author, new_category, new_status_val, book_id)
            )
            db_conn.commit()
            db_conn.close()

            dialog.destroy()
            messagebox.showinfo("Success", f'Book "{new_title}" updated successfully!')
            self.load_categories_filter()
            self.refresh_dashboard()

        ctk.CTkButton(dialog, text="Save Changes", font=ctk.CTkFont(weight="bold"), command=save_changes).pack(padx=20, pady=10, fill="x")


if __name__ == "__main__":
    app = LibraryApp()
    app.mainloop()
