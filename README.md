# MyFin - Personal Finance Manager

A Flask-based web application for managing and analyzing personal finance data from CSV bank statements.

## Features

### Home Page
- **Financial Overview**: Display total income, total expenses, and balance with interactive cards
- **Cumulative Chart**: Visualize cumulative income and expenses over time using Plotly
- **Quick Navigation**: Direct links to income and expense analysis

### Analysis Page
- **Advanced Filtering**: Filter transactions by type (income/expenses), search text, and date ranges
- **Sorting**: Sort transactions by date or amount in ascending/descending order
- **Tagging System**: 
  - Assign tags to transactions using an editable select box
  - Create new tags on the fly
  - Visual histogram showing transaction totals by tag
- **Find Similar**: Search for similar transactions based on description, counterparty, or amount
- **Bulk Tagging**: Tag multiple similar transactions at once
- **Tag the Search**: Bulk tag all transactions matching current filters
- **Find Patterns**: AI-powered pattern detection to group similar transactions
- **Pagination**: Browse through large transaction datasets efficiently

### Summary Analysis
- **Multi-Granularity Views**: Analyze finances by day, week, month, or year
- **Database Views**: Optimized SQL views for fast performance on large datasets
- **Comparative Metrics**:
  - Overall average comparison (across all periods)
  - Same-period average (e.g., all Aprils, all Mondays)
  - Color-coded indicators (green = below average, red = above average)
- **Tag Distribution**: View spending by category at each granularity level
- **Period Details**: Income, expenses, balance, and transaction counts per period

### Pattern Analysis (NEW)
- **Intelligent Detection**: AI-powered detection of recurring transactions
- **Monthly Patterns**: Identifies transactions that occur regularly each month
- **Validation Wizard**: Interactive interface to review and validate detected patterns
- **Transaction Selection**: Choose which transactions belong to each pattern
- **Recurrent Tracking**:
  - Total recurrent income summary
  - Total recurrent expenses summary
  - Pattern count and details
- **Pattern Management**: Save, view, and delete validated patterns

### Data Import
- **CSV Import**: Admin-only feature to import bank CSV files
- **Duplicate Detection**: Automatically skips duplicate transactions
- **Format Support**: Handles semicolon-separated CSV files with European date and number formats

### Authentication
- **Admin System**: Admin users created via command-line interface
- **Login Page**: Secure login with Flask-Login
- **Access Control**: Import functionality restricted to admin users

## Installation

1. **Clone the repository** (or navigate to the project folder):
   ```bash
   cd /Users/jaoga/devlab/OWN/myfin
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**:
   ```bash
   flask --app app init-db
   ```

5. **Create an admin user**:
   ```bash
   flask --app app create-admin
   ```
   Follow the prompts to enter username and password.

6. **Initialize database views for summary analysis**:
   ```bash
   python init_views.py
   ```
   This creates optimized SQL views for the Summary Analysis feature.

7. **Migrate database for pattern analysis**:
   ```bash
   python migrate_patterns.py
   ```
   This creates the pattern tables for recurring transaction detection.

## Running the Application

1. **Start the Flask development server**:
   ```bash
   python app.py
   ```
   or
   ```bash
   flask --app app run
   ```

2. **Access the application**:
   Open your browser and navigate to `http://localhost:5000`

3. **Login**:
   Use the admin credentials you created earlier

## Usage

### Importing Data

1. Login as an admin user
2. Navigate to "Import Data" in the navigation bar
3. Upload your CSV file (must be semicolon-separated with the correct format)
4. The application will import transactions and skip duplicates

### CSV Format

Your CSV file should have the following columns (semicolon-separated):
- `Numéro de compte` - Account Number
- `Nom du compte` - Account Name
- `Compte contrepartie` - Counterparty Account
- `Numéro de mouvement` - Transaction Number
- `Date comptable` - Accounting Date (DD/MM/YYYY)
- `Date valeur` - Value Date (DD/MM/YYYY)
- `Montant` - Amount (European format: -1.234,56)
- `Devise` - Currency (e.g., EUR)
- `Libellés` - Description
- `Détails du mouvement` - Transaction Details
- `Message` - Additional Message

### Analyzing Transactions

1. **View Overview**: Check the home page for overall financial statistics
2. **Filter Transactions**: Use the analyze page to filter by type, date range, or search text
3. **Tag Transactions**: 
   - Select a tag from the dropdown for each transaction
   - Create new tags by selecting "+ Add new tag"
4. **Find Similar**: Click the search icon to find and bulk-tag similar transactions

## Database Schema

### Users
- `id`: Primary key
- `username`: Unique username
- `password_hash`: Hashed password
- `is_admin`: Boolean flag for admin privileges
- `created_at`: Account creation timestamp

### Transactions
- `id`: Primary key
- `account_number`: Bank account number
- `account_name`: Account holder name
- `counterparty_account`: Other party's account
- `transaction_number`: Bank transaction reference
- `accounting_date`: Transaction date (indexed)
- `value_date`: Value date
- `amount`: Transaction amount (negative for expenses)
- `currency`: Currency code
- `description`: Transaction description
- `details`: Detailed transaction information
- `message`: Additional message
- `tag_id`: Foreign key to tags table
- `imported_at`: Import timestamp

### Tags
- `id`: Primary key
- `name`: Unique tag name
- `color`: Hex color code for visualization
- `created_at`: Tag creation timestamp

## Technology Stack

- **Backend**: Flask 3.0.0
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Flask-Login
- **Data Processing**: Pandas
- **Visualization**: Plotly
- **Frontend**: TailwindCSS, Font Awesome
- **JavaScript**: Vanilla JS for interactivity

## Security Notes

- Change the `SECRET_KEY` in `config.py` for production use
- Admin users can only be created via command-line interface
- Passwords are hashed using Werkzeug's security functions
- File uploads are restricted to CSV files with a 16MB limit

## Project Structure

```
myfin/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── models.py              # Database models
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── login.html        # Login page
│   ├── index.html        # Home page
│   ├── analyze.html      # Analysis page
│   └── import.html       # Import page
├── uploads/              # Upload directory (created automatically)
└── finance.db            # SQLite database (created on first run)
```

## License

Personal project - feel free to use and modify as needed.
