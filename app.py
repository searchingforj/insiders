import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
from pytz import timezone

@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def format_date(dt_str):
    """Convert UTC to Eastern Time"""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S%z")
        return dt.astimezone(timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S ET')
    except:
        return dt_str

st.set_page_config(page_title="SEC J-Code Tracker", layout="wide")
db = init_db()

st.title("🔍 SEC Form 4 J-Code Transactions")
st.caption("Tracking insider transactions with 'J' coded transactions")

try:
    data = db.table('j_code_filings') \
             .select('filing_id, ticker, company_name, filing_date, transaction_date, filing_url') \
             .order('filing_date', desc=True) \
             .limit(100) \
             .execute()

    df = pd.DataFrame(data.data)
    
    if df.empty:
        st.warning("No filings found. Run the scraper first!")
    else:
        # Format dates
        df['Filed Date'] = df['filing_date'].apply(format_date)
        df['Trade Date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d')
        
        # Display with proper link formatting
        st.dataframe(
            df[['Filed Date', 'Trade Date', 'ticker', 'company_name', 'filing_url']],
            column_config={
                "filing_url": st.column_config.LinkColumn(
                    "SEC Filing",
                    display_text="📄 View",
                    help="View official SEC filing"
                ),
                "ticker": "Symbol",
                "company_name": "Company"
            },
            hide_index=True,
            use_container_width=True,
            height=700
        )

except Exception as e:
    st.error("Database connection failed")
    st.code(f"Error: {str(e)}")
