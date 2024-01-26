import streamlit as st
from init import initialize_database

initialize_database()

col1, col2 = st.columns(2)

with col1:
    st.image('logo.png', width=300)

with col2:
    st.markdown(
        """
                ### Group Details
    
                Name: 🧐 DataVision
    
                ### Topic
                A Deep Learning Approach to KYC Document Verification for the Customer 
                Registration in Zimbabwean Financial Institutions
            """
    )
