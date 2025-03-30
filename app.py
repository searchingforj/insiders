import streamlit as st
from supabase import create_client
import pandas as pd

@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

st.title('SEC Form 4 J-Code Tracker')
db = init_db()

try:
    # Fetch data with your exact column names
    data = db.table('j_code_filings') \
             .select('filing_id, ticker, company_name, filing_date, filing_url') \
             .order('filing_date', desc=True) \
             .limit(50) \
             .execute()
    
    df = pd.DataFrame(data.data)
    
    if df.empty:
        st.warning("No filings found in database. Run the scraper first!")
    else:
        # Format the display
        df['filing_date'] = pd.to_datetime(df['filing_date']).dt.strftime('%Y-%m-%d %H:%M')
        df['SEC Filing'] = df['filing_url'].apply(lambda x: f'[View Filing]({x})')
        
        st.dataframe(
            df[['filing_date', 'ticker', 'company_name', 'SEC Filing']],
            column_config={
                "SEC Filing": st.column_config.LinkColumn(),
                "filing_date": "Date Filed"
            },
            hide_index=True,
            use_container_width=True
        )

except Exception as e:
    st.error("Database connection failed. Check your secrets.toml")
    st.code(f"Error details: {str(e)}")
