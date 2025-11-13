"""
Database migration to add Pattern model tables
Run this once to create the pattern tables: python migrate_patterns.py
"""
from app import app, db
from sqlalchemy import text

def migrate():
    """Create pattern tables and add merge_id field"""
    with app.app_context():
        # Create all tables (will only create new ones)
        db.create_all()
        
        # Add merge_id column if it doesn't exist (for existing tables)
        try:
            # Check if merge_id column exists
            result = db.session.execute(text("PRAGMA table_info(patterns)"))
            columns = [row[1] for row in result]
            
            if 'merge_id' not in columns:
                # Add the column
                db.session.execute(text("ALTER TABLE patterns ADD COLUMN merge_id INTEGER"))
                db.session.commit()
                print("✅ Added merge_id column to patterns table")
                
                # Initialize merge_id for existing patterns
                db.session.execute(text("UPDATE patterns SET merge_id = id WHERE merge_id IS NULL"))
                db.session.commit()
                print("✅ Initialized merge_id for existing patterns")
            else:
                # Column exists, just update NULL values
                result = db.session.execute(text("UPDATE patterns SET merge_id = id WHERE merge_id IS NULL"))
                db.session.commit()
                if result.rowcount > 0:
                    print(f"✅ Updated {result.rowcount} patterns with merge_id")
                else:
                    print("✅ All patterns already have merge_id set")
                    
        except Exception as e:
            print(f"⚠️  Note: {e}")
        
        print("✅ Pattern tables created/updated successfully!")
        print("   - patterns (with merge_id field)")
        print("   - pattern_transactions (association table)")

if __name__ == '__main__':
    migrate()
