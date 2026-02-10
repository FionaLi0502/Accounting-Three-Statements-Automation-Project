# 🧪 TESTING GUIDE

Complete guide for testing the Three Statements Automation application.

---

## Quick Test (5 Minutes)

### Smoke Test

```bash
# 1. Start app
streamlit run streamlit_app.py

# 2. Click "Use Sample Data"
# Expected: TB and GL data loaded

# 3. Click "Generate 3-Statement Model"
# Expected: Income Statement, Balance Sheet, Cash Flow displayed

# 4. Download Excel
# Expected: File downloads successfully

# 5. Download PDF
# Expected: File downloads successfully
```

If all 5 steps work → **App is functional!** ✅

---

## Comprehensive Test Suite

### Test 1: Column Header Normalization

**Purpose:** Verify column matching works regardless of naming/order

**Steps:**
1. Create test CSV with shuffled columns:
```csv
Credit,AccountName,TxnDate,Debit,AccountNumber
100,Revenue,2023-12-31,0,4000
0,Cash,2023-12-31,100,1000
```

2. Upload file
3. Check: Should load without errors

**Expected:** ✅ Columns normalized correctly

---

### Test 2: Trial Balance Validation

**Purpose:** Verify TB balance checking

**Test 2a: Balanced TB**
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-12-31,1000,Cash,100,0,USD
2023-12-31,4000,Revenue,0,100,USD
```

**Expected:** ✅ No balance issues

**Test 2b: Unbalanced TB**
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-12-31,1000,Cash,100,0,USD
2023-12-31,4000,Revenue,0,110,USD
```

**Expected:** ⚠️ Balance issue detected (difference: $10)

---

### Test 3: GL Activity Validation

**Test 3a: GL with TransactionID**
```csv
TxnDate,TransactionID,AccountNumber,AccountName,Debit,Credit,Currency
2023-01-01,TXN001,1000,Cash,100,0,USD
2023-01-01,TXN001,4000,Revenue,0,100,USD
2023-01-02,TXN002,1000,Cash,50,0,USD
2023-01-02,TXN002,5000,COGS,0,50,USD
```

**Expected:** ✅ Per-transaction validation performed

**Test 3b: GL without TransactionID**
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-01-01,1000,Cash,100,0,USD
2023-01-01,4000,Revenue,0,100,USD
```

**Expected:** ℹ️ Info message about overall-only validation

---

### Test 4: Unit Conversion

**Test 4a: USD Dollars**
1. Select "USD dollars" in sidebar
2. Upload TB with amounts: 1000, 2000, 5000
3. Generate model

**Expected:** Amounts divided by 1000 (1.0, 2.0, 5.0 in template)

**Test 4b: USD Thousands**
1. Select "USD thousands" in sidebar
2. Upload TB with amounts: 100, 200, 500
3. Generate model

**Expected:** Amounts unchanged (100, 200, 500 in template)

---

### Test 5: Account Mapping

**Test 5a: Name-Based Mapping**
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-12-31,9999,Cash and Cash Equivalents,100,0,USD
2023-12-31,9998,Accounts Receivable,50,0,USD
2023-12-31,9997,A/R,30,0,USD
```

**Expected:** All three mapped correctly despite unusual account numbers

**Test 5b: Range-Based Mapping**
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-12-31,1050,Unknown Asset,100,0,USD
2023-12-31,4500,Unknown Revenue,0,100,USD
```

**Expected:** Mapped by account number ranges

---

### Test 6: Missing Columns

**Test 6a: Missing TransactionID**
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-12-31,1000,Cash,100,0,USD
```

**Expected:** ℹ️ Info message, proceeds with overall validation

**Test 6b: Missing Required Column**
```csv
TxnDate,AccountNumber,Debit,Credit
2023-12-31,1000,100,0
```

**Expected:** ⚠️ Critical error, blocks processing

---

### Test 7: Multi-Year Handling

**Test 7a: Single Year**
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-12-31,1000,Cash,100,0,USD
2023-12-31,4000,Revenue,0,100,USD
```

**Expected:** 
- Income Statement ✅
- Balance Sheet ✅
- Cash Flow ⚠️ (requires multi-year)

**Test 7b: Two Years**
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-12-31,1000,Cash,100,0,USD
2023-12-31,4000,Revenue,0,100,USD
2024-12-31,1000,Cash,150,0,USD
2024-12-31,4000,Revenue,0,150,USD
```

**Expected:**
- Income Statement ✅ (both years)
- Balance Sheet ✅ (both years)
- Cash Flow ✅ (Year 2)

**Test 7c: Four Years**
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2021-12-31,1000,Cash,50,0,USD
2021-12-31,4000,Revenue,0,50,USD
2022-12-31,1000,Cash,75,0,USD
2022-12-31,4000,Revenue,0,75,USD
2023-12-31,1000,Cash,100,0,USD
2023-12-31,4000,Revenue,0,100,USD
2024-12-31,1000,Cash,125,0,USD
2024-12-31,4000,Revenue,0,125,USD
```

**Expected:** ⚠️ Warning about >3 years, uses most recent 3

---

### Test 8: Downgrade Modes

**Test 8a: TB Only**
1. Upload only Trial Balance
2. Leave GL Activity empty

**Expected:**
- ✅ Full 3-statement model
- ✅ No downgrade warnings

**Test 8b: GL Only**
1. Leave Trial Balance empty
2. Upload only GL Activity

**Expected:**
- ⚠️ Downgrade warning banner
- ✅ Income Statement
- ⚠️ Incomplete Balance Sheet message
- ⚠️ Incomplete Cash Flow message

---

### Test 9: Sample Data Features

**Test 9a: Download Sample Model**
1. Click "Download Sample Model"
2. Open downloaded Excel file

**Expected:** 
- ✅ File opens in Excel
- ✅ Contains realistic demo data
- ✅ All formulas work

**Test 9b: Use Sample Data**
1. Click "Use Sample Data"
2. Should auto-load TB and GL

**Expected:**
- ✅ Both files loaded
- ✅ Can generate model immediately

**Test 9c: Random Test Dataset**
1. Click "Load Random Test Dataset"
2. Should load one of 5 backup GL files

**Expected:**
- ✅ Random dataset loaded
- ✅ Dataset name shown
- ✅ Can proceed with validation

---

### Test 10: Auto-Fixes

**Test 10a: Missing Dates**
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
,1000,Cash,100,0,USD
2023-12-31,4000,Revenue,0,100,USD
```

**Expected:**
- ⚠️ Issue detected: 1 missing date
- ✅ Auto-fix available
- ✅ Removes row when applied

**Test 10b: Duplicates**
```csv
TxnDate,TransactionID,AccountNumber,AccountName,Debit,Credit,Currency
2023-01-01,TXN001,1000,Cash,100,0,USD
2023-01-01,TXN001,1000,Cash,100,0,USD
2023-01-01,TXN002,4000,Revenue,0,100,USD
```

**Expected:**
- ⚠️ Issue detected: 2 duplicate IDs
- ✅ Auto-fix available
- ✅ Removes duplicate when applied

---

## Automated Test Suite

### Run All Tests

```bash
cd accounting_app
python -m pytest tests/test_app.py -v
```

### Test Coverage

```bash
pytest tests/test_app.py --cov=. --cov-report=html
```

Opens coverage report in browser.

---

## Performance Testing

### Test Large Files

**Small:** 100 transactions → Should complete in < 5 seconds
**Medium:** 1,000 transactions → Should complete in < 10 seconds
**Large:** 10,000 transactions → Should complete in < 30 seconds

### Stress Test

```python
# Create large test file
import pandas as pd
import numpy as np

dates = pd.date_range('2023-01-01', '2024-12-31', freq='D')
accounts = np.random.randint(1000, 5000, size=len(dates))
amounts = np.random.uniform(10, 10000, size=len(dates))

df = pd.DataFrame({
    'TxnDate': dates,
    'TransactionID': [f'TXN{i:06d}' for i in range(len(dates))],
    'AccountNumber': accounts,
    'AccountName': ['Test'] * len(dates),
    'Debit': amounts,
    'Credit': amounts,
    'Currency': ['USD'] * len(dates)
})

df.to_csv('stress_test.csv', index=False)
```

Upload `stress_test.csv` and verify app handles it.

---

## Browser Compatibility

Test on:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Chrome
- [ ] Mobile Safari

---

## User Acceptance Testing

### Scenario 1: First-Time User

**Journey:**
1. Opens app for first time
2. Doesn't know what to upload
3. Clicks "Use Sample Data"
4. Sees validation results
5. Generates model
6. Downloads reports

**Expected:** ✅ Clear, intuitive, no confusion

### Scenario 2: Advanced User

**Journey:**
1. Has custom GL export from ERP
2. Columns in different order
3. Some missing TransactionIDs
4. Uploads and sees issues
5. Applies selective fixes
6. Reviews results
7. Downloads for further analysis

**Expected:** ✅ Powerful, flexible, transparent

### Scenario 3: Error Recovery

**Journey:**
1. Uploads wrong file format
2. Sees error message
3. Uploads correct file
4. Continues successfully

**Expected:** ✅ Helpful errors, easy recovery

---

## Edge Cases

### Test Edge Case 1: Empty File
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
```

**Expected:** ⚠️ Clear error message

### Test Edge Case 2: Single Transaction
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-12-31,1000,Cash,100,100,USD
```

**Expected:** ⚠️ Out of balance error

### Test Edge Case 3: All Zeros
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-12-31,1000,Cash,0,0,USD
2023-12-31,4000,Revenue,0,0,USD
```

**Expected:** ✅ Processes but generates zero statements

### Test Edge Case 4: Very Long Account Names
```csv
TxnDate,AccountNumber,AccountName,Debit,Credit,Currency
2023-12-31,1000,This Is A Very Very Very Long Account Name That Might Break Layout,100,0,USD
```

**Expected:** ✅ Handles gracefully

---

## Regression Testing

After making changes, test:

1. **Core Features:**
   - [ ] TB upload works
   - [ ] GL upload works
   - [ ] Validation works
   - [ ] Model generation works
   - [ ] Downloads work

2. **Sample Data:**
   - [ ] All three buttons work
   - [ ] Files load correctly

3. **Edge Cases:**
   - [ ] Missing columns handled
   - [ ] Extra columns ignored
   - [ ] Shuffled order works

---

## Bug Report Template

If you find a bug:

```markdown
**Bug Description:**
[Clear description of the issue]

**Steps to Reproduce:**
1. Go to...
2. Click on...
3. Upload file...
4. See error

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happens]

**Screenshots:**
[If applicable]

**Environment:**
- Browser: Chrome 120
- OS: Windows 11
- App URL: https://your-app.streamlit.app

**Sample Data:**
[Attach minimal CSV that reproduces the issue]
```

---

## Test Checklist for Release

Before deploying to production:

### Functionality
- [ ] All automated tests pass
- [ ] Sample data loads correctly
- [ ] Random dataset works
- [ ] TB-only workflow works
- [ ] GL-only workflow works
- [ ] TB+GL workflow works
- [ ] Unit conversion works
- [ ] Excel downloads correctly
- [ ] PDF downloads correctly
- [ ] AI summary works (or fallback)

### Data Quality
- [ ] Validation detects all issue types
- [ ] Auto-fixes work correctly
- [ ] Balance checking accurate
- [ ] Account mapping comprehensive
- [ ] Multi-year handling correct

### User Experience
- [ ] UI responsive on mobile
- [ ] Error messages helpful
- [ ] Warnings clear
- [ ] Documentation complete
- [ ] Sample data representative

### Performance
- [ ] < 15 seconds for typical dataset
- [ ] Handles 10,000+ transactions
- [ ] No memory leaks
- [ ] Efficient validation

### Security
- [ ] No API keys in code
- [ ] User data not logged
- [ ] File uploads validated
- [ ] No SQL injection risks

---

**🎉 Testing Complete!**

Ready to deploy? See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
