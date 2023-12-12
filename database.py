from sqlalchemy import Column
from sqlalchemy import DATE
from sqlalchemy import DATETIME
from sqlalchemy import INTEGER
from sqlalchemy import JSON
from sqlalchemy import TEXT

from init import Base


# Define the ApplicationForm model
class ApplicationForm(Base):
    __tablename__ = 'application_form'
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    session_id = Column(TEXT, nullable=False)
    names = Column(TEXT, nullable=False)
    surname = Column(TEXT, nullable=False)
    gender = Column(TEXT, nullable=False)
    dob = Column(DATE, nullable=False)
    money_access = Column(TEXT, nullable=False)
    created = Column(DATETIME, nullable=False)

    def model_details(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'names': self.names,
            'surname': self.surname,
            'gender': self.gender,
            'dob': self.dob,
            'money_access': self.money_access,
            'created': self.created
        }


# Define the ApplicationForm model
class UploadedDocument(Base):
    __tablename__ = 'uploaded_document'
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    session_id = Column(TEXT, nullable=False)
    name = Column(TEXT, nullable=False)
    category = Column(TEXT, nullable=False)
    type = Column(TEXT, nullable=False)
    option = Column(TEXT)
    # POI
    uploaded_poi_image_path = Column(TEXT)
    poi_image_path_od = Column(TEXT)
    poi_image_path_ocr = Column(TEXT)
    poi_image_path_fr = Column(TEXT)
    # PORec
    uploaded_po_recent_image_path = Column(TEXT)
    po_recent_image_path_fr = Column(TEXT)
    # POR
    uploaded_por_image_path = Column(TEXT)
    por_image_path_od = Column(TEXT)
    por_image_path_ocr = Column(TEXT)
    # POIn
    uploaded_poin_image_path = Column(TEXT)
    poin_image_path_od = Column(TEXT)
    poin_image_path_ocr = Column(TEXT)
    #
    predictions = Column(JSON)

    def model_details(self):
        return {
            #
            'id': self.id,
            'session_id': self.session_id,
            'name': self.name,
            'category': self.category,
            'type': self.type,
            'option': self.option,
            #
            'uploaded_poi_image_path': self.uploaded_poi_image_path,
            'poi_image_path_od': self.poi_image_path_od,
            'poi_image_path_ocr': self.poi_image_path_ocr,
            'poi_image_path_fr': self.poi_image_path_fr,
            #
            'uploaded_po_recent_image_path': self.uploaded_po_recent_image_path,
            'po_recent_image_path_fr': self.po_recent_image_path_fr,
            #
            'uploaded_por_image_path': self.uploaded_por_image_path,
            'por_image_path_od': self.por_image_path_od,
            'por_image_path_ocr': self.por_image_path_ocr,
            #
            'uploaded_poin_image_path': self.uploaded_poin_image_path,
            'poin_image_path_od': self.poin_image_path_od,
            'poin_image_path_ocr': self.poin_image_path_ocr,
            #
            'predictions': self.predictions
        }
