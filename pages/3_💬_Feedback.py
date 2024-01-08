import streamlit as st
from streamlit import session_state

from helper import validate_email

from datagrip import send_feedback_email

if 'feedback_session_id' not in session_state:
    session_state['feedback_session_id'] = 0


def save_feedback():
    status, response = send_feedback_email(name, email, feedback)
    if status == 200:
        st.success('Your feedback sent via email')

    if status != 200:
        st.error('Connection issue on sending feedback')


st.header("Feedback Page")

if session_state.get('feedback_session_id') == 0:

    # Heading
    st.subheader(":blue[Fill in feedback form]", divider=True)
    # Get user input
    name = st.text_input("Your Name")
    if name:
        st.write(':green[Input detected]')

    email = st.text_input("Your Email")
    valid_email = False
    if email:
        valid_email = validate_email(email)
        if valid_email:
            st.write(':green[Input detected]')
        else:
            st.error("Invalid email address")

    feedback = st.text_area("Your Feedback")
    if name:
        st.write(':green[Input detected]')

    submit_button = st.button("Submit")

    if submit_button:
        save_feedback()
        name, email, feedback = str(), str(), str()
