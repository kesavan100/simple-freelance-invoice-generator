import sqlite3
import shutil
from datetime import datetime, date
from pathlib import Path
from flask import g, current_app
from app.config import Config


def get_db():
    """Returns the SQLite database connection for the current request context."""
    if "db" not in g:
        db_path = Path(current_app.config.get("DATABASE_PATH", Config.DATABASE_PATH))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row
        # Enable Foreign Key enforcement in SQLite
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(e=None):
    """Closes database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app=None):
    """Initializes schema and default freelancer profile."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    
    if app:
        db_path = Path(app.config.get("DATABASE_PATH", Config.DATABASE_PATH))
    else:
        db_path = Path(Config.DATABASE_PATH)
        
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
        
    # Ensure default profile row exists
    cur = conn.cursor()
    
    # Auto-migrate upi_id column if not present
    try:
        cur.execute("ALTER TABLE freelancer_profile ADD COLUMN upi_id TEXT DEFAULT 'alexmorgan@okhdfcbank'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Ensure default users table and seed default user
    from werkzeug.security import generate_password_hash
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL DEFAULT 'Freelancer Admin',
            role TEXT NOT NULL DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("SELECT id FROM users WHERE email = 'shalinimurugan1905@gmail.com' OR email = 'admin@freelance.local'")
    if not cur.fetchone():
        hashed_pw = generate_password_hash("admin123")
        cur.execute("""
            INSERT INTO users (email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """, ('shalinimurugan1905@gmail.com', hashed_pw, 'Shalini M', 'admin'))
        conn.commit()

    cur.execute("SELECT id FROM freelancer_profile WHERE id = 1")
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO freelancer_profile (
                id, full_name, business_name, email, phone, address, website,
                tax_number, upi_id, default_currency, default_tax_percent, default_payment_terms, default_template
            ) VALUES (
                1, 'Shalini M', 'Morgan Creative Labs', 'shalinimurugan1905@gmail.com',
                '+91 98765 43210', '402 Tech Hub, Innovation Boulevard, Bengaluru, Karnataka 560100',
                'https://morganlabs.design', 'GSTIN29ABCDE1234F1Z5', 'alexmorgan@okhdfcbank', 'INR', 18.0,
                'Payment due within 15 days of invoice date.', 'classic'
            )
        """)
        conn.commit()
    conn.close()


def log_activity(action: str, entity_type: str, entity_id: int, description: str):
    """Logs an action to the activity_logs table."""
    try:
        db = get_db()
        db.execute(
            "INSERT INTO activity_logs (action, entity_type, entity_id, description) VALUES (?, ?, ?, ?)",
            (action, entity_type, entity_id, description)
        )
        db.commit()
    except Exception as e:
        # Avoid crashing primary operations if activity log fails
        print(f"Failed to log activity: {e}")


def create_backup() -> Path:
    """Creates a timestamped backup of the SQLite database."""
    db_path = Path(Config.DATABASE_PATH)
    if not db_path.exists():
        raise FileNotFoundError("Database file does not exist.")
        
    backup_dir = Path(Config.BACKUP_FOLDER)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_file = backup_dir / f"invoice_backup_{timestamp}.db"
    
    # Safe SQLite backup using VACUUM INTO or file copy
    shutil.copy2(db_path, backup_file)
    return backup_file


def seed_demo_data():
    """Seeds rich, realistic demo clients, invoices, expenses, and logs for portfolio presentation."""
    db = get_db()
    
    # Check if we already have clients or invoices
    existing_clients = db.execute("SELECT COUNT(*) as count FROM clients").fetchone()["count"]
    if existing_clients > 0:
        return False, "Demo data already exists or data is not empty."

    # 1. Insert Profile if needed
    db.execute("""
        INSERT OR REPLACE INTO freelancer_profile (
            id, full_name, business_name, email, phone, address, website,
            tax_number, upi_id, default_currency, default_tax_percent, default_payment_terms, default_template
        ) VALUES (
            1, 'Alex Morgan', 'Morgan Creative Labs', 'alex@morganlabs.design',
            '+91 98765 43210', '402 Tech Hub, Innovation Boulevard, Bengaluru, Karnataka 560100',
            'https://morganlabs.design', 'GSTIN29ABCDE1234F1Z5', 'alexmorgan@okhdfcbank', 'INR', 18.0,
            'Payment due within 15 days of invoice date.', 'classic'
        )
    """)

    # 2. Insert Clients
    clients = [
        ("ABC Technologies", "ABC Technologies Pvt Ltd", "billing@abctech.io", "+91 98111 22334", "Floor 6, Tower B, Electronic City, Bengaluru", "GSTIN29AABCA1122D1Z1", "Enterprise SaaS client. Fast payments."),
        ("Pixel Studio", "Pixel Creative Agency", "finance@pixelstudio.design", "+91 98222 33445", "18 Art District, Indiranagar, Bengaluru", "GSTIN29AABCP3344E1Z2", "Design agency subcontracting UI/UX engineering."),
        ("John Designs", "Johnathan Miller Consulting", "john@johndesigns.com", "+1 (555) 234-5678", "742 Evergreen Terrace, San Francisco, CA 94107", "US-EIN-94-3829102", "Overseas product advisory & frontend architecture.")
    ]
    
    client_ids = {}
    for name, company, email, phone, addr, tax_no, notes in clients:
        cur = db.execute(
            "INSERT INTO clients (name, company_name, email, phone, address, tax_number, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, company, email, phone, addr, tax_no, notes)
        )
        client_ids[name] = cur.lastrowid

    # 3. Insert Invoices & Line Items
    from app.services.qr_service import generate_verification_token
    from app.services.invoice_service import calculate_document_hash

    invoices_data = [
        {
            "invoice_number": "INV-001",
            "client_id": client_ids["ABC Technologies"],
            "invoice_date": "2026-08-01",
            "due_date": "2026-08-16",
            "currency": "INR",
            "subtotal": 36500.0,
            "discount_percent": 0.0,
            "discount_amount": 0.0,
            "tax_percent": 18.0,
            "tax_amount": 6570.0,
            "total": 43070.0,
            "status": "Paid",
            "payment_terms": "Payment due within 15 days of invoice date.",
            "notes": "Full payment received with gratitude. Thank you for your partnership!",
            "template": "classic",
            "paid_date": "2026-08-14",
            "items": [
                ("Enterprise React Dashboard Frontend Architecture", 15, 1500.0, 22500.0),
                ("REST API & WebSocket Integration with State Management", 10, 1400.0, 14000.0)
            ]
        },
        {
            "invoice_number": "INV-002",
            "client_id": client_ids["Pixel Studio"],
            "invoice_date": "2026-08-10",
            "due_date": "2026-08-25",
            "currency": "INR",
            "subtotal": 22500.0,
            "discount_percent": 5.0,
            "discount_amount": 1125.0,
            "tax_percent": 18.0,
            "tax_amount": 3847.5,
            "total": 25222.5,
            "status": "Paid",
            "payment_terms": "Net 15 days.",
            "notes": "Delivered milestone 1 design tokens and responsive prototypes.",
            "template": "modern",
            "paid_date": "2026-08-22",
            "items": [
                ("Design System Component Library in Vanilla CSS & TypeScript", 12, 1250.0, 15000.0),
                ("Interactive Prototype Animation & Accessibility Audit", 6, 1250.0, 7500.0)
            ]
        },
        {
            "invoice_number": "INV-003",
            "client_id": client_ids["ABC Technologies"],
            "invoice_date": "2026-08-20",
            "due_date": "2026-09-04",
            "currency": "INR",
            "subtotal": 12000.0,
            "discount_percent": 0.0,
            "discount_amount": 0.0,
            "tax_percent": 18.0,
            "tax_amount": 2160.0,
            "total": 14160.0,
            "status": "Pending",
            "payment_terms": "Payment due within 15 days of invoice date.",
            "notes": "Sprint 2 backend services and invoice verification endpoints.",
            "template": "classic",
            "paid_date": None,
            "items": [
                ("Python / Flask Microservice API Development", 8, 1500.0, 12000.0)
            ]
        },
        {
            "invoice_number": "INV-004",
            "client_id": client_ids["John Designs"],
            "invoice_date": "2026-07-15",
            "due_date": "2026-07-30",
            "currency": "INR",
            "subtotal": 8000.0,
            "discount_percent": 0.0,
            "discount_amount": 0.0,
            "tax_percent": 0.0,
            "tax_amount": 0.0,
            "total": 8000.0,
            "status": "Overdue",
            "payment_terms": "Net 15 days. Wire transfer / PayPal.",
            "notes": "Advisory consultation on AI pipeline integration.",
            "template": "minimal",
            "paid_date": None,
            "items": [
                ("AI Pipeline Strategy & Technical Roadmap Review", 5, 1600.0, 8000.0)
            ]
        }
    ]

    for inv in invoices_data:
        token = generate_verification_token()
        doc_hash = calculate_document_hash(
            inv["invoice_number"],
            inv["client_id"],
            inv["total"],
            inv["invoice_date"]
        )
        
        cur = db.execute("""
            INSERT INTO invoices (
                invoice_number, client_id, invoice_date, due_date, currency,
                subtotal, discount_percent, discount_amount, tax_percent, tax_amount,
                total, status, payment_terms, notes, template, verification_token,
                document_hash, paid_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inv["invoice_number"], inv["client_id"], inv["invoice_date"], inv["due_date"],
            inv["currency"], inv["subtotal"], inv["discount_percent"], inv["discount_amount"],
            inv["tax_percent"], inv["tax_amount"], inv["total"], inv["status"],
            inv["payment_terms"], inv["notes"], inv["template"], token, doc_hash, inv["paid_date"]
        ))
        
        inv_id = cur.lastrowid
        
        for idx, (desc, hrs, rate, amt) in enumerate(inv["items"]):
            db.execute("""
                INSERT INTO invoice_items (invoice_id, description, hours, hourly_rate, amount, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (inv_id, desc, hrs, rate, amt, idx))
            
        if inv["status"] == "Paid":
            db.execute("""
                INSERT INTO payment_records (invoice_id, amount, payment_date, payment_method, notes)
                VALUES (?, ?, ?, 'Bank Transfer', 'Full settlement received')
            """, (inv_id, inv["total"], inv["paid_date"]))

    # 4. Insert Realistic Expenses
    expenses = [
        ("2026-08-25", "Adobe Creative Cloud Annual Subscription", "Adobe Systems", "Software", 2499.0, "INR", "Credit Card", "Creative suite for UI/UX prototypes and vector branding."),
        ("2026-08-23", "Client meeting local transit & commute", "Uber", "Travel", 1200.0, "INR", "UPI", "Client presentation at Electronic City campus."),
        ("2026-08-20", "High-speed Fiber Broadband Monthly Connection", "Airtel Broadband", "Internet", 999.0, "INR", "Auto-debit", "Dedicated business fiber connectivity 300 Mbps."),
        ("2026-08-15", "GitHub Copilot & JetBrains IDE License", "GitHub / JetBrains", "Software", 1850.0, "INR", "Credit Card", "Developer tooling & code intelligence productivity tools."),
        ("2026-08-05", "Ergonomic Mechanical Keyboard & Monitor Arm", "Amazon India", "Equipment", 4800.0, "INR", "Debit Card", "Workstation ergonomic upgrade."),
        ("2026-08-02", "Cloud Staging VPS & Custom Domain Renewal", "Hetzner Cloud", "Utilities", 1450.0, "INR", "Credit Card", "Infrastructure hosting for client demos and staging apps.")
    ]
    
    for dt, desc, merch, cat, amt, curr, pmethod, notes in expenses:
        db.execute("""
            INSERT INTO expenses (date, description, merchant, category, amount, currency, payment_method, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (dt, desc, merch, cat, amt, curr, pmethod, notes))

    # 5. Activity Logs
    db.execute("INSERT INTO activity_logs (action, entity_type, entity_id, description) VALUES ('CREATE', 'INVOICE', 1, 'Created invoice INV-001 for ABC Technologies')")
    db.execute("INSERT INTO activity_logs (action, entity_type, entity_id, description) VALUES ('PAYMENT', 'INVOICE', 1, 'Marked invoice INV-001 as Paid (₹43,070)')")
    db.execute("INSERT INTO activity_logs (action, entity_type, entity_id, description) VALUES ('CREATE', 'INVOICE', 2, 'Created invoice INV-002 for Pixel Studio')")
    db.execute("INSERT INTO activity_logs (action, entity_type, entity_id, description) VALUES ('PAYMENT', 'INVOICE', 2, 'Marked invoice INV-002 as Paid (₹25,222.50)')")
    db.execute("INSERT INTO activity_logs (action, entity_type, entity_id, description) VALUES ('CREATE', 'INVOICE', 3, 'Created invoice INV-003 for ABC Technologies')")
    db.execute("INSERT INTO activity_logs (action, entity_type, entity_id, description) VALUES ('CREATE', 'EXPENSE', 1, 'Recorded expense for Adobe Systems (₹2,499)')")

    db.commit()
    return True, "Demo data successfully seeded."
