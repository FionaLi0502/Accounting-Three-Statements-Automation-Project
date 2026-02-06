# 📊 Three Statements Automation

An AI-powered Streamlit application that automates the creation of complete 3-statement financial models from General Ledger (GL) data.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](your-app-url-here)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 What This App Does

Upload your messy GL data → Get a complete 3-statement financial model in seconds!

**Features:**
- 🔍 **Smart Data Validation** - Detects and fixes common data quality issues
- 💱 **Currency Conversion** - Automatically converts to USD
- 📊 **Complete Financial Statements** - Income Statement, Balance Sheet, Cash Flow
- 🤖 **AI-Powered Insights** - Generates executive summary and recommendations
- 📥 **Export Options** - Download Excel model and PDF reports
- 🔄 **Data Reconciliation** - Tracks all changes made to your data

---

## 🚀 Live Demo

Try the app here: [**Three Statements Automation**](your-deployed-streamlit-url)

Or run locally in 2 minutes (see [Quick Start](#quick-start) below)

---

## 📸 Screenshots

### Data Upload & Validation
<img width="1810" height="725" alt="image" src="https://github.com/user-attachments/assets/07926ded-1296-461d-a603-44b03db96ccb"/>
*Detects 7 types of data quality issues with AI suggestions*

### Complete 3-Statement Model
<img width="1742" height="446" alt="image" src="https://github.com/user-attachments/assets/31047a55-8bbe-4c78-96b5-9e1cd83ae434" />
<img width="1741" height="448" alt="image" src="https://github.com/user-attachments/assets/77080446-af14-44bd-bb28-d054bc5a732c" />
<img width="1744" height="449" alt="image" src="https://github.com/user-attachments/assets/d7b89f9e-e598-4a02-8c24-3d3648de83f6" />
*Generates Income Statement, Balance Sheet, and Cash Flow*

### AI Summary & Insights
<img width="823" height="781" alt="image" src="https://github.com/user-attachments/assets/6016a7dd-93db-491a-a4d2-2200fc7bf2a0" />
<br>
*Provides executive summary and recommendations*

---

## ✨ Key Features

### 1️⃣ Data Validation with AI Suggestions

The app automatically detects:
- ❌ Missing dates or account numbers
- ❌ Duplicate transactions
- ❌ Invalid account numbers
- ❌ Debits ≠ Credits (out of balance)
- ❌ Outliers and anomalies
- ❌ Future-dated transactions

Each issue includes:
- **Row-level details** - See exactly which transactions have problems
- **Sample data** - Preview affected rows
- **AI suggestions** - Get recommended fixes
- **One-click fixes** - Accept or decline corrections individually

### 2️⃣ Currency Conversion

Supports 10+ currencies with automatic conversion to USD:
- USD, EUR, GBP, JPY, CNY, CAD, AUD, CHF, INR, MXN

### 3️⃣ Complete Financial Statements

**Income Statement:**
- Revenue, COGS, Gross Profit
- Operating Expenses (Salaries, Rent, Marketing, IT, Travel, Depreciation)
- EBIT, Interest, EBT, Tax, Net Income

**Balance Sheet:**
- Current Assets (Cash, AR, Inventory)
- Fixed Assets (PP&E, Other)
- Current Liabilities (AP, Accrued Expenses)
- Long-term Debt
- Equity (Common Stock, Retained Earnings)

**Cash Flow Statement:**
- Operating Activities
- Investing Activities
- Financing Activities

### 4️⃣ Data Reconciliation

Tracks and explains:
- Original vs. cleaned transaction counts
- What was removed and why
- Changes by year and category
- Downloadable reconciliation report (CSV)

### 5️⃣ AI-Generated Summary

Provides:
- Executive summary
- Revenue trend analysis
- Profitability metrics
- Balance sheet health assessment
- Custom recommendations

### 6️⃣ Export Options

- **Excel Model** - Updated 3-statement template
- **PDF Report** - Professional summary with tables

---

## 🏗️ How It Works

```
GL Data Upload → Data Validation → Fix Issues → Generate Model → Review & Download
```

1. **Upload** your GL data (CSV or Excel)
2. **Review** validation issues (missing dates, duplicates, etc.)
3. **Accept AI fixes** or proceed with original data
4. **Generate** complete 3-statement financial model
5. **Review** reconciliation and AI insights
6. **Download** Excel model and PDF report

---

## 🛠️ Tech Stack

- **Framework**: [Streamlit](https://streamlit.io/)
- **Data Processing**: Pandas, NumPy
- **Excel Generation**: OpenPyXL
- **PDF Generation**: ReportLab
- **AI Integration**: Anthropic Claude / OpenAI (optional)
- **Database**: SQLite (for future features)

---

## 📋 Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

---

## ⚡ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/three-statements-automation.git
cd three-statements-automation
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the App

```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📝 Data Format Requirements

Your GL data should include these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `TxnDate` | ✅ Yes | Transaction date |
| `AccountNumber` | ✅ Yes | GL account number (1000-9999) |
| `AccountName` | Recommended | Account description |
| `Debit` | ✅ Yes* | Debit amount |
| `Credit` | ✅ Yes* | Credit amount |
| `TransactionID` | Recommended | Unique identifier |
| `Currency` | Optional | Currency code (defaults to USD) |

*Either Debit/Credit OR a single Amount column is required.

### Account Number Ranges

The app expects standard GL account numbering:

- **1000-1499**: Current Assets
- **1500-1999**: Fixed Assets
- **2000-2499**: Current Liabilities
- **2500-2999**: Long-term Liabilities
- **3000-3999**: Equity
- **4000-4999**: Revenue
- **5000-5999**: Cost of Goods Sold
- **6000-7999**: Operating Expenses

### Sample Data Format

```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-01-05,4001,Product Revenue,0.00,5200.00,USD
2023-01-08,6100,Rent Expense,1800.00,0.00,USD
2023-01-12,1001,Cash,2400.00,0.00,USD
```

---

## 🎓 Usage Guide

### Step 1: Upload Your Data

1. Click **"Upload your file"**
2. Select your CSV or Excel file
3. File is loaded and currency conversion happens automatically

### Step 2: Review Validation Issues

1. App scans for 7 types of issues
2. Each issue shows:
   - Severity (Critical/Warning/Info)
   - Affected row count
   - Sample data
   - AI suggestion
3. Check/uncheck fixes you want to apply

### Step 3: Apply Fixes

**Option A: Accept AI Fixes**
- Checks all boxes
- Applies all recommended corrections
- Shows summary of changes

**Option B: Decline & Continue**
- Unchecks all boxes
- Proceeds with original data
- No changes made

### Step 4: Generate Financial Model

1. Click **"🚀 Generate 3-Statement Model"**
2. Wait 5-10 seconds
3. View complete financial statements

### Step 5: Review Results

**Three Statement Model:**
- Income Statement (all line items)
- Balance Sheet (all accounts)
- Cash Flow Statement

**Data Reconciliation:**
- Original vs. cleaned transaction counts
- Changes by year and category
- Download reconciliation report

**AI Summary:**
- Executive summary
- Key findings
- Recommendations

### Step 6: Download Reports

- **Excel Model**: Updated 3-statement template with your data
- **PDF Report**: Professional summary with formatted tables

---

## 🔧 Configuration

### Currency Exchange Rates

Edit rates in `streamlit_app.py` (lines 33):

```python
EXCHANGE_RATES = {
    'USD': 1.0,
    'EUR': 1.08,  # Update these rates as needed
    'GBP': 1.27,
    # Add more currencies here
}
```

### Account Number Mappings

Customize account ranges in `calculate_financial_statements()` function:

```python
# Example: Change revenue range
revenue = year_data[year_data['AccountNumber'].between(4000, 4999)]['Credit'].sum()
# Change to:
revenue = year_data[year_data['AccountNumber'].between(3000, 3999)]['Credit'].sum()
```

---

## 📦 Deployment

### Deploy to Streamlit Cloud (Free)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Three Statements Automation"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your repository
   - Main file: `streamlit_app.py`
   - Click "Deploy"

3. **Your app is live!**
   - Get a permanent URL: `https://your-app-name.streamlit.app`
   - Share with others
   - Updates automatically when you push to GitHub

---

## 🧪 Testing

### Sample Data Included

The app shows sample data format when no file is uploaded:

```python
TxnDate    AccountNumber  AccountName    Debit   Credit  Currency
2023-01-05      4001      Revenue        0.00    5200.00    USD
2023-01-08      6100      Rent Expense   1800.00    0.00    USD
```

### Create Your Own Test File

1. Copy the sample format
2. Add more rows with your test data
3. Save as `test_data.csv`
4. Upload to the app

---

## 📊 Example Output

### Financial Metrics Calculated

- **Gross Margin**: (Gross Profit / Revenue) × 100%
- **EBIT Margin**: (EBIT / Revenue) × 100%
- **Net Margin**: (Net Income / Revenue) × 100%
- **Debt-to-Equity**: Total Liabilities / Total Equity
- **Asset Breakdown**: Current vs. Fixed assets
- **Cash Flow Analysis**: Operating, Investing, Financing activities

---

## 🐛 Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt --upgrade
```

### "Excel template not found"
- Make sure `3_statement_excel_completed_model.xlsx` is in the project root
- Or comment out Excel download section if you don't need it

### "Out of balance" error
- Your GL data has Debits ≠ Credits
- Check for missing transactions or data entry errors
- The app will show you the exact difference

### No data showing in statements
- Check your account number ranges (should be 1000-7999)
- Verify you have transactions in the expected ranges
- Check date range of your data

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Report bugs** - Open an issue describing the problem
2. **Suggest features** - Tell us what would make this better
3. **Submit PRs** - Fork, make changes, submit pull request
4. **Improve docs** - Help make the README clearer

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Inspired by the need for faster financial model creation
- Thanks to the open-source community

---

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/three-statements-automation/issues)
- **Questions**: Open a discussion on GitHub
- **Feedback**: Use the feedback form in the app

---

## 🎓 Educational Purpose

⚠️ **Early Demo Notice**

This is an early-stage demo built as part of a self-learning experiment.

It is for **educational purposes only** and is **not intended for production use**.

I hope this project can inspire others to build more AI tools in finance.

Thank you for your valuable feedback!

---

## 🔮 Roadmap

### Planned Features

- [ ] Multi-currency support (beyond current 10)
- [ ] Custom account mapping UI
- [ ] Historical comparison (YoY, QoQ)
- [ ] Budget vs. Actual analysis
- [ ] More export formats (Google Sheets, Power BI)
- [ ] Advanced AI insights (anomaly detection, forecasting)
- [ ] User authentication & saved sessions
- [ ] Batch processing for multiple companies

### Recently Added

- ✅ Data validation with individual checkboxes
- ✅ Row-level error details
- ✅ Sample data preview on landing page
- ✅ Updated Early Demo Notice

---

## ⭐ Star This Project

If you find this useful, please give it a star! ⭐

It helps others discover the project and motivates continued development.

---

**Made with ❤️ for the finance and accounting community**
