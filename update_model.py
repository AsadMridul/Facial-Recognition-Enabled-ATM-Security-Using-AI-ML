import face_recognition
import os
import pickle
import cv2
import sys # To read command-line arguments

# --- Configuration ---
DATASET_PATH = "dataset"
ENCODINGS_FILE = "encodings.pickle"
MAX_IMAGE_WIDTH = 800

# --- 1. Load Existing Encodings (if any) ---
print(f"[INFO] Loading existing encodings from {ENCODINGS_FILE}...")
try:
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    known_encodings = data["encodings"]
    known_names = data["names"]
    print(f"[INFO] Loaded {len(known_names)} existing encodings.")
except FileNotFoundError:
    print("[INFO] No existing encodings file found. Starting a new one.")
    known_encodings = []
    known_names = []
except Exception as e:
    print(f"[ERROR] Could not load encodings file: {e}. Starting fresh.")
    known_encodings = []
    known_names = []


# --- 2. Get New User Name from Command Line ---
try:
    # We expect the user to run: python update_model.py "New User Name"
    person_name = sys.argv[1] 
    print(f"[INFO] Target user for update: {person_name}")
except IndexError:
    print("[ERROR] You must provide the new user's name as an argument.")
    print("Usage: python update_model.py \"User Name\"")
    sys.exit()

person_dir = os.path.join(DATASET_PATH, person_name)

if not os.path.isdir(person_dir):
    print(f"[ERROR] Directory not found: {person_dir}")
    print("Make sure the name matches the folder name in 'dataset' exactly (it is case-sensitive).")
    sys.exit()

# --- 3. Check if User is Already Trained ---
if person_name in known_names:
    print(f"[WARNING] {person_name} is already in the encodings file.")
    print("To re-train this user, you must run the full 'train_model.py' script.")
    sys.exit()


# --- 4. Process Only the New User's Images ---
print(f"[INFO] Processing images for new user: {person_name}...")
print("[INFO] Using 'cnn' model. This may take a moment...")
new_encodings_added = 0

for filename in os.listdir(person_dir):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        image_path = os.path.join(person_dir, filename)
        
        try:
            image = cv2.imread(image_path)
            (h, w) = image.shape[:2]
            if w > MAX_IMAGE_WIDTH:
                r = MAX_IMAGE_WIDTH / float(w)
                dim = (MAX_IMAGE_WIDTH, int(h * r))
                image = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Find the face
            boxes = face_recognition.face_locations(rgb_image, model='cnn')

            # Compute the embedding
            encodings = face_recognition.face_encodings(rgb_image, boxes)

            if encodings:
                # Add the new encoding and name to our lists
                known_encodings.append(encodings[0])
                known_names.append(person_name)
                new_encodings_added += 1
            else:
                print(f"  [WARNING] No face found in {filename}. Skipping.")

        except Exception as e:
            print(f"  [ERROR] Failed to process {filename}. Reason: {e}")

# --- 5. Save the COMBINED Data ---
if new_encodings_added > 0:
    print(f"\n[INFO] Added {new_encodings_added} new encodings for {person_name}.")
    print("[INFO] Appending new encodings and saving to disk...")
    new_data = {"encodings": known_encodings, "names": known_names}

    with open(ENCODINGS_FILE, "wb") as f: # Overwrite with the *updated* full list
        f.write(pickle.dumps(new_data))

    print(f"[SUCCESS] Update complete. Total users trained: {len(known_encodings)}.")
else:
    print(f"[WARNING] No new faces were encoded for {person_name}. File not updated.")