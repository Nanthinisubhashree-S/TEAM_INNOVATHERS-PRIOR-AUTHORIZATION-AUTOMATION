import numpy as np
from PIL import Image
import onnxruntime as ort
from config import ONNX_MODEL_PATH

session = ort.InferenceSession(ONNX_MODEL_PATH)
bone_to_icd10 = {
    'femur': 'S72.0',
    'tibia': 'S82.5',
    'radius': 'S52.5',
    'ulna': 'S52.6'
}

def preprocess_image(image: Image.Image):
    image = image.convert('RGB')
    image = image.resize((640,640))
    image_np = np.array(image)/255.0
    image_np = image_np.transpose(2,0,1).astype(np.float32)
    image_np = np.expand_dims(image_np, axis=0)
    return image_np

def detect_fracture(image_np):
    inputs = {session.get_inputs()[0].name: image_np}
    outputs = session.run(None, inputs)
    return outputs

def postprocess(outputs, conf_threshold=0.5):
    predictions = outputs[0]
    class_ids = []
    for pred in predictions:
        conf_obj = pred[4]
        class_scores = pred[5:]
        class_id = int(np.argmax(class_scores))
        confidence = conf_obj * class_scores[class_id]
        if confidence > conf_threshold: class_ids.append(class_id)
    return class_ids

def map_to_icd10(class_ids):
    bone_classes = ['femur', 'tibia', 'radius', 'ulna']
    detected_bones = [bone_classes[cid] for cid in class_ids]
    icd10_codes = [bone_to_icd10[bone] for bone in detected_bones]
    return detected_bones, icd10_codes