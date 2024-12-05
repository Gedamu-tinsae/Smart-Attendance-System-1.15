import sys
import io
import tensorflow as tf
import numpy as np
import os
import cv2
import base64
from io import BytesIO
from PIL import Image
import logging
from flask import Blueprint, request, jsonify, current_app, flash, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from sklearn.metrics.pairwise import cosine_similarity
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import json

# Redirect stdout and stderr to handle encoding explicitly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])

def get_model_directory():
    """Get the absolute path to the models directory."""
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_directory = os.path.join(app_root, 'app', 'models')
    if not os.path.exists(model_directory):
        os.makedirs(model_directory)
    return model_directory

model_directory = get_model_directory()

def preprocess_image(img_path):
    """Preprocess the image to be used for feature extraction."""
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Image at path {img_path} could not be loaded.")
    img = cv2.resize(img, (224, 224))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = np.expand_dims(img, axis=0)
    img = preprocess_input(img)
    return img

def get_feature_vector(model, img_path):
    """Extract features from the image using the given model."""
    img = preprocess_image(img_path)
    features = model.predict(img)
    return features.flatten()

def create_feature_extractor_model():
    """Create and return a MobileNetV2 feature extractor model."""
    model = MobileNetV2(weights='imagenet', include_top=False, pooling='avg')
    return model

def train_model(student_id, images, model_directory):
    logging.debug(f"student_id in train model: {student_id}")

    # Create label mapping
    student_ids = list(set([student_id]))  # This is for the current student; adapt if handling multiple students
    label_mapping = {id: idx for idx, id in enumerate(student_ids)}

    # Save label mapping to a file
    label_mapping_path = os.path.join(model_directory, 'label_mapping.json')
    with open(label_mapping_path, 'w') as f:
        json.dump(label_mapping, f)

    # Preprocess images
    processed_images = []
    labels = []
    for image in images:
        # Ensure image is a path
        img_path = image
        if not isinstance(img_path, str):
            raise TypeError(f"Expected img_path to be a string, got {type(img_path).__name__}.")
        # Convert image to feature vector
        features = get_feature_vector(create_feature_extractor_model(), img_path)
        processed_images.append(features)
        labels.append(label_mapping[student_id])  # Use numeric label

    processed_images = np.array(processed_images)
    labels = np.array(labels)

    # Save the features
    features_path = os.path.join(model_directory, f"features_{student_id}.npy")
    np.save(features_path, processed_images)
    
    return True

def load_and_preprocess_image(image_data):
    """Load and preprocess the image from base64 data."""
    try:
        # Decode base64 image data
        image_data = image_data.split(',')[1]  # Skip the metadata part
        image = base64.b64decode(image_data)
        img = Image.open(BytesIO(image))
        
        # Save image to a temporary file
        img_path = os.path.join(model_directory, 'temp_image.jpg')
        img.save(img_path)
        
        return img_path
    except Exception as e:
        logging.error(f"Error during image preprocessing: {str(e)}", exc_info=True)
        raise e


def recognize_face(image_data, student_id, model_directory):
    logging.debug(f"student_id in recognize face: {student_id}")
    """Load model and make predictions."""
    
    model = create_feature_extractor_model()
    features_path = os.path.join(model_directory, f"features_{student_id}.npy")
    label_mapping_path = os.path.join(model_directory, 'label_mapping.json')

    if not os.path.exists(features_path):
        logging.error(f"Features not found at {features_path}. Please train the model first.")
        return None

    try:
        # Load label mapping
        with open(label_mapping_path, 'r') as f:
            label_mapping = json.load(f)

        known_person_features = np.load(features_path)
        test_img_path = load_and_preprocess_image(image_data)
        test_features = get_feature_vector(model, test_img_path)
        
        similarities = cosine_similarity([test_features], known_person_features)
        if np.max(similarities) > 0.8:  # Adjust threshold as needed
            return student_id
        else:
            return None
    except Exception as e:
        error_message = f"Prediction error: {str(e)}"
        logging.error(error_message, exc_info=True)
        raise e
