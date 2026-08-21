from fastmcp import FastMCP
import os
import sqlite3
 
DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")
 
mcp = FastMCP("ExpensesTracker")
 
 
def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT DEFAULT '',
        note TEXT DEFAULT '',
        type TEXT NOT NULL DEFAULT 'expense')""")
 
 
init_db()
 
 
@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    '''Add a new expense entry to the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note, type) VALUES (?,?,?,?,?,'expense')",
            (date, amount, category, subcategory, note)
        )
        return {"status": "ok", "id": cur.lastrowid}
 
 
@mcp.tool()
def list_expenses(start_date, end_date):
    '''List expense entries within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note, type
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
 
 
@mcp.tool()
def summarize(start_date, end_date, category=None):
    '''Summarize expenses and credits by category within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        query = (
            """
            SELECT category, type, SUM(amount) AS total_amount, COUNT(*) AS count
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " GROUP BY category, type ORDER BY type ASC, category ASC"
        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
 
        total_expenses = sum(r["total_amount"] for r in rows if r["type"] == "expense")
        total_credits = sum(r["total_amount"] for r in rows if r["type"] == "credit")
 
        return {
            "breakdown": rows,
            "total_expenses": total_expenses,
            "total_credits": total_credits,
            "net": total_credits - total_expenses
        }
 
 
@mcp.tool()
def delete_expense(id):
    '''Delete an expense entry by its ID.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM expenses WHERE id = ?", (id,))
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}"}
        return {"status": "ok", "deleted_id": id}
 
 
@mcp.tool()
def update_expense(id, date=None, amount=None, category=None, subcategory=None, note=None):
    '''Update one or more fields of an existing expense entry by ID.'''
    fields = {"date": date, "amount": amount, "category": category, "subcategory": subcategory, "note": note}
    updates = {k: v for k, v in fields.items() if v is not None}
 
    if not updates:
        return {"status": "error", "message": "No fields to update"}
 
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [id]
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(f"UPDATE expenses SET {set_clause} WHERE id = ?", values)
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}"}
        return {"status": "ok", "updated_id": id, "changes": updates}
 
 
@mcp.tool()
def add_credit(date, amount, category, subcategory="", note=""):
    '''Add a credit/income entry (money received) to the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note, type) VALUES (?,?,?,?,?,'credit')",
            (date, amount, category, subcategory, note)
        )
        return {"status": "ok", "id": cur.lastrowid}
 
 
@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Read fresh each time so you can edit the file without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()
 
 
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)