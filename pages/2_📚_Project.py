from datetime import date
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import streamlit as st
from PIL import Image
from pandas import DataFrame
from streamlit import session_state

from database import ApplicationForm
from database import UploadedDocument
from helper import convert_and_resize
from helper import convert_from_pdf_to_png
from helper import cut_image
from helper import get_end_of_month
from helper import read_ocr_results
from helper import read_pickle_file
from helper import save_pdf_file
from helper import validate_form_data
from helper import write_dict_to_pickle
from init import PAGE_HELP
from middleware import delete_model_record_by_id
from middleware import get_model_details_by_filter
from middleware import new_record
from middleware import run_facial_recognition_similarity_model
from middleware import run_object_detection_model
from middleware import run_optical_character_recognition_model
from middleware import update_model_record_by_session_id

# Session variables
# # Generate session id
if 'session_id' not in session_state:
    session_state['session_id'] = str(uuid4())

# # Generate navigation id
if 'navigation_id' not in session_state:
    session_state['navigation_id'] = 0

# # Generate navigation id
if 'poi_document' not in session_state:
    session_state['poi_document'] = 0

# # Generate navigation id
if 'recent_pic' not in session_state:
    session_state['recent_pic'] = 0

# #

st.title('Customer Registration App')

# Create the navigation bar using st.sidebar
NAV_LIST = [
    "Application Form",
    "Proof of Identity",
    "Face Identity",
    "Proof of residency",
    "Proof of income",
    "KYC Document verification report"
]
if 0 <= session_state.get('navigation_id') <= len(NAV_LIST):
    nav_selection = st.sidebar.radio("Project Steps", NAV_LIST, index=int(session_state.get('navigation_id')))


# Button callbacks
def restart():
    filter_details = {'session_id': session_state.get('session_id')}
    # Get Application form data
    application_form_details_list = get_model_details_by_filter(ApplicationForm, filter_details)
    # Get Documents data
    documents_details_list = get_model_details_by_filter(UploadedDocument, filter_details)

    # Delete Application Form Records
    for _form in application_form_details_list:
        delete_model_record_by_id(ApplicationForm, _form.get('id'))

    # Delete Uploaded Document Records
    for _document in documents_details_list:
        delete_model_record_by_id(UploadedDocument, _document.get('id'))

    st.success('All data and documents provided cleared. Start afresh')

    session_state['navigation_id'] = 0


# # Application Form
def application_form_button_clicked(form_data: dict):
    unavailable_fields = validate_form_data(form_data)
    quoted_list_unavailable_fields = ['"{}"'.format(word.capitalize()) for word in unavailable_fields]

    if unavailable_fields:
        st.error('Please do not leave {} fields blank'.format(' '.join(quoted_list_unavailable_fields)))
        session_state['navigation_id'] = 0

    else:
        st.success('Application form data submitted successfully!')
        new_record(ApplicationForm, form_data)
        session_state['navigation_id'] = 1


def back_to_application_form_clicked():
    session_state['navigation_id'] = 0.5


def continue_with_application_form_clicked():
    session_state['navigation_id'] = 1


def go_to_application_form_clicked():
    filter_details = {'session_id': session_state.get('session_id')}
    application_details_list = get_model_details_by_filter(ApplicationForm, filter_details)
    application_details = application_details_list[0]

    delete_model_record_by_id(ApplicationForm, application_details.get('id'))

    session_state['navigation_id'] = 0


# # Proof of ID document
def poi_document_button_clicked(_poi_document_path: str, _poi_document_name: str, _poi_document_type: str):
    # Run OD Model
    output_filepath_od = run_object_detection_model(_poi_document_path, _poi_document_name)

    # Run OCR Model
    _poi_document_ocr_dict, output_filepath_ocr = run_optical_character_recognition_model(
        _poi_document_path, _poi_document_name
    )

    _poi_ocr_result_file_path = write_dict_to_pickle(_poi_document_ocr_dict, 'ocr', _poi_document_name)

    _filter_dict = {
        'session_id': session_state.get('session_id'),
        'type': _poi_document_type
    }
    update_data = {
        'poi_image_path_od': output_filepath_od,
        'poi_image_path_ocr': output_filepath_ocr,
        'predictions': {'ocr': _poi_ocr_result_file_path}
    }
    update_model_record_by_session_id(UploadedDocument, _filter_dict, update_data)

    # Navigate
    session_state['navigation_id'] = 1.5


# #
def upload_another_poi_document():
    filter_data = {'session_id': session_state.get('session_id'), 'type': 'poi_document'}
    _poi_document_details_list = get_model_details_by_filter(UploadedDocument, filter_data)
    _poi_document_details = _poi_document_details_list[0]

    delete_model_record_by_id(UploadedDocument, _poi_document_details.get('id'))
    st.warning('Upload another Proof of Identity document')
    session_state['navigation_id'] = 1


# #
def collect_fr_images_button_clicked():
    # Navigate
    session_state['navigation_id'] = 2


def discard_poi_recent_pic_button_clicked(record_id: int):
    delete_model_record_by_id(UploadedDocument, record_id)

    # Navigate
    session_state['navigation_id'] = 2


def submit_poi_recent_pics_clicked(_poi_document_details: dict, _recent_pictures_list: list):
    # Get POI document details
    _poi_document_image_id = _poi_document_details.get('id')
    _poi_document_path = _poi_document_details.get('uploaded_image_path')

    # Pre-allocate variable memory
    least_distance = 999999
    least_distance_image_id = int()
    least_distance_image_path = str()
    least_distance_image_result = dict()

    # Iterate over recent pictures list
    image_1_output_path = str()
    for image_details in _recent_pictures_list:
        image_id = image_details.get('id')
        distance, image_1_output_path, image_2_output_path, verification_details = \
            run_facial_recognition_similarity_model(
                _poi_document_details, image_details
            )

        if distance < least_distance:
            least_distance_image_id = image_id
            least_distance_image_path = image_2_output_path
            least_distance = distance
            least_distance_image_result = verification_details

    # Delete other images
    all_recent_pic_ids = [picture.get('id') for picture in _recent_pictures_list]

    for picture_id in all_recent_pic_ids:
        if picture_id != least_distance_image_id:
            delete_model_record_by_id(UploadedDocument, picture_id)

    # POI document FR record
    _filter_dict_poi_fr = {'id': _poi_document_image_id}
    _update_data_poi_fr = {'poi_image_path_fr': image_1_output_path}
    update_model_record_by_session_id(UploadedDocument, _filter_dict_poi_fr, _update_data_poi_fr)

    # Update selected recent picture record
    _filter_dict_fr = {'id': least_distance_image_id}
    _update_data_fr = {
        'po_recent_image_path_fr': least_distance_image_path,
        'predictions': least_distance_image_result
    }
    update_model_record_by_session_id(UploadedDocument, _filter_dict_fr, _update_data_fr)

    # Navigate
    session_state['navigation_id'] = 2.5


def back_to_selfies():
    filter_data = {'session_id': session_state.get('session_id'), 'type': 'poi_recent_pic'}
    _po_recent_document_details_list = get_model_details_by_filter(UploadedDocument, filter_data)
    _po_recent_document_details = _po_recent_document_details_list[0]

    delete_model_record_by_id(UploadedDocument, _po_recent_document_details.get('id'))
    st.warning('Upload another set of selfie pictures')

    # Navigate
    session_state['navigation_id'] = 2


def proceed_to_por():
    # Navigate
    session_state['navigation_id'] = 3


def back_to_face_identity():
    # Navigate
    session_state['navigation_id'] = 2.5


def submit_por_document(_por_document_path: str, _por_document_type: str, _por_document_name: st):
    # Run OCR model
    _por_document_ocr_dict, output_filepath_ocr = run_optical_character_recognition_model(
        _por_document_path, _por_document_name
    )

    # Save results
    _por_ocr_result_file_path = write_dict_to_pickle(_por_document_ocr_dict, 'ocr', _por_document_name)

    _filter_dict = {
        'session_id': session_state.get('session_id'),
        'type': _por_document_type
    }
    update_data = {
        'por_image_path_ocr': output_filepath_ocr,
        'predictions': {'ocr': _por_ocr_result_file_path}
    }
    update_model_record_by_session_id(UploadedDocument, _filter_dict, update_data)

    # Navigate
    session_state['navigation_id'] = 3.5


def upload_another_por_document():
    filter_data = {'session_id': session_state.get('session_id'), 'type': 'por_document'}
    _por_document_details_list = get_model_details_by_filter(UploadedDocument, filter_data)
    _por_document_details = _por_document_details_list[0]

    delete_model_record_by_id(UploadedDocument, _por_document_details.get('id'))
    st.warning('Upload another Proof of Residency document')
    session_state['navigation_id'] = 3


def proceed_to_poin():
    # Navigate
    session_state['navigation_id'] = 4


def back_to_por():
    # Navigate
    session_state['navigation_id'] = 3.5


def submit_poin_document(
        _poin_document_1_path: str,
        _poin_document_1_name: str,
        _poin_document_2_path: str,
        _poin_document_2_name: str,
        _poin_document_type: str
):
    # Run OCR model
    _poin_document_ocr_1_dict, output_filepath_1_ocr = run_optical_character_recognition_model(
        _poin_document_1_path, _poin_document_1_name
    )
    _poin_document_ocr_2_dict, output_filepath_2_ocr = run_optical_character_recognition_model(
        _poin_document_2_path, _poin_document_2_name
    )

    # Save results
    _poin_ocr_result_file_1_path = write_dict_to_pickle(_poin_document_ocr_1_dict, 'ocr', _poin_document_1_name)
    _poin_ocr_result_file_2_path = write_dict_to_pickle(_poin_document_ocr_2_dict, 'ocr', _poin_document_2_name)

    # Filter
    _filter_dict_1 = {
        'session_id': session_state.get('session_id'),
        'name': _poin_document_1_name,
        'type': _poin_document_type
    }
    _filter_dict_2 = {
        'session_id': session_state.get('session_id'),
        'name': _poin_document_2_name,
        'type': _poin_document_type
    }

    # Update data
    update_data_1 = {
        'poin_image_path_ocr': output_filepath_1_ocr,
        'predictions': {'ocr': _poin_ocr_result_file_1_path}
    }
    update_data_2 = {
        'poin_image_path_ocr': output_filepath_2_ocr,
        'predictions': {'ocr': _poin_ocr_result_file_2_path}
    }

    # Update model
    update_model_record_by_session_id(UploadedDocument, _filter_dict_1, update_data_1)
    update_model_record_by_session_id(UploadedDocument, _filter_dict_2, update_data_2)

    # Navigate
    session_state['navigation_id'] = 4.5


def upload_another_poin_document():
    filter_data = {'session_id': session_state.get('session_id'), 'type': 'poin_document'}
    _por_document_details_list = get_model_details_by_filter(UploadedDocument, filter_data)

    for item in _por_document_details_list:
        delete_model_record_by_id(UploadedDocument, item.get('id'))

    st.warning('Upload another Proof of Income document')

    # Navigation
    session_state['navigation_id'] = 4


def get_kyc_report():
    # Navigate
    session_state['navigation_id'] = 5


# Display content based on the selected navigation poi_document_type
if session_state.get('navigation_id') == 0:
    with st.form(key='my_form'):
        # Heading
        st.subheader(":blue[Fill in application form]", divider=True, help=PAGE_HELP)
        # Form variables
        date_today = date.today()  # Get current date
        date_18_years_ago = date_today - timedelta(days=18 * 365)  # Subtract 18 years from today's date
        date_18_years_ago = get_end_of_month(date_18_years_ago)
        date_100_years_ago = date_today - timedelta(days=100 * 365)  # Subtract 100 years from today's date
        date_100_years_ago = get_end_of_month(date_100_years_ago)
        # Form design
        name_s = st.text_input('Given Name(s)', placeholder='Type your given names here ...')
        surname = st.text_input('Surname', placeholder='Type your surname here ...')
        gender = st.selectbox(
            'Select your gender',
            ('Male', 'Female'),
            placeholder="Click dropdown arrow and choose an poi_document_type"
        )
        date_of_birth = st.date_input(
            'Date of birth',
            min_value=date_100_years_ago,
            value=date_18_years_ago,
            max_value=date_18_years_ago,
            format='YYYY-MM-DD'
        )
        address = st.text_area('Residential Address', placeholder="Type your the address of where you reside here ...")
        money_access = st.selectbox(
            'Do you have a bank account or mobile wallet',
            ('Yes', 'No'),
            placeholder="Click dropdown arrow and choose an poi_document_type"
        )
        created_time = datetime.now()
        application_data = {
            'session_id': session_state.get('session_id'),
            'names': name_s,
            'surname': surname,
            'gender': gender,
            'dob': date_of_birth.strftime("%Y-%m-%d"),
            'money_access': money_access,
            'created': created_time.strftime("%Y-%m-%d")
        }
        st.form_submit_button('Submit', on_click=application_form_button_clicked, args=(application_data,))

if session_state.get('navigation_id') == 0.5:
    st.warning(
        '#### If you navigate back to the :blue[Application Form] page, you will have to fill in the application '
        'form again'
    )

    col1, col2 = st.columns(2)

    with col1:
        st.button(
            'Continue with Proof Of Identity',
            use_container_width=True,
            on_click=continue_with_application_form_clicked
        )

    with col2:
        st.button(
            'Go to Application form page',
            type='primary',
            use_container_width=True,
            on_click=go_to_application_form_clicked
        )

if session_state.get('navigation_id') == 1:

    # Identity Document
    st.subheader(":blue[Upload Identity Document]", divider=True, help='Up')
    st.button('Back', on_click=back_to_application_form_clicked)
    # Select Proof of identity document type
    poi_document_option = st.selectbox(
        ':blue[Select the type of document you are have]',
        ('Zimbabwean National ID', 'Zimbabwean Issued Passport'),
        placeholder="Click dropdown arrow and choose",
        index=None
    )

    if poi_document_option:
        st.write(':green[You selected {}]'.format(poi_document_option))

    # Upload image file
    poi_doc_uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

    # # When POI document is uploaded
    if poi_doc_uploaded_file is not None:
        # Get file extension
        file_extension = Path(poi_doc_uploaded_file.name).suffix

        # Read the image file
        poi_doc_uploaded_image = Image.open(poi_doc_uploaded_file)

        # Convert image to png, then resize
        poi_document_name, poi_document_path = convert_and_resize(
            poi_doc_uploaded_image, session_state.get('session_id'), 'poi_document'
        )

        poi_document_details = {
            'session_id': session_state.get('session_id'),
            'name': poi_document_name,
            'uploaded_poi_image_path': poi_document_path,
            'category': 'poi',
            'type': 'poi_document',
            'option': poi_document_option
        }

        # Save information to database
        new_record(UploadedDocument, poi_document_details)

        # Display image
        st.image(poi_document_path)

        # Submit image ot OD model
        st.button(
            'Submit my {}'.format(poi_document_option),
            use_container_width=True,
            on_click=poi_document_button_clicked,
            args=(poi_document_path, poi_document_name, 'poi_document')
        )

if session_state.get('navigation_id') == 1.5:
    # Identity Document
    st.subheader(":blue[Identity Document Authentication]", divider=True, help='Up')
    st.button('Upload a different document', on_click=upload_another_poi_document)
    # Get POI Document Details
    poi_document_details_list = get_model_details_by_filter(
        UploadedDocument, {'session_id': session_state.get('session_id'), 'type': 'poi_document'}
    )
    poi_document_details = poi_document_details_list[0]
    poi_document_od_predicted_path = poi_document_details.get('poi_image_path_od')
    poi_document_ocr_predicted_path = poi_document_details.get('poi_image_path_ocr')
    poi_document_ocr_pickle = poi_document_details.get('predictions')

    # Read data
    poi_document_ocr_dict = read_pickle_file(poi_document_ocr_pickle.get('ocr'))
    poi_document_ocr_results = read_ocr_results(poi_document_ocr_dict)
    poi_document_ocr_df = DataFrame(
        {'text': poi_document_ocr_results['text'], 'score': poi_document_ocr_results['score']}
    )

    # Display OD Predictions
    st.image(poi_document_od_predicted_path)

    st.subheader(":blue[Identity Document Details]", divider=True, help='Up')

    # Display OCR Predictions
    col1, col2 = st.columns(2)

    with col1:
        st.image(poi_document_ocr_predicted_path)

    with col2:
        st.table(poi_document_ocr_df)

    # Proceed to
    st.button(
        'Proceed to Facial Recognition Verification',
        use_container_width=True,
        on_click=collect_fr_images_button_clicked
    )

if session_state.get('navigation_id') == 2:

    filter_dict_recent_pics = {'session_id': session_state.get('session_id'), 'type': 'poi_recent_pic'}
    recent_pictures_list = get_model_details_by_filter(UploadedDocument, filter_dict_recent_pics)
    number_of_recent_pictures = len(recent_pictures_list)

    # Recent Picture
    st.subheader(
        ":blue[Selfies for verification ({} out of 3 pictures taken)]".format(number_of_recent_pictures),
        divider=True,
        help='Up'
    )

    # Get photos
    if number_of_recent_pictures < 3:
        poi_recent_picture = st.camera_input('Take face portrait selfie')

        if poi_recent_picture:
            # Read the image file
            poi_recent_picture_image = Image.open(poi_recent_picture)

            # Convert image to png, then resize
            poi_recent_picture_name, poi_recent_picture_path = convert_and_resize(
                poi_recent_picture_image,
                session_state.get('session_id'),
                'poi_recent_pic_{}'.format(number_of_recent_pictures + 1)
            )

            poi_recent_picture_details = {
                'session_id': session_state.get('session_id'),
                'name': poi_recent_picture_name,
                'uploaded_po_recent_image_path': poi_recent_picture_path,
                'category': 'poi',
                'type': 'poi_recent_pic'
            }

            # Save information to database

            new_record(UploadedDocument, poi_recent_picture_details)

    col1, col2, col3 = st.columns(3)

    if number_of_recent_pictures >= 1:
        pic_1_details = recent_pictures_list[0]
        pic_1_image_id = pic_1_details.get('id')
        pic_1_image_path = pic_1_details.get('uploaded_po_recent_image_path')
        with col1:
            st.write("Selfie 1")
            st.image(pic_1_image_path)
            st.button(
                'Discard',
                key=1,
                type='primary',
                use_container_width=True,
                on_click=discard_poi_recent_pic_button_clicked,
                args=(pic_1_image_id,)
            )

    if number_of_recent_pictures >= 2:
        pic_2_details = recent_pictures_list[1]
        pic_2_image_id = pic_2_details.get('id')
        pic_2_image_path = pic_2_details.get('uploaded_po_recent_image_path')
        with col2:
            st.write("Selfie 2")
            st.image(pic_2_image_path)
            st.button(
                'Discard',
                key=2,
                type='primary',
                use_container_width=True,
                on_click=discard_poi_recent_pic_button_clicked,
                args=(pic_2_image_id,)
            )

    if number_of_recent_pictures == 3:
        pic_3_details = recent_pictures_list[2]
        pic_3_image_id = pic_3_details.get('id')
        pic_3_image_path = pic_3_details.get('uploaded_po_recent_image_path')
        with col3:
            st.write("Selfie 3")
            st.image(pic_3_image_path)
            st.button(
                'Discard',
                key=3,
                type='primary',
                use_container_width=True,
                on_click=discard_poi_recent_pic_button_clicked,
                args=(pic_3_image_id,)
            )

    if number_of_recent_pictures == 3:
        filter_dict_poi_document = {'session_id': session_state.get('session_id'), 'type': 'poi_document'}
        poi_document_details_list = get_model_details_by_filter(UploadedDocument, filter_dict_poi_document)
        poi_document_details = poi_document_details_list[0]
        st.button(
            'Submit for verification',
            use_container_width=True,
            on_click=submit_poi_recent_pics_clicked,
            args=(poi_document_details, recent_pictures_list,)
        )

if session_state.get('navigation_id') == 2.5:
    # Get POI document details
    poi_document_filter = {'session_id': session_state.get('session_id'), 'type': 'poi_document'}
    poi_document_details_list = get_model_details_by_filter(UploadedDocument, poi_document_filter)
    poi_document_details = poi_document_details_list[0]

    # Identity Document
    st.subheader(
        ":blue[Selfie Face Similarity to {} Face]".format(poi_document_details.get('option')),
        divider=True,
        help='Up'
    )

    # Get recent pic details
    poi_recent_picture_filter = {'session_id': session_state.get('session_id'), 'type': 'poi_recent_pic'}
    poi_recent_picture_details_list = get_model_details_by_filter(UploadedDocument, poi_recent_picture_filter)
    poi_recent_picture_details = poi_recent_picture_details_list[0]

    st.button('Take another set of selfies', on_click=back_to_selfies)

    #
    col1, col2 = st.columns(2)

    with col1:
        poi_recent_picture_predictions = poi_recent_picture_details.get('predictions')
        poi_recent_picture_distance = poi_recent_picture_predictions.get('distance')
        st.image(poi_recent_picture_details.get('po_recent_image_path_fr'))

    with col2:
        st.image(poi_document_details.get('poi_image_path_fr'))

    if poi_recent_picture_distance < 0.4:
        st.info('The faces have a {} difference, which is below the acceptable threshold'.format(
            round(poi_recent_picture_distance, 2))
        )
        st.button('Proceed to Proof of residency', use_container_width=True, on_click=proceed_to_por)

    else:
        st.error('The faces have a huge difference. Please take another set of selfies to verify with')

if session_state.get('navigation_id') == 3:
    # Identity Document
    st.subheader(
        ":blue[Proof Of Residency Document]",
        divider=True,
        help='Provide your Proof of residency document here. ZETDC invoice or Municipality statement'
    )
    st.button('Back to face verification', on_click=back_to_face_identity)

    # Select Proof of identity document type
    por_document_option = st.selectbox(
        ':blue[Select the type of document you are have]',
        ('ZETDC Invoice', 'Municipality Statement'),
        placeholder="Click dropdown arrow and choose",
        index=None
    )

    if por_document_option:
        st.write(':green[You selected {}]'.format(por_document_option))

    # Upload document
    por_doc_uploaded_file = st.file_uploader("Choose a file", type=["jpg", "jpeg", "png", "pdf"])

    if por_doc_uploaded_file:
        # Read the image file
        por_doc_uploaded_image = Image.open(por_doc_uploaded_file)

        # Convert image to png, then resize
        por_document_name, por_document_path = convert_and_resize(
            por_doc_uploaded_image, session_state.get('session_id'), 'por_document'
        )

        por_picture_details = {
            'session_id': session_state.get('session_id'),
            'name': por_document_name,
            'uploaded_por_image_path': por_document_path,
            'category': 'por',
            'type': 'por_document',
            'option': por_document_option
        }

        new_record(UploadedDocument, por_picture_details)

        # Display image
        st.image(por_document_path)

        st.button(
            'Submit',
            use_container_width=True,
            on_click=submit_por_document,
            args=(por_document_path, 'por_document', por_document_name)
        )

if session_state.get('navigation_id') == 3.5:
    # Identity Document
    st.subheader(
        ":blue[Proof Of Residency Document]",
        divider=True,
        help='Proof of residency verification'
    )
    st.button('Upload another Proof of Residency document', on_click=upload_another_por_document)

    por_document_filter = {'session_id': session_state.get('session_id'), 'type': 'por_document'}
    poi_document_details_list = get_model_details_by_filter(UploadedDocument, por_document_filter)
    poi_document_details = poi_document_details_list[0]

    #
    por_document_ocr_predicted_path = poi_document_details.get('por_image_path_ocr')
    por_document_ocr_pickle = poi_document_details.get('predictions')
    por_document_ocr_dict = read_pickle_file(por_document_ocr_pickle.get('ocr'))
    por_document_ocr_results = read_ocr_results(por_document_ocr_dict)
    poi_document_ocr_df = DataFrame(
        {'text': por_document_ocr_results['text'], 'score': por_document_ocr_results['score']}
    )

    st.write('### Detected on uploaded document')
    st.image(por_document_ocr_predicted_path)

    st.write('### Detected text in detail')
    st.table(poi_document_ocr_df)

    st.button('Proceed to Proof of income', use_container_width=True, on_click=proceed_to_poin)

if session_state.get('navigation_id') == 4:
    # Identity Document
    st.subheader(
        ":blue[Proof Of Income Document]",
        divider=True,
        help='Proof of residency verification'
    )
    st.button('Back to Proof of residency verification', on_click=back_to_por)

    # Select Proof of identity document type
    poin_document_option = st.selectbox(
        ':blue[Select the type of document you are have]',
        ('Bank Statement', 'Employment Confirmation Letter', 'Payslip'),
        placeholder="Click dropdown arrow and choose",
        index=None
    )

    if poin_document_option:
        st.write(':green[You selected {}]'.format(poin_document_option))

    # Upload document
    poin_doc_uploaded_file = st.file_uploader("Choose a file", type=["jpg", "jpeg", "png", "pdf"])

    if poin_doc_uploaded_file:

        # Check file extension
        if poin_doc_uploaded_file.name.endswith('pdf'):
            poin_document_pdf_path, por_document_name = save_pdf_file(
                session_state.get('session_id'),
                'poin',
                poin_doc_uploaded_file
            )
            pages, poin_document_path = convert_from_pdf_to_png(poin_document_pdf_path, por_document_name)

            if len(pages) == 1:
                top_image_path, bottom_image_path, top_image_name, bottom_image_name = cut_image(
                    poin_document_path, por_document_name
                )
                st.image(top_image_path)
                st.image(bottom_image_path)

                poin_document_1_details = {
                    'session_id': session_state.get('session_id'),
                    'name': top_image_name,
                    'uploaded_poin_image_path': top_image_path,
                    'category': 'poin',
                    'type': 'poin_document',
                    'option': poin_document_option
                }
                poin_document_2_details = {
                    'session_id': session_state.get('session_id'),
                    'name': bottom_image_name,
                    'uploaded_poin_image_path': bottom_image_path,
                    'category': 'poin',
                    'type': 'poin_document',
                    'option': poin_document_option
                }

                new_record(UploadedDocument, poin_document_1_details)
                new_record(UploadedDocument, poin_document_2_details)

                st.button(
                    'Submit',
                    use_container_width=True,
                    on_click=submit_poin_document,
                    args=(top_image_path, top_image_name, bottom_image_path, bottom_image_name, 'poin_document')
                )

        else:
            # Read the image file
            por_doc_uploaded_image = Image.open(poin_doc_uploaded_file)

            # Convert image to png, then resize
            poin_document_name, poin_document_path = convert_and_resize(
                por_doc_uploaded_image, session_state.get('session_id'), 'poin_document'
            )

            poin_document_details = {
                'session_id': session_state.get('session_id'),
                'name': poin_document_name,
                'uploaded_por_image_path': poin_document_path,
                'category': 'poin',
                'type': 'poin_document',
                'option': poin_document_option
            }

            new_record(UploadedDocument, poin_document_details)

            # Display image
            st.image(poin_document_path)

            st.button(
                'Submit',
                use_container_width=True
            )

if session_state.get('navigation_id') == 4.5:
    # Identity Document
    st.subheader(
        ":blue[Proof Of Income Verification]",
        divider=True,
        help='Proof of residency verification'
    )
    st.button('Upload another Proof of income document', on_click=upload_another_poin_document)

    poin_document_filter = {'session_id': session_state.get('session_id'), 'type': 'poin_document'}
    poin_document_details_list = get_model_details_by_filter(UploadedDocument, poin_document_filter)

    for document in poin_document_details_list:
        #
        poin_document_ocr_predicted_path = document.get('poin_image_path_ocr')
        poin_document_ocr_pickle = document.get('predictions')
        poin_document_ocr_dict = read_pickle_file(poin_document_ocr_pickle.get('ocr'))
        poin_document_ocr_results = read_ocr_results(poin_document_ocr_dict)
        poi_document_ocr_df = DataFrame(
            {'text': poin_document_ocr_results['text'], 'score': poin_document_ocr_results['score']}
        )
        st.image(poin_document_ocr_predicted_path)

    st.button('Get KYC document verification report', use_container_width=True, on_click=get_kyc_report)

if session_state.get('navigation_id') == 5:
    # Identity Document
    st.subheader(
        ":blue[KYC document verification report for customer]",
        divider=True,
        help='Proof of residency verification'
    )

    col1, col2, col3 = st.columns(3)
    with col3:
        st.button('Start afresh', use_container_width=True, type='primary', on_click=restart)

    #
    st.write('### Proof of Identity ✅')
    st.write('### Proof of Residency ✅')
    st.write('### Proof of Income ✅')
