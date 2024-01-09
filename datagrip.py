from os import environ
from requests import get
from requests import post
from requests import delete
from requests.exceptions import ConnectionError as ReqConnError
from json import loads
from json import dumps

FACIAL_RECOGNITION_MODEL_URL = environ.get('FACIAL_RECOGNITION_MODEL_URL')
STORAGE_URL = environ.get('STORAGE_URL')
EMAIL_COMM_URL = environ.get('EMAIL_COMM_URL')
STORAGE_CONTAINER_NAME = environ.get('STORAGE_CONTAINER_NAME')
PREDICTIONS_CONTAINER_NAME = environ.get('PREDICTIONS_CONTAINER_NAME')


def get_cloud_storage_files_by_session_id(session_id: str, container_name: str):
    api_link = '{}/get-folder-contents/{}?filter_text={}'.format(STORAGE_URL, container_name, session_id)

    try:
        # Make the POST request
        data = get(api_link)

        status, response = data.status_code, loads(data.text)
        return status, response

    except ReqConnError:
        return 404, str()


def upload_file_to_cloud_storage(file_name: str, file_path: str):
    api_link = '{}/upload-blob/{}/{}'.format(STORAGE_URL, STORAGE_CONTAINER_NAME, file_name)

    # Prepare the data and files
    files = {'file': open(file_path, 'rb')}

    try:
        # Make the POST request
        data = post(api_link, files=files)

        status, response = data.status_code, loads(data.text)
        return status, response

    except ReqConnError:
        return 404, str()


def delete_file_from_cloud_storage(file_name: str, container_name: str = STORAGE_CONTAINER_NAME):
    api_link = '{}/delete-blob/{}/{}'.format(STORAGE_URL, container_name, file_name)

    try:
        # Make the POST request
        data = delete(api_link)

        status, response = data.status_code, loads(data.text)
        return status, response

    except ReqConnError:
        return 404, str()


def facial_extraction_model(image_name: str):
    api_link = '{}/face-extraction/{}?storage_container_name={}'.format(
        FACIAL_RECOGNITION_MODEL_URL,
        image_name,
        STORAGE_CONTAINER_NAME
    )

    try:
        # Make the POST request
        data = post(api_link)

        status, response = data.status_code, loads(data.text)
        return status, response

    except ReqConnError:
        return 404, dict()


def facial_recognition_model(image_1_name: str, image_2_name: str):
    api_link = '{}/face-similarity/{}/{}?storage_container_name={}&predictions_container_name={}'.format(
        FACIAL_RECOGNITION_MODEL_URL,
        image_1_name,
        image_2_name,
        STORAGE_CONTAINER_NAME,
        PREDICTIONS_CONTAINER_NAME
    )

    try:
        # Make the POST request
        data = post(api_link)

        status, response = data.status_code, loads(data.text)
        return status, response

    except ReqConnError:
        return 404, dict()


def send_feedback_email(sender_name: str, sender_email_address: str, feedback_message: str):
    # Prepare Request Data
    email_data = {
        'mail_server': environ.get('MAIL_SERVER'),
        'mail_port': environ.get('MAIL_PORT'),
        'has_tls': True,
        'sender_email_address': environ.get('EMAIL_ADDRESS'),
        'sender_password': environ.get('EMAIL_PASSWORD'),
        'recipient_email_address': environ.get('RECEIVING_EMAIL_ADDRESS'),
        'email_subject': 'Feedback from {} on the KYC App'.format(sender_name),
        'has_message_body': True,
        'message_body': feedback_message,
        "greeting_message": "Hello Ben",
        "sender_name": "From {}, email address {}".format(sender_name, sender_email_address)
    }

    # Make Request
    api_link = '{}/send-email'.format(EMAIL_COMM_URL)
    headers = {"Content-Type": "application/json"}
    try:
        data = post(api_link, headers=headers, data=dumps(email_data))
        status, response = data.status_code, loads(data.text)
        return status, response

    except ReqConnError:
        return 404, {
            'message': 'Server connection interrupted, our apologies. Admin has been contacted. '
                       'You will be notified as soon as the issue is resolved.',
            'category': 'warning'
        }
