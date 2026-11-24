from flask import Flask, render_template, url_for, request, session, redirect, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.secret_key = "a"
db = SQLAlchemy(app)

class user(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(100), nullable=False)

@app.before_request
def before_request():
    g.user = None
    if "id" in session:
        print("Hello")
        g.user = user.query.get(session["id"])

@app.context_processor
def Global():
    return{
        "username": g.get("user") if g.get("user") else None
    }

def migrate_user_email():
    columns = {column["name"] for column in inspect(db.engine).get_columns("user")}
    if "email" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE user ADD COLUMN email VARCHAR(254)"))
            connection.execute(text("CREATE UNIQUE INDEX uq_user_email ON user (email)"))

@app.route('/register', methods = ["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().casefold()
        raw_password = request.form.get('password', '')
        if not username or not email or not raw_password:
            return render_template("register.html", error="Please enter a username, email, and password.")
        if user.query.filter_by(username=username).first():
            return render_template("register.html", error="That username is already in use.")
        if user.query.filter_by(email=email).first():
            return render_template("register.html", error="That email is already in use.")

        password = generate_password_hash(raw_password)
        try:
            newUser = user(username=username, email=email, password_hash=password)
            db.session.add(newUser)
            db.session.commit()
            session["id"] = newUser.id
            return redirect(url_for("home"))
        except IntegrityError:
            db.session.rollback()
            if user.query.filter_by(username=username).first():
                error = "That username is already in use."
            elif user.query.filter_by(email=email).first():
                error = "That email is already in use."
            else:
                raise
            return render_template("register.html", error=error)
        
    return render_template("register.html")

@app.route('/logout')
def logout():
    session.clear();
    g.user = None
    return redirect(url_for("home"))  

@app.route('/')
def home():
    return render_template("index.html")

@app.route("/contact", methods=["GET", "POST"])
def contacts():
    if request.method == 'POST' and g.user == None:
        name = request.form.get("username")
        msg = request.form.get("message")
 
        new_contact = Contact(username=name, message=msg)
        db.session.add(new_contact)
        db.session.commit()
 
        return f"Your message has been sent."
 
    return render_template("contact.html")

# login page
@app.route('/login', methods = ["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = user.query.filter_by(username=username).first()
        if existing_user and check_password_hash(existing_user.password_hash, password):
            session["id"] = existing_user.id
            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid username or password.")
        
    return render_template("login.html")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        migrate_user_email()
    app.run(debug=True)