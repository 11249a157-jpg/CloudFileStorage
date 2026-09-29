import os
from datetime import datetime

from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
    send_file,
    abort
)

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from werkzeug.utils import secure_filename


app = Flask(__name__)

load_dotenv(
    os.path.join(app.root_path, ".env")
)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

AZURE_CONNECTION_STRING = os.getenv(
    "AZURE_STORAGE_CONNECTION_STRING"
)

print("Azure connection string found:", AZURE_CONNECTION_STRING is not None)

AZURE_CONTAINER_NAME = "cloud-files"

blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_CONNECTION_STRING
)

container_client = blob_service_client.get_container_client(
    AZURE_CONTAINER_NAME
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cloud_storage.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    files = db.relationship(
        "File",
        backref="owner",
        lazy=True
    )


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    storage_name = db.Column(
        db.String(255),
        nullable=False
    )

    upload_date = db.Column(
        db.DateTime,
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not username or not email or not password:
            return "Please fill in all fields."

        existing_user = User.query.filter(
            (User.username == username) |
            (User.email == email)
        ).first()

        if existing_user:
            return "Username or email already exists."

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(
            user.password,
            password
        ):
            session["user_id"] = user.id

            return redirect(url_for("dashboard"))

        return "Invalid email or password!"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    files = File.query.filter_by(
        user_id=user.id
    ).order_by(File.upload_date.desc()).all()

    return render_template(
        "dashboard.html",
        user=user,
        files=files
    )

@app.route("/upload", methods=["POST"])
def upload():

    if "user_id" not in session:
        return redirect(url_for("login"))

    uploaded_file = request.files.get("file")

    if uploaded_file is None or uploaded_file.filename == "":
        return "Please select a file."

    safe_filename = secure_filename(uploaded_file.filename)

    if not safe_filename:
        return "Invalid filename."

    storage_name = (
        f"{session['user_id']}_"
        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_"
        f"{safe_filename}"
    )

    try:
        blob_client = container_client.get_blob_client(
            storage_name
        )

        blob_client.upload_blob(
            uploaded_file,
            overwrite=False
        )

        new_file = File(
            filename=safe_filename,
            storage_name=storage_name,
            upload_date=datetime.now(),
            user_id=session["user_id"]
        )

        db.session.add(new_file)
        db.session.commit()

    except Exception:
        db.session.rollback()
        return "File upload failed."

    return redirect(url_for("dashboard"))

@app.route("/download/<int:file_id>")
def download(file_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    file_record = File.query.filter_by(
        id=file_id,
        user_id=session["user_id"]
    ).first()

    if file_record is None:
        abort(404)

    try:
        blob_client = container_client.get_blob_client(
            file_record.storage_name
        )

        file_data = blob_client.download_blob().readall()

        from io import BytesIO

        return send_file(
            BytesIO(file_data),
            as_attachment=True,
            download_name=file_record.filename
        )

    except Exception:
        return "File download failed."

@app.route("/delete/<int:file_id>", methods=["POST"])
def delete_file(file_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    file_record = File.query.filter_by(
        id=file_id,
        user_id=session["user_id"]
    ).first()

    if file_record is None:
        abort(404)

    try:
        blob_client = container_client.get_blob_client(
            file_record.storage_name
        )

        blob_client.delete_blob()

        db.session.delete(file_record)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("DELETE ERROR:", e)
        return f"File deletion failed: {e}"

    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run()