import streamlit as st

from init import HELLO_PAGE
from init import initialize_database

initialize_database()

st.write("## :blue[CHINHOYI UNIVERSITY OF TECHNOLOGY]")

col1, col2 = st.columns(2)

with col1:
    st.image('logo.jpeg', width=300)

with col2:
    st.markdown(HELLO_PAGE)
