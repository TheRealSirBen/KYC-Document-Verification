from init import PAGE_HELP
from os import environ

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
from database import AnalysisResults

from datagrip import upload_file_to_cloud_storage
from datagrip import delete_file_from_cloud_storage
from datagrip import facial_extraction_model

from helper import convert_and_resize
from helper import convert_from_pdf_to_png
from helper import cut_image
from helper import get_end_of_month
from helper import read_ocr_results
from helper import read_pickle_file
from helper import save_pdf_file
from helper import validate_form_data
from helper import write_dict_to_pickle
from helper import get_row_average_mid_point
from helper import restructured_detected_text
from helper import get_national_id_detected_text
from helper import check_text_similarity
from helper import convert_coordinates
from helper import draw_bounding_box_on_image
from helper import convert_date_format
from helper import get_national_id_detected_features
from helper import get_kyc_document_detected_text
from helper import get_list_unique_elements
from helper import delete_files_by_session_id

from middleware import delete_model_record_by_id
from middleware import get_model_details_by_filter
from middleware import new_record
from middleware import run_facial_recognition_similarity_model
from middleware import run_object_detection_model
from middleware import run_optical_character_recognition_model
from middleware import update_model_record_by_session_id
from middleware import delete_session_files_from_cloud_storage

IMAGE_TYPES = environ['IMAGE_TYPES']
IMAGE_TYPES = IMAGE_TYPES.split('-')

# Report Variables
poin_document_text_detection_analysis_df = DataFrame()

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

st.header('Customer Registration App')

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
    session_id = session_state.get('session_id')
    filter_details = {'session_id': session_id}

    # Get Application form data
    _application_form_details_list = get_model_details_by_filter(ApplicationForm, filter_details)

    # Get Documents data
    documents_details_list = get_model_details_by_filter(UploadedDocument, filter_details)

    # Get Analysis Results data
    analysis_results_details_list = get_model_details_by_filter(AnalysisResults, filter_details)

    # Delete Application Form Records
    for _form in _application_form_details_list:
        delete_model_record_by_id(ApplicationForm, _form.get('id'))

    # Delete Uploaded Document Records
    for _document in documents_details_list:
        delete_model_record_by_id(UploadedDocument, _document.get('id'))

    # Delete Analysis Results Records
    for _analysis_results in analysis_results_details_list:
        delete_model_record_by_id(AnalysisResults, _analysis_results.get('id'))

    # Delete all session locally stored images
    delete_files_by_session_id(session_id, 'images')
    delete_files_by_session_id(session_id, 'pdfs')
    delete_files_by_session_id(session_id, 'predictions')

    # Delete all session cloud stored images
    delete_session_files_from_cloud_storage(session_id)

    st.success(
        'All data and documents provided have been deleted and clearednfrom the system. Kindly provide feedback on '
        'the 💬 Feedback page. '
        'You are also free to restart the process'
    )

    session_state['navigation_id'] = 0


# # Application Form
def application_form_button_clicked():
    unavailable_fields = validate_form_data(form_data)
    quoted_list_unavailable_fields = ['"{}"'.format(word.capitalize()) for word in unavailable_fields]

    if unavailable_fields:
        st.error('Please do not leave {} fields blank'.format(' '.join(quoted_list_unavailable_fields)))
        session_state['navigation_id'] = 0

    if not unavailable_fields:
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
    _poi_document_od_dict, output_filepath_od = run_object_detection_model(_poi_document_path, _poi_document_name)

    # Run OCR Model
    _poi_document_ocr_dict, output_filepath_ocr = run_optical_character_recognition_model(
        _poi_document_path, _poi_document_name
    )

    _poi_od_result_file_path = write_dict_to_pickle(_poi_document_od_dict, 'od', _poi_document_name)
    _poi_ocr_result_file_path = write_dict_to_pickle(_poi_document_ocr_dict, 'ocr', _poi_document_name)

    _filter_dict = {
        'session_id': session_state.get('session_id'),
        'type': _poi_document_type
    }
    update_data = {
        'poi_image_path_od': output_filepath_od,
        'poi_image_path_ocr': output_filepath_ocr,
        'predictions': {'ocr': _poi_ocr_result_file_path, 'od': _poi_od_result_file_path}
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
    all_recent_pic_ids = [picture.get('id') for picture in _recent_pictures_list]

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

        if distance == 999999:
            st.warning('At least one of the Selfies did not a clear face. Please retake')
            least_distance = distance
            break

        if distance < least_distance:
            least_distance_image_id = image_id
            least_distance_image_path = image_2_output_path
            least_distance = distance
            least_distance_image_result = verification_details

    if least_distance == 999999:
        # Delete all images
        for picture_id in all_recent_pic_ids:
            delete_model_record_by_id(UploadedDocument, picture_id)

        # Navigate
        session_state['navigation_id'] = 2

    if least_distance != 999999:
        # Delete other images
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


def submit_image_for_text_analysis(_por_document_path: str, _por_document_type: str, _por_document_name: str):
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

    for _por_document_details in _por_document_details_list:
        delete_model_record_by_id(UploadedDocument, _por_document_details.get('id'))

    st.warning('Upload another Proof of Residency document')
    session_state['navigation_id'] = 3


def proceed_to_poin():
    # Navigate
    session_state['navigation_id'] = 4


def back_to_por():
    # Navigate
    session_state['navigation_id'] = session_state.get('por_document_navigation_key')


def submit_pdf_images_for_text_analysis(
        _document_1_path: str,
        _document_1_name: str,
        _document_2_path: str,
        _document_2_name: str,
        _document_type: str,
        _document_category: str,
        next_navigation_id: float
):
    # Run OCR model
    _document_ocr_1_dict, output_filepath_1_ocr = run_optical_character_recognition_model(
        _document_1_path, _document_1_name
    )
    _document_ocr_2_dict, output_filepath_2_ocr = run_optical_character_recognition_model(
        _document_2_path, _document_2_name
    )

    # Save results
    _ocr_result_file_1_path = write_dict_to_pickle(_document_ocr_1_dict, 'ocr', _document_1_name)
    _ocr_result_file_2_path = write_dict_to_pickle(_document_ocr_2_dict, 'ocr', _document_2_name)

    # Filter
    _filter_dict_1 = {
        'session_id': session_state.get('session_id'),
        'name': _document_1_name,
        'type': _document_type
    }
    _filter_dict_2 = {
        'session_id': session_state.get('session_id'),
        'name': _document_2_name,
        'type': _document_type
    }

    # Update data
    update_data_1 = {
        '{}_image_path_ocr'.format(_document_category): output_filepath_1_ocr,
        'predictions': {'ocr': _ocr_result_file_1_path}
    }
    update_data_2 = {
        '{}_image_path_ocr'.format(_document_category): output_filepath_2_ocr,
        'predictions': {'ocr': _ocr_result_file_2_path}
    }

    # Update model
    update_model_record_by_session_id(UploadedDocument, _filter_dict_1, update_data_1)
    update_model_record_by_session_id(UploadedDocument, _filter_dict_2, update_data_2)

    # Navigate
    session_state['navigation_id'] = next_navigation_id


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
    form_data = dict()

    # Heading
    st.subheader(":blue[Fill in application form]", divider=True, help=PAGE_HELP)
    application_form = st.form('form1')
    # Form variables
    date_today = date.today()  # Get current date
    date_18_years_ago = date_today - timedelta(days=18 * 365)  # Subtract 18 years from today's date
    date_18_years_ago = get_end_of_month(date_18_years_ago)
    date_100_years_ago = date_today - timedelta(days=100 * 365)  # Subtract 100 years from today's date
    date_100_years_ago = get_end_of_month(date_100_years_ago)

    # Form design
    #
    names = application_form.text_input('Given Name(s)', placeholder='Type your given names here ...')
    if names:
        form_data['names'] = names
        application_form.write(" :green[Name(s) received]")

    #
    surname = application_form.text_input('Surname', placeholder='Type your surname here ...')
    if surname:
        form_data['surname'] = surname
        application_form.write(" :green[Surname received]")

    #
    form_data['gender'] = application_form.selectbox(
        'Select your gender',
        ('Male', 'Female'),
        placeholder="Click dropdown arrow and select your gender",
        index=None
    )

    #
    form_data['dob'] = application_form.date_input(
        'Date of birth',
        min_value=date_100_years_ago,
        value=date_18_years_ago,
        max_value=date_18_years_ago,
        format='YYYY-MM-DD'
    )

    #
    address = application_form.text_area(
        'Residential Address', placeholder="Type your the address of where you reside here ..."
    )
    if address:
        form_data['address'] = address
        application_form.write(" :green[Residential address received]")

    #
    form_data['money_access'] = application_form.selectbox(
        'Do you have a bank account or mobile wallet',
        ('Yes', 'No'),
        placeholder="Click dropdown arrow and select your status",
        index=None
    )

    if 'names' not in form_data or 'surname' not in form_data or 'address' not in form_data:
        application_form.form_submit_button('Submit for inspection')

    if 'names' in form_data and 'surname' in form_data and 'address' in form_data:
        form_data['session_id'] = session_state.get('session_id')
        form_data['created'] = datetime.now()
        application_form.form_submit_button(
            'Approve and submit application form', on_click=application_form_button_clicked
        )

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

    st.button('Back', on_click=back_to_application_form_clicked)

    # Identity Document
    st.subheader(":blue[Upload Identity Document]", divider=True, help='Up')
    # Select Proof of identity document type
    poi_document_option = st.selectbox(
        ':blue[Select the type of document you are have]',
        ('Zimbabwean National ID',),
        placeholder="Click dropdown arrow and select your document type",
        index=None
    )

    if poi_document_option:
        st.write(':green[You selected {}]'.format(poi_document_option))

    # Upload image file
    poi_doc_uploaded_file = st.file_uploader("Choose an image", type=IMAGE_TYPES)

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

        upload_poi_document_status, upload_poi_document_response = upload_file_to_cloud_storage(
            poi_document_name, poi_document_path
        )

        # Check for face
        poi_document_face_extraction_status, poi_document_face_extraction_response = facial_extraction_model(
            poi_document_name
        )

        # When image face is not appropriate
        if poi_document_face_extraction_status == 400:
            delete_file_from_cloud_storage(poi_document_name)
            st.warning('Image face not visible please upload another Identity document image')
            session_state['navigation_id'] = 1

        # When image face is verifiable
        if poi_document_face_extraction_status == 200:
            st.info(upload_poi_document_response.get('message'))
            st.success('Face detected in uploaded image')

            por_document_details = {
                'session_id': session_state.get('session_id'),
                'name': poi_document_name,
                'uploaded_poi_image_path': poi_document_path,
                'category': 'poi',
                'type': 'poi_document',
                'option': poi_document_option
            }

            # Save information to database
            new_record(UploadedDocument, por_document_details)

            # Display image
            st.image(poi_document_path)

            # Submit image to OD and OCR models
            st.button(
                'Submit my {}'.format(poi_document_option),
                use_container_width=True,
                on_click=poi_document_button_clicked,
                args=(poi_document_path, poi_document_name, 'poi_document')
            )

if session_state.get('navigation_id') == 1.5:
    st.button('Upload a different document', on_click=upload_another_poi_document)
    # Identity Document
    st.subheader(":blue[Proof of identity document key feature detection]", divider=True)

    # Get Application form details
    application_form_details_list = get_model_details_by_filter(
        ApplicationForm, {'session_id': session_state.get('session_id')}
    )
    application_form_details = application_form_details_list[0]

    # Get POI Document Details
    por_document_details_list = get_model_details_by_filter(
        UploadedDocument, {'session_id': session_state.get('session_id'), 'type': 'poi_document'}
    )
    por_document_details = por_document_details_list[0]
    poi_document_od_predicted_path = por_document_details.get('poi_image_path_od')
    poi_document_ocr_predicted_path = por_document_details.get('poi_image_path_ocr')
    poi_document_ocr_pickle = por_document_details.get('predictions')
    poi_document_ocr_dict = read_pickle_file(poi_document_ocr_pickle.get('ocr'))
    poi_document_od_dict = read_pickle_file(poi_document_ocr_pickle.get('od'))
    poi_document_ocr_results = read_ocr_results(poi_document_ocr_dict)
    poi_document_text_detected = poi_document_ocr_results.get('text')
    bboxes = poi_document_ocr_results.get('bbox')

    # Process data
    poi_document_text_detected = [word.strip().upper() for word in poi_document_text_detected]
    box_mid_points = [get_row_average_mid_point(bbox) for bbox in bboxes]
    text_list_df = restructured_detected_text(bboxes, box_mid_points, poi_document_text_detected)

    id_name_s: str = get_national_id_detected_text('FIRST NAME', text_list_df)
    id_surname: str = get_national_id_detected_text('SURNAME', text_list_df)
    id_dob: str = get_national_id_detected_text('DATE OF BIRTH', text_list_df)

    application_form_name: str = application_form_details.get('names')
    application_form_surname: str = application_form_details.get('surname')
    application_form_dob: str = application_form_details.get('dob')

    # Display OD Predictions
    st.write("#### :green[Results image display]")
    st.image(poi_document_od_predicted_path)

    st.write("#### :green[Results analysis]")
    poi_document_detected_features = get_national_id_detected_features(poi_document_od_dict)
    poi_document_detected_features.append(['face', '✅'])
    poi_document_detected_features_df = DataFrame(poi_document_detected_features, columns=['Feature', 'Check'])
    st.table(poi_document_detected_features_df)

    # Insert into database
    poi_document_detected_features_dict = poi_document_detected_features_df.to_dict(orient='records')
    poi_document_detected_features_details = {
        'session_id': session_state.get('session_id'),
        'result_type': 'poi document detected features',
        'result': poi_document_detected_features_dict
    }
    poi_document_detected_features_check = get_model_details_by_filter(AnalysisResults, {
        'session_id': session_state.get('session_id'),
        'result_type': 'poi document detected features'
    })
    if not poi_document_detected_features_check:
        new_record(AnalysisResults, poi_document_detected_features_details)

    # Display OCR Predictions
    st.subheader(":blue[Proof of identity document text detection]", divider=True)

    st.write("### :green[Results image display]")
    st.image(poi_document_ocr_predicted_path)

    st.write("### :green[Detected text snapshot]")
    poi_document_ocr_df = DataFrame(
        {'Detected text': poi_document_ocr_results['text'], 'Detection confidence': poi_document_ocr_results['score']}
    )
    st.table(poi_document_ocr_df.head())

    st.write("### :green[Results analysis]")
    poi_document_text_detection_analysis = [
        [
            'ID Number',
            get_national_id_detected_text('ID NUMBER', text_list_df)
        ],
        [
            'Name(s)',
            id_name_s,
            application_form_name,
            check_text_similarity(id_name_s, application_form_name.upper())
        ],
        [
            'Surname',
            id_surname,
            application_form_surname,
            check_text_similarity(id_surname, application_form_surname.upper())
        ],
        [
            'Date Of Birth',
            id_dob,
            application_form_dob,
            check_text_similarity(id_dob, convert_date_format(application_form_dob, 'dd/mm/yyyy'))
        ]
    ]

    poi_document_text_detection_analysis_df = DataFrame(
        poi_document_text_detection_analysis,
        columns=['Details', 'Text on document', 'Text on application form', 'Comparison'],
    )
    poi_document_text_detection_analysis_df.fillna(str(), inplace=True)
    st.table(poi_document_text_detection_analysis_df)

    # Insert into Database
    poi_document_text_detection_analysis_dict = poi_document_text_detection_analysis_df.to_dict(orient='records')
    poi_document_text_detection_analysis_details = {
        'session_id': session_state.get('session_id'),
        'result_type': 'poi document text detection',
        'result': poi_document_text_detection_analysis_dict
    }
    poi_document_text_detection_analysis_check = get_model_details_by_filter(AnalysisResults, {
        'session_id': session_state.get('session_id'),
        'result_type': 'poi document text detection'
    })
    if not poi_document_text_detection_analysis_check:
        new_record(AnalysisResults, poi_document_text_detection_analysis_details)

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
            upload_poi_recent_picture_status, upload_poi_recent_picture_response = upload_file_to_cloud_storage(
                poi_recent_picture_name, poi_recent_picture_path
            )

            # Check for face
            poi_recent_pic_face_extraction_status, poi_recent_pic_face_extraction_response = facial_extraction_model(
                poi_recent_picture_name
            )

            # When image face is not appropriate
            if poi_recent_pic_face_extraction_status == 400:
                st.warning('Image face not visible please take another selfie')
                delete_file_from_cloud_storage(poi_recent_picture_name)
                session_state['navigation_id'] = 2

            if poi_recent_pic_face_extraction_status == 200:
                st.info('Image face detected')
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
        por_document_details_list = get_model_details_by_filter(UploadedDocument, filter_dict_poi_document)
        por_document_details = por_document_details_list[0]
        st.button(
            'Submit for verification',
            use_container_width=True,
            on_click=submit_poi_recent_pics_clicked,
            args=(por_document_details, recent_pictures_list,)
        )

if session_state.get('navigation_id') == 2.5:
    # Get POI document details
    poi_document_filter = {'session_id': session_state.get('session_id'), 'type': 'poi_document'}
    por_document_details_list = get_model_details_by_filter(UploadedDocument, poi_document_filter)
    por_document_details = por_document_details_list[0]

    # Identity Document
    st.subheader(
        ":blue[Selfie Face Similarity to {} Face]".format(por_document_details.get('option')),
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
        st.image(por_document_details.get('poi_image_path_fr'))

    if poi_recent_picture_distance < 0.4:
        st.info('The faces have a {} difference, which is below the acceptable threshold'.format(
            round(poi_recent_picture_distance, 2))
        )
        st.button('Proceed to Proof of residency', use_container_width=True, on_click=proceed_to_por)

    else:
        st.error('The faces have a huge difference. Please take another set of selfies to verify with')
        st.button('Proceed to Proof of residency', use_container_width=True, on_click=proceed_to_por)

if session_state.get('navigation_id') == 3:
    # Identity Document
    st.subheader(
        ":blue[Proof Of Residency Document]",
        divider=True,
        help='Provide your Proof of residency document here'
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
    por_doc_uploaded_file = st.file_uploader("Choose a file", type=["pdf"])

    pdf_check, image_check = False, False
    if por_doc_uploaded_file is not None:

        por_doc_uploaded_image = None

        pdf_check = por_doc_uploaded_file.name.endswith('pdf')
        image_check = por_doc_uploaded_file.name.endswith(tuple(IMAGE_TYPES))

        # When uploaded file is pdf
        if pdf_check:
            por_document_pdf_path, por_document_name = save_pdf_file(
                session_state.get('session_id'),
                'por',
                por_doc_uploaded_file
            )
            pages, converted_por_document_path = convert_from_pdf_to_png(por_document_pdf_path, por_document_name)

            if len(pages) == 1:
                top_image_path, bottom_image_path, top_image_name, bottom_image_name = cut_image(
                    converted_por_document_path, por_document_name
                )
                st.image(top_image_path)
                st.image(bottom_image_path)

                por_document_1_details = {
                    'session_id': session_state.get('session_id'),
                    'name': top_image_name,
                    'uploaded_por_image_path': top_image_path,
                    'category': 'por',
                    'type': 'por_document',
                    'option': por_document_option
                }
                por_document_2_details = {
                    'session_id': session_state.get('session_id'),
                    'name': bottom_image_name,
                    'uploaded_por_image_path': bottom_image_path,
                    'category': 'por',
                    'type': 'por_document',
                    'option': por_document_option
                }

                new_record(UploadedDocument, por_document_1_details)
                new_record(UploadedDocument, por_document_2_details)

                # Clear variables
                por_doc_uploaded_file = None
                pdf_check = False

                st.button(
                    'Submit',
                    use_container_width=True,
                    on_click=submit_pdf_images_for_text_analysis,
                    args=(
                        top_image_path, top_image_name, bottom_image_path, bottom_image_name, 'por_document', 'por', 3.6
                    )
                )

        # When uploaded file is image
        if image_check:
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

            image_check = False

            st.button(
                'Submit',
                use_container_width=True,
                on_click=submit_image_for_text_analysis,
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
    por_document_details_list = get_model_details_by_filter(UploadedDocument, por_document_filter)
    por_document_details = por_document_details_list[0]

    #
    por_document_ocr_predicted_path = por_document_details.get('por_image_path_ocr')
    por_document_ocr_pickle = por_document_details.get('predictions')
    por_document_ocr_dict = read_pickle_file(por_document_ocr_pickle.get('ocr'))
    por_document_ocr_results = read_ocr_results(por_document_ocr_dict)
    poi_document_ocr_df = DataFrame(
        {'text': por_document_ocr_results['text'], 'score': por_document_ocr_results['score']}
    )

    st.write('### Detected on uploaded document')
    st.image(por_document_ocr_predicted_path)

    st.write('### Detected text in detail')
    st.table(poi_document_ocr_df)

    session_state['por_document_navigation_key'] = 3.5

    st.button('Proceed to Proof of income', use_container_width=True, on_click=proceed_to_poin)

if session_state.get('navigation_id') == 3.6:
    # POR Document
    st.button('Upload another Proof of Residency document', on_click=upload_another_por_document)
    st.subheader(
        ":blue[Proof of residency document text detection]",
        divider=True
    )

    # Get Application form details
    application_form_details_list = get_model_details_by_filter(
        ApplicationForm, {'session_id': session_state.get('session_id')}
    )
    application_form_details = application_form_details_list[0]

    por_document_filter = {'session_id': session_state.get('session_id'), 'type': 'por_document'}
    por_document_details_list = get_model_details_by_filter(UploadedDocument, por_document_filter)

    for document in por_document_details_list:
        por_document_ocr_pickle = document.get('predictions')
        if por_document_ocr_pickle is None:
            delete_model_record_by_id(UploadedDocument, document.get('id'))

    st.write('### :green[Results image display]')

    por_document_modified_ocr_path_list = list()
    por_document_surname_existence = False
    por_document_address_existence = False
    for document in por_document_details_list:
        por_document_ocr_predicted_path = document.get('por_image_path_ocr')
        por_document_image_path = document.get('uploaded_por_image_path')
        por_document_image_name = document.get('name')
        por_document_ocr_pickle = document.get('predictions')

        if por_document_ocr_pickle is not None:
            por_document_ocr_dict = read_pickle_file(por_document_ocr_pickle.get('ocr'))
            por_document_ocr_results = read_ocr_results(por_document_ocr_dict)
            poi_document_ocr_df = DataFrame(
                {'text': por_document_ocr_results['text'], 'score': por_document_ocr_results['score']}
            )

            por_document_ocr_text_list = [ocr_details[1][0] for ocr_details in por_document_ocr_dict]
            por_document_ocr_text_formatted_list = [word.strip().upper() for word in por_document_ocr_text_list]
            por_document_ocr_bboxes_list = [ocr_details[0] for ocr_details in por_document_ocr_dict]

            por_detected_text_bboxes = list()

            # Surname
            por_detected_boxes_surname = get_kyc_document_detected_text(
                [application_form_details.get('surname').upper()],
                por_document_ocr_text_formatted_list,
                por_document_ocr_bboxes_list
            )
            if por_detected_boxes_surname:
                por_document_surname_existence = por_document_surname_existence or True

            for bbox in por_detected_boxes_surname:
                por_detected_text_bboxes.append(bbox)

            # Address
            address_details: str = application_form_details.get('address').upper()
            address_details = address_details.replace('\n', ' ')
            address_details_list = address_details.split()
            por_detected_boxes_address = get_kyc_document_detected_text(
                [word.strip().upper() for word in address_details_list],
                por_document_ocr_text_formatted_list,
                por_document_ocr_bboxes_list
            )

            if por_detected_boxes_address:
                por_document_address_existence = por_document_address_existence or True

            for bbox in por_detected_boxes_address:
                por_detected_text_bboxes.append(bbox)

            por_detected_text_bboxes = get_list_unique_elements(por_detected_text_bboxes)

            if por_detected_text_bboxes:
                por_detected_text_relative_bboxes = convert_coordinates(por_detected_text_bboxes)
                por_document_modified_ocr_path = draw_bounding_box_on_image(
                    por_document_image_path,
                    por_document_image_name,
                    por_detected_text_relative_bboxes,
                    'ocr_modified'
                )
                por_document_modified_ocr_path_list.append(por_document_modified_ocr_path)

            st.image(por_document_ocr_predicted_path)

    if por_document_modified_ocr_path_list:
        st.write('### :green[Image analysis]')
        for por_document_modified_ocr_path in por_document_modified_ocr_path_list:
            st.image(por_document_modified_ocr_path)

    st.write('### :green[Result analysis]')

    # Existence statuses
    if por_document_surname_existence:
        por_document_surname_assessment = '✅'
    else:
        por_document_surname_assessment = '❌'

    if por_document_address_existence:
        por_document_address_assessment = '✅'
    else:
        por_document_address_assessment = '❌'

    por_document_text_detection_analysis = [
        ['Is name similar on POR document?', por_document_surname_existence, por_document_surname_assessment],
        ['Is address similar on POR document?', por_document_address_existence, por_document_address_assessment]
    ]
    por_document_text_detection_analysis_df = DataFrame(
        por_document_text_detection_analysis, columns=['Assessment', 'Analysis', 'Status']
    )
    st.table(por_document_text_detection_analysis_df)

    # Insert into Database
    por_document_text_detection_analysis_dict = por_document_text_detection_analysis_df.to_dict(orient='records')
    por_document_text_detection_analysis_details = {
        'session_id': session_state.get('session_id'),
        'result_type': 'por document text detection',
        'result': por_document_text_detection_analysis_dict
    }
    por_document_text_detection_analysis_check = get_model_details_by_filter(AnalysisResults, {
        'session_id': session_state.get('session_id'),
        'result_type': 'por document text detection'
    })
    if not por_document_text_detection_analysis_check:
        new_record(AnalysisResults, por_document_text_detection_analysis_details)

    session_state['por_document_navigation_key'] = 3.6
    st.button('Proceed to Proof of income', use_container_width=True, on_click=proceed_to_poin)

if session_state.get('navigation_id') == 4:
    # Proof of Income Document
    st.subheader(
        ":blue[Proof Of Income Document]",
        divider=True,
        help='Proof of residency verification'
    )
    st.button('Back to Proof of residency verification', on_click=back_to_por)

    # Select Proof of identity document type
    poin_document_option = st.selectbox(
        ':blue[Select the type of document you are have]',
        ('Employment Confirmation Letter',),
        placeholder="Click dropdown arrow and choose",
        index=None
    )

    if poin_document_option:
        st.write(':green[You selected {}]'.format(poin_document_option))

    # Upload document
    poin_doc_uploaded_file = st.file_uploader("Choose a file", type=["pdf"])

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

                poin_doc_uploaded_file = None

                st.button(
                    'Submit',
                    use_container_width=True,
                    on_click=submit_pdf_images_for_text_analysis,
                    args=(
                        top_image_path,
                        top_image_name,
                        bottom_image_path,
                        bottom_image_name,
                        'poin_document',
                        'poin',
                        4.5
                    )
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
    # Proof of Income Document
    st.button('Upload another Proof of income document', on_click=upload_another_poin_document)
    st.subheader(
        ":blue[Proof of income document text detection]",
        divider=True
    )

    poin_document_filter = {'session_id': session_state.get('session_id'), 'type': 'poin_document'}
    poin_document_details_list = get_model_details_by_filter(UploadedDocument, poin_document_filter)

    # Get Application form details
    application_form_details_list = get_model_details_by_filter(
        ApplicationForm, {'session_id': session_state.get('session_id')}
    )
    application_form_details = application_form_details_list[0]

    for document in poin_document_details_list:
        poin_document_ocr_pickle = document.get('predictions')
        if poin_document_ocr_pickle is None:
            delete_model_record_by_id(UploadedDocument, document.get('id'))

    st.write('### :green[Results image display]')
    poin_document_surname_existence = False
    poin_document_address_existence = False
    poin_document_modified_ocr_path_list = list()

    for document in poin_document_details_list:
        #
        poin_document_ocr_predicted_path = document.get('poin_image_path_ocr')
        poin_document_image_path = document.get('uploaded_poin_image_path')
        poin_document_image_name = document.get('name')
        poin_document_ocr_pickle = document.get('predictions')
        poin_document_ocr_dict = read_pickle_file(poin_document_ocr_pickle.get('ocr'))

        poin_document_ocr_text_list = [ocr_details[1][0] for ocr_details in poin_document_ocr_dict]
        poin_document_ocr_text_formatted_list = [word.strip().upper() for word in poin_document_ocr_text_list]
        poin_document_ocr_bboxes_list = [ocr_details[0] for ocr_details in poin_document_ocr_dict]

        poin_detected_text_bboxes = list()

        # Surname
        poin_detected_boxes_surname = get_kyc_document_detected_text(
            [application_form_details.get('surname').upper()],
            poin_document_ocr_text_formatted_list,
            poin_document_ocr_bboxes_list
        )
        if poin_detected_boxes_surname:
            poin_document_surname_existence = poin_document_surname_existence or True

        for bbox in poin_detected_boxes_surname:
            poin_detected_text_bboxes.append(bbox)

        # Address
        address_details: str = application_form_details.get('address').upper()
        address_details = address_details.replace('\n', ' ')
        address_details_list = address_details.split()
        poin_detected_boxes_address = get_kyc_document_detected_text(
            [word.strip().upper() for word in address_details_list],
            poin_document_ocr_text_formatted_list,
            poin_document_ocr_bboxes_list
        )

        if poin_detected_boxes_address:
            poin_document_address_existence = poin_document_address_existence or True

        for bbox in poin_detected_boxes_address:
            poin_detected_text_bboxes.append(bbox)

        poin_detected_text_bboxes = get_list_unique_elements(poin_detected_text_bboxes)

        if poin_detected_text_bboxes:
            poin_detected_text_relative_bboxes = convert_coordinates(poin_detected_text_bboxes)
            poin_document_modified_ocr_path = draw_bounding_box_on_image(
                poin_document_image_path,
                poin_document_image_name,
                poin_detected_text_relative_bboxes,
                'ocr_modified'
            )
            poin_document_modified_ocr_path_list.append(poin_document_modified_ocr_path)
        #

        st.image(poin_document_ocr_predicted_path)

    if poin_document_modified_ocr_path_list:
        st.write('### :green[Image analysis]')
        for poin_document_modified_ocr_path in poin_document_modified_ocr_path_list:
            st.image(poin_document_modified_ocr_path)

    st.write('### :green[Result analysis]')

    # Existence statuses
    if poin_document_surname_existence:
        poin_document_surname_assessment = '✅'
    else:
        poin_document_surname_assessment = '❌'

    if poin_document_address_existence:
        poin_document_address_assessment = '✅'
    else:
        poin_document_address_assessment = '❌'

    poin_document_text_detection_analysis = [
        ['Is name similar on PO Income document?', poin_document_surname_existence, poin_document_surname_assessment],
        ['Is address similar on PO Income document?', poin_document_address_existence, poin_document_address_assessment]
    ]
    poin_document_text_detection_analysis_df = DataFrame(
        poin_document_text_detection_analysis, columns=['Assessment', 'Analysis', 'Status']
    )
    st.table(poin_document_text_detection_analysis_df)

    # Insert into Database
    poin_document_text_detection_analysis_dict = poin_document_text_detection_analysis_df.to_dict(orient='records')
    poin_document_text_detection_analysis_details = {
        'session_id': session_state.get('session_id'),
        'result_type': 'poin document text detection',
        'result': poin_document_text_detection_analysis_dict
    }
    poin_document_text_detection_analysis_check = get_model_details_by_filter(AnalysisResults, {
        'session_id': session_state.get('session_id'),
        'result_type': 'poin document text detection'
    })
    if not poin_document_text_detection_analysis_check:
        new_record(AnalysisResults, poin_document_text_detection_analysis_details)

    st.button('Get KYC document verification report', use_container_width=True, on_click=get_kyc_report)

if session_state.get('navigation_id') == 5:
    # POI document features
    poi_document_detected_features_details_list = get_model_details_by_filter(
        AnalysisResults,
        {'session_id': session_state.get('session_id'), 'result_type': 'poi document detected features'}
    )
    poi_document_detected_features_details: dict = poi_document_detected_features_details_list[0]
    poi_document_detected_features_results = poi_document_detected_features_details.get('result')
    poi_document_detected_features_df = DataFrame(poi_document_detected_features_results)

    # POI document text detection
    poi_document_text_detected_details_list = get_model_details_by_filter(
        AnalysisResults,
        {'session_id': session_state.get('session_id'), 'result_type': 'poi document text detection'}
    )
    poi_document_text_detected_details: dict = poi_document_text_detected_details_list[0]
    poi_document_text_detected_results = poi_document_text_detected_details.get('result')
    poi_document_text_detected_df = DataFrame(poi_document_text_detected_results)

    # POR document text detection
    por_document_text_detected_details_list = get_model_details_by_filter(
        AnalysisResults,
        {'session_id': session_state.get('session_id'), 'result_type': 'por document text detection'}
    )
    por_document_text_detected_details: dict = por_document_text_detected_details_list[0]
    por_document_text_detected_results = por_document_text_detected_details.get('result')
    por_document_text_detected_df = DataFrame(por_document_text_detected_results)

    # POIn document text detection
    poin_document_text_detected_details_list = get_model_details_by_filter(
        AnalysisResults,
        {'session_id': session_state.get('session_id'), 'result_type': 'poin document text detection'}
    )
    poin_document_text_detected_details: dict = poin_document_text_detected_details_list[0]
    poin_document_text_detected_results = poin_document_text_detected_details.get('result')
    poin_document_text_detected_df = DataFrame(poin_document_text_detected_results)

    col1, col2 = st.columns(2)
    with col1:
        st.button('Start afresh', use_container_width=True, type='primary', on_click=restart)

    # Identity Document
    st.subheader(
        ":blue[KYC document verification report for customer]",
        divider=True,
        help='Proof of residency verification'
    )

    # POI
    st.write('### :green[Proof of Identity]')
    st.table(poi_document_detected_features_df)
    st.table(poi_document_text_detected_df)

    # POR
    st.write('### :green[Proof of Residency]')
    st.table(por_document_text_detected_df)

    # POIn
    st.write('### :green[Proof of Income]')
    st.table(poin_document_text_detected_df)
