from os import remove
from os import listdir
from os.path import isfile
from os.path import join

from datetime import date
from datetime import datetime

import calendar
import pickle
import fitz
from fuzzywuzzy import fuzz
from re import match

from pandas import DataFrame
from random import randint

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


def get_row_average_mid_point(row: list) -> float:
    y_1 = row[0][1]
    y_4 = row[3][1]
    mid_point_left = y_1 + ((y_4 - y_1) / 2)

    y_2 = row[1][1]
    y_3 = row[2][1]
    mid_point_right = y_2 + ((y_3 - y_2) / 2)

    return (mid_point_left + mid_point_right) / 2


def in_box_range(y_value: float, box: list) -> bool:
    y_1 = box[0][1]
    y_2 = box[1][1]
    y_3 = box[2][1]
    y_4 = box[3][1]

    y_min = min(y_1, y_2)
    y_max = max(y_3, y_4)

    if y_min <= y_value <= y_max:
        return True

    return False


def restructured_detected_text(bounding_boxes: list, box_mid_points: list, text_detected) -> DataFrame:
    row_items = list()

    # Iterate over number of detected words
    for row_index in range(len(bounding_boxes)):
        same_row_items = list()

        # Iterate over number of detected words setting ech word constant
        for element_index in range(len(bounding_boxes)):

            # Check if in same row
            check = in_box_range(box_mid_points[row_index], bounding_boxes[element_index])

            # When word is in the same row
            if check:
                same_row_items.append(element_index)

        # Save row items
        row_items.append(same_row_items)

    row_items = [tuple(item) for item in row_items]  # Convert inner lists to tuples
    row_items = list(set(row_items))

    row_items = sorted(row_items, key=lambda x: len(x), reverse=True)

    row_list, enlisted = list(), list()
    for tuple_item in row_items:

        add_row = True
        for element in tuple_item:
            if element in enlisted:
                add_row = False

        if add_row:
            row_list.append(tuple_item)

            for element in tuple_item:
                enlisted.append(element)

    row_list = sorted(row_list, key=lambda x: x[0])

    text_list = list()
    for row_tuple in row_list:
        words = [text_detected[row_item] for row_item in row_tuple]
        text_list.append(words)

    text_list_df = DataFrame(text_list)

    return text_list_df


def get_national_id_detected_text(attribute: str, text_df: DataFrame) -> str | None:
    result = text_df[text_df.iloc[:, 0] == attribute]
    if not result.empty:
        return result.iloc[0, 1]

    return None


def get_national_id_detected_features(results: dict) -> list:
    detected_classes = results.get('classes')

    expected_classes = ['court-of-arms', 'fingerprint', 'seal', 'zimbabwe-bird']

    detected_features = list()

    for class_name in expected_classes:

        # When class is detected
        if class_name in detected_classes:
            detected_features.append([class_name, '✅'])

        # When class is not detected
        if class_name not in detected_classes:
            detected_features.append([class_name, '❌'])

    return detected_features


def get_kyc_document_detected_text(search_term_list: list, detected_text_list: list, detected_bboxes_list: list):
    por_detected_text_index_list = list()

    # Iterate over Search List
    for search_term in search_term_list:

        # Iterate over detected list
        for detected_text_index in range(len(detected_text_list)):

            if search_term in detected_text_list[detected_text_index]:
                por_detected_text_index_list.append(detected_text_index)

    por_detected_bboxes_list = [detected_bboxes_list[index] for index in por_detected_text_index_list]

    return por_detected_bboxes_list


def check_text_similarity(text_1: str, text_2: str, similarity_threshold: float = 70) -> str:
    # Compare the texts
    similarity_score = fuzz.ratio(text_1, text_2)

    # Determine if the texts are similar or not based on the similarity score
    if similarity_score >= similarity_threshold:
        return '✅'

    return '❌'


def convert_date_format(date_string: str, desired_format: str) -> str:
    # Define the input and output format codes
    input_format_codes = ['yyyy', 'mm', 'dd']
    output_format_codes = ['%Y', '%m', '%d']

    # Map the input format codes to the corresponding output format codes
    format_mapping = dict(zip(input_format_codes, output_format_codes))

    # Replace the format codes in the desired format with the corresponding output format codes
    for code in input_format_codes:
        desired_format = desired_format.replace(code, format_mapping[code])

    # Convert the date string to the desired format
    converted_date = datetime.strptime(date_string, '%Y-%m-%d').strftime(desired_format)

    return converted_date


def get_list_unique_elements(elements_list: list) -> list:
    unique_elements = list()
    for element in elements_list:
        if element not in unique_elements:
            unique_elements.append(element)
    return unique_elements


def delete_files_by_session_id(session_id: str, folder_path: str):
    for filename in listdir(folder_path):
        if session_id in filename:
            file_path = join(folder_path, filename)
            if isfile(file_path):
                remove(file_path)


def validate_email(email_string: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if match(pattern, email_string):
        return True
    return False
