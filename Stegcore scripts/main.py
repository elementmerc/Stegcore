#File: main.py
#Author: Mercury
#Description: A file for the UI of stegprotocolv4.py

#Importing necessary libraries
import stegprotocolv4 as Sv4
import customtkinter as customtk
from PIL import Image, ImageTk
from pathlib import Path

# Base directory of this script— to ensure assets resolve correctly
# regardless of where Python is invoked from
BASE_DIR = Path(__file__).parent

#Setting the theme
customtk.set_appearance_mode("System")
customtk.set_default_color_theme("dark-blue")

class StegGUI(customtk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Stegcore")

        # iconbitmap() only works on Windows with .ico files.
        # iconphoto() + Pillow works cross-platform and accepts .ico directly.
        icon_image = Image.open(BASE_DIR / "Stag.ico")
        self._icon = ImageTk.PhotoImage(icon_image)  # Keep reference to avoid GC
        self.iconphoto(True, self._icon)

        frame = customtk.CTkFrame(self)
        frame.pack(pady=20, padx=20, fill='both', expand=True)

        #The Encoding button
        self.encode_button = customtk.CTkButton(
            master=frame, command=self.encoding_event,
            text='Embed',
            font=('Consolas',19))
        self.encode_button.pack(padx=100, pady=30)

        #The decoding button
        self.decode_button = customtk.CTkButton(
            master=frame, command=self.decoding_event,
            text='Extract',
            font=('Consolas', 19))
        self.decode_button.pack(padx=100, pady=50)


    def encoding_event(self):
        Sv4.encoding()
    
    def decoding_event(self):
        Sv4.decoding()

if __name__ == "__main__":
    app = StegGUI()
    app.mainloop()