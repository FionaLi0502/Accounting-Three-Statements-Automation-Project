# ⚡ QUICKSTART GUIDE

**Get the app running in 3 minutes!**

---

## 🚀 Option 1: Run Locally (Fastest for Testing)

### Step 1: Install Dependencies (1 minute)

```bash
# Navigate to project folder
cd accounting_app

# Install required packages
pip install streamlit pandas numpy openpyxl python-dateutil reportlab anthropic --break-system-packages
```

### Step 2: Run the App (30 seconds)

```bash
streamlit run streamlit_app.py
```

**That's it!** App opens in your browser at `http://localhost:8501`

### Step 3: Try Sample Data (30 seconds)

1. Click "📊 Use Sample Data" button in sidebar
2. Click "🚀 Generate 3-Statement Model"
3. Download Excel and PDF

**Done!** ✅

---

## ☁️ Option 2: Deploy to Streamlit Cloud (Free Hosting)

### Step 1: Push to GitHub (2 minutes)

```bash
# Initialize git
cd accounting_app
git init

# Add files
git add .
git commit -m "Three Statements Automation"

# Push to GitHub (replace with your URL)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 2: Deploy (1 minute)

1. Go to https://share.streamlit.io
2. Click "New app"
3. Select your repository
4. Main file: `streamlit_app.py`
5. Click "Deploy"

**That's it!** Get a public URL like `https://your-app.streamlit.app`

---

## 📊 Quick Feature Demo

### Test 1: Sample Data (30 seconds)
```
1. Click "Use Sample Data"
2. See TB and GL data loaded
3. Click "Generate Model"
4. View Income Statement, Balance Sheet, Cash Flow
```

### Test 2: Unit Conversion (1 minute)
```
1. Sidebar → Select "USD thousands"
2. Upload sample_tb.csv
3. Generate model
4. See amounts in thousands
```

### Test 3: Validation (1 minute)
```
1. Upload sample GL with issues
2. See validation warnings
3. Check/uncheck fixes
4. Apply selected fixes
5. Generate clean model
```

---

## 📁 Project Structure at a Glance

```
accounting_app/
├── streamlit_app.py          # ← START HERE (main app)
├── validation.py              # Data validation logic
├── mapping.py                 # Account mapping rules
├── excel_writer.py            # Excel generation
├── pdf_export.py              # PDF generation
├── ai_summary.py              # AI insights
├── sample_data.py             # Sample data handlers
├── requirements.txt           # Dependencies
├── README.md                  # Full documentation
├── DEPLOYMENT_GUIDE.md        # Deployment instructions
├── TESTING_GUIDE.md           # Testing procedures
└── assets/
    ├── templates/             # Excel templates
    └── sample_data/           # Demo files
```

---

## 🎯 What To Test First

### 1. Basic Workflow
✅ Upload TB + GL → Generate model → Download

### 2. Sample Data
✅ Click "Use Sample Data" → Instant demo

### 3. Random Dataset
✅ Click "Load Random Test Dataset" → Different data each time

### 4. Downloads
✅ Excel model with your data
✅ Professional PDF report

---

## ⚙️ Configuration (Optional)

### Add AI Summary (Optional)

1. Get Anthropic API key from https://console.anthropic.com
2. Create `.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "your_key_here"
```
3. Restart app

**Without API key:** App uses rule-based summary (works fine!)

### Customize Account Ranges

Edit `mapping.py`:
```python
DEFAULT_ACCOUNT_RANGES = {
    'cash': (1000, 1099),     # Your range here
    'revenue': (4000, 4999),  # Your range here
}
```

---

## 🐛 Common Issues & Quick Fixes

### Issue: "Module not found"
```bash
pip install -r requirements.txt
```

### Issue: "Template not found"
- Check `assets/templates/` folder exists
- Ensure Excel files are in that folder

### Issue: "Sample data not found"
- Check `assets/sample_data/` folder exists
- Ensure CSV files are in that folder

### Issue: App won't start
```bash
# Update Streamlit
pip install streamlit --upgrade

# Clear cache
streamlit cache clear
```

---

## 📚 Next Steps

Once you have it running:

1. **Read full docs:** [README.md](README.md)
2. **Deploy to cloud:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. **Run tests:** [TESTING_GUIDE.md](TESTING_GUIDE.md)
4. **Customize:** Edit `mapping.py` for your account structure

---

## 💡 Tips for Best Results

### For Complete Output:
✅ Upload Trial Balance (ending balances)
✅ Include both Balance Sheet and P&L accounts
✅ Multi-year data for Cash Flow Statement

### For Transaction Validation:
✅ Include TransactionID in GL Activity
✅ Ensure Debits = Credits per transaction

### For Accurate Mapping:
✅ Use standard account names (Cash, AR, Revenue, etc.)
✅ Or configure custom ranges in `mapping.py`

---

## 🎓 Understanding the Workflow

```
1. UPLOAD
   ├─ Trial Balance (recommended)
   └─ GL Activity (optional)
          ↓
2. VALIDATE
   ├─ Check balance
   ├─ Detect issues
   └─ Apply fixes
          ↓
3. MAP ACCOUNTS
   ├─ Name-based (primary)
   └─ Range-based (fallback)
          ↓
4. GENERATE
   ├─ Income Statement
   ├─ Balance Sheet
   └─ Cash Flow (GAAP indirect)
          ↓
5. DOWNLOAD
   ├─ Excel Model
   └─ PDF Report
```

---

## 🚦 Status Indicators

**✅ Green:** Everything working, full output available
**⚠️ Yellow:** Partial data, downgraded mode, warnings
**🔴 Red:** Critical errors, must fix to proceed

---

## 📞 Getting Help

**Questions?**
1. Check [README.md](README.md) - comprehensive docs
2. Check [TESTING_GUIDE.md](TESTING_GUIDE.md) - troubleshooting
3. Open GitHub Issue

**Found a bug?**
1. Check if it's a known issue
2. Try with sample data
3. Report with minimal reproduction case

---

## ✅ Success Checklist

Before you start customizing:

- [ ] App runs locally
- [ ] Sample data loads
- [ ] Model generates
- [ ] Excel downloads
- [ ] PDF downloads
- [ ] Read README.md

---

**That's it! You're ready to go!** 🎉

For more details, see the full [README.md](README.md)
