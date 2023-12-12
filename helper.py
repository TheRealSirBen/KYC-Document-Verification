import calendar
import pickle
from datetime import date
from datetime import datetime
from os.path import join
from random import randint

import fitz
from PIL import Image
from cv2 import imread
from cv2 import imwrite
from cv2 import rectangle

from init import IMAGE_FOLDER
from init import IMAGE_MAX_SIZE
from init import PDF_FOLDER
from init import PDF_MAX_SIZE
from init import PREDICTIONS_FOLDER


def validate_form_data(form_data: dict) -> list:
    unavailable_fields = list()

    for field in form_data:
        record = form_data.get(field)
        if record in [str(), '', None]:
            unavailable_fields.append(field)

    return unavailable_fields


def get_end_of_month(date_input: date) -> datetime:
    date_year, date_month = date_input.year, date_input.month
    res = calendar.monthrange(date_year, date_month)
    end_day = res[1]

    return datetime(date_year, date_month, end_day)


def convert_and_resize(image: Image, instance_id: str, document_type: str) -> (str, str):
    # Resize the image while maintaining the aspect ratio
    image.thumbnail(IMAGE_MAX_SIZE)

    # Out filename
    output_filename = '{}_{}.png'.format(instance_id, document_type)
    output_filepath = join(IMAGE_FOLDER, output_filename)

    # Save the resized image
    image.save(output_filepath)

    return output_filename, output_filepath


def draw_bounding_box_on_image(image_path: str, image_name: str, bounding_boxes: list, model_type: str):
    # Load the image
    image = imread(image_path)
    color = (randint(0, 255), randint(0, 255), randint(0, 255))
    for bbox in bounding_boxes:
        # Define the coordinates of the bounding box
        x = bbox.get('x')
        y = bbox.get('y')
        w = bbox.get('w')
        h = bbox.get('h')

        # Draw the bounding box on the image
        rectangle(image, (x, y), (x + w, y + h), color, 2)

    # Save the image with the bounding box
    output_filepath = join(PREDICTIONS_FOLDER, '{}_{}'.format(model_type, image_name))
    imwrite(output_filepath, image)

    return output_filepath


def write_dict_to_pickle(dictionary: dict, model_type: str, name: str) -> str:
    file_path = join(PREDICTIONS_FOLDER, '{}_{}.pkl'.format(model_type, name))
    with open(file_path, 'wb') as file:
        pickle.dump(dictionary, file)
    file.close()

    return file_path


def read_pickle_file(file_path):
    with open(file_path, 'rb') as file:
        data = pickle.load(file)
    file.close()
    return data


def convert_coordinates(polygon_coordinates: list) -> list:
    relative_coordinates = list()
    for polygon_points in polygon_coordinates:
        x_values = [point[0] for point in polygon_points]
        y_values = [point[1] for point in polygon_points]

        x_min = min(x_values)
        y_min = min(y_values)
        x_max = max(x_values)
        y_max = max(y_values)

        width = x_max - x_min
        height = y_max - y_min
        relative_coordinates.append({'x': int(x_min), 'y': int(y_min), 'w': int(width), 'h': int(height)})

    return relative_coordinates


def read_ocr_results(ocr_results: list) -> dict:
    bounding_boxes = [line[0] for line in ocr_results]
    texts = [line[1][0] for line in ocr_results]
    scores = [line[1][1] for line in ocr_results]

    return {'bbox': bounding_boxes, 'text': texts, 'score': scores}


def cut_image(image_path: str, file_name: str):
    # Open the image
    image = Image.open(image_path)

    # Resize the image while maintaining the aspect ratio
    image.thumbnail(PDF_MAX_SIZE)

    # Get the width and height of the image
    width, height = image.size

    # Calculate the coordinates for cutting the image into halves
    top_half = (0, 0, width, height // 2)
    bottom_half = (0, height // 2, width, height)

    # Crop the image using the calculated coordinates
    top_image = image.crop(top_half)
    bottom_image = image.crop(bottom_half)

    # Save the top and bottom halves as separate images
    top_image_path = join(IMAGE_FOLDER, '{}_1.png'.format(file_name))
    bottom_image_path = join(IMAGE_FOLDER, '{}_2.png'.format(file_name))

    #
    top_image.save(top_image_path)
    bottom_image.save(bottom_image_path)

    return top_image_path, bottom_image_path, '{}_1.png'.format(file_name), '{}_2.png'.format(file_name)


def save_pdf_file(instance_id: str, model_type: str, uploaded_file):
    file_name = '{}_{}'.format(instance_id, model_type)
    save_path = join(PDF_FOLDER, '{}.pdf'.format(file_name))

    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    f.close()

    return save_path, file_name


def convert_from_pdf_to_png(path_to_pdf: str, file_name: str):
    doc = fitz.open(path_to_pdf)
    zoom = 5
    mat = fitz.Matrix(zoom, zoom)
    pages = [p for p in doc]
    output_path = join(IMAGE_FOLDER, '{}.png'.format(file_name))
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=mat)
    pix.save(output_path)
    doc.close()

    return pages, output_path
