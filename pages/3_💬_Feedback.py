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
        session_state['feedback_session_id'] = 1

    if status != 200:
        st.error('Connection issue on sending feedback')


st.header("Feedback Page")

if session_state.get('feedback_session_id') == 0:
    form_data = dict()

    # Heading
    st.subheader(":blue[Fill in feedback form]", divider=True)
    feedback_form = st.form(key='feedback_form')
    # Get user input
    name = feedback_form.text_input("Your Name")
    if name:
        form_data['name'] = name
        feedback_form.write(':green[Input detected]')

    email = feedback_form.text_input("Your Email")
    valid_email = False
    if email:
        valid_email = validate_email(email)
        if valid_email:
            form_data['email'] = email
            feedback_form.write(':green[Input detected]')
        else:
            feedback_form.error("Invalid email address")

    feedback = feedback_form.text_area("Your Feedback")
    if feedback:
        form_data['feedback'] = feedback
        feedback_form.write(':green[Input detected]')

    if 'name' not in form_data or 'email' not in form_data or 'feedback' not in form_data:
        feedback_form.form_submit_button('Submit for inspection')

    if 'name' in form_data and 'email' in form_data and 'feedback' in form_data:
        feedback_form.form_submit_button('Submit feedback form', on_click=save_feedback, type='primary')

if session_state.get('feedback_session_id') == 1:
    session_state['feedback_session_id'] = 0
    write_feedback = st.button('Give feedback')
