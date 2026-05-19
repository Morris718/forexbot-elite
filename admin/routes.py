from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, session
)
from flask_login import login_required, current_user, login_user, logout_user
from functools import wraps
from database import db
from auth.models import User, Transaction, Referral
from trading.bot import Trade
from datetime import datetime, timedelta
from sqlalchemy import func, or_

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin', static_folder='../static')


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login as admin', 'warning')
            return redirect(url_for('admin.admin_login'))
        if not current_user.is_admin:
            flash('Access denied. Admin only.', 'danger')
            return redirect(url_for('trading.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        user = User.query.filter(db.func.lower(User.email) == email).first()
        
        if user and user.check_password(password):
            if user.is_admin:
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()
                flash(f'Welcome, Admin {user.full_name}!', 'success')
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Access denied. Not an admin account.', 'danger')
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('admin/admin_login.html')


@admin_bp.route('/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin.admin_login'))


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Stats
    total_users = User.query.filter_by(is_admin=False).count()
    total_trades = Trade.query.count()
    open_trades = Trade.query.filter_by(status='OPEN').count()
    
    total_deposits = db.session.query(func.sum(Transaction.amount)).filter_by(
        transaction_type='DEPOSIT', status='COMPLETED'
    ).scalar() or 0
    
    total_withdrawals = db.session.query(func.sum(Transaction.amount)).filter_by(
        transaction_type='WITHDRAWAL', status='COMPLETED'
    ).scalar() or 0
    
    pending_withdrawals = Transaction.query.filter_by(
        transaction_type='WITHDRAWAL', status='PENDING'
    ).count()
    
    pending_deposits = Transaction.query.filter_by(
        transaction_type='DEPOSIT', status='PROCESSING'
    ).count()
    
    total_user_balance = db.session.query(func.sum(User.balance)).scalar() or 0
    total_bonus = db.session.query(func.sum(User.bonus_balance)).scalar() or 0
    
    # Recent activity
    recent_users = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).limit(10).all()
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(15).all()
    
    # Pending items needing attention
    urgent_withdrawals = Transaction.query.filter_by(
        transaction_type='WITHDRAWAL', status='PENDING'
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    urgent_deposits = Transaction.query.filter(
        Transaction.transaction_type == 'DEPOSIT',
        Transaction.status.in_(['PROCESSING', 'PENDING'])
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    # Today stats
    today = datetime.utcnow().date()
    new_users_today = User.query.filter(
        func.date(User.created_at) == today,
        User.is_admin == False
    ).count()
    
    deposits_today = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == 'DEPOSIT',
        Transaction.status == 'COMPLETED',
        func.date(Transaction.created_at) == today
    ).scalar() or 0
    
    return render_template('admin/admin_dashboard.html',
                           total_users=total_users,
                           total_trades=total_trades,
                           open_trades=open_trades,
                           total_deposits=round(total_deposits, 2),
                           total_withdrawals=round(total_withdrawals, 2),
                           pending_withdrawals=pending_withdrawals,
                           pending_deposits=pending_deposits,
                           total_user_balance=round(total_user_balance, 2),
                           total_bonus=round(total_bonus, 2),
                           recent_users=recent_users,
                           recent_transactions=recent_transactions,
                           urgent_withdrawals=urgent_withdrawals,
                           urgent_deposits=urgent_deposits,
                           new_users_today=new_users_today,
                           deposits_today=round(deposits_today, 2))


@admin_bp.route('/users')
@admin_required
def users():
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    
    query = User.query.filter_by(is_admin=False)
    
    if search:
        query = query.filter(
            or_(
                User.email.contains(search),
                User.username.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    users_list = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/admin_users.html',
                           users=users_list,
                           search=search)


@admin_bp.route('/user/<int:user_id>')
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(
        Transaction.created_at.desc()
    ).limit(50).all()
    
    trades = Trade.query.filter_by(user_id=user_id).order_by(
        Trade.opened_at.desc()
    ).limit(50).all()
    
    referrals = Referral.query.filter_by(referrer_id=user_id).all()
    
    open_trades_count = Trade.query.filter_by(user_id=user_id, status='OPEN').count()
    closed_trades = Trade.query.filter_by(user_id=user_id, status='CLOSED').all()
    total_pnl = sum(t.profit_loss for t in closed_trades)
    
    return render_template('admin/admin_user_detail.html',
                           user=user,
                           transactions=transactions,
                           trades=trades,
                           referrals=referrals,
                           open_trades_count=open_trades_count,
                           total_pnl=round(total_pnl, 2))


@admin_bp.route('/user/<int:user_id>/adjust', methods=['POST'])
@admin_required
def adjust_balance(user_id):
    user = User.query.get_or_404(user_id)
    
    try:
        amount = float(request.form.get('amount', 0))
        action = request.form.get('action', 'add')
        reason = request.form.get('reason', 'Admin adjustment')
        
        if action == 'add':
            user.balance += amount
            tx_type = 'BONUS'
            notes = f'Admin credit: {reason}'
        elif action == 'subtract':
            if amount > user.balance:
                flash('Cannot subtract more than user balance', 'danger')
                return redirect(url_for('admin.user_detail', user_id=user_id))
            user.balance -= amount
            tx_type = 'WITHDRAWAL'
            notes = f'Admin debit: {reason}'
        else:
            flash('Invalid action', 'danger')
            return redirect(url_for('admin.user_detail', user_id=user_id))
        
        # Create transaction record
        tx = Transaction(
            user_id=user.id,
            transaction_type=tx_type,
            amount=amount,
            payment_method='ADMIN',
            status='COMPLETED',
            reference_id=Transaction.generate_reference(),
            notes=notes,
            admin_notes=f'Processed by {current_user.username}',
            processed_by=current_user.id,
            completed_at=datetime.utcnow()
        )
        db.session.add(tx)
        db.session.commit()
        
        flash(f'Balance adjusted: {"added" if action == "add" else "subtracted"} ${amount}', 'success')
    except ValueError:
        flash('Invalid amount', 'danger')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot change your own admin status', 'warning')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'User {"promoted to" if user.is_admin else "demoted from"} admin', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/transactions')
@admin_required
def transactions():
    filter_type = request.args.get('type', 'all')
    filter_status = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    
    query = Transaction.query
    
    if filter_type != 'all':
        query = query.filter_by(transaction_type=filter_type.upper())
    
    if filter_status != 'all':
        query = query.filter_by(status=filter_status.upper())
    
    transactions_list = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=30, error_out=False
    )
    
    return render_template('admin/admin_transactions.html',
                           transactions=transactions_list,
                           filter_type=filter_type,
                           filter_status=filter_status)


@admin_bp.route('/withdrawals')
@admin_required
def withdrawals():
    pending = Transaction.query.filter_by(
        transaction_type='WITHDRAWAL', status='PENDING'
    ).order_by(Transaction.created_at.desc()).all()
    
    completed = Transaction.query.filter_by(
        transaction_type='WITHDRAWAL', status='COMPLETED'
    ).order_by(Transaction.completed_at.desc()).limit(50).all()
    
    rejected = Transaction.query.filter_by(
        transaction_type='WITHDRAWAL', status='REJECTED'
    ).order_by(Transaction.created_at.desc()).limit(50).all()
    
    return render_template('admin/admin_withdrawals.html',
                           pending=pending,
                           completed=completed,
                           rejected=rejected)


@admin_bp.route('/deposits')
@admin_required
def deposits():
    pending = Transaction.query.filter(
        Transaction.transaction_type == 'DEPOSIT',
        Transaction.status.in_(['PROCESSING', 'PENDING'])
    ).order_by(Transaction.created_at.desc()).all()
    
    completed = Transaction.query.filter_by(
        transaction_type='DEPOSIT', status='COMPLETED'
    ).order_by(Transaction.completed_at.desc()).limit(50).all()
    
    return render_template('admin/admin_deposits.html',
                           pending=pending,
                           completed=completed)


@admin_bp.route('/transaction/<int:txn_id>/approve', methods=['POST'])
@admin_required
def approve_transaction(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    user = User.query.get(txn.user_id)
    
    txn.status = 'COMPLETED'
    txn.completed_at = datetime.utcnow()
    txn.processed_by = current_user.id
    txn.admin_notes = f'Approved by {current_user.username} at {datetime.utcnow().strftime("%Y-%m-%d %H:%M")}'
    
    if txn.transaction_type == 'DEPOSIT':
        user.balance += txn.amount
        user.total_deposited += txn.amount
        if not user.has_deposited and txn.amount >= 10:
            user.has_deposited = True
        flash(f'✅ Deposit of ${txn.amount} approved for {user.email}', 'success')
    elif txn.transaction_type == 'WITHDRAWAL':
        user.total_withdrawn += txn.amount
        flash(f'✅ Withdrawal of ${txn.amount} approved for {user.email}', 'success')
    
    db.session.commit()
    return redirect(request.referrer or url_for('admin.dashboard'))


@admin_bp.route('/transaction/<int:txn_id>/reject', methods=['POST'])
@admin_required
def reject_transaction(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    user = User.query.get(txn.user_id)
    reason = request.form.get('reason', 'Rejected by admin')
    
    txn.status = 'REJECTED'
    txn.processed_by = current_user.id
    txn.admin_notes = f'Rejected by {current_user.username}: {reason}'
    
    # Refund withdrawal back to balance
    if txn.transaction_type == 'WITHDRAWAL':
        user.balance += txn.amount
        flash(f'❌ Withdrawal rejected. ${txn.amount} refunded to {user.email}', 'warning')
    else:
        flash(f'❌ Transaction rejected', 'warning')
    
    db.session.commit()
    return redirect(request.referrer or url_for('admin.dashboard'))


@admin_bp.route('/analytics')
@admin_required
def analytics():
    # Time-based analytics
    now = datetime.utcnow()
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)
    
    # Daily registrations (last 7 days)
    daily_signups = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= last_7_days,
        User.is_admin == False
    ).group_by(func.date(User.created_at)).all()
    
    # Daily deposits (last 7 days)
    daily_deposits = db.session.query(
        func.date(Transaction.created_at).label('date'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.created_at >= last_7_days,
        Transaction.transaction_type == 'DEPOSIT',
        Transaction.status == 'COMPLETED'
    ).group_by(func.date(Transaction.created_at)).all()
    
    # Top depositors
    top_depositors = db.session.query(
        User, func.sum(Transaction.amount).label('total')
    ).join(Transaction).filter(
        Transaction.transaction_type == 'DEPOSIT',
        Transaction.status == 'COMPLETED'
    ).group_by(User.id).order_by(func.sum(Transaction.amount).desc()).limit(10).all()
    
    # Top traders
    top_traders = db.session.query(
        User, func.count(Trade.id).label('trade_count')
    ).join(Trade).group_by(User.id).order_by(func.count(Trade.id).desc()).limit(10).all()
    
    # Top referrers
    top_referrers = User.query.filter_by(is_admin=False).order_by(
        User.total_referrals.desc()
    ).limit(10).all()
    
    return render_template('admin/admin_analytics.html',
                           daily_signups=daily_signups,
                           daily_deposits=daily_deposits,
                           top_depositors=top_depositors,
                           top_traders=top_traders,
                           top_referrers=top_referrers)


@admin_bp.route('/settings')
@admin_required
def settings():
    admin_users = User.query.filter_by(is_admin=True).all()
    return render_template('admin/admin_settings.html', admin_users=admin_users)


@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    """Real-time stats API"""
    total_users = User.query.filter_by(is_admin=False).count()
    pending_w = Transaction.query.filter_by(transaction_type='WITHDRAWAL', status='PENDING').count()
    pending_d = Transaction.query.filter(
        Transaction.transaction_type == 'DEPOSIT',
        Transaction.status.in_(['PROCESSING', 'PENDING'])
    ).count()
    open_trades = Trade.query.filter_by(status='OPEN').count()
    
    return jsonify({
        'total_users': total_users,
        'pending_withdrawals': pending_w,
        'pending_deposits': pending_d,
        'open_trades': open_trades
    })
