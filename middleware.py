from functools import lru_cache
from os.path import join

import yaml
from PIL import Image
from deepface import DeepFace
from paddleocr import PaddleOCR
from sqlalchemy.orm import sessionmaker
from ultralytics import YOLO

from helper import convert_coordinates
from helper import draw_bounding_box_on_image
from helper import read_ocr_results
from init import Base
from init import PREDICTIONS_FOLDER
from init import create_connection

engine = create_connection()
Session = sessionmaker(bind=engine)


@lru_cache()
def load_paddle_ocr_model():
    ocr = PaddleOCR(use_angle_cls=True, lang='en', rec_model_dir='deep-learning-models/ocr_model')
    return ocr


@lru_cache()
def load_yolo_od_model():
    od = YOLO('deep-learning-models/od_model.pt')
    return od


@lru_cache()
def load_deep_face_configurations():
    # Read the YAML file
    with open('deep-learning-models/fr_model_thresholds.yaml', 'r') as file:
        yaml_data = yaml.safe_load(file)

    # Create a dictionary from the YAML data
    data_dict = dict(yaml_data)

    # Access the values in the dictionary
    hyper_parameters = data_dict['hyper_parameters']
    threshold = data_dict['threshold']

    # Print the dictionaries
    return hyper_parameters, threshold


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


@lru_cache()
def delete_model_record_by_id(model: Base, _id: int):
    session = Session()
    session.query(model).filter_by(id=_id).delete()
    session.commit()
    session.close()


# Run Optical Character Recognition Model on image
@lru_cache()
def run_optical_character_recognition_model(image_path: str, image_name: str):
    # Get predictions
    ocr = load_paddle_ocr_model()
    result = ocr.ocr(image_path, cls=True)

    ocr_results = read_ocr_results(result)
    bounding_boxes = convert_coordinates(ocr_results['bbox'])

    ocr_output_file_path = draw_bounding_box_on_image(image_path, image_name, bounding_boxes, 'ocr')

    return result, ocr_output_file_path


# Run Facial Recognition model on images
def run_facial_recognition_similarity_model(image_1_details: dict, image_2_details: dict):
    # Get Model Parameters
    hyper_parameters, threshold = load_deep_face_configurations()

    # Extract Image 1 data
    image_1_path, image_1_name = image_1_details.get('uploaded_poi_image_path'), image_1_details.get('name')
    image_2_path, image_2_name = image_2_details.get('uploaded_po_recent_image_path'), image_2_details.get('name')

    # Image verification

    verification_details = DeepFace.verify(
        img1_path=image_1_path,
        img2_path=image_2_path,
        enforce_detection=False,
        model_name=hyper_parameters['model_name'],
        detector_backend=hyper_parameters['detector_backend']
    )
    # Get Inference Results
    distance, facial_areas = verification_details.get('distance'), verification_details.get('facial_areas')
    # Get facial results
    image_1_facials, image_2_facials = facial_areas.get('img1'), facial_areas.get('img2')
    # Draw bounding boxes on images
    image_1_output_path = draw_bounding_box_on_image(image_1_path, image_1_name, [image_1_facials], 'fr')
    image_2_output_path = draw_bounding_box_on_image(image_2_path, image_2_name, [image_2_facials], 'fr')

    result = {
        'distance': distance,
        'facial_areas_image_1': facial_areas.get('img1'),
        'facial_areas_image_2': facial_areas.get('img2')
    }

    return distance, image_1_output_path, image_2_output_path, result


# Run Object Detection model on image
@lru_cache()
def run_object_detection_model(image_path: str, image_name: str) -> str:
    # Out filename
    output_filepath = join(PREDICTIONS_FOLDER, 'od_{}'.format(image_name))

    # infer on a local image
    od = load_yolo_od_model()
    results = od(image_path)

    # Show the results
    for r in results:
        im_array = r.plot()  # plot a BGR numpy array of predictions
        im = Image.fromarray(im_array[..., ::-1])  # RGB PIL image
        im.save(output_filepath)  # save image

    return output_filepath
