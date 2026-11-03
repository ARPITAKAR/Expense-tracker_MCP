from fastmcp import FastMCP
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
# --------------------------------------------------
# 1. FastMCP Server
# --------------------------------------------------
mcp = FastMCP("Expense Tracker")

CATEGORIES_PATH = os.path.join(
    os.path.dirname(__file__), "categories.json"
)

# --------------------------------------------------
# 2. PostgreSQL Connection
# --------------------------------------------------

def get_db_connection():
    """Create and return PostgreSQL Connection"""
    
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        database=os.getenv("PGDATABASE", "expense_tracker"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD")
    )
    
# --------------------------------------------------
# 3. Initialize Database
# --------------------------------------------------

def init_db():
    """Create expenses table if it does not exist"""
    
    with get_db_connection() as conn:
        with conn.cursor() as curr:
            curr.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id BIGSERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    amount NUMERIC(12,2) NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)

    print("PostgreSQL database initialized.")
init_db()
# --------------------------------------------------
# 4. Add Expense Tool
# --------------------------------------------------
@mcp.tool()
def add_expense(date:str,
                amount:float,
                category:str,
                subcategory:str="",
                note:str=""):
    with get_db_connection() as conn:
        with conn.cursor() as curr:
            curr.execute(
                """
                INSERT INTO expenses
                (date, amount, category, subcategory, note)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (date, amount, category, subcategory, note)
            )
            
            expense_id = curr.fetchone()[0]
            
            return {
                'status':"ok",
                "id": expense_id
            }
# --------------------------------------------------
# 5. List Expenses Tool
# --------------------------------------------------
# execute() sends SQL to PostgreSQL.
# fetchall() retrieves all returned records.
# fetchone() retrieves one record.
# fetchmany() retrieves a specified number of records.

@mcp.tool()
def list_expense(start_date: str, end_date: str):
     with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as curr:
                curr.execute(
                    """
                    SELECT id, date, amount, category, note
                    FROM expenses
                    WHERE date BETWEEN %s AND %s
                    ORDER BY id ASC
                    """,
                    (start_date, end_date)
                )
                rows = curr.fetchall()
                # Convert PostgreSQL DATE and Decimal values
                # into JSON-friendly values
                results = []

                for row in rows:
                    item = dict(row)
                    item["date"] = item["date"].isoformat()
                    item["amount"] = float(item["amount"])
                    results.append(item)

                return results
            
            
# --------------------------------------------------
# 6. Summarize Expenses Tool
# --------------------------------------------------

@mcp.tool()
def summarize(
    start_date: str,
    end_date: str,
    category: str = None
):
    """Summarize expenses by category within an inclusive date range."""

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            query = """
                SELECT category,
                       SUM(amount) AS total_amount
                FROM expenses
                WHERE date BETWEEN %s AND %s
            """

            params = [start_date, end_date]

            if category:
                query += " AND category = %s"
                params.append(category)

            query += """
                GROUP BY category
                ORDER BY category ASC
            """

            cur.execute(query, params)

            rows = cur.fetchall()

            return [
                {
                    "category": row["category"],
                    "total_amount": float(row["total_amount"])
                }
                for row in rows
            ]
            
# --------------------------------------------------
# 7. Categories Resource
# --------------------------------------------------

@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def categories():
    """Read expense categories from JSON file."""

    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()
    
                
if __name__=="__main__":
    mcp.run(transport='http',host="0.0.0.0",port=8000)
                
                
               