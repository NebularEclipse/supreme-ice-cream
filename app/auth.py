import functools

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            try:
                db.execute(
                    'INSERT INTO users (username, password) VALUES (?, ?)',
                    (username, generate_password_hash(password))
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                user_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
                init_accounts(user_id)
                return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/auth.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()

        if user is None or not check_password_hash(user['password'], password):
            error = 'Incorrect username or password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/auth.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


def init_accounts(user_id):
    db  = get_db()
    for n in ['Wallet', 'Savings', 'Checking']:
        db.execute("INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)", (user_id, n, 'asset', 0))

    for n in ['Credit Card']:
        db.execute("INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)", (user_id, n, 'liability', 0))

    for n in ['Opening Balances']:
        db.execute("INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)", (user_id, n, 'equity', 0))

    for n in ['Income']:
        db.execute("INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)", (user_id, n, 'revenue', 0))

    for n in ['Expenses']:
        db.execute("INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)", (user_id, n, 'expense', 0))

    db.commit()