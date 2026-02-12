# 🚀 DEPLOYMENT GUIDE

## Quick Deployment to Streamlit Cloud

### Prerequisites
- GitHub account
- Streamlit Cloud account (free at share.streamlit.io)

---

## Step 1: Prepare Your Repository

### 1.1 Create GitHub Repository

```bash
# On GitHub:
# 1. Go to github.com
# 2. Click "+" → "New repository"
# 3. Name: "Accounting-Three-Statements-Automation-Project"
# 4. Make it Public
# 5. Click "Create repository"
```

### 1.2 Initialize Local Git

```bash
cd accounting_app

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Production-ready Three Statements Automation with modular architecture"

# Add remote (replace with your GitHub URL)
git remote add origin https://github.com/YOUR_USERNAME/Accounting-Three-Statements-Automation-Project.git

# Push
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy to Streamlit Cloud

### 2.1 Sign Up

1. Go to https://share.streamlit.io
2. Click "Sign up"
3. Sign in with your GitHub account
4. Authorize Streamlit

### 2.2 Create New App

1. Click "New app" button
2. Fill in the form:
   - **Repository**: Select `YOUR_USERNAME/Accounting-Three-Statements-Automation-Project`
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
   - **App URL** (optional): Choose custom name like `three-statements-automation`

3. Click "Advanced settings" (optional):
   - **Python version**: 3.10
   - **Secrets**: Add ANTHROPIC_API_KEY if you have one

4. Click "Deploy!"

### 2.3 Wait for Deployment

- Takes 2-5 minutes
- Watch deployment logs
- Status will change to "Your app is live!"

### 2.4 Get Your URL

Your app will be live at:
```
https://YOUR_APP_NAME.streamlit.app
```

Or:
```
https://YOUR_USERNAME-accounting-three-statements-automation-project-streamlit-app-xyz123.streamlit.app
```

---

## Step 3: Configure Secrets (Optional)

If you want AI summary feature:

1. In Streamlit Cloud dashboard, click on your app
2. Click "Settings" → "Secrets"
3. Add:
```toml
ANTHROPIC_API_KEY = "your_api_key_here"
```
4. Click "Save"
5. App will restart automatically

---

## Step 4: Test Your Deployment

### 4.1 Basic Tests

1. Open your app URL
2. Click "Use Sample Data" button
3. Should load TB and GL data
4. Click "Generate 3-Statement Model"
5. Should generate Income Statement, Balance Sheet, Cash Flow
6. Download Excel and PDF

### 4.2 Advanced Tests

1. Upload your own CSV file
2. Test validation features
3. Test with TB only
4. Test with GL only
5. Test unit conversion

---

## Step 5: Update Your App

Whenever you make changes:

```bash
git add .
git commit -m "Your update message"
git push
```

Streamlit Cloud will automatically redeploy!

---

## Alternative Deployments

### Option B: Deploy Locally (Development)

```bash
# Run on your machine
streamlit run streamlit_app.py

# Access at http://localhost:8501
```

### Option C: Deploy to Heroku

1. Create `Procfile`:
```
web: streamlit run streamlit_app.py --server.port=$PORT
```

2. Create `runtime.txt`:
```
python-3.10.12
```

3. Deploy:
```bash
heroku create your-app-name
git push heroku main
```

### Option D: Docker Deployment

1. Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

2. Build and run:
```bash
docker build -t accounting-app .
docker run -p 8501:8501 accounting-app
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError"

**Solution:** Check `requirements.txt` is complete:
```txt
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
openpyxl>=3.1.0
python-dateutil>=2.8.0
reportlab>=4.0.0
anthropic>=0.18.0
```

### Issue: "Sample files not found"

**Solution:** Ensure folder structure:
```
accounting_app/
├── streamlit_app.py
├── assets/
│   ├── templates/
│   │   └── Financial_Model_TEMPLATE_ZERO_USD_thousands_GAAP.xlsx
│   └── sample_data/
│       └── sample_tb.csv
```

### Issue: "App crashes on startup"

**Solution:** Check logs in Streamlit Cloud dashboard:
1. Click on your app
2. Click "Manage app" → "Logs"
3. Read error messages
4. Fix the issue
5. Push update

### Issue: "Excel template not found"

**Solution:** 
- Verify template files are committed to git
- Check file paths in `sample_data.py`
- Ensure files are in `assets/templates/` directory

---

## Performance Optimization

### For Large Datasets

Edit `streamlit_app.py` to add caching:

```python
import streamlit as st

@st.cache_data
def load_large_dataset(file):
    return pd.read_csv(file)
```

### For Faster Validation

Use sampling for very large files:

```python
# In validation.py
if len(df) > 50000:
    sample_df = df.sample(10000)  # Validate sample
```

---

## Security Best Practices

### 1. Protect API Keys

Never commit API keys! Use Streamlit Secrets:

```python
# In streamlit_app.py
import streamlit as st

api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
```

### 2. Validate User Inputs

Already implemented in `validation.py`:
- Column checking
- Data type validation
- Balance verification

### 3. Limit File Size

Add to `streamlit_app.py`:

```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

if file.size > MAX_FILE_SIZE:
    st.error("File too large. Max 50MB.")
```

---

## Monitoring

### View App Analytics

Streamlit Cloud provides:
- Number of visitors
- Session duration
- Error rates
- Resource usage

Access via: Dashboard → Your App → Analytics

### Custom Logging

Add to `streamlit_app.py`:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"User uploaded file: {file.name}")
```

---

## Maintenance

### Regular Updates

1. **Weekly:** Check for security updates
```bash
pip list --outdated
pip install --upgrade package_name
```

2. **Monthly:** Review and respond to user feedback

3. **Quarterly:** Update documentation

### Backup Strategy

1. **Code:** Auto-backed up in GitHub
2. **Data:** Sample files in git
3. **Configuration:** Document all settings

---

## Success Checklist

Before launching:

- [ ] All tests pass locally
- [ ] Sample data loads correctly
- [ ] All buttons work
- [ ] Excel downloads properly
- [ ] PDF downloads properly
- [ ] Documentation is complete
- [ ] README has correct URLs
- [ ] No sensitive data in code
- [ ] API keys in Secrets (not code)
- [ ] App tested on mobile
- [ ] App tested in different browsers

---

## Going Live

### Announce Your App

1. **LinkedIn Post:**
```
🚀 Just launched my AI-powered financial automation tool!

Upload messy GL data → Get complete 3-statement models in seconds

✅ Trial Balance + GL Activity support
✅ GAAP-compliant Cash Flow
✅ AI-powered insights
✅ Professional PDF/Excel exports

Try it: [your-url]
```

2. **GitHub README Badge:**
```markdown
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app.streamlit.app)
```

3. **Portfolio:**
Add to your personal website/portfolio

---

## Support

Need help deploying?

- Streamlit Docs: https://docs.streamlit.io/streamlit-cloud
- Streamlit Forum: https://discuss.streamlit.io
- GitHub Issues: File an issue in your repo

---

**🎉 Congratulations! Your app is now live!**
