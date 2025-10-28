# Facial Recognition Enabled ATM Security Using AI

A robust, AI-powered ATM simulation that replaces traditional PINs with a high-accuracy, deep learning-based facial recognition system. This project provides a secure, two-factor authentication workflow, using a **Convolutional Neural Network (CNN)** for primary user verification and a **Twilio WhatsApp OTP** as a secure fallback.



## Key Features

* **AI-Powered Authentication:** Leverages a deep learning model for robust and accurate facial recognition.
* **Secure 2FA Fallback:** Automatically sends a One-Time Password (OTP) via the Twilio WhatsApp API if facial recognition fails, ensuring the legitimate user can still gain access.
* **Robust CNN Training:** Uses a **Convolutional Neural Network (CNN)** in the training script (`train_model.py`) for superior accuracy compared to HOG models, making it more resilient to variations in lighting and pose.
* **Secure Registration Portal:** An easy-to-use GUI for new users to register their name, phone number, and capture the 10 photos required for training.
* **Dynamic Model Updating:** Includes an `update_model.py` script to add a newly registered user to the existing face model (`encodings.pickle`) without needing to retrain the entire dataset.
* **Audit & Security Logging:** Automatically captures and saves a snapshot of any individual who fails the facial verification step to the `unauthorized_access` folder for later review.
* **Anti-Fraud Detection:** The verification screen explicitly blocks access if it detects more than one face, preventing "shoulder-surfing" or spoofing attempts.

---

## How it Works: The Security Process

This system is designed for security and robustness, handling both successful and failed verifications gracefully.

1.  **Login Attempt:** A user initiates a session by entering their **Card Owner Name**.
2.  **Facial Verification:** The system activates the camera and searches for the user's face.
    * It detects all faces using a **Histogram of Oriented Gradients (HOG)** model for real-time performance.
    * It generates a **128-d face embedding** (a unique mathematical signature) for the detected face.
    * It compares this embedding against the pre-trained embeddings in `encodings.pickle` using **Euclidean Distance**.
3.  **Verification Scenarios:**
    * **✅ Success:** If the detected face is a match (`distance < 0.55`) **AND** the matched name is the same as the Card Owner Name, access is granted.
    * **❌ Mismatch:** If a face is matched, but it's not the correct user (e.g., a different registered user), it's treated as a **Mismatch** and access is denied.
    * **❌ Failure / Timeout:** If no face is matched, or the 20-second timer expires, the facial verification fails.
4.  **OTP Fallback:** On any failure (Mismatch or Timeout), the system does not lock the user out. Instead, it offers to send a 6-digit OTP to the legitimate card owner's registered WhatsApp number.
5.  **OTP Verification:** The user enters the OTP. A simple **string comparison** confirms the code, and access is granted. This ensures that even if the AI fails (e.g., bad lighting, new glasses), the real user can still complete their transaction.

---

## Algorithms & Technologies

* **Face Detection (Training):** **Convolutional Neural Network (CNN)**. This deep learning model is used in `train_model.py` to find faces in the registration photos. It is highly accurate and robust to variations in pose, lighting, and angle.
* **Face Detection (Live):** **Histogram of Oriented Gradients (HOG)**. A faster, classic machine learning feature descriptor used for real-time face detection in the `gui_atm_app.py`.
* **Face Encoding:** **Deep Metric Learning (ResNet-34 based)**. The `face_recognition` library uses a deep neural network (similar to ResNet-34) trained on the LFW dataset to generate a unique 128-point vector (embedding) for each face.
* **Face Matching:** **Euclidean Distance**. The system calculates the "distance" between the 128-d embedding of the live face and all known embeddings. The match with the smallest distance is chosen.
* **OTP Generation:** **CSPRNG** (Cryptographically Secure Pseudo-Random Number Generator) via Python's `random` module to create a secure 6-digit code.
* **Backend & GUI:**
    * **Python 3**
    * **Tkinter:** For the desktop graphical user interface (GUI).
    * **OpenCV:** For capturing and processing real-time video from the webcam.
    * **Pillow (PIL):** For handling and displaying images within the Tkinter GUI.
    * **Twilio REST API:** For sending the OTP message to the user's WhatsApp.

---

## 🛠️ How to Set Up and Run

### 1. Prerequisites

* Python 3.8+
* A Twilio account (for OTP)
* A webcam
* `CMake` and `dlib` (these must be installed before `face_recognition`).
    * On Windows, installing `CMake` is easiest via the installer.
    * On Windows, you may need to install Microsoft C++ Build Tools.
    * Run: `pip install cmake dlib`

### 2. Installation

1.  Clone this repository:
    ```bash
    git clone https://github.com/AsadMridul/Facial-Recognition-Enabled-ATM-Security-Using-AI-ML.git
    cd Facial-Recognition-Enabled-ATM-Security-Using-AI-ML
    ```

2.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your secret keys:**
    * Create a file named `config.py` in the main folder.
    * Add your Twilio keys to it:
    ```python
    # config.py
    TWILIO_ACCOUNT_SID = "YOUR_SID_HERE"
    TWILIO_AUTH_TOKEN = "YOUR_TOKEN_HERE"
    ```

### 3. How to Use

1.  **Register yourself:** Run the app first to register your face.
    ```bash
    python gui_atm_app.py
    ```
    * Click "Register New User".
    * Enter your name (e.g., `Asad_Mridul`) and your phone number (with country code, e.g., `+8801...`).
    * Capture at least 10 photos of your face.
    * Click "Finish Registration".

2.  **Train the model:** You *must* train the model on your new photos.
    * **To train all users (first time):**
        ```bash
        python train_model.py
        ```
    * **To add *just* the new user you registered:**
        ```bash
        python update_model.py "Asad_Mridul"
        ```
        *(Use the exact name you registered with)*

3.  **Run the ATM:**
    ```bash
    python gui_atm_app.py
    ```
    * You can now log in using your name. The camera will verify your face.
