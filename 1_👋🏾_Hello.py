import streamlit as st

from init import initialize_database

# initialise database
if 'database ready' not in st.session_state:
    initialize_database()
    st.session_state['database ready'] = 1

st.write("## :blue[CHINHOYI UNIVERSITY OF TECHNOLOGY]")

col1, col2 = st.columns(2)

with col1:
    st.image('logo.jpeg', width=300)

with col2:
    st.markdown(
        """
                ### Student Details
    
                - Name: Benedict T. Dlamini
                - Student Number: C22148273B
                - Programme: MSC. Big Data Analytics
    
                ### Topic
                A Deep Learning Approach to KYC Document Verification for the Customer 
                Registration in Zimbabwean Financial Institutions: Case of Old Mutual Zimbabwe
            """
    )
