import functools

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        )


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form["username"]
        first_name = request.form["first_name"]
        middle_name = request.form["middle_name"]
        no_middle_name = "no_middle_name" in request.form
        last_name = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        db = get_db()
        error = None

        if not username:
            error = "Username is required."
        elif not first_name:
            error = "First Name is required"
        elif no_middle_name == False and not middle_name:
            error = "Middle Name is required"
        elif no_middle_name and middle_name:
            error = "I thought you have no middle name?"
        elif not last_name:
            error = "Last Name is required"
        elif not password or not confirm_password:
            error = "Password and Confirmation are required."
        elif password != confirm_password:
            error = "Passwords doesn't match."

        if error is None:
            try:
                db.execute("BEGIN TRANSACTION")
                db.execute(
                    "INSERT INTO names (first_name, middle_name, no_middle_name, last_name) VALUES (?, ?, ?, ?)",
                    (first_name, middle_name, no_middle_name, last_name),
                )
                name_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                db.execute(
                    "INSERT INTO users (name_id, username, password, email) VALUES (?, ?, ?, ?)",
                    (name_id, username, generate_password_hash(password), email),
                )
                user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                db.execute(
                    "INSERT INTO accounts (user_id, account_name, account_type, balance) VALUES (?, ?, ?, ?)",
                    (user_id, "Credit", "Credit", 0)
                )
                db.execute(
                    "INSERT INTO accounts (user_id, account_name, account_type, balance) VALUES (?, ?, ?, ?)",
                    (user_id, "Debit", "Debit", 0)
                )
                db.commit()
                db.rollback()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return render_template("auth/auth.html", rap=None)

        flash(error)

    rap = "right-panel-active"
    return render_template("auth/auth.html", rap=rap, signup=True)


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        error = None
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user["password"], password):
            error = "Incorrect password."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard.index"))

        flash(error)

    return render_template("auth/auth.html", rap=None, login=True)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
