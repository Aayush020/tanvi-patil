import os
from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
from datetime import date, timedelta
import mysql.connector
from decimal import Decimal
from dotenv import load_dotenv  # <-- import dotenv

# ================= LOAD ENV =================
load_dotenv()  # automatically reads .env file

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # <-- use secret from .env

# ================= MAIL CONFIG =================
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 587))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config['MAIL_USE_SSL'] = os.getenv("MAIL_USE_SSL", "False") == "True"
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']
app.config['MAIL_DEBUG'] = True

mail = Mail(app)

# ================= DATABASE =================
def get_db():
    db = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    return db

# ================= DATABASE INIT =================
def init_db():
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255),
        type VARCHAR(100),
        location VARCHAR(255),
        size VARCHAR(50),
        price DECIMAL(15,2),
        owner VARCHAR(255),
        contact VARCHAR(100),
        status VARCHAR(50),
        sold_price DECIMAL(15,2)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS collaborations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        supplier VARCHAR(255),
        category VARCHAR(100),
        service VARCHAR(255),
        contact_person VARCHAR(255),
        contact_number VARCHAR(50),
        email VARCHAR(255),
        start_date DATE,
        due_date DATE,
        total_amount DECIMAL(15,2),
        paid_amount DECIMAL(15,2),
        pending_amount DECIMAL(15,2)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS collaboration_interactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        collaboration_id INT,
        note TEXT,
        date DATE,
        FOREIGN KEY (collaboration_id) REFERENCES collaborations(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS interactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        property_id INT,
        customer_name VARCHAR(255),
        contact VARCHAR(50),
        notes TEXT,
        date DATE,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )
    """)

    db.commit()
    cur.close()
    db.close()

init_db()

# ================= USERS =================
USERS = {
    "tanvipatil": {"password": "tanvipatil@2211", "role": "admin"},
    "superadmin": {"password": "superadmin123", "role": "superadmin"}
}

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = USERS.get(request.form["username"])
        if user and user["password"] == request.form["password"]:
            session["username"] = request.form["username"]
            session["role"] = user["role"]
            return redirect("/dashboard")
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS count FROM properties")
    total_properties = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM properties WHERE status='Sold'")
    total_sold = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM collaborations")
    total_collab = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM collaborations WHERE pending_amount=0")
    collab_completed = cur.fetchone()["count"]

    cur.execute("SELECT SUM(sold_price) AS total FROM properties WHERE status='Sold'")
    property_revenue = cur.fetchone()["total"] or Decimal(0)

    cur.execute("SELECT SUM(paid_amount) AS total FROM collaborations")
    collaboration_revenue = cur.fetchone()["total"] or Decimal(0)

    total_revenue = float(property_revenue + collaboration_revenue)
    adjusted_property_revenue = float(property_revenue * Decimal('0.9'))
    adjusted_collaboration_revenue = float(collaboration_revenue * Decimal('0.9'))
    total_adjusted_revenue = adjusted_property_revenue + adjusted_collaboration_revenue

    stats = {
        "total_properties": total_properties,
        "total_sold": total_sold,
        "collab_completed": collab_completed,
        "total_collab": total_collab,
        "property_revenue": float(property_revenue),
        "collaboration_revenue": float(collaboration_revenue),
        "total_revenue": total_revenue,
        "adjusted_property_revenue": adjusted_property_revenue,
        "adjusted_collaboration_revenue": adjusted_collaboration_revenue,
        "total_adjusted_revenue": total_adjusted_revenue
    }

    cur.close()
    db.close()

    if session["role"] == "superadmin":
        return render_template("dashboard_actual.html", stats=stats)

    return render_template("dashboard_adjusted.html", stats=stats)

# ---------------- PROPERTIES ----------------
@app.route("/properties")
def properties_page():
    if "username" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM properties")
    properties = cur.fetchall()
    cur.close()
    db.close()
    return render_template("properties.html", properties=properties)

@app.route("/properties/add", methods=["GET", "POST"])
def add_property():
    if request.method == "POST":
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO properties
            (title,type,location,size,price,owner,contact,status,sold_price)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form["title"],
            request.form["type"],
            request.form["location"],
            request.form["size"],
            request.form["price"],
            request.form["owner"],
            request.form["contact"],
            "Available",
            0
        ))
        db.commit()
        cur.close()
        db.close()
        return redirect("/properties")
    return render_template("add_property.html")

@app.route("/properties/<int:pid>")
def property_detail(pid):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM properties WHERE id=%s", (pid,))
    prop = cur.fetchone()
    if not prop:
        cur.close()
        db.close()
        return "Property Not Found", 404

    cur.execute("SELECT * FROM interactions WHERE property_id=%s ORDER BY date DESC", (pid,))
    interactions = cur.fetchall()
    prop["interactions"] = interactions
    cur.close()
    db.close()
    return render_template("property_detail.html", prop=prop)

@app.route("/properties/<int:pid>/sold", methods=["POST"])
def mark_sold(pid):
    sold_price = float(request.form["sold_price"])
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM properties WHERE id=%s", (pid,))
    prop = cur.fetchone()

    cur.execute("UPDATE properties SET status='Sold', sold_price=%s WHERE id=%s", (sold_price, pid))
    db.commit()
    cur.close()
    db.close()

    msg = Message(subject="Property Sold Notification",
                  recipients=[app.config['MAIL_USERNAME']])
    msg.html = f"""
    <h2>Property Sold!</h2>
    <p><b>Title:</b> {prop['title']}</p>
    <p><b>Type:</b> {prop['type']}</p>
    <p><b>Location:</b> {prop['location']}</p>
    <p><b>Size:</b> {prop['size']}</p>
    <p><b>Owner:</b> {prop['owner']}</p>
    <p><b>Sold Price:</b> ₹ {sold_price}</p>
    <p><b>Date of Sale:</b> {date.today().isoformat()}</p>
    """
    mail.send(msg)
    return redirect("/properties")

@app.route("/properties/<int:pid>/edit", methods=["GET", "POST"])
def edit_property(pid):
    if "username" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "POST":
        cur.execute("""
            UPDATE properties SET
            title=%s, type=%s, location=%s, size=%s,
            price=%s, owner=%s, contact=%s, status=%s, sold_price=%s
            WHERE id=%s
        """, (
            request.form["title"], request.form["type"], request.form["location"], request.form["size"],
            request.form["price"], request.form["owner"], request.form["contact"], request.form["status"],
            float(request.form["sold_price"]), pid
        ))
        db.commit()
        cur.close()
        db.close()
        return redirect(f"/properties/{pid}")

    cur.execute("SELECT * FROM properties WHERE id=%s", (pid,))
    prop = cur.fetchone()
    cur.close()
    db.close()
    return render_template("edit_property.html", prop=prop)

@app.route("/properties/<int:pid>/delete")
def delete_property(pid):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM properties WHERE id=%s", (pid,))
    db.commit()
    cur.close()
    db.close()
    return redirect("/properties")

@app.route("/properties/<int:pid>/interactions/add", methods=["POST"])
def add_interaction(pid):
    if "username" not in session:
        return redirect("/login")
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO interactions (property_id, customer_name, contact, notes, date)
        VALUES (%s,%s,%s,%s,%s)
    """, (
        pid, request.form["customer_name"], request.form["contact"],
        request.form["notes"], date.today()
    ))
    db.commit()
    cur.close()
    db.close()
    return redirect(f"/properties/{pid}")

# ---------------- COLLABORATIONS ----------------
@app.route("/collaborations")
def collaborations_page():
    if "username" not in session:
        return redirect("/login")
    filter_type = request.args.get("filter")
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM collaborations")
    data = cur.fetchall()
    cur.close()
    db.close()

    today = date.today()
    processed = []
    for c in data:
        status = "Active"
        due = c["due_date"]
        if isinstance(due, str):
            due = date.fromisoformat(due)
        if due < today:
            status = "Expired"
        elif due <= today + timedelta(days=30):
            status = "Due Soon"
        row = dict(c)
        row["status"] = status

        if filter_type == "pending" and row["pending_amount"] == 0:
            continue
        if filter_type == "completed" and row["pending_amount"] != 0:
            continue
        if filter_type == "due_soon" and status != "Due Soon":
            continue

        processed.append(row)

    if filter_type == "due_asc":
        processed.sort(key=lambda x: x["due_date"])
    elif filter_type == "due_desc":
        processed.sort(key=lambda x: x["due_date"], reverse=True)

    return render_template("collaborations.html", collaborations=processed)

@app.route("/collaborations/<int:cid>")
def view_collaboration(cid):
    if "username" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM collaborations WHERE id=%s", (cid,))
    collab = cur.fetchone()
    if not collab:
        cur.close()
        db.close()
        return "Collaboration Not Found", 404

    # Fetch collaboration interactions
    cur.execute("SELECT * FROM collaboration_interactions WHERE collaboration_id=%s ORDER BY date DESC", (cid,))
    collab["interactions"] = cur.fetchall()
    cur.close()
    db.close()

    return render_template("collaboration_detail.html", collab=collab)

@app.route("/collaborations/<int:cid>/edit", methods=["GET", "POST"])
def edit_collaboration(cid):
    if "username" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "POST":
        total = float(request.form["total_amount"])
        paid = float(request.form["paid_amount"])
        pending = total - paid

        cur.execute("""
            UPDATE collaborations SET
            supplier=%s, category=%s, service=%s,
            contact_person=%s, contact_number=%s, email=%s,
            start_date=%s, due_date=%s,
            total_amount=%s, paid_amount=%s, pending_amount=%s
            WHERE id=%s
        """, (
            request.form["supplier"], request.form["category"], request.form["service"],
            request.form["contact_person"], request.form["contact_number"], request.form["email"],
            request.form["start_date"], request.form["due_date"],
            total, paid, pending, cid
        ))
        db.commit()
        cur.close()
        db.close()
        return redirect(f"/collaborations/{cid}")

    cur.execute("SELECT * FROM collaborations WHERE id=%s", (cid,))
    collab = cur.fetchone()
    cur.close()
    db.close()

    if collab:
        collab["profit"] = collab["paid_amount"] - collab["pending_amount"]

    return render_template("edit_collaboration.html", collab=collab)

@app.route("/collaborations/add", methods=["GET", "POST"])
def add_collaboration():
    if "username" not in session:
        return redirect("/login")

    collab = None

    if request.method == "POST":
        total = float(request.form["total_amount"])
        paid = float(request.form["paid_amount"])
        pending = total - paid

        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO collaborations
            (supplier, category, service, contact_person, contact_number, email,
             start_date, due_date, total_amount, paid_amount, pending_amount)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form["supplier"], request.form["category"], request.form["service"],
            request.form["contact_person"], request.form["contact_number"], request.form["email"],
            request.form["start_date"], request.form["due_date"], total, paid, pending
        ))
        db.commit()
        cur.close()
        db.close()
        return redirect("/collaborations")

    return render_template("add_collaboration.html", collab=collab)

@app.route("/collaborations/<int:cid>/interactions/add", methods=["POST"])
# ================= Collaboration Interactions =================

# Add Interaction
@app.route("/collaborations/<int:collab_id>/add_interaction", methods=["POST"])
def add_collab_interaction(collab_id):
    if "username" not in session:
        return redirect("/login")

    data = request.form
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO collaboration_interactions (collaboration_id, note, date)
        VALUES (%s, %s, %s)
    """, (
        collab_id,
        data["notes"],            # note from form
        data["interaction_date"]  # date from form
    ))
    db.commit()
    cur.close()
    db.close()

    return redirect(f"/collaborations/{collab_id}")  # redirect to detail page

# Delete Interaction
@app.route("/collaborations/<int:collab_id>/delete_interaction/<int:interaction_id>", methods=["POST"])
def delete_interaction(collab_id, interaction_id):
    if "username" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM collaboration_interactions WHERE id=%s", (interaction_id,))
    db.commit()
    cur.close()
    db.close()

    return redirect(f"/collaborations/{collab_id}")  # redirect to detail page


# REVENUE ----------------
@app.route("/revenue/actual")
def revenue_actual():
    if "username" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    # Property revenue
    cur.execute("SELECT SUM(sold_price) AS total_property FROM properties WHERE status='Sold'")
    row = cur.fetchone()
    property_total = float(row["total_property"] or 0)

    # Collaboration revenue
    cur.execute("SELECT SUM(paid_amount) AS total_collab FROM collaborations")
    row = cur.fetchone()
    collaboration_total = float(row["total_collab"] or 0)

    db.close()

    # Totals and profit
    grand_total = property_total + collaboration_total
    profit = grand_total  # You can adjust with deductions if needed

    # Ensure we send a dictionary with all keys
    revenue = {
        "property_total": round(property_total, 2),
        "collaboration_total": round(collaboration_total, 2),
        "grand_total": round(grand_total, 2),
        "profit": round(profit, 2)
    }

    return render_template("revenue_actual.html", revenue=revenue)



@app.route("/revenue/adjusted")
def revenue_adjusted():
    if "username" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    # Property revenue
    cur.execute("SELECT SUM(sold_price) AS total_property FROM properties WHERE status='Sold'")
    row = cur.fetchone()
    property_total = float(row["total_property"] or 0)

    # Collaboration revenue
    cur.execute("SELECT SUM(paid_amount) AS total_collab FROM collaborations")
    row = cur.fetchone()
    collaboration_total = float(row["total_collab"] or 0)

    db.close()

    # Apply 90% adjustment
    property_total_adj = property_total * 0.9
    collaboration_total_adj = collaboration_total * 0.9
    grand_total = property_total_adj + collaboration_total_adj
    profit = grand_total  # same as grand_total for adjusted revenue

    # Always return a dictionary to match the template
    revenue = {
        "property_total": round(property_total_adj, 2),
        "collaboration_total": round(collaboration_total_adj, 2),
        "grand_total": round(grand_total, 2),
        "profit": round(profit, 2)
    }

    return render_template("revenue_adjusted.html", revenue=revenue)



@app.route("/collaborations/<int:cid>/delete", methods=["POST"])
def delete_collaboration(cid):
    if "username" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()
    # Delete collaboration
    cur.execute("DELETE FROM collaborations WHERE id=%s", (cid,))
    db.commit()
    cur.close()
    db.close()

    return redirect("/collaborations")



# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
