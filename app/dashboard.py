from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from app.auth import login_required
from app.db import get_db

bp = Blueprint('dashboard', __name__)  # Create a Blueprint named 'dashboard'


def get_user(id):
    user = (
        get_db()
        .execute(
            "SELECT id, username"
            " FROM users"
            " WHERE id = ?",
            (id,),
        )
        .fetchone()
    )

    if user is None:
        abort(404, f"User id {id} doesn't exist.")

    return user


def get_accounts(user_id):
    accounts = (
        get_db()
        .execute(
            "SELECT id, name, type, balance"
            " FROM accounts"
            " WHERE user_id = ?"
            " ORDER BY type, name DESC",
            (user_id,),
        )
        .fetchall()
    )

    if accounts is None:
        abort(404, f"User id {user_id} doesn't exist.")

    return accounts


def get_account(id, check_user=True):
    account = (
        get_db()
        .execute(
            "SELECT id, name, type, balance, user_id"
            " FROM accounts"
            " WHERE id = ?",
            (id,),
        )
        .fetchone()
    )

    if account is None:
        abort(404, f"Account id {id} doesn't exist.")

    if check_user and account['user_id'] != g.user['id']:
        abort(403)

    return account


def get_transactions(user_id):
    transactions = (
        get_db()
        .execute(
            "SELECT t.id, t.user_id, t.date, t.description, te.amount"
            " FROM transactions t"
            " JOIN transaction_entries te ON t.id = te.transaction_id"
            " WHERE t.user_id = ?",
            (user_id,),
        )
        .fetchmany(3)
    )

    if transactions is None:
        abort(404, f"User id {user_id} doesn't exist.")

    return transactions


@bp.route('/')
@login_required
def index():
    db = get_db()
    user = get_user(g.user['id'])
    accounts = get_accounts(g.user['id'])
    transactions = get_transactions(g.user['id'])

    return render_template('dashboard/index.html', user=user, accounts=accounts, transactions=transactions)


@bp.route('/accounts')
@login_required
def accounts():
    db = get_db()
    user = get_user(g.user['id'])
    accounts = get_accounts(g.user['id'])

    return render_template('dashboard/accounts.html', user=user, accounts=accounts)


@bp.route('/transactions')
@login_required
def transactions():
    db = get_db()
    user = get_user(g.user['id'])
    transactions = db.execute(
        "SELECT t.id, t.user_id, t.date, t.description, te.amount"
        " FROM transactions t"
        " JOIN transaction_entries te ON t.id = te.transaction_id"
        " WHERE t.user_id = ?",
        (g.user['id'],),
    ).fetchall()

    return render_template('dashboard/transactions.html', user=user, transactions=transactions)


@bp.route('/create_account', methods=['POST'])
@login_required
def create_account():
    name = request.form['name']
    type = request.form['type']
    balance = 0
    error = None

    if not name:
        error = 'Name is required.'
    if not type:
        error = 'Type is required.'
    
    if error is not None:
        flash(error)
    else:
        db = get_db()
        db.execute(
            "INSERT INTO accounts (name, type, balance, user_id)"
            " VALUES (?, ?, ?, ?)",
            (name, type, balance, g.user['id']),
        )
        db.commit()
    
    return redirect(url_for('dashboard.index'))


def get_account(id, check_user=True):
    account = (
        get_db()
        .execute(
            "SELECT id, name, type, balance, user_id"
            " FROM accounts"
            " WHERE id = ?",
            (id,),
        )
        .fetchone()
    )

    if account is None:
        abort(404, f"Account id {id} doesn't exist.")

    if check_user and account['user_id'] != g.user['id']:
        abort(403)

    return account


@bp.route('/<int:id>/update_account', methods=('GET', 'POST'))
@login_required
def update_account(id):
    account = get_account(id)
    user = get_user(g.user['id'])
    if request.method == 'POST':
        name = request.form['name']
        type = request.form['type']
        error = None

        if not name:
            error = 'Name is required.'
        if not type:
            error = 'Type is required.'
        
        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE accounts SET name = ?, type = ? WHERE id = ?",
                (name, type, id),
            )
            db.commit()
        
        return redirect(url_for('dashboard.accounts'))

    return render_template('dashboard/update_account.html', user=user, account=account)


@bp.route('/<int:id>/confirm_delete_account', methods=('GET', 'POST'))
@login_required
def confirm_delete_account(id):
    account = get_account(id)
    return render_template('dashboard/del_account.html', account=account)

@bp.route('/<int:id>/delete_account', methods=('GET', 'POST'))
@login_required
def delete_account(id):
    account = get_account(id)
    db = get_db()
    db.execute('DELETE FROM accounts WHERE id = ?', (id,))
    db.commit()

    return redirect(url_for('dashboard.accounts'))
        

@bp.route('/create_transaction', methods=['POST'])
@login_required
def create_transaction():
    date = request.form['date']
    description = request.form['description']
    value = request.form['value']
    credit = request.form['credit']
    debit = request.form['debit']
    error = None

    if not date:
        error = 'Date is required.'
    if not description:
        error = 'Description is required.'
    if not value:
        error = 'Value is required.'
    if not credit:
        error = 'Credit is required.'
    if not debit:
        error = 'Debit is required.'

    if error is not None:
        flash(error)
    else:
        db = get_db()
        db.execute(
            "INSERT INTO transactions (user_id, date, description)"
            " VALUES (?, ?, ?)",
            (g.user['id'], date, description),
        )
        transaction_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO transaction_entries (transaction_id, amount, credited_id, debited_id)"
            " VALUES (?, ?, ?, ?)",
            (transaction_id, value, credit, debit),
        )
        credit_account = get_account(credit)
        if credit_account['type'] == 'liability' or credit_account['type'] == 'equity' or credit_account['type'] == 'revenue':
            new_c_bal = credit_account['balance'] + float(value)
        else:
            new_c_bal = credit_account['balance'] - float(value)
        debit_account = get_account(debit)
        if debit_account['type'] == 'asset' or debit_account['type'] == 'expense':
            new_d_bal = debit_account['balance'] + float(value)
        else:
            new_d_bal = debit_account['balance'] - float(value)

        db.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?",
            (new_c_bal, credit),
        )
        db.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?",
            (new_d_bal, debit),
        )
        db.commit()

    return redirect(url_for('dashboard.index'))
