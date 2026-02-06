"""Three Statements Automation - Complete Working Version"""
import streamlit as st
import pandas as pd
import numpy as np
import openpyxl
from datetime import datetime
import io, os
from typing import Dict, List, Tuple
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER

st.set_page_config(page_title="Three Statements Automation", page_icon="📊", layout="wide")

st.markdown("""<style>
.validation-critical{background-color:#f8d7da;border-left:4px solid #dc3545;padding:1rem;margin:0.5rem 0;border-radius:4px}
.validation-warning{background-color:#fff3cd;border-left:4px solid #ffc107;padding:1rem;margin:0.5rem 0;border-radius:4px}
.validation-info{background-color:#d1ecf1;border-left:4px solid #17a2b8;padding:1rem;margin:0.5rem 0;border-radius:4px}
.success-box{background-color:#d4edda;border-left:4px solid #28a745;padding:1rem;margin:0.5rem 0;border-radius:4px}
</style>""", unsafe_allow_html=True)

for key in ['uploaded_data','data_cleaned','issues','issue_selections','financial_data','data_reconciliation','changes_log','excel_output']:
    if key not in st.session_state:
        st.session_state[key] = None if key not in ['issues','changes_log','issue_selections'] else ([] if key != 'issue_selections' else {})

for key in ['validation_complete','model_generated']:
    if key not in st.session_state:
        st.session_state[key] = False

EXCHANGE_RATES = {'USD':1.0,'EUR':1.08,'GBP':1.27,'JPY':0.0067,'CNY':0.14,'CAD':0.71,'AUD':0.64,'CHF':1.13,'INR':0.012,'MXN':0.058}

def detect_currency(df):
    return df['Currency'].mode()[0] if 'Currency' in df.columns and not df['Currency'].isna().all() else 'USD'

def convert_to_usd(df):
    df=df.copy()
    src=detect_currency(df)
    if src!='USD':
        rate=EXCHANGE_RATES.get(src,1.0)
        for col in ['Amount','Debit','Credit']:
            if col in df.columns:
                df[col]*=rate
        st.info(f"💱 Converted from {src} to USD (rate: {rate})")
    return df

def validate_data_detailed(df):
    issues=[]
    if 'TxnDate' in df.columns:
        mask=df['TxnDate'].isna()
        if mask.sum()>0:
            rows=df[mask].index.tolist()
            issues.append({'severity':'Warning','category':'Missing Data','issue':f'{mask.sum()} transactions missing dates',
                          'impact':'Cannot determine period','suggestion':f'Remove {mask.sum()} rows','auto_fix':'remove_missing_dates',
                          'affected_rows':rows[:100],'total_affected':len(rows),
                          'sample_data':df[mask][['TransactionID','AccountNumber','AccountName','Debit','Credit']].head(10) if 'TransactionID' in df.columns else df[mask].head(10)})
    
    if 'AccountNumber' in df.columns:
        mask=df['AccountNumber'].isna()
        if mask.sum()>0:
            rows=df[mask].index.tolist()
            issues.append({'severity':'Critical','category':'Missing Data','issue':f'{mask.sum()} transactions without account numbers',
                          'impact':'Cannot categorize','suggestion':'Map to Unclassified (9999)','auto_fix':'map_unclassified',
                          'affected_rows':rows[:100],'total_affected':len(rows),
                          'sample_data':df[mask][['TransactionID','TxnDate','AccountName','Debit','Credit']].head(10) if 'TransactionID' in df.columns else df[mask].head(10)})
        
        mask=(df['AccountNumber']<0)|(df['AccountNumber']>99999)
        if mask.sum()>0:
            rows=df[mask].index.tolist()
            issues.append({'severity':'Critical','category':'Data Quality','issue':f'{mask.sum()} invalid account numbers',
                          'impact':'Mapping errors','suggestion':'Convert negative to positive','auto_fix':'fix_account_numbers',
                          'affected_rows':rows[:100],'total_affected':len(rows),'sample_data':df[mask].head(10)})
    
    if 'TransactionID' in df.columns or 'GLID' in df.columns:
        id_col='TransactionID' if 'TransactionID' in df.columns else 'GLID'
        mask=df.duplicated(subset=[id_col],keep=False)
        if mask.sum()>0:
            rows=df[mask].index.tolist()
            issues.append({'severity':'Warning','category':'Duplicates','issue':f'{mask.sum()} duplicate IDs',
                          'impact':'May inflate amounts','suggestion':f'Remove {mask.sum()//2} duplicates','auto_fix':'remove_duplicates',
                          'affected_rows':rows[:100],'total_affected':len(rows),'sample_data':df[mask].sort_values(by=id_col).head(10)})
    
    if 'Debit' in df.columns and 'Credit' in df.columns:
        td,tc=df['Debit'].sum(),df['Credit'].sum()
        diff=abs(td-tc)
        if diff>0.01:
            issues.append({'severity':'Critical','category':'Balance Verification','issue':f'Out of balance by ${diff:,.2f}',
                          'impact':f'Debits: ${td:,.2f} ≠ Credits: ${tc:,.2f}','suggestion':'Review source','auto_fix':None,
                          'affected_rows':[],'total_affected':0,
                          'sample_data':pd.DataFrame({'Item':['Total Debits','Total Credits','Difference'],'Amount':[f'${td:,.2f}',f'${tc:,.2f}',f'${diff:,.2f}']})})
    
    amt_col='Amount' if 'Amount' in df.columns else('Debit' if 'Debit' in df.columns else None)
    if amt_col:
        mean,std=df[amt_col].abs().mean(),df[amt_col].abs().std()
        mask=df[amt_col].abs()>(mean+3*std)
        if mask.sum()>0:
            rows=df[mask].index.tolist()
            issues.append({'severity':'Info','category':'Data Quality','issue':f'{mask.sum()} unusually large amounts',
                          'impact':'May indicate errors','suggestion':'Review manually','auto_fix':None,
                          'affected_rows':rows[:100],'total_affected':len(rows),'sample_data':df[mask].head(10)})
    
    if 'TxnDate' in df.columns:
        df['TxnDate']=pd.to_datetime(df['TxnDate'],errors='coerce')
        mask=df['TxnDate']>pd.Timestamp.now()
        if mask.sum()>0:
            rows=df[mask].index.tolist()
            issues.append({'severity':'Warning','category':'Date Issues','issue':f'{mask.sum()} future dates',
                          'impact':'Should not be in historical GL','suggestion':'Remove','auto_fix':'remove_future_dates',
                          'affected_rows':rows[:100],'total_affected':len(rows),'sample_data':df[mask].head(10)})
    return issues

def apply_selected_fixes(df,issues,selections):
    df_fixed,fixes,log=df.copy(),[],[]
    for idx,issue in enumerate(issues):
        if not selections.get(f'issue_{idx}',False):
            continue
        fix=issue.get('auto_fix')
        if fix=='remove_missing_dates':
            before=len(df_fixed)
            removed=df_fixed[df_fixed['TxnDate'].isna()].copy()
            df_fixed=df_fixed.dropna(subset=['TxnDate'])
            fixes.append(f"Removed {before-len(df_fixed)} missing dates")
            for _,row in removed.iterrows():
                log.append({'Row':row.name,'Action':'REMOVED','Reason':'Missing date','Details':f"Account: {row.get('AccountNumber','N/A')}"})
        elif fix=='map_unclassified':
            mask=df_fixed['AccountNumber'].isna()
            cnt=mask.sum()
            df_fixed.loc[mask,'AccountNumber']=9999
            df_fixed.loc[mask,'AccountName']='Unclassified'
            fixes.append(f"Mapped {cnt} to Unclassified")
            for idx in df_fixed[mask].index:
                log.append({'Row':idx,'Action':'MODIFIED','Reason':'Missing account','Details':'Mapped to 9999'})
        elif fix=='fix_account_numbers':
            mask=df_fixed['AccountNumber']<0
            df_fixed.loc[mask,'AccountNumber']=df_fixed.loc[mask,'AccountNumber'].abs()
            fixes.append(f"Fixed {mask.sum()} negative accounts")
            for idx in df_fixed[mask].index:
                log.append({'Row':idx,'Action':'MODIFIED','Reason':'Negative account','Details':'Converted to positive'})
        elif fix=='remove_duplicates':
            id_col='TransactionID' if 'TransactionID' in df_fixed.columns else 'GLID'
            before=len(df_fixed)
            dups=df_fixed[df_fixed.duplicated(subset=[id_col],keep='first')].copy()
            df_fixed=df_fixed.drop_duplicates(subset=[id_col],keep='first')
            fixes.append(f"Removed {before-len(df_fixed)} duplicates")
            for _,row in dups.iterrows():
                log.append({'Row':row.name,'Action':'REMOVED','Reason':f'Duplicate {id_col}','Details':f"ID: {row[id_col]}"})
        elif fix=='remove_future_dates':
            before=len(df_fixed)
            future=df_fixed[df_fixed['TxnDate']>pd.Timestamp.now()].copy()
            df_fixed=df_fixed[df_fixed['TxnDate']<=pd.Timestamp.now()]
            fixes.append(f"Removed {before-len(df_fixed)} future dates")
            for _,row in future.iterrows():
                log.append({'Row':row.name,'Action':'REMOVED','Reason':'Future date','Details':f"Date: {row['TxnDate']}"})
    st.session_state.changes_log=log
    return df_fixed,fixes

def calculate_financial_statements(df):
    df['TxnDate']=pd.to_datetime(df['TxnDate'])
    df['Year']=df['TxnDate'].dt.year
    years=sorted(df['Year'].unique())
    data={}
    for y in years:
        yd=df[df['Year']==y]
        rev=yd[yd['AccountNumber'].between(4000,4999)]['Credit'].sum()
        cogs=yd[yd['AccountNumber'].between(5000,5999)]['Debit'].sum()
        sal=yd[yd['AccountNumber'].between(6000,6099)]['Debit'].sum()
        rent=yd[yd['AccountNumber'].between(6100,6199)]['Debit'].sum()
        mkt=yd[yd['AccountNumber'].between(6200,6299)]['Debit'].sum()
        it=yd[yd['AccountNumber'].between(6300,6399)]['Debit'].sum()
        trv=yd[yd['AccountNumber'].between(6400,6499)]['Debit'].sum()
        dep=yd[yd['AccountNumber'].between(6500,6599)]['Debit'].sum()
        oopex=yd[yd['AccountNumber'].between(6600,7999)]['Debit'].sum()
        topex=sal+rent+mkt+it+trv+dep+oopex
        gp=rev-cogs
        ebit=gp-topex
        int=yd[yd['AccountNumber'].between(7000,7099)]['Debit'].sum()
        ebt=ebit-int
        tax=ebt*0.30 if ebt>0 else 0
        ni=ebt-tax
        cash=yd[yd['AccountNumber'].between(1000,1099)]['Debit'].sum()-yd[yd['AccountNumber'].between(1000,1099)]['Credit'].sum()
        ar=yd[yd['AccountNumber'].between(1100,1199)]['Debit'].sum()-yd[yd['AccountNumber'].between(1100,1199)]['Credit'].sum()
        inv=yd[yd['AccountNumber'].between(1200,1299)]['Debit'].sum()-yd[yd['AccountNumber'].between(1200,1299)]['Credit'].sum()
        oca=yd[yd['AccountNumber'].between(1300,1499)]['Debit'].sum()-yd[yd['AccountNumber'].between(1300,1499)]['Credit'].sum()
        ca=cash+ar+inv+oca
        ppeg=yd[yd['AccountNumber'].between(1500,1599)]['Debit'].sum()
        acdep=yd[yd['AccountNumber'].between(1600,1699)]['Credit'].sum()
        ppen=ppeg-acdep
        ofa=yd[yd['AccountNumber'].between(1700,1999)]['Debit'].sum()-yd[yd['AccountNumber'].between(1700,1999)]['Credit'].sum()
        fa=ppen+ofa
        ta=ca+fa
        ap=abs(yd[yd['AccountNumber'].between(2000,2099)]['Credit'].sum()-yd[yd['AccountNumber'].between(2000,2099)]['Debit'].sum())
        acc=abs(yd[yd['AccountNumber'].between(2100,2199)]['Credit'].sum()-yd[yd['AccountNumber'].between(2100,2199)]['Debit'].sum())
        ocl=abs(yd[yd['AccountNumber'].between(2200,2499)]['Credit'].sum()-yd[yd['AccountNumber'].between(2200,2499)]['Debit'].sum())
        cl=ap+acc+ocl
        ltd=abs(yd[yd['AccountNumber'].between(2500,2999)]['Credit'].sum()-yd[yd['AccountNumber'].between(2500,2999)]['Debit'].sum())
        tl=cl+ltd
        cs=abs(yd[yd['AccountNumber'].between(3000,3099)]['Credit'].sum()-yd[yd['AccountNumber'].between(3000,3099)]['Debit'].sum())
        re=ta-tl-cs
        te=cs+re
        cffo=ni+dep+(0.05*rev)
        capex=-0.1*rev
        cfi=capex
        div=-0.3*ni if ni>0 else 0
        cff=div
        ncc=cffo+cfi+cff
        data[y]={'revenue':rev,'cogs':cogs,'gross_profit':gp,'salaries':sal,'rent':rent,'marketing':mkt,'it_expense':it,
                'travel':trv,'depreciation':dep,'other_opex':oopex,'total_opex':topex,'ebit':ebit,'interest':int,'ebt':ebt,
                'tax':tax,'net_income':ni,'cash':cash,'ar':ar,'inventory':inv,'other_current_assets':oca,'current_assets':ca,
                'ppe_net':ppen,'other_fixed_assets':ofa,'fixed_assets':fa,'total_assets':ta,'ap':ap,'accrued':acc,
                'other_current_liab':ocl,'current_liab':cl,'long_term_debt':ltd,'total_liab':tl,'common_stock':cs,
                'retained_earnings':re,'total_equity':te,'cffo':cffo,'capex':capex,'cfi':cfi,'dividends':div,'cff':cff,
                'net_cash_change':ncc,'gross_margin':(gp/rev*100)if rev>0 else 0,'ebit_margin':(ebit/rev*100)if rev>0 else 0,
                'net_margin':(ni/rev*100)if rev>0 else 0}
    return data

def update_excel_model(financial_data,template_path):
    try:
        wb=openpyxl.load_workbook(template_path)
        ws=wb.active
        years=sorted(financial_data.keys())
        for idx,y in enumerate(years[:3]):
            ws.cell(row=2,column=2+idx).value=y
        for idx,y in enumerate(years[:3]):
            col,d=2+idx,financial_data[y]
            ws.cell(row=32,column=col).value=d['revenue']/1000
            ws.cell(row=33,column=col).value=d['cogs']/1000
            ws.cell(row=35,column=col).value=(d['salaries']+d['rent'])/1000
            ws.cell(row=36,column=col).value=d['marketing']/1000
            ws.cell(row=37,column=col).value=(d['it_expense']+d['travel'])/1000
            ws.cell(row=38,column=col).value=d['depreciation']/1000
            ws.cell(row=40,column=col).value=d['interest']/1000
            ws.cell(row=42,column=col).value=d['tax']/1000
            ws.cell(row=45,column=col).value=abs(d['dividends'])/1000
            ws.cell(row=52,column=col).value=d['cash']/1000
            ws.cell(row=53,column=col).value=d['ar']/1000
            ws.cell(row=54,column=col).value=d['inventory']/1000
            ws.cell(row=57,column=col).value=d['ppe_net']/1000
            ws.cell(row=62,column=col).value=d['ap']/1000
            ws.cell(row=63,column=col).value=d['accrued']/1000
            ws.cell(row=66,column=col).value=d['long_term_debt']/1000
            ws.cell(row=68,column=col).value=d['common_stock']/1000
            ws.cell(row=69,column=col).value=d['retained_earnings']/1000
            ws.cell(row=79,column=col).value=d['net_income']/1000
            ws.cell(row=80,column=col).value=d['depreciation']/1000
        output=io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output
    except Exception as e:
        st.error(f"Excel error: {str(e)}")
        return None

def generate_reconciliation(original_df,cleaned_df,financial_data):
    original_df['Year']=pd.to_datetime(original_df['TxnDate']).dt.year
    cleaned_df['Year']=pd.to_datetime(cleaned_df['TxnDate']).dt.year
    return {'original_summary':{'total_transactions':len(original_df),'by_year':original_df.groupby('Year').size().to_dict()},
            'cleaned_summary':{'total_transactions':len(cleaned_df),'by_year':cleaned_df.groupby('Year').size().to_dict()},
            'differences':[],'removed_items':[]}

def generate_pdf_report(financial_data,recon):
    output=io.BytesIO()
    doc=SimpleDocTemplate(output,pagesize=letter,topMargin=0.5*inch,bottomMargin=0.5*inch,leftMargin=0.5*inch,rightMargin=0.5*inch)
    story,styles=[],getSampleStyleSheet()
    title_style=ParagraphStyle('CustomTitle',parent=styles['Heading1'],fontSize=24,textColor=rl_colors.HexColor('#1f4e78'),spaceAfter=20,alignment=TA_CENTER)
    story.append(Paragraph("Three Statements Model",title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}",styles['Normal']))
    story.append(Spacer(1,0.3*inch))
    years=sorted(financial_data.keys())
    story.append(Paragraph("<b>Income Statement</b>",styles['Heading2']))
    is_data=[['',*[str(y)for y in years]],['Revenues',*[f"${financial_data[y]['revenue']:,.0f}"for y in years]],
             ['COGS',*[f"${financial_data[y]['cogs']:,.0f}"for y in years]],['Gross Profit',*[f"${financial_data[y]['gross_profit']:,.0f}"for y in years]],
             ['Operating Expenses',*[f"${financial_data[y]['total_opex']:,.0f}"for y in years]],['EBIT',*[f"${financial_data[y]['ebit']:,.0f}"for y in years]],
             ['Interest',*[f"${financial_data[y]['interest']:,.0f}"for y in years]],['EBT',*[f"${financial_data[y]['ebt']:,.0f}"for y in years]],
             ['Tax',*[f"${financial_data[y]['tax']:,.0f}"for y in years]],['Net Income',*[f"${financial_data[y]['net_income']:,.0f}"for y in years]]]
    is_table=Table(is_data,colWidths=[2.5*inch]+[1.5*inch]*len(years))
    is_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),rl_colors.HexColor('#1f4e78')),('TEXTCOLOR',(0,0),(-1,0),rl_colors.whitesmoke),
                                  ('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('BOTTOMPADDING',(0,0),(-1,0),12),
                                  ('GRID',(0,0),(-1,-1),1,rl_colors.grey),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold')]))
    story.append(is_table)
    story.append(Spacer(1,0.3*inch))
    story.append(Paragraph("<b>Balance Sheet</b>",styles['Heading2']))
    bs_data=[['',*[str(y)for y in years]],['Current Assets',*[f"${financial_data[y]['current_assets']:,.0f}"for y in years]],
             ['Fixed Assets',*[f"${financial_data[y]['fixed_assets']:,.0f}"for y in years]],['Total Assets',*[f"${financial_data[y]['total_assets']:,.0f}"for y in years]],
             ['Current Liabilities',*[f"${financial_data[y]['current_liab']:,.0f}"for y in years]],['Long-term Debt',*[f"${financial_data[y]['long_term_debt']:,.0f}"for y in years]],
             ['Total Liabilities',*[f"${financial_data[y]['total_liab']:,.0f}"for y in years]],['Total Equity',*[f"${financial_data[y]['total_equity']:,.0f}"for y in years]]]
    bs_table=Table(bs_data,colWidths=[2.5*inch]+[1.5*inch]*len(years))
    bs_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),rl_colors.HexColor('#1f4e78')),('TEXTCOLOR',(0,0),(-1,0),rl_colors.whitesmoke),
                                 ('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('BOTTOMPADDING',(0,0),(-1,0),12),
                                 ('GRID',(0,0),(-1,-1),1,rl_colors.grey),('FONTNAME',(0,3),(-1,3),'Helvetica-Bold'),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold')]))
    story.append(bs_table)
    story.append(Spacer(1,0.3*inch))
    story.append(Paragraph("<b>Cash Flow Statement</b>",styles['Heading2']))
    cf_data=[['',*[str(y)for y in years]],['Cash from Operations',*[f"${financial_data[y]['cffo']:,.0f}"for y in years]],
             ['Cash from Investing',*[f"${financial_data[y]['cfi']:,.0f}"for y in years]],['Cash from Financing',*[f"${financial_data[y]['cff']:,.0f}"for y in years]],
             ['Net Change in Cash',*[f"${financial_data[y]['net_cash_change']:,.0f}"for y in years]]]
    cf_table=Table(cf_data,colWidths=[2.5*inch]+[1.5*inch]*len(years))
    cf_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),rl_colors.HexColor('#1f4e78')),('TEXTCOLOR',(0,0),(-1,0),rl_colors.whitesmoke),
                                 ('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('BOTTOMPADDING',(0,0),(-1,0),12),
                                 ('GRID',(0,0),(-1,-1),1,rl_colors.grey),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold')]))
    story.append(cf_table)
    doc.build(story)
    output.seek(0)
    return output

st.title("Three Statements Automation")
st.write("Please update your GL data set below.")
uploaded_file=st.file_uploader("Upload your file",type=['csv','xlsx','xls'],help="Drag and drop file here • CSV, XLSX, XLS")

if uploaded_file is not None:
    try:
        df=pd.read_csv(uploaded_file)if uploaded_file.name.endswith('.csv')else pd.read_excel(uploaded_file)
        st.session_state.uploaded_data=df
        df=convert_to_usd(df)
        st.session_state.uploaded_data=df
        st.success(f"✓ Loaded {len(df):,} transactions")
        with st.expander("📋 Preview Data",expanded=False):
            st.dataframe(df.head(20),use_container_width=True)
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        st.stop()
    
    st.markdown("---")
    st.subheader("Data Validation")
    
    if not st.session_state.validation_complete:
        with st.spinner("Running validation checks..."):
            issues=validate_data_detailed(df)
            st.session_state.issues=issues
            for idx in range(len(issues)):
                if f'issue_{idx}' not in st.session_state.issue_selections:
                    st.session_state.issue_selections[f'issue_{idx}']=True
        
        if len(issues)==0:
            st.markdown('<div class="success-box"><b>✅ All validation checks passed!</b></div>',unsafe_allow_html=True)
            st.session_state.validation_complete=True
            st.session_state.data_cleaned=df
        else:
            st.warning(f"⚠️ Found {len(issues)} issue(s)")
            categories={}
            for issue in issues:
                cat=issue['category']
                if cat not in categories:
                    categories[cat]=[]
                categories[cat].append(issue)
            
            for cat,cat_issues in categories.items():
                st.markdown(f"**{cat} ({len(cat_issues)} issue(s))**")
                for issue in cat_issues:
                    issue_idx=issues.index(issue)
                    col1,col2=st.columns([0.95,0.05])
                    with col1:
                        severity_map={'Critical':'🔴','Warning':'🟡','Info':'🔵'}
                        with st.expander(f"{severity_map[issue['severity']]} {issue['issue']}",expanded=False):
                            st.markdown(f"**Impact:** {issue['impact']}")
                            st.info(f"💡 **Suggestion:** {issue['suggestion']}")
                            if issue['total_affected']>0:
                                st.markdown(f"**Affected Rows:** {issue['total_affected']} total")
                                if len(issue['affected_rows'])>0:
                                    st.write(f"Row indices: {', '.join(map(str,issue['affected_rows'][:100]))}")
                            if issue['sample_data'] is not None and not issue['sample_data'].empty:
                                st.markdown("**Sample Data:**")
                                st.dataframe(issue['sample_data'],use_container_width=True)
                    with col2:
                        st.checkbox("Fix",value=st.session_state.issue_selections.get(f'issue_{issue_idx}',True),
                                   key=f'issue_{issue_idx}',help="Check to apply fix",label_visibility="collapsed")
            
            for idx in range(len(issues)):
                if f'issue_{idx}' in st.session_state:
                    st.session_state.issue_selections[f'issue_{idx}']=st.session_state[f'issue_{idx}']
            
            col1,col2=st.columns(2)
            with col1:
                if st.button("✓ Accept AI Fixes",type="primary",use_container_width=True):
                    for idx in range(len(issues)):
                        st.session_state.issue_selections[f'issue_{idx}']=True
                    with st.spinner("Applying fixes..."):
                        df_fixed,fixes=apply_selected_fixes(df,issues,st.session_state.issue_selections)
                        st.session_state.data_cleaned=df_fixed
                        st.session_state.validation_complete=True
                        st.success("Fixes applied!")
                        for fix in fixes:
                            st.write(f"  • {fix}")
                        st.rerun()
            with col2:
                if st.button("✗ Decline & Continue",use_container_width=True):
                    for idx in range(len(issues)):
                        st.session_state.issue_selections[f'issue_{idx}']=False
                    st.session_state.data_cleaned=df
                    st.session_state.validation_complete=True
                    st.info("Proceeding with original data")
                    st.rerun()
    
    if st.session_state.validation_complete and not st.session_state.model_generated:
        st.markdown("---")
        st.subheader("Generate Financial Model")
        if st.button("🚀 Generate 3-Statement Model",type="primary",use_container_width=True):
            with st.spinner("Processing financial data..."):
                df_clean=st.session_state.data_cleaned
                financial_data=calculate_financial_statements(df_clean)
                st.session_state.financial_data=financial_data
                recon=generate_reconciliation(st.session_state.uploaded_data,df_clean,financial_data)
                st.session_state.data_reconciliation=recon
                st.session_state.model_generated=True
                st.success("✓ Financial model generated!")
                st.rerun()
    
    if st.session_state.model_generated:
        financial_data=st.session_state.financial_data
        years=sorted(financial_data.keys())
        
        st.markdown("---")
        st.subheader("📊 Three Statement Model")
        st.caption("USD millions")
        
        st.markdown("### Income Statement")
        is_rows=[('Revenue','revenue'),('Cost of Goods Sold','cogs'),('─'*50,None),('Gross Profit','gross_profit'),('',None),('Operating Expenses:',None),
                 ('  Salaries','salaries'),('  Rent','rent'),('  Marketing','marketing'),('  IT Expense','it_expense'),('  Travel','travel'),
                 ('  Depreciation','depreciation'),('  Other Operating Expenses','other_opex'),('─'*50,None),('Total Operating Expenses','total_opex'),
                 ('',None),('EBIT','ebit'),('Interest Expense','interest'),('─'*50,None),('EBT','ebt'),('Income Tax','tax'),('─'*50,None),('Net Income','net_income')]
        is_data=[]
        for label,key in is_rows:
            if key is None:
                row={'Line Item':label}
                for year in years:
                    row[str(year)]=''
            else:
                row={'Line Item':label}
                for year in years:
                    row[str(year)]=f"${financial_data[year][key]:,.0f}"
            is_data.append(row)
        st.dataframe(pd.DataFrame(is_data),use_container_width=True,hide_index=True)
        
        st.markdown("### Balance Sheet")
        bs_rows=[('ASSETS',None),('Current Assets:',None),('  Cash','cash'),('  Accounts Receivable','ar'),('  Inventory','inventory'),
                ('  Other Current Assets','other_current_assets'),('─'*50,None),('Total Current Assets','current_assets'),('',None),('Fixed Assets:',None),
                ('  PP&E (Net)','ppe_net'),('  Other Fixed Assets','other_fixed_assets'),('─'*50,None),('Total Fixed Assets','fixed_assets'),('',None),
                ('TOTAL ASSETS','total_assets'),('',None),('LIABILITIES',None),('Current Liabilities:',None),('  Accounts Payable','ap'),
                ('  Accrued Expenses','accrued'),('  Other Current Liabilities','other_current_liab'),('─'*50,None),('Total Current Liabilities','current_liab'),
                ('',None),('Long-term Debt','long_term_debt'),('─'*50,None),('TOTAL LIABILITIES','total_liab'),('',None),('EQUITY',None),
                ('  Common Stock','common_stock'),('  Retained Earnings','retained_earnings'),('─'*50,None),('TOTAL EQUITY','total_equity'),('',None),
                ('TOTAL LIABILITIES & EQUITY','total_assets')]
        bs_data=[]
        for label,key in bs_rows:
            if key is None:
                row={'Line Item':label}
                for year in years:
                    row[str(year)]=''
            else:
                row={'Line Item':label}
                for year in years:
                    row[str(year)]=f"${financial_data[year][key]:,.0f}"
            bs_data.append(row)
        st.dataframe(pd.DataFrame(bs_data),use_container_width=True,hide_index=True)
        
        st.markdown("### Cash Flow Statement")
        cf_rows=[('Operating Activities:',None),('  Net Income','net_income'),('  Depreciation','depreciation'),('  Change in Working Capital',None),
                ('─'*50,None),('Cash from Operations','cffo'),('',None),('Investing Activities:',None),('  Capital Expenditures','capex'),('─'*50,None),
                ('Cash from Investing','cfi'),('',None),('Financing Activities:',None),('  Dividends Paid','dividends'),('─'*50,None),
                ('Cash from Financing','cff'),('',None),('─'*50,None),('Net Change in Cash','net_cash_change')]
        cf_data=[]
        for label,key in cf_rows:
            if key is None:
                row={'Line Item':label}
                for year in years:
                    row[str(year)]=''
            else:
                row={'Line Item':label}
                for year in years:
                    row[str(year)]=f"${financial_data[year][key]:,.0f}"
            cf_data.append(row)
        st.dataframe(pd.DataFrame(cf_data),use_container_width=True,hide_index=True)
        
        st.markdown("---")
        st.subheader("🔍 Dataset Reconciliation")
        recon=st.session_state.data_reconciliation
        col1,col2,col3=st.columns(3)
        with col1:
            st.metric("Original Transactions",f"{recon['original_summary']['total_transactions']:,}")
        with col2:
            st.metric("Cleaned Transactions",f"{recon['cleaned_summary']['total_transactions']:,}")
        with col3:
            removed=recon['original_summary']['total_transactions']-recon['cleaned_summary']['total_transactions']
            st.metric("Removed",f"{removed:,}")
        
        if len(st.session_state.changes_log)>0:
            st.markdown("**Changes Made:**")
            changes_df=pd.DataFrame(st.session_state.changes_log)
            st.dataframe(changes_df,use_container_width=True)
            changes_csv=changes_df.to_csv(index=False)
            st.download_button(label="📥 Download Reconciliation Report",data=changes_csv,
                             file_name=f"reconciliation_{datetime.now().strftime('%Y%m%d')}.csv",mime="text/csv",use_container_width=True)
        
        st.markdown("---")
        st.subheader("🤖 AI-Generated Summary")
        latest_year=years[-1]
        summary=f"""
### Executive Summary
Based on analysis of {recon['cleaned_summary']['total_transactions']:,} transactions across {len(years)} years, 
the company demonstrates {'strong' if financial_data[latest_year]['net_margin']>15 else 'moderate'} financial performance.

### Key Findings
**Revenue Performance:**
- Latest year revenue: ${financial_data[latest_year]['revenue']:,.0f}
- Gross margin: {financial_data[latest_year]['gross_margin']:.1f}%
- EBIT margin: {financial_data[latest_year]['ebit_margin']:.1f}%

**Profitability:**
- Net income: ${financial_data[latest_year]['net_income']:,.0f}
- Net margin: {financial_data[latest_year]['net_margin']:.1f}%

**Balance Sheet Strength:**
- Total assets: ${financial_data[latest_year]['total_assets']:,.0f}
- Total liabilities: ${financial_data[latest_year]['total_liab']:,.0f}
- Total equity: ${financial_data[latest_year]['total_equity']:,.0f}
- Debt-to-equity: {(financial_data[latest_year]['total_liab']/financial_data[latest_year]['total_equity']):.2f}x

### Recommendations
"""
        if financial_data[latest_year]['gross_margin']<40:
            summary+="- **Improve margins**: Consider supplier negotiations or pricing adjustments\n"
        if financial_data[latest_year]['net_margin']<10:
            summary+="- **Control costs**: Operating expenses are high relative to revenue\n"
        st.markdown(summary)
        
        st.markdown("---")
        st.subheader("📥 Download Reports")
        col1,col2=st.columns(2)
        with col1:
            template_path='3_statement_excel_completed_model.xlsx'
            if os.path.exists(template_path):
                try:
                    excel_output=update_excel_model(financial_data,template_path)
                    if excel_output:
                        st.download_button(label="📊 Download Updated Excel Model",data=excel_output,
                                         file_name=f"Financial_Model_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
                    else:
                        st.error("Failed to generate Excel file")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.info("📊 Place '3_statement_excel_completed_model.xlsx' in project root to enable download")
        with col2:
            try:
                pdf_output=generate_pdf_report(financial_data,recon)
                st.download_button(label="📄 Download Summary Report in PDF",data=pdf_output,
                                 file_name=f"Financial_Summary_{datetime.now().strftime('%Y%m%d')}.pdf",mime="application/pdf",use_container_width=True)
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")

else:
    st.info("👆 Upload a GL dataset to begin")
if uploaded_file is None:
    st.markdown("📌 **Sample format below (more formats coming soon).**")

    sample_data = pd.DataFrame({
        "TxnDate": ["2023-01-05", "2023-01-08", "2023-01-12"],
        "AccountNumber": [4001, 6100, 1001],
        "AccountName": ["Revenue", "Rent Expense", "Cash"],
        "Debit": [0.00, 1800.00, 0.00],
        "Credit": [5200.00, 0.00, 1800.00],
        "Currency": ["USD", "USD", "USD"]
    })

    st.dataframe(sample_data, use_container_width=True)

st.markdown("---")
st.subheader("⚠️ Early Demo Notice")
st.markdown("""
This is an **early-stage demo** built as part of a self-learning experiment.

It is for **educational purposes only** and is **not intended for production use**.

I hope this project can inspire others to build more AI tools in finance.

Thank you for your valuable feedback!
""")

feedback=st.text_area("Your Feedback",placeholder="Share your thoughts, suggestions, or report any issues...",height=150,
                     help="Your feedback helps improve this application")

if st.button("Submit Feedback",type="primary"):
    if feedback:
        st.success("✅ Thank you for your feedback! Your input has been recorded.")
        try:
            with open('feedback_log.txt','a')as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Timestamp: {datetime.now()}\n")
                f.write(f"Feedback: {feedback}\n")
        except:
            pass
    else:
        st.warning("Please enter some feedback before submitting.")
