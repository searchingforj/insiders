import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# Initialize Supabase connection
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# App configuration
st.set_page_config(page_title="SEC Form 4 J-Code Tracker", layout="wide")
db = init_db()

# Custom CSS for better table display
st.markdown("""
<style>
    .dataframe th {
        background-color: #2c3e50 !important;
        color: white !important;
    }
    .dataframe td {
        font-size: 14px;
    }
    a {
        color: #3498db !important;
    }
</style>
""", unsafe_allow_html=True)

# Main app
st.title("📈 SEC Form 4 J-Code Transactions")
st.caption("Tracking insider transactions with 'J' transaction codes")

with st.container():
    col1, col2 = st.columns([3,1])
    with col1:
        st.markdown("""
        **Key Fields:**
        - **Trade Date**: When the transaction occurred (from XML `periodOfReport`)
        - **Filed Date**: When SEC processed the filing (from RSS `updated`)
        - **Ticker**: Company stock symbol (from XML `issuerTradingSymbol`)
        """)
    with col2:
        st.metric("Total Filings", 
                 db.table('j_code_filings')
                  .select('*', count='exact')
                  .execute().count)

# Data display
try:
    # Fetch data with explicit column selection
    data = db.table('j_code_filings') \
             .select('filing_id, ticker, company_name, filing_date, transaction_date, filing_url') \
             .order('filing_date', desc=True) \
             .limit(200) \
             .execute()

    df = pd.DataFrame(data.data)
    
    if df.empty:
        st.warning("No filings found in database. Run the scraper first!")
    else:
        # Format columns
        df['Filed Date'] = pd.to_datetime(df['filing_date']).dt.strftime('%Y-%m-%d %H:%M')
        df['Trade Date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d')
        df['SEC Filing'] = df['filing_url'].apply(lambda x: f'[View]({x})')
        
        # Display interactive table
        st.dataframe(
            df[['Trade Date', 'Filed Date', 'ticker', 'company_name', 'SEC Filing']],
            column_config={
                "SEC Filing": st.column_config.LinkColumn(display_text="🔗"),
                "ticker": "Symbol",
                "company_name": "Company"
            },
            hide_index=True,
            use_container_width=True,
            height=700
        )
        
        # Download option
        csv = df[['Trade Date', 'Filed Date', 'ticker', 'company_name', 'filing_url']].to_csv(index=False)
        st.download_button(
            "📥 Export to CSV",
            data=csv,
            file_name='j_code_filings.csv',
            mime='text/csv'
        )

except Exception as e:
    st.error("Failed to load data. Check your database connection.")
    st.code(f"Error details: {str(e)}")
