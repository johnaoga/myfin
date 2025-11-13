from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
import os
import pandas as pd
import plotly
import plotly.graph_objs as go
import json
from datetime import datetime
from sqlalchemy import or_, func

from config import Config
from models import db, User, Transaction, Tag

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    # Calculate totals
    total_in = db.session.query(func.sum(Transaction.amount)).filter(Transaction.amount > 0).scalar() or 0
    total_out = abs(db.session.query(func.sum(Transaction.amount)).filter(Transaction.amount < 0).scalar() or 0)
    balance = total_in - total_out
    
    # Get cumulative data for plot
    transactions = Transaction.query.order_by(Transaction.accounting_date.asc()).all()
    
    if transactions:
        dates = []
        cumulative_in = []
        cumulative_out = []
        running_in = 0
        running_out = 0
        
        for trans in transactions:
            dates.append(trans.accounting_date)
            if trans.amount > 0:
                running_in += trans.amount
            else:
                running_out += abs(trans.amount)
            cumulative_in.append(running_in)
            cumulative_out.append(running_out)
        
        # Create plotly figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=cumulative_in, mode='lines', name='Cumulative Income', 
                                 line=dict(color='#10b981', width=2)))
        fig.add_trace(go.Scatter(x=dates, y=cumulative_out, mode='lines', name='Cumulative Expenses',
                                 line=dict(color='#ef4444', width=2)))
        
        fig.update_layout(
            title='Cumulative Income vs Expenses Over Time',
            xaxis_title='Date',
            yaxis_title='Amount (EUR)',
            hovermode='x unified',
            template='plotly_white',
            height=400
        )
        
        plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        plot_json = None
    
    return render_template('index.html', 
                         total_in=total_in, 
                         total_out=total_out, 
                         balance=balance,
                         plot_json=plot_json)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/analyze')
@login_required
def analyze():
    # Get query parameters
    transaction_type = request.args.get('type', 'all')  # 'in', 'out', 'all'
    search_text = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    sort_by = request.args.get('sort_by', 'accounting_date')
    sort_order = request.args.get('sort_order', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Build query
    query = Transaction.query
    
    # Filter by type
    if transaction_type == 'in':
        query = query.filter(Transaction.amount > 0)
    elif transaction_type == 'out':
        query = query.filter(Transaction.amount < 0)
    
    # Filter by search text
    if search_text:
        query = query.filter(
            or_(
                Transaction.description.ilike(f'%{search_text}%'),
                Transaction.details.ilike(f'%{search_text}%'),
                Transaction.account_name.ilike(f'%{search_text}%'),
                Transaction.counterparty_account.ilike(f'%{search_text}%')
            )
        )
    
    # Filter by date range
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.accounting_date >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.accounting_date <= end_dt)
        except ValueError:
            pass
    
    # Apply sorting
    sort_column = getattr(Transaction, sort_by, Transaction.accounting_date)
    if sort_order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items
    
    # Get all tags for dropdown
    tags = Tag.query.order_by(Tag.name).all()
    
    # Calculate tag statistics for histogram
    tag_stats = db.session.query(
        Tag.name,
        Tag.color,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction).group_by(Tag.id).all()
    
    # Create histogram
    if tag_stats:
        tag_names = [stat.name for stat in tag_stats]
        tag_totals = [stat.total for stat in tag_stats]
        tag_colors = [stat.color for stat in tag_stats]
        
        fig = go.Figure(data=[
            go.Bar(x=tag_names, y=tag_totals, marker_color=tag_colors)
        ])
        
        fig.update_layout(
            title='Transaction Amounts by Tag',
            xaxis_title='Tag',
            yaxis_title='Total Amount (EUR)',
            template='plotly_white',
            height=300
        )
        
        histogram_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        histogram_json = None
    
    return render_template('analyze.html',
                         transactions=transactions,
                         pagination=pagination,
                         tags=tags,
                         transaction_type=transaction_type,
                         search_text=search_text,
                         start_date=start_date,
                         end_date=end_date,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         histogram_json=histogram_json)

@app.route('/summary')
@login_required
def summary():
    """Summary analysis page with different granularities"""
    from sqlalchemy import text
    from collections import defaultdict
    import calendar
    
    granularity = request.args.get('granularity', 'month')  # day, week, month, year
    
    # Map granularity to view name
    view_map = {
        'day': 'daily_summary',
        'week': 'weekly_summary',
        'month': 'monthly_summary',
        'year': 'yearly_summary'
    }
    
    if granularity not in view_map:
        granularity = 'month'
    
    view_name = view_map[granularity]
    
    # Query the view
    try:
        query = text(f"""
            SELECT 
                period,
                year,
                {f"month," if granularity in ['month', 'day'] else ''}
                {f"week," if granularity == 'week' else ''}
                {f"day, day_of_week," if granularity == 'day' else ''}
                total_in,
                total_out,
                balance,
                transaction_count
                {f", period_start, period_end" if granularity != 'day' else ''}
            FROM {view_name}
            ORDER BY period DESC
        """)
        
        result = db.session.execute(query)
        periods_data = []
        
        for row in result:
            # Parse row based on granularity
            if granularity == 'day':
                # Columns: period, year, month, day, day_of_week, total_in, total_out, balance, transaction_count
                period_data = {
                    'period': row[0],
                    'year': row[1],
                    'month': row[2],
                    'week': None,
                    'day': row[3],
                    'day_of_week': row[4],
                    'total_in': row[5],
                    'total_out': row[6],
                    'balance': row[7],
                    'transaction_count': row[8],
                }
            elif granularity == 'week':
                # Columns: period, year, week, total_in, total_out, balance, transaction_count, period_start, period_end
                period_data = {
                    'period': row[0],
                    'year': row[1],
                    'month': None,
                    'week': row[2],
                    'day': None,
                    'day_of_week': None,
                    'total_in': row[3],
                    'total_out': row[4],
                    'balance': row[5],
                    'transaction_count': row[6],
                }
            elif granularity == 'month':
                # Columns: period, year, month, total_in, total_out, balance, transaction_count, period_start, period_end
                period_data = {
                    'period': row[0],
                    'year': row[1],
                    'month': row[2],
                    'week': None,
                    'day': None,
                    'day_of_week': None,
                    'total_in': row[3],
                    'total_out': row[4],
                    'balance': row[5],
                    'transaction_count': row[6],
                }
            else:  # year
                # Columns: period, year, total_in, total_out, balance, transaction_count, period_start, period_end
                period_data = {
                    'period': row[0],
                    'year': row[1],
                    'month': None,
                    'week': None,
                    'day': None,
                    'day_of_week': None,
                    'total_in': row[2],
                    'total_out': row[3],
                    'balance': row[4],
                    'transaction_count': row[5],
                }
            
            periods_data.append(period_data)
        
        # Calculate averages
        if periods_data:
            # Overall averages
            total_periods = len(periods_data)
            avg_in = sum(p['total_in'] for p in periods_data) / total_periods if total_periods > 0 else 0
            avg_out = sum(p['total_out'] for p in periods_data) / total_periods if total_periods > 0 else 0
            
            # Same-period averages (e.g., all Aprils, all Mondays, etc.)
            period_groups = defaultdict(list)
            
            for period in periods_data:
                if granularity == 'month':
                    # Group by month name (all Januaries, all Februaries, etc.)
                    key = period['month']
                elif granularity == 'week':
                    # Group by week number
                    key = period['week']
                elif granularity == 'day':
                    # Group by day of week
                    key = period['day_of_week']
                else:  # year
                    key = 'all'
                
                period_groups[key].append(period)
            
            # Calculate same-period averages
            same_period_avg = {}
            for key, group in period_groups.items():
                same_period_avg[key] = {
                    'avg_in': sum(p['total_in'] for p in group) / len(group),
                    'avg_out': sum(p['total_out'] for p in group) / len(group),
                }
            
            # Add averages to each period
            for period in periods_data:
                period['overall_avg_in'] = avg_in
                period['overall_avg_out'] = avg_out
                
                if granularity == 'month':
                    key = period['month']
                elif granularity == 'week':
                    key = period['week']
                elif granularity == 'day':
                    key = period['day_of_week']
                else:
                    key = 'all'
                
                period['same_period_avg_in'] = same_period_avg[key]['avg_in']
                period['same_period_avg_out'] = same_period_avg[key]['avg_out']
        
        # Get tag distribution for selected granularity
        # For now, we'll get overall tag distribution and can filter by date in template
        tag_stats = db.session.query(
            Tag.name,
            Tag.color,
            func.sum(func.abs(Transaction.amount)).label('total_amount'),
            func.count(Transaction.id).label('count')
        ).join(Transaction).group_by(Tag.id).all()
        
        # Format period labels
        for period in periods_data:
            if granularity == 'month':
                month_num = int(period['month'])
                month_name = calendar.month_name[month_num]
                period['label'] = f"{month_name} {period['year']}"
                period['same_period_label'] = month_name
            elif granularity == 'week':
                period['label'] = f"Week {period['week']}, {period['year']}"
                period['same_period_label'] = f"Week {period['week']}"
            elif granularity == 'day':
                day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                period['label'] = period['period']
                period['same_period_label'] = day_names[int(period['day_of_week'])]
            else:  # year
                period['label'] = period['period']
                period['same_period_label'] = period['period']
        
    except Exception as e:
        flash(f'Error loading summary data: {str(e)}. Please run init_views.py to create database views.', 'danger')
        periods_data = []
        tag_stats = []
    
    return render_template('summary.html',
                         granularity=granularity,
                         periods=periods_data,
                         tag_stats=tag_stats)

@app.route('/api/tag-transaction', methods=['POST'])
@login_required
def tag_transaction():
    data = request.get_json()
    transaction_id = data.get('transaction_id')
    tag_name = data.get('tag_name')
    
    if not transaction_id or not tag_name:
        return jsonify({'success': False, 'message': 'Missing data'}), 400
    
    transaction = db.session.get(Transaction, transaction_id)
    if not transaction:
        return jsonify({'success': False, 'message': 'Transaction not found'}), 404
    
    # Get or create tag
    tag = Tag.query.filter_by(name=tag_name).first()
    if not tag:
        tag = Tag(name=tag_name)
        db.session.add(tag)
        db.session.flush()
    
    transaction.tag_id = tag.id
    db.session.commit()
    
    return jsonify({'success': True, 'tag_id': tag.id})

@app.route('/api/find-similar/<int:transaction_id>')
@login_required
def find_similar(transaction_id):
    transaction = db.session.get(Transaction, transaction_id)
    if not transaction:
        return jsonify({'success': False, 'message': 'Transaction not found'}), 404
    
    # Find similar transactions based on description and amount
    similar = Transaction.query.filter(
        Transaction.id != transaction_id,
        or_(
            Transaction.description.ilike(f'%{transaction.description[:30]}%') if transaction.description else False,
            Transaction.counterparty_account == transaction.counterparty_account,
            func.abs(Transaction.amount - transaction.amount) < 0.01
        )
    ).limit(20).all()
    
    results = [{
        'id': t.id,
        'date': t.accounting_date.strftime('%Y-%m-%d'),
        'amount': t.amount,
        'description': t.description,
        'tag': t.tag.name if t.tag else None
    } for t in similar]
    
    # Include the original transaction's tag if it exists
    original_tag = transaction.tag.name if transaction.tag else None
    
    return jsonify({
        'success': True, 
        'similar': results,
        'original_tag': original_tag
    })

@app.route('/api/bulk-tag', methods=['POST'])
@login_required
def bulk_tag():
    data = request.get_json()
    transaction_ids = data.get('transaction_ids', [])
    tag_name = data.get('tag_name')
    
    if not transaction_ids or not tag_name:
        return jsonify({'success': False, 'message': 'Missing data'}), 400
    
    # Get or create tag
    tag = Tag.query.filter_by(name=tag_name).first()
    if not tag:
        tag = Tag(name=tag_name)
        db.session.add(tag)
        db.session.flush()
    
    # Update all transactions
    Transaction.query.filter(Transaction.id.in_(transaction_ids)).update(
        {Transaction.tag_id: tag.id}, 
        synchronize_session=False
    )
    db.session.commit()
    
    return jsonify({'success': True, 'count': len(transaction_ids)})

@app.route('/api/find-patterns')
@login_required
def find_patterns():
    """Find similar patterns in filtered transaction results"""
    from collections import defaultdict
    
    # Get filter parameters
    transaction_type = request.args.get('type', 'all')
    search_text = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Build query (same logic as analyze page)
    query = Transaction.query
    
    if transaction_type == 'in':
        query = query.filter(Transaction.amount > 0)
    elif transaction_type == 'out':
        query = query.filter(Transaction.amount < 0)
    
    if search_text:
        query = query.filter(
            or_(
                Transaction.description.ilike(f'%{search_text}%'),
                Transaction.details.ilike(f'%{search_text}%'),
                Transaction.account_name.ilike(f'%{search_text}%'),
                Transaction.counterparty_account.ilike(f'%{search_text}%')
            )
        )
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.accounting_date >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.accounting_date <= end_dt)
        except ValueError:
            pass
    
    transactions = query.all()
    
    if len(transactions) < 2:
        return jsonify({'success': True, 'patterns': []})
    
    # Group transactions by patterns
    patterns = []
    
    # Pattern 1: Group by counterparty account
    counterparty_groups = defaultdict(list)
    for t in transactions:
        if t.counterparty_account:
            counterparty_groups[t.counterparty_account].append(t)
    
    for counterparty, trans_list in counterparty_groups.items():
        if len(trans_list) >= 2:  # Only include patterns with 2+ transactions
            patterns.append({
                'description': f'Counterparty: {counterparty[:30]}...' if len(counterparty) > 30 else f'Counterparty: {counterparty}',
                'transactions': [{
                    'id': t.id,
                    'date': t.accounting_date.strftime('%Y-%m-%d'),
                    'amount': t.amount,
                    'description': t.description,
                    'tag': t.tag.name if t.tag else None
                } for t in trans_list]
            })
    
    # Pattern 2: Group by similar amounts (within 1 euro)
    amount_groups = defaultdict(list)
    for t in transactions:
        # Round to nearest euro for grouping
        rounded_amount = round(t.amount)
        amount_groups[rounded_amount].append(t)
    
    for amount, trans_list in amount_groups.items():
        if len(trans_list) >= 3:  # Only include patterns with 3+ transactions
            patterns.append({
                'description': f'Similar amount: ~€{amount:.2f}',
                'transactions': [{
                    'id': t.id,
                    'date': t.accounting_date.strftime('%Y-%m-%d'),
                    'amount': t.amount,
                    'description': t.description,
                    'tag': t.tag.name if t.tag else None
                } for t in trans_list]
            })
    
    # Pattern 3: Group by description keywords (first 20 chars)
    desc_groups = defaultdict(list)
    for t in transactions:
        if t.description:
            # Use first 20 chars as pattern key
            key = t.description[:20].strip().lower()
            if key:
                desc_groups[key].append(t)
    
    for desc_key, trans_list in desc_groups.items():
        if len(trans_list) >= 2:  # Only include patterns with 2+ transactions
            patterns.append({
                'description': f'Similar description: "{desc_key}..."',
                'transactions': [{
                    'id': t.id,
                    'date': t.accounting_date.strftime('%Y-%m-%d'),
                    'amount': t.amount,
                    'description': t.description,
                    'tag': t.tag.name if t.tag else None
                } for t in trans_list]
            })
    
    # Limit to top 10 patterns by transaction count
    patterns.sort(key=lambda p: len(p['transactions']), reverse=True)
    patterns = patterns[:10]
    
    return jsonify({'success': True, 'patterns': patterns})

@app.route('/api/get-search-results')
@login_required
def get_search_results():
    """Get all transactions matching current search filters"""
    # Get filter parameters
    transaction_type = request.args.get('type', 'all')
    search_text = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Build query (same logic as analyze page)
    query = Transaction.query
    
    if transaction_type == 'in':
        query = query.filter(Transaction.amount > 0)
    elif transaction_type == 'out':
        query = query.filter(Transaction.amount < 0)
    
    if search_text:
        query = query.filter(
            or_(
                Transaction.description.ilike(f'%{search_text}%'),
                Transaction.details.ilike(f'%{search_text}%'),
                Transaction.account_name.ilike(f'%{search_text}%'),
                Transaction.counterparty_account.ilike(f'%{search_text}%')
            )
        )
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.accounting_date >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.accounting_date <= end_dt)
        except ValueError:
            pass
    
    # Order by date descending
    transactions = query.order_by(Transaction.accounting_date.desc()).all()
    
    # Format results
    results = [{
        'id': t.id,
        'date': t.accounting_date.strftime('%Y-%m-%d'),
        'amount': t.amount,
        'description': t.description,
        'tag': t.tag.name if t.tag else None
    } for t in transactions]
    
    return jsonify({'success': True, 'transactions': results})

@app.route('/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_data():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                # Read CSV with semicolon separator - try different encodings
                # Try UTF-8 with BOM first, then UTF-8, then latin-1
                encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                df = None
                last_error = None
                
                for encoding in encodings:
                    try:
                        file.seek(0)  # Reset file pointer
                        df = pd.read_csv(file, sep=';', encoding=encoding)
                        # Verify we have the expected columns
                        if 'Numéro de compte' in df.columns or any('compte' in col.lower() for col in df.columns):
                            break
                    except Exception as e:
                        last_error = e
                        continue
                
                if df is None:
                    raise Exception(f'Could not read CSV with any encoding. Last error: {last_error}')
                
                # Log successful encoding and column names for debugging
                print(f"Successfully read CSV with encoding: {encoding}")
                print(f"Columns found: {list(df.columns)}")
                
                imported_count = 0
                skipped_count = 0
                
                for _, row in df.iterrows():
                    # Parse date (format: DD/MM/YYYY)
                    try:
                        accounting_date = datetime.strptime(row['Date comptable'], '%d/%m/%Y').date()
                    except:
                        continue
                    
                    try:
                        value_date = datetime.strptime(row['Date valeur'], '%d/%m/%Y').date()
                    except:
                        value_date = accounting_date
                    
                    # Parse amount (format: -1.234,56)
                    amount_str = str(row['Montant']).replace('.', '').replace(',', '.')
                    try:
                        amount = float(amount_str)
                    except:
                        continue
                    
                    # Check if transaction already exists
                    existing = Transaction.query.filter_by(
                        account_number=row['Numéro de compte'],
                        transaction_number=str(row['Numéro de mouvement']),
                        accounting_date=accounting_date,
                        amount=amount
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Create new transaction
                    transaction = Transaction(
                        account_number=row['Numéro de compte'],
                        account_name=row['Nom du compte'],
                        counterparty_account=row['Compte contrepartie'] if pd.notna(row['Compte contrepartie']) else None,
                        transaction_number=str(row['Numéro de mouvement']),
                        accounting_date=accounting_date,
                        value_date=value_date,
                        amount=amount,
                        currency=row['Devise'],
                        description=row['Libellés'] if pd.notna(row['Libellés']) else None,
                        details=row['Détails du mouvement'] if pd.notna(row['Détails du mouvement']) else None,
                        message=row['Message'] if pd.notna(row['Message']) else None
                    )
                    
                    db.session.add(transaction)
                    imported_count += 1
                
                db.session.commit()
                flash(f'Successfully imported {imported_count} transactions. Skipped {skipped_count} duplicates.', 'success')
                return redirect(url_for('index'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error importing file: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('Please upload a CSV file', 'danger')
            return redirect(request.url)
    
    return render_template('import.html')

# CLI Commands
@app.cli.command('create-admin')
def create_admin():
    """Create an admin user via command line."""
    import getpass
    
    username = input('Enter username: ')
    
    if User.query.filter_by(username=username).first():
        print(f'User {username} already exists!')
        return
    
    password = getpass.getpass('Enter password: ')
    password_confirm = getpass.getpass('Confirm password: ')
    
    if password != password_confirm:
        print('Passwords do not match!')
        return
    
    user = User(username=username, is_admin=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    print(f'Admin user {username} created successfully!')

@app.cli.command('init-db')
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Database initialized!')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
