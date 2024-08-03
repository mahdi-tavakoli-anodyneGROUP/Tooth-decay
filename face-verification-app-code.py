from pathlib import Path
from tkinter import Tk, Canvas, Button, filedialog
import os
import cv2

# Initialize the global variable to store the selected file path
selected_file_path = ""


def truncate_text(text, max_width, font, canvas):
    # Measure the text width
    text_width = canvas.create_text(0, 0, text=text, font=font, anchor="nw")
    while canvas.bbox(text_width)[2] > max_width:
        text = text[:-4] + "..."
        canvas.itemconfig(text_width, text=text)
    canvas.delete(text_width)  # Clean up the temporary text item
    return text


# Function to open file explorer and display file info
def upload_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")]
    )
    if file_path:
        display_file_info(file_path)


def display_file_info(file_path):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    # Calculate the maximum width for the name to avoid overlapping
    max_name_width = 300  # Approximate width before overlapping with the size label

    # Update labels
    truncated_name = truncate_text(file_name, max_name_width, ("Inter", 17 * -1), canvas)
    canvas.itemconfig(name_label, text=truncated_name)
    canvas.itemconfig(size_label, text=f"{file_size} bytes")
    canvas.itemconfig(status_label, text="Uploaded", fill="green")

    # Store the file path in a global variable
    global selected_file_path
    selected_file_path = file_path


# Function to remove the uploaded file
def remove_file():
    global selected_file_path
    selected_file_path = ""

    # Clear the labels
    canvas.itemconfig(name_label, text="")
    canvas.itemconfig(size_label, text="")
    canvas.itemconfig(status_label, text="Nothing uploaded", fill="red")


# Function to print the saved file path or capture a photo from the camera
def check_file_path():
    global selected_file_path
    if selected_file_path:
        print(f"Selected file path: {selected_file_path}")
    else:
        print("No file selected.")


# Function to capture a photo from the camera
def capture_photo():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open video stream.")
        return

    cv2.namedWindow("Press 's' to save and 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        cv2.imshow("Press 's' to save and 'q' to quit", frame)

        key = cv2.waitKey(1)
        if key % 256 == ord('s'):
            # Save the captured frame
            file_path = "captured_image.jpg"
            cv2.imwrite(file_path, frame)
            display_file_info(file_path)
            break
        elif key % 256 == ord('q'):
            # Quit without saving
            break

    cap.release()
    cv2.destroyAllWindows()


OUTPUT_PATH = Path(__file__).parent

window = Tk()
window.geometry("760x357")
window.configure(bg="#FFFFFF")
window.title("Face Verification App")

canvas = Canvas(
    window,
    bg="#FFFFFF",
    height=357,
    width=760,
    bd=0,
    highlightthickness=0,
    relief="ridge"
)

canvas.place(x=0, y=0)
canvas.create_rectangle(
    0.0,
    94.0,
    760.0,
    178.0,
    fill="#D9D9D9",
    outline=""
)

canvas.create_rectangle(
    0.0,
    177.0,
    760.0,
    261.0,
    fill="#FFFFFF",
    outline=""
)

canvas.create_rectangle(
    0.0,
    0.0,
    760.0,
    94.0,
    fill="#E4DE62",
    outline=""
)

canvas.create_rectangle(
    0.0,
    261.0,
    760.0,
    357.0,
    fill="#D9D9D9",
    outline=""
)

canvas.create_text(
    18.0,
    28.0,
    anchor="nw",
    text="Face Verification App",
    fill="#000000",
    font=("Inter", 28 * -1)
)

# Calculate button positions to maintain equal spacing
button_width = 165  # Increased width of the buttons
button_height = 48
button_spacing = (760 - 4 * button_width) / 5

button_positions = [
    button_spacing,
    button_spacing * 2 + button_width,
    button_spacing * 3 + 2 * button_width,
    button_spacing * 4 + 3 * button_width,
]

# Replace image buttons with standard buttons
button_1 = Button(
    text="Remove File",
    borderwidth=1,
    highlightthickness=0,
    command=remove_file,
    relief="solid",
    bg="#E4DE62",
    fg="#000000",
    activebackground="#E4DE62",
    activeforeground="#000000",
    font=("Inter", 13)
)
button_1.place(
    x=button_positions[0],
    y=283.0,
    width=button_width,
    height=button_height
)

button_2 = Button(
    text="Upload File",
    borderwidth=1,
    highlightthickness=0,
    command=upload_file,
    relief="solid",
    bg="#E4DE62",
    fg="#000000",
    activebackground="#E4DE62",
    activeforeground="#000000",
    font=("Inter", 13)
)
button_2.place(
    x=button_positions[1],
    y=283.0,
    width=button_width,
    height=button_height
)

button_3 = Button(
    text="Capture from Camera",
    borderwidth=1,
    highlightthickness=0,
    command=capture_photo,
    relief="solid",
    bg="#E4DE62",
    fg="#000000",
    activebackground="#E4DE62",
    activeforeground="#000000",
    font=("Inter", 13)
)
button_3.place(
    x=button_positions[2],
    y=283.0,
    width=button_width,
    height=button_height
)

button_4 = Button(
    text="Check",
    borderwidth=1,
    highlightthickness=0,
    command=check_file_path,
    relief="solid",
    bg="#E4DE62",
    fg="#000000",
    activebackground="#E4DE62",
    activeforeground="#000000",
    font=("Inter", 13)
)
button_4.place(
    x=button_positions[3],
    y=283.0,
    width=button_width,
    height=button_height
)

canvas.create_text(
    24.0,
    124.0,
    anchor="nw",
    text="Name",
    fill="#000000",
    font=("Inter", 20 * -1)
)

canvas.create_text(
    348.0,
    124.0,
    anchor="nw",
    text="Size\n",
    fill="#000000",
    font=("Inter", 20 * -1)
)

canvas.create_text(
    624.0,
    124.0,
    anchor="nw",
    text="Status\n",
    fill="#000000",
    font=("Inter", 20 * -1)
)

# Labels to display selected file information
name_label = canvas.create_text(
    24.0,
    202.0,
    anchor="nw",
    text="",
    fill="#000000",
    font=("Inter", 17 * -1)
)

size_label = canvas.create_text(
    348.0,
    202.0,
    anchor="nw",
    text="",
    fill="#000000",
    font=("Inter", 17 * -1)
)

status_label = canvas.create_text(
    624.0,
    202.0,
    anchor="nw",
    text="Nothing uploaded",
    fill="red",
    font=("Inter", 17 * -1)
)

window.resizable(False, False)
window.mainloop()
