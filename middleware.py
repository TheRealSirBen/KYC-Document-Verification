from os import environ
from os.path import join

from PIL import Image
from sqlalchemy.orm import sessionmaker
from ultralytics import YOLO

from helper import draw_bounding_box_on_image

from datagrip import ping_facial_recognition_api
from datagrip import ping_text_recognition_api
from datagrip import facial_recognition_model
from datagrip import text_recognition_model
from datagrip import download_file_from_cloud_storage
from datagrip import get_cloud_storage_files_by_session_id
from datagrip import delete_file_from_cloud_storage

from init import Base
from init import PREDICTIONS_FOLDER
from init import create_connection

STORAGE_CONTAINER_NAME = environ.get('STORAGE_CONTAINER_NAME')
PREDICTIONS_CONTAINER_NAME = environ.get('PREDICTIONS_CONTAINER_NAME')

engine = create_connection()
Session = sessionmaker(bind=engine)


def load_paddle_ocr_model():
    ocr = PaddleOCR(use_angle_cls=True, lang='en', rec_model_dir='deep-learning-models/ocr_model')
    return ocr


def load_yolo_od_model():
    od = YOLO('deep-learning-models/od_model.pt')
    return od


# Add record to database table
def new_record(model: Base, record_data: dict):
    # Start session
    session = Session()

    # instantiate application model
    application_record = model(**record_data)

    # Add to record
    session.add(application_record)
    session.commit()
    session.close()


# Retrieve from database table
def get_model_details_by_filter(model: Base, filter_dict: dict) -> list:
    session = Session()
    model_query = session.query(model).filter_by(**filter_dict).all()
    session.close()
    model_details = [query.model_details() for query in model_query]
    return model_details


# Update record in database table
def update_model_record_by_session_id(model: Base, filter_dict: dict, update_data: dict):
    session = Session()
    model_query = session.query(model).filter_by(**filter_dict).first()
    if model_query:
        for key in update_data:
            setattr(model_query, key, update_data[key])
        session.commit()
        session.close()


def delete_model_record_by_id(model: Base, _id: int):
    session = Session()
    session.query(model).filter_by(id=_id).delete()
    session.commit()
    session.close()


def check_models_availability() -> list:
    message_list = list()
    message_list.append('Object Detection Model Available')

    # OCR Model
    ping_ocr_status, ping_ocr_response = ping_text_recognition_api()
    if ping_ocr_status == 200:
        message_list.append('OCR Model Available')

    # Facial Recognition Model
    ping_ocr_status, ping_ocr_response = ping_facial_recognition_api()
    if ping_ocr_status == 200:
        message_list.append('Facial Recognition Model Available')

    return message_list


# Run Optical Character Recognition Model on image
def run_optical_character_recognition_model(image_name: str):
    model_result_status, model_result_response = text_recognition_model(image_name)

    # When model run is successful
    if model_result_status == 200:
        model_data: dict = model_result_response.get('data')
        ocr_results: dict = model_data.get('ocr_results')

        ocr_image_name = model_data.get('ocr_image_name')
        download_status, download_image_path = download_file_from_cloud_storage(
            ocr_image_name, PREDICTIONS_CONTAINER_NAME
        )

        return ocr_results, download_image_path


# Run Facial Recognition model on images
def run_facial_recognition_similarity_model(image_1_details: dict, image_2_details: dict):
    # Extract Images data
    image_1_path, image_1_name = image_1_details.get('uploaded_poi_image_path'), image_1_details.get('name')
    image_2_path, image_2_name = image_2_details.get('uploaded_po_recent_image_path'), image_2_details.get('name')

    fr_status, fr_response = facial_recognition_model(image_1_name, image_2_name)

    if fr_status == 200:
        verification_details = fr_response.get('data')

        # Get Inference Results
        distance = verification_details.get('distance')

        # Get facial results
        image_1_facials = verification_details.get('facial_areas_image_1')
        image_2_facials = verification_details.get('facial_areas_image_2')

        # Draw bounding boxes on images
        image_1_output_path = draw_bounding_box_on_image(
            image_1_path, image_1_name, [image_1_facials], 'fr'
        )
        image_2_output_path = draw_bounding_box_on_image(
            image_2_path, image_2_name, [image_2_facials], 'fr'
        )

        return distance, image_1_output_path, image_2_output_path, verification_details

    return 999999, str(), str(), fr_response


# Run Object
def run_object_detection_model(image_path: str, image_name: str) -> tuple[dict, str]:
    # Out filename
    output_filepath = join(PREDICTIONS_FOLDER, 'od_{}'.format(image_name))

    # infer on a local image
    od = load_yolo_od_model()
    results = od(image_path)

    model_classes, detected_classes = dict(), list()
    for _attrs in results:
        model_classes = _attrs.names
        model_boxes = _attrs.boxes
        detected_classes = model_boxes.cls

    detected_class_names = list(set([model_classes[int(i)] for i in detected_classes]))

    # Show the results
    for r in results:
        im_array = r.plot()  # plot a BGR numpy array of predictions
        im = Image.fromarray(im_array[..., ::-1])  # RGB PIL image
        im.save(output_filepath)  # save image

    return {'classes': detected_class_names}, output_filepath


def delete_session_files_from_cloud_storage(session_id: str):
    # Stored Images
    store_files_status, store_files_response = get_cloud_storage_files_by_session_id(session_id, STORAGE_CONTAINER_NAME)

    store_files_list = store_files_response.get('data')

    if store_files_list:
        for store_file in store_files_list:
            delete_file_from_cloud_storage(store_file, STORAGE_CONTAINER_NAME)

    # Predictions Images
    predictions_files_status, predictions_files_response = get_cloud_storage_files_by_session_id(
        session_id, PREDICTIONS_CONTAINER_NAME
    )

    predictions_files_list = predictions_files_response.get('data')

    if predictions_files_list:
        for predictions_file in predictions_files_list:
            delete_file_from_cloud_storage(predictions_file, STORAGE_CONTAINER_NAME)
