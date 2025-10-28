import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, Label, Entry, Button
from PIL import Image, ImageTk
import cv2
import face_recognition
import numpy as np
import os
import pickle
import random
import time
from datetime import datetime
from twilio.rest import Client  
import shutil 
import config 

# --- Configuration ---
ENCODINGS_FILE = "encodings.pickle"
UNAUTHORIZED_ACCESS_DIR = "unauthorized_access"
PHONE_NUMBERS_FILE = "phone_numbers.txt"
DATASET_PATH = "dataset"
TOLERANCE = 0.55
SCALE = 0.25
VERIFICATION_TIMEOUT = 20  
try:
    # Initialize client from the imported config file
    twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    print("[INFO] Twilio client initialized from config file.")
except Exception as e:
    print(f"[ERROR] Twilio client failed to initialize: {e}")
    print("[INFO] Make sure config.py exists and keys are correct.")
    twilio_client = None
# ----------------------------------------

if not os.path.exists(UNAUTHORIZED_ACCESS_DIR):
    os.makedirs(UNAUTHORIZED_ACCESS_DIR)
if not os.path.exists(DATASET_PATH):
    os.makedirs(DATASET_PATH)


print("[INFO] Loading face encodings...")
try:
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    known_encodings = data["encodings"]
    known_names = data["names"]
    print(f"[INFO] Loaded {len(known_names)} known faces.")
except FileNotFoundError:
    print(f"[ERROR] '{ENCODINGS_FILE}' not found. Please run train_model.py or update_model.py.")
    known_encodings = []
    known_names = []
except Exception as e:
    print(f"[ERROR] Error loading {ENCODINGS_FILE}: {e}")
    known_encodings = []
    known_names = []


print("[INFO] Loading phone numbers...")
phone_book = {}
try:
   
    with open(PHONE_NUMBERS_FILE, mode='r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            parts = line.split(',')
            if len(parts) >= 2: # <-- Back to 2 parts
                # Use .strip() on each part to remove extra spaces
                name = parts[0].strip()
                number = parts[1].strip()
                
                if name: # Ensure name is not empty
                        phone_book[name.lower()] = number

    print(f"[INFO] Loaded {len(phone_book)} user phone numbers.")
    
        
except FileNotFoundError:
    print(f"[WARNING] '{PHONE_NUMBERS_FILE}' not found. Register users to create it.")
except Exception as e:
    print(f"[ERROR] Error reading {PHONE_NUMBERS_FILE}: {e}")


# --- Helper Functions (Saving, OTP) ---

def send_otp(phone_number):
    """
    Sends a real OTP via the basic Twilio Messaging API using the WhatsApp Sandbox.
    """
    print("-----------------------------------------")
    print(f"[INFO] Attempting to send WhatsApp OTP to {phone_number} via Messaging API...")
    
    # --- 1. Get your Twilio Sandbox number ---
    # This is the shared number from Twilio, e.g., +14155238886
    TWILIO_SANDBOX_NUMBER = "whatsapp:+14155238886" 
    
    # --- 2. Generate our own OTP ---
    otp_code = str(random.randint(100000, 999999))
    body = f"Your Secure ATM verification code is: {otp_code}"
    
    # --- 3. Format the 'to' number ---
    to_whatsapp_number = f"whatsapp:{phone_number}"

    # --- 4. Check if client is configured (Simulation Mode) ---
    if not twilio_client or not phone_number.startswith('+'):
        print("[SIMULATION] Twilio client not configured or invalid number (must start with +).")
        print(f"[SIMULATION] Simulated OTP is '{otp_code}'")
        print("-----------------------------------------")
        messagebox.showinfo("OTP Sent (Simulation)", f"OTP '{otp_code}' has been sent to WhatsApp ({phone_number}).\n(Twilio not configured)")
        return otp_code # <-- Return the simulated OTP
    
    # --- 5. Send the real message ---
    try:
        message = twilio_client.messages.create(
            from_=TWILIO_SANDBOX_NUMBER,
            body=body,
            to=to_whatsapp_number
        )
        
        print(f"[SUCCESS] Twilio WhatsApp message sent! SID: {message.sid}")
        messagebox.showinfo("OTP Sent", "An OTP has been sent to your WhatsApp.")
        return otp_code 
        
    except Exception as e:
        print(f"[ERROR] Twilio failed to send WhatsApp message: {e}")
        messagebox.showerror("OTP Error", f"Could not send OTP: {e}\n\n1. Did you join the Sandbox?\n2. Is your Sandbox number in the code correct?")
        return "ERROR" # <-- Return an error state


def save_unauthorized_access(frame, owner_name):
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}_{owner_name or 'unknown'}.jpg"
    filepath = os.path.join(UNAUTHORIZED_ACCESS_DIR, filename)
    cv2.imwrite(filepath, frame)
    print(f"[ALERT] Unauthorized access attempt recorded: {filename}")



def draw_label(frame, text, left, top, right, bottom, color):
    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
    cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
    cv2.putText(frame, text, (left + 6, bottom - 8), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 1, cv2.LINE_AA)

def put_banner(frame, text, y=40, color=(0,0,255)):
    cv2.putText(frame, text, (30, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA)


# --- Main GUI Application Class ---

class AtmApp(tk.Tk):
    """Main application class to manage frames (screens)."""
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.titlefont = tkfont.Font(family='Helvetica', size=18, weight="bold")
        self.labelfont = tkfont.Font(family='Helvetica', size=12)
        self.entryfont = tkfont.Font(family='Helvetica', size=12)

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        # --- ADDED AmountEntryPage ---
        for F in (LoginPage, FacialVerificationPage, OtpPage, TransactionPage, RegistrationPage, AmountEntryPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.current_user_name = tk.StringVar()
        self.current_user_phone = tk.StringVar()
        self.generated_otp = tk.StringVar() # This will store the REAL or SIMULATED otp
        self.current_transaction_type = tk.StringVar() # <-- ADDED THIS LINE

        self.title("Secure AI ATM")
        self.geometry("1000x700") 
        self.show_frame("LoginPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, 'on_show'):
            frame.on_show()

    def get_frame(self, page_name):
        return self.frames[page_name]


# --- Screen 1: Login Page (NO PIN) ---

class LoginPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        # --- Left Side: ATM Image ---
        left_frame = tk.Frame(self, width=500, bg='white')
        left_frame.pack(side="left", fill="both", expand=True)
        
        try:
            img = Image.open("Atm.jpg") 
            img = img.resize((500, 600), Image.LANCZOS)
            self.atm_image = ImageTk.PhotoImage(img)
            img_label = Label(left_frame, image=self.atm_image)
            img_label.pack(pady=50)
        except FileNotFoundError:
            Label(left_frame, text="ATM Image Not Found\n(Make sure Atm.jpg is in the folder)", font=controller.labelfont).pack(pady=50, padx=20)


        # --- Right Side: Login Form ---
        right_frame = tk.Frame(self, width=500)
        right_frame.pack(side="right", fill="both", expand=True)
        
        form_frame = tk.Frame(right_frame)
        form_frame.place(relx=0.5, rely=0.5, anchor="center")

        Label(form_frame, text="Login to ATM System", font=controller.titlefont).pack(pady=20)

        Label(form_frame, text="Card Owner Name (Case-Sensitive):", font=controller.labelfont).pack(pady=(10, 5))
        self.name_entry = Entry(form_frame, font=controller.entryfont, width=30)
        self.name_entry.pack(pady=5, ipady=4)

        

        self.notification_label = Label(form_frame, text="", font=controller.labelfont, fg="red")
        self.notification_label.pack(pady=10)

        Button(form_frame, text="Login", font=controller.labelfont, bg="#4CAF50", fg="white", width=25, command=self.attempt_login).pack(pady=10, ipady=5)
        Button(form_frame, text="Register New User", font=controller.labelfont, bg="#008CBA", fg="white", width=25, command=lambda: controller.show_frame("RegistrationPage")).pack(pady=10, ipady=5)

    def attempt_login(self):
        entered_name_cased = self.name_entry.get().strip() # e.g., "John_Doe"
        entered_name_lower = entered_name_cased.lower() # e.g., "john_doe"

        if not entered_name_cased:
            self.notification_label.config(text="Please enter a name.")
            return

        
        
        # 1. Check if user is in the *trained* face model
        if entered_name_cased in known_names:
            print(f"[INFO] Card for '{entered_name_cased}' inserted.")
            self.controller.current_user_name.set(entered_name_cased)
            
            # Find the user's phone number
            phone = phone_book.get(entered_name_lower)
            if not phone:
                print(f"[WARNING] No phone number found for {entered_name_cased}")
                self.controller.current_user_phone.set("")
            else:
                self.controller.current_user_phone.set(phone)

            # Move to the facial verification page
            self.controller.show_frame("FacialVerificationPage")
        else:
            # Check if they are in the phone book but just not trained
            if entered_name_lower in phone_book:
                print(f"[ERROR] Name '{entered_name_cased}' not registered in face model.")
                self.notification_label.config(text="Name not registered in face model.\nPlease re-train.")
            else:
                print(f"[ERROR] Name '{entered_name_cased}' not found in system.")
                self.notification_label.config(text="Name not found in system.")

    def on_show(self):
        # Clear fields when showing the page
        self.name_entry.delete(0, 'end')
        self.notification_label.config(text="")


# --- Screen 2: Facial Verification Page ---
class FacialVerificationPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.cap = None
        self.access_granted = False
        self.start_time = 0
        self.last_frame = None
        self.stop_loop = False

        Label(self, text="Facial Verification", font=controller.titlefont).pack(pady=10)
        Label(self, text="Please look directly at the camera.", font=controller.labelfont).pack()

        self.video_label = Label(self)
        self.video_label.pack(pady=10, padx=20)

        self.status_label = Label(self, text="Initializing Camera...", font=controller.labelfont, fg="blue")
        self.status_label.pack(pady=10)

        Button(self, text="Cancel", font=controller.labelfont, bg="#f44336", fg="white", command=self.cancel_verification).pack(pady=10)

    def on_show(self):
        print("[INFO] Opening camera for verification...")
        self.access_granted = False
        self.start_time = time.time()
        self.status_label.config(text=f"You have {VERIFICATION_TIMEOUT} seconds...", fg="blue")
        self.stop_loop = False
        
        self.cap = cv2.VideoCapture(0) 
        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", "Could not open camera. Check permissions.")
            self.controller.show_frame("LoginPage")
            return
        
        self.update_frame()

    def cancel_verification(self):
        self.stop_loop = True
        if self.cap:
            self.cap.release()
            
        if not self.access_granted and self.last_frame is not None:
            owner_name = self.controller.current_user_name.get()
            print("[INFO] Verification cancelled by user.")
            save_unauthorized_access(self.last_frame, owner_name)
            
        self.controller.show_frame("LoginPage")

    def update_frame(self):
        if self.stop_loop:
            if self.cap:
                self.cap.release()
            return 

        elapsed = time.time() - self.start_time
        if elapsed > VERIFICATION_TIMEOUT:
            self.handle_failure("Verification Timed Out")
            return
        
        self.status_label.config(text=f"Time remaining: {VERIFICATION_TIMEOUT - int(elapsed)}s")

        try:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                print("[ERROR] Camera read failed.")
                self.after(20, self.update_frame) 
                return
        except Exception as e:
            print(f"[ERROR] Camera capture exception: {e}")
            self.after(20, self.update_frame)
            return

        self.last_frame = frame.copy() 
        processed_frame = frame.copy()

        small_frame = cv2.resize(frame, (0, 0), fx=SCALE, fy=SCALE)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
        
        if len(face_locations) > 1:
            # play_buzzer() # <-- REMOVED
            put_banner(processed_frame, "Multiple Faces Detected!", y=50, color=(0,0,255))
            for (top, right, bottom, left) in face_locations:
                top, right, bottom, left = int(top / SCALE), int(right / SCALE), int(bottom / SCALE), int(left / SCALE)
                draw_label(processed_frame, "Multiple", left, top, right, bottom, (0, 0, 255))
        
        elif len(face_locations) == 1:
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            (top, right, bottom, left) = face_locations[0]
            top, right, bottom, left = int(top / SCALE), int(right / SCALE), int(bottom / SCALE), int(left / SCALE)
            
            display_name = "Unknown"
            color = (0, 0, 255) 
            
            if face_encodings:
                face_encoding = face_encodings[0]
                matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=TOLERANCE)
                
                if True in matches:
                    face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                    best_idx = int(np.argmin(face_distances))
                    
                    if matches[best_idx]:
                        matched_name = known_names[best_idx]
                        display_name = matched_name
                        
                        if matched_name == self.controller.current_user_name.get():
                            color = (0, 200, 0) # Green
                            self.access_granted = True
                        else:
                            display_name = "Mismatch"
                            color = (0, 0, 255) # Red
            
            draw_label(processed_frame, display_name, left, top, right, bottom, color)
        
        else:
            put_banner(processed_frame, "No face detected.", y=50, color=(0, 165, 255))

        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_frame)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk 
        self.video_label.config(image=imgtk)

        if self.access_granted:
            self.handle_success()
            return
        
        self.after(20, self.update_frame) 

    def handle_success(self):
        print(f"\n[SUCCESS] Welcome, {self.controller.current_user_name.get()}! Face verified.")
        self.status_label.config(text="Access Granted!", fg="green")
        self.stop_loop = True
        if self.cap:
            self.cap.release()
            
        messagebox.showinfo("Success", "Face Verified. You can now proceed.")
        # --- GO TO NEW MAIN MENU ---
        self.controller.show_frame("TransactionPage") # This is now the main menu

    def handle_failure(self, reason=""):
        print(f"\n[ACCESS DENIED] {reason}")
        self.status_label.config(text=f"Access Denied: {reason}", fg="red")
        self.stop_loop = True
        if self.cap:
            self.cap.release()
        
        if self.last_frame is not None:
            save_unauthorized_access(self.last_frame, self.controller.current_user_name.get())
        
        owner_phone = self.controller.current_user_phone.get()
        if owner_phone:
            if messagebox.askyesno("Verification Failed", "Authorize transaction via OTP?"):
                # --- THIS BLOCK IS NOW CORRECT ---
                result = send_otp(owner_phone)
                
                if result == "ERROR":
                    self.controller.show_frame("LoginPage")
                    return

                self.controller.generated_otp.set(result)
                self.controller.show_frame("OtpPage")
            else:
                messagebox.showerror("Access Denied", "Transaction Cancelled.")
                self.controller.show_frame("LoginPage")
        else:
            messagebox.showerror("Access Denied", "Facial recognition failed and no phone number on file.")
            self.controller.show_frame("LoginPage")


# --- Screen 3: OTP Page ---
class OtpPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        Label(self, text="OTP Verification", font=controller.titlefont).pack(pady=20)
        Label(self, text="An OTP was sent to your WhatsApp.", font=controller.labelfont).pack(pady=10) # <-- Updated text

        self.otp_entry = Entry(self, font=controller.entryfont, width=20)
        self.otp_entry.pack(pady=10, ipady=5)
        
        self.notification_label = Label(self, text="", font=controller.labelfont, fg="red")
        self.notification_label.pack(pady=5)

        Button(self, text="Verify OTP", font=controller.labelfont, bg="#4CAF50", fg="white", command=self.verify_otp).pack(pady=10, ipady=5)
        Button(self, text="Cancel", font=controller.labelfont, bg="#f44336", fg="white", command=lambda: controller.show_frame("LoginPage")).pack(pady=5, ipady=5)

    def on_show(self):
        self.otp_entry.delete(0, 'end')
        self.notification_label.config(text="")
        
    def verify_otp(self):
        user_otp = self.otp_entry.get().strip()
        correct_otp = self.controller.generated_otp.get() # This is the code we returned from send_otp

        if not user_otp:
            self.notification_label.config(text="Please enter the OTP.")
            return

        # --- This is now a simple string comparison ---
        if user_otp == correct_otp:
            print("\n[SUCCESS] OTP verified. Access granted.")
            # --- GO TO NEW MAIN MENU ---
            self.controller.show_frame("TransactionPage") # This is now the main menu
        else:
            print("\n[FAILURE] Incorrect OTP.")
            self.notification_label.config(text="Incorrect OTP. Try again.")
            

# --- Screen 4: Main Menu Page ---
# (Replaces the old TransactionPage)
class TransactionPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        self.welcome_label = Label(self, text="", font=controller.titlefont, fg="green")
        self.welcome_label.pack(pady=40)
        
        Label(self, text="Please select a transaction:", font=controller.labelfont).pack(pady=20)
        
        # --- New Button Layout ---
        button_frame = tk.Frame(self)
        button_frame.pack()
        
        Button(button_frame, text="Withdraw", font=controller.labelfont, bg="#008CBA", fg="white", width=20, height=2,
               command=lambda: self.go_to_amount_entry("Withdrawal")).pack(side="left", padx=20, pady=20)
               
        Button(button_frame, text="Deposit", font=controller.labelfont, bg="#008CBA", fg="white", width=20, height=2,
               command=lambda: self.go_to_amount_entry("Deposit")).pack(side="right", padx=20, pady=20)
        
        # --- End Session Button ---
        Button(self, text="End Session", font=controller.labelfont, bg="#f44336", fg="white", width=20,
               command=lambda: controller.show_frame("LoginPage")).pack(pady=50, ipady=10)
        
    def go_to_amount_entry(self, trans_type):
        # Set the transaction type, then show the amount page
        self.controller.current_transaction_type.set(trans_type)
        self.controller.show_frame("AmountEntryPage")
        
    def on_show(self):
        user = self.controller.current_user_name.get()
        self.welcome_label.config(text=f"Welcome, {user}!")


# --- Screen 4.5: Amount Entry Page ---
# (This is the new page)
class AmountEntryPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.title_label = Label(self, text="", font=controller.titlefont)
        self.title_label.pack(pady=20)
        
        Label(self, text="Please enter the amount:", font=controller.labelfont).pack(pady=10)

        self.amount_entry = Entry(self, font=controller.entryfont, width=20)
        self.amount_entry.pack(pady=10, ipady=5)
        
        self.notification_label = Label(self, text="", font=controller.labelfont, fg="red")
        self.notification_label.pack(pady=5)

        Button(self, text="Confirm", font=controller.labelfont, bg="#4CAF50", fg="white", width=15, command=self.process_transaction).pack(pady=10, ipady=5)
        # --- Changed Cancel button target ---
        Button(self, text="Cancel", font=controller.labelfont, bg="#f44336", fg="white", width=15, command=lambda: controller.show_frame("TransactionPage")).pack(pady=5, ipady=5)

    def on_show(self):
        # Clear the form
        self.amount_entry.delete(0, 'end')
        self.notification_label.config(text="")
        
        # Set the title based on the transaction type
        trans_type = self.controller.current_transaction_type.get()
        self.title_label.config(text=trans_type)
        
    def process_transaction(self):
        amount_str = self.amount_entry.get()
        trans_type = self.controller.current_transaction_type.get()
        
        try:
            amount = int(amount_str)
            if amount <= 0:
                self.notification_label.config(text="Amount must be greater than zero.")
                return
                
            # --- This is where the transaction is "successful" ---
            
            # Show the "congratulation message"
            messagebox.showinfo("Success", f"{trans_type} of ${amount} was successful!")
            
            # Go back to the main menu
            # --- Changed target page ---
            self.controller.show_frame("TransactionPage") 
            
        except ValueError:
            self.notification_label.config(text="Invalid amount. Please enter numbers only.")


# --- Screen 5: Registration Page 

class RegistrationPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.cap = None
        self.stop_loop = False
        self.current_frame = None 
        self.capture_count = 0

        # --- Left Side: Form ---
        left_frame = tk.Frame(self, width=400)
        left_frame.pack(side="left", fill="y", padx=20, pady=20)

        Label(left_frame, text="Register New User", font=controller.titlefont).pack(pady=20)
        
        Label(left_frame, text="Full Name (e.g., John_Doe):", font=controller.labelfont).pack(anchor="w")
        self.name_entry = Entry(left_frame, font=controller.entryfont, width=30)
        self.name_entry.pack(pady=5, ipady=4, fill="x")

        Label(left_frame, text="Phone (e.g., +880123456789):", font=controller.labelfont).pack(anchor="w")
        self.phone_entry = Entry(left_frame, font=controller.entryfont, width=30)
        self.phone_entry.pack(pady=5, ipady=4, fill="x")
        
        
        
        self.capture_button = Button(left_frame, text="Capture Face (0/10)", font=controller.labelfont, bg="#FF9800", fg="white", command=self.capture_face)
        self.capture_button.pack(pady=20, ipady=8, fill="x")
        
        self.status_label = Label(left_frame, text="Enter details and look at camera.", font=controller.labelfont)
        self.status_label.pack(pady=10)
        
        Button(left_frame, text="Finish Registration", font=controller.labelfont, bg="#4CAF50", fg="white", command=self.finish_registration).pack(pady=10, ipady=8, fill="x")
        Button(left_frame, text="Cancel", font=controller.labelfont, bg="#f44336", fg="white", command=self.cancel_registration).pack(pady=10, ipady=8, fill="x")

        # --- Right Side: Camera ---
        right_frame = tk.Frame(self, width=600)
        right_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        Label(right_frame, text="Registration Camera", font=controller.titlefont).pack(pady=10)
        self.video_label = Label(right_frame)
        self.video_label.pack()

    def on_show(self):
        self.name_entry.delete(0, 'end')
        self.phone_entry.delete(0, 'end')
        self.status_label.config(text="Enter details and look at camera.", fg="black")
        self.capture_count = 0
        self.capture_button.config(text=f"Capture Face ({self.capture_count}/10)", state="normal")
        self.stop_loop = False
        
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", "Could not open camera.")
            return
        self.update_registration_frame()

    def update_registration_frame(self):
        if self.stop_loop:
            if self.cap:
                self.cap.release()
            return

        ret, frame = self.cap.read()
        if not ret:
            self.after(20, self.update_registration_frame)
            return
        
        self.current_frame = frame.copy() 
        
        (h, w) = frame.shape[:2]
        cv2.rectangle(frame, (w//4, h//4), (w*3//4, h*3//4), (0, 255, 0), 2)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_frame)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.config(image=imgtk)
        
        self.after(20, self.update_registration_frame)

    def capture_face(self):
        name = self.name_entry.get().strip()
        if not name:
            self.status_label.config(text="Please enter a name first!", fg="red")
            return
            
        if self.current_frame is None:
            self.status_label.config(text="Camera not ready. Try again.", fg="red")
            return
            
        person_dir = os.path.join(DATASET_PATH, name)
        os.makedirs(person_dir, exist_ok=True)
        
        self.capture_count += 1
        filename = f"{name}_{self.capture_count:02d}.png"
        filepath = os.path.join(person_dir, filename)
        
        try:
            cv2.imwrite(filepath, self.current_frame)
            print(f"[INFO] Saved registration photo: {filepath}")
            self.status_label.config(text=f"Captured image {self.capture_count}/10", fg="green")
            self.capture_button.config(text=f"Capture Face ({self.capture_count}/10)")
            
            if self.capture_count >= 10:
                self.status_label.config(text="Sufficient images captured. Click Finish.", fg="blue")
                self.capture_button.config(state="disabled")

        except Exception as e:
            print(f"[ERROR] Could not save image: {e}")
            self.status_label.config(text=f"Error saving image: {e}", fg="red")

    def stop_camera(self):
        self.stop_loop = True
        if self.cap:
            self.cap.release()
            
    def finish_registration(self):
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        # --- PIN REMOVED ---

        if self.capture_count < 3: 
            self.status_label.config(text="Please capture at least 3 photos.", fg="red")
            return
            
        if not name or not phone:
            self.status_label.config(text="Please fill out all fields (Name, Phone).", fg="red")
            return
            
        # Save phone number
        try:
            user_exists = False
            name_lower = name.lower()
            if os.path.exists(PHONE_NUMBERS_FILE):
                with open(PHONE_NUMBERS_FILE, "r", encoding='utf-8-sig') as f:
                    for line in f:
                        if line.startswith(f"{name_lower},"):
                            user_exists = True
                            break
            
            if user_exists:
                print(f"[INFO] User {name} already in phone_book. Skipping save.")
                self.status_label.config(text=f"User {name} already exists.", fg="red")
                phone_book[name_lower] = phone # Update live book
            else:
                with open(PHONE_NUMBERS_FILE, "a", encoding='utf-8') as f:
                    # --- UPDATE FILE FORMAT (NO PIN) ---
                    f.write(f"\n{name_lower},{phone}") 
                phone_book[name_lower] = phone # Update live phone book
                print(f"[INFO] Added {name} with phone {phone} to {PHONE_NUMBERS_FILE}")

        except Exception as e:
            print(f"[ERROR] Could not save phone number: {e}")
            messagebox.showerror("File Error", f"Could not save phone number: {e}")
            return
            
        self.stop_camera()
        
        messagebox.showinfo("Registration Successful!",
            f"User {name} registered.\n\n"
            f"NOTE: You must now re-train the model.\n"
            f"Please run 'update_model.py \"{name}\"' from your terminal.")
            
        self.controller.show_frame("LoginPage")

    def cancel_registration(self):
        self.stop_camera()
        name = self.name_entry.get().strip()
        if name and self.capture_count > 0:
            if messagebox.askyesno("Cancel?", "Cancel registration and delete captured photos?"):
                person_dir = os.path.join(DATASET_PATH, name)
                if os.path.exists(person_dir):
                    try:
                        shutil.rmtree(person_dir)
                        print(f"[INFO] Removed directory: {person_dir}")
                    except Exception as e:
                        print(f"[ERROR] Could not remove dir: {e}")
        self.controller.show_frame("LoginPage")


# --- Run the Application ---

if __name__ == "__main__":
    app = AtmApp()
    app.mainloop()