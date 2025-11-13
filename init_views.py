"""
Database views initialization for summary analysis
Run this once to create the views: python init_views.py
"""
from app import app, db
from sqlalchemy import text

def create_views():
    """Create database views for efficient summary queries"""
    with app.app_context():
        # Drop existing views if they exist
        views_to_drop = [
            'daily_summary',
            'weekly_summary', 
            'monthly_summary',
            'yearly_summary'
        ]
        
        for view in views_to_drop:
            try:
                db.session.execute(text(f'DROP VIEW IF EXISTS {view}'))
            except:
                pass
        
        # Daily Summary View
        db.session.execute(text("""
            CREATE VIEW daily_summary AS
            SELECT 
                strftime('%Y-%m-%d', accounting_date) as period,
                strftime('%Y', accounting_date) as year,
                strftime('%m', accounting_date) as month,
                strftime('%d', accounting_date) as day,
                strftime('%w', accounting_date) as day_of_week,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_in,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_out,
                SUM(amount) as balance,
                COUNT(*) as transaction_count
            FROM transactions
            GROUP BY strftime('%Y-%m-%d', accounting_date)
        """))
        
        # Weekly Summary View
        db.session.execute(text("""
            CREATE VIEW weekly_summary AS
            SELECT 
                strftime('%Y-W%W', accounting_date) as period,
                strftime('%Y', accounting_date) as year,
                strftime('%W', accounting_date) as week,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_in,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_out,
                SUM(amount) as balance,
                COUNT(*) as transaction_count,
                MIN(accounting_date) as period_start,
                MAX(accounting_date) as period_end
            FROM transactions
            GROUP BY strftime('%Y-W%W', accounting_date)
        """))
        
        # Monthly Summary View
        db.session.execute(text("""
            CREATE VIEW monthly_summary AS
            SELECT 
                strftime('%Y-%m', accounting_date) as period,
                strftime('%Y', accounting_date) as year,
                strftime('%m', accounting_date) as month,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_in,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_out,
                SUM(amount) as balance,
                COUNT(*) as transaction_count,
                MIN(accounting_date) as period_start,
                MAX(accounting_date) as period_end
            FROM transactions
            GROUP BY strftime('%Y-%m', accounting_date)
        """))
        
        # Yearly Summary View
        db.session.execute(text("""
            CREATE VIEW yearly_summary AS
            SELECT 
                strftime('%Y', accounting_date) as period,
                strftime('%Y', accounting_date) as year,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_in,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_out,
                SUM(amount) as balance,
                COUNT(*) as transaction_count,
                MIN(accounting_date) as period_start,
                MAX(accounting_date) as period_end
            FROM transactions
            GROUP BY strftime('%Y', accounting_date)
        """))
        
        db.session.commit()
        print("✅ Database views created successfully!")
        print("   - daily_summary")
        print("   - weekly_summary")
        print("   - monthly_summary")
        print("   - yearly_summary")

if __name__ == '__main__':
    create_views()
