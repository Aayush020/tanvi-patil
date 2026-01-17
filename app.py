import os
from flask import Flask, request, render_template_string
from flask_mail import Mail, Message

# ================== APP SETUP ==================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Loaded from environment

# ================== MAIL CONFIG ==================
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 587))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config['MAIL_USE_SSL'] = os.getenv("MAIL_USE_SSL", "False") == "True"
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']
app.config['MAIL_DEBUG'] = True  # logs SMTP interactions

mail = Mail(app)

# ================== TEST ROUTE ==================
@app.route("/test-mail", methods=["GET", "POST"])
def test_mail():
    if request.method == "POST":
        recipient = request.form.get("to")
        subject = request.form.get("subject", "Test Email")
        body = request.form.get("body", "This is a test email from Flask!")

        msg = Message(subject=subject, recipients=[recipient])
        msg.body = body

        try:
            mail.send(msg)
            return f"✅ Email successfully sent to {recipient}"
        except Exception as e:
            # Log the error to Render logs
            print("❌ Mail sending failed:", e)
            return f"❌ Mail sending failed: {e}"

    # Simple HTML form to test sending emails
    return render_template_string("""
        <h2>Send Test Email</h2>
        <form method="POST">
            To: <input type="email" name="to" required><br><br>
            Subject: <input type="text" name="subject"><br><br>
            Body:<br>
            <textarea name="body" rows="5" cols="40"></textarea><br><br>
            <input type="submit" value="Send Email">
        </form>
    """)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
