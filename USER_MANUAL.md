# 📚 Library Management System - User Manual

> **User Guide & Operating Instructions**

---

## 1. Introduction

Welcome to the **Library Management System**. This user manual guides you through operating the application to manage books, track issue/borrow status, perform searches, and update records.

---

## 2. Getting Started

### Step 1: Launching the App
1. Open your terminal or command prompt in the project root folder `library_management`.
2. Run the command:
   ```bash
   python app.py
   ```
3. Open your web browser and navigate to:
   ```text
   http://127.0.0.1:5000
   ```

---

## 3. Core Features & How To Use Them

### 📖 Adding a New Book
1. On the **Dashboard**, locate the **Add New Book** card on the left side.
2. Enter the **Book Title**, **Author**, and **Category**.
3. Select the initial status (`Available` or `Borrowed`).
4. Click **Add Book to Library**. A success banner will confirm the addition.

### 🔍 Searching & Filtering Books
1. Type search terms into the **Search** field (matches title, author, or category).
2. Filter specifically using the **All Categories** or **All Statuses** dropdown menus.
3. Click **Filter**. To clear filters, click **Reset**.

### 🔄 Issuing or Returning a Book
1. Find the target book in the **Book List** table.
2. Click the **Issue** button to mark an available book as borrowed.
3. Click the **Return** button to mark a borrowed book as available again.

### ✏️ Editing a Book Record
1. Click the **Edit** button in the action column for the book you wish to update.
2. Update any fields (Title, Author, Category, Status).
3. Click **Save Changes**.

### 🗑️ Deleting a Book
1. Click the **Delete** button next to the target book.
2. Confirm the prompt to remove the book permanently.

---

## 4. Troubleshooting & Support

If you encounter any issues, click on **Help & FAQ** in the top navigation bar or refer to `KNOWLEDGE_BASE.md`.