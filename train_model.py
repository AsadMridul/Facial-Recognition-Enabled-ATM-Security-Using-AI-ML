# train_model.py

import face_recognition
import os
import pickle
import cv2  # We'll use OpenCV to resize images

# --- Configuration ---
DATASET_PATH = "dataset"
ENCODINGS_FILE = "encodings.pickle"
MAX_IMAGE_WIDTH = 800  # Set a max width for images to prevent memory errors

# --- Main Script ---
print("[INFO] Starting to quantify faces using the 'cnn' model...")
print("[INFO] This will be slower but much more accurate. Please be patient.")
print(f"[INFO] Large images will be resized to a max width of {MAX_IMAGE_WIDTH}px to save memory.")

known_encodings = []
known_names = []

# Loop through each person's folder in the dataset
for person_name in os.listdir(DATASET_PATH):
    person_dir = os.path.join(DATASET_PATH, person_name)
    
    if not os.path.isdir(person_dir):
        continue

    print(f"[INFO] Processing images for {person_name}...")
    
    for filename in os.listdir(person_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(person_dir, filename)
            
            try:
                # Load image using OpenCV
                image = cv2.imread(image_path)
                
                # --- NEW MEMORY FIX ---
                # Check image width and resize if it's too large
                (h, w) = image.shape[:2]
                if w > MAX_IMAGE_WIDTH:
                    r = MAX_IMAGE_WIDTH / float(w)
                    dim = (MAX_IMAGE_WIDTH, int(h * r))
                    image = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
                # ----------------------

                # Convert from BGR (OpenCV) to RGB (face_recognition)
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Find the face location (bounding box) using the CNN model
                boxes = face_recognition.face_locations(rgb_image, model='cnn')

                # Compute the facial embedding
                encodings = face_recognition.face_encodings(rgb_image, boxes)

                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(person_name)
                else:
                    print(f"  [WARNING] No face found in {filename}. Skipping.")

            except Exception as e:
                print(f"  [ERROR] Failed to process {filename}. Reason: {e}")

# Save the encodings
print("\n[INFO] Serializing encodings to disk...")
data = {"encodings": known_encodings, "names": known_names}
with open(ENCODINGS_FILE, "wb") as f:
    f.write(pickle.dumps(data))

print(f"[SUCCESS] Training complete. Saved {len(known_encodings)} face encodings to {ENCODINGS_FILE}.")