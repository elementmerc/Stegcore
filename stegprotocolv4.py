#File: Stegprotocolv4.py
#Author: Mercury
#Description: A program to perform steganography and ascon encryption on information

#Importing libraries
from tkinter import filedialog
import tkinter.messagebox as tkMessageBox
from pathlib import Path
from stego_lsb import LSBSteg
from ascon.ascon import ascon_encrypt, get_random_bytes, ascon_decrypt
import customtkinter as customtk
from os import remove

#The encryption module
def embed_text_in_image(text, image, info_type):
    '''
    Breakdown of the function:
    1. Read the contents of the text file
    2. Choose the variant of encryption (already selected)
    3. Encode both the password(associated_data) and the information
    4. Encrypt the information into a ciphertext
    5. Hide the information in the image and save
    6. Export the key and nonce to a file for decryption
    '''
    # Opening the text file and read its contents
    secret_text = Path(text).read_text(errors='ignore')

    #Preparing the components for encryption
    '''
    variant: The ascon algorithm of string type
    associated_data, key, nonce: Various keys of byte type that are used in encryption
    plaintext: The text to be embedded in byte format
    '''
    variant = "Ascon-128"
    key   = get_random_bytes(16)
    nonce = get_random_bytes(16)
    plaintext = secret_text.encode("utf-8")
    dialog = customtk.CTkInputDialog(text='Input a passphrase:', title="Passphrase")

    associated_data = (dialog.get_input()).encode("utf-8")
    if  associated_data == '':
        tkMessageBox.showerror(message='Passphrase required')
        exit()
    
    #Encrypting the text
    try:
        ciphertext = ascon_encrypt(key, nonce, associated_data, plaintext, variant)
        temp = './temp.bin'
        Path(temp).write_bytes(ciphertext)
    except:
        tkMessageBox.showerror(message="Unable to encrypt text")
        remove(temp)
        exit()

    try:
        output_image = filedialog.asksaveasfilename(title = "Save output image as", defaultextension=".png")
    except:
        tkMessageBox.showerror(message="Operation cancelled by user")
        remove(temp)

    #Using stegano to hide the text, and write the unlock codes
    try:
        processed = LSBSteg.hide_data(image, temp, output_image, 3, 9)
        remove(temp)
        processing_save = True
    except:
        tkMessageBox.showerror(message="Image is too small. Please select a larger image")
        processing_save = False

    #Writing the keys to the kingdom
    if processing_save == True:
        try:
            key_file = filedialog.asksaveasfilename(title = "Save the key as", defaultextension=".bin")
            keys_list = [key, nonce, info_type.encode("utf-8")]
            delimiter = b'ElementMerc'
            with open(key_file, 'wb') as unlock_info:
                for every_key in keys_list:
                    unlock_info.write(every_key + delimiter)
                unlock_info.close()
            tkMessageBox.showinfo(message='Embedding complete')
        except:
            tkMessageBox.showerror(message='Unable to save key file')
            remove(temp)
            remove(processed)
    
#The decryption function
def extract_text_in_image(image, authentication):
    '''
    Breakdown of the function
    1. Take in the image and authentication file
    2. Convert the authentication to a text file
    3. Break down the file to key and  nonce
    4. Extract info from image
    5. Decrypt using the authentication information
    6. Save the file
    '''
    #Getting necessary info
    delimiter = b'ElementMerc'
    with open(authentication, "rb") as reader:
        data = reader.read()
        data_list = data.split(delimiter)
    reader.close
    key = data_list[0]
    nonce = data_list[1]
    info_type = data_list[2]
    variant = "Ascon-128"
    
    #Instant decoding
    try:
        output_text_file = filedialog.asksaveasfilename(title="Save the decoded text as", defaultextension=info_type.decode("utf-8"))
    except:
        tkMessageBox.showerror('Operation cancelled by user')
        return False

    try:
        temp_file = './temp.txt'
        parse_text_as_string = LSBSteg.recover_data(image, temp_file, 3)
        image_check = True
    except IndexError:
        image_check = False
        tkMessageBox.showerror(message="No information detected in the image")
    
    if image_check == True:
        try:
            temp = Path(temp_file).read_bytes()
            dialog = customtk.CTkInputDialog(text='Input the passphrase:', title="Passphrase")
            associated_data = (dialog.get_input()).encode("utf-8")
            #Decrypting using the information
            unencrypted_text = (ascon_decrypt(key, nonce, associated_data, temp, variant)).decode("utf-8")
            password_check = True
        except:
            tkMessageBox.showerror(message="Invalid Password")

    #Saving the decoded text
    if password_check == True:
        try:
            Path(output_text_file).write_text(unencrypted_text)
            remove(temp_file)
            tkMessageBox.showinfo(message="Extraction complete")
        except:
            tkMessageBox.showerror(message="Extraction Error")

#The encoding process
def encoding():
    text_file_check = False
    text_file = filedialog.askopenfilename(title = "Select a text file",
     filetypes=[('Text files', [".txt"])])
    
    if text_file == '':
        tkMessageBox.showerror(message='No text file selected')
    elif Path(text_file).suffix != ".txt":
        tkMessageBox.showerror(message='Invalid file format')
    else:
        info_file_type = Path(text_file).suffix
        text_file_check = True

    if text_file_check == True:
        image_file = filedialog.askopenfilename(title = "Select an image", filetypes=[("Image files", ["*.png", "*.jpg", ".jpeg"])])
        if image_file == '':
            tkMessageBox.showerror(message='No image selected')
        elif Path(image_file).suffix not in [".png", ".jpg", ".jpeg"]:
            tkMessageBox.showerror(message="Invalid image format")
        else:
            embed_text_in_image(text_file, image_file, info_file_type)
    

#The decoding process
def decoding():
    encrypted_image_check = False
    encrypted_image = filedialog.askopenfilename(title="Select the encoded image", filetypes=[("Image files", "*.png")])
   
    if encrypted_image == '':
        tkMessageBox.showerror(message="No image selected")
    elif Path(encrypted_image).suffix not in [".png"]:
        tkMessageBox.showerror(message="Invalid image format")
    else:
        encrypted_image_check = True
    
    if encrypted_image_check == True:
        authentication = filedialog.askopenfilename(title="Select the authentication file",filetypes=[("Binary files", "*.bin")])
        if authentication == '':
            tkMessageBox.showerror(message='No authentication file selected')
        elif Path(authentication).suffix not in [".bin"]:
            tkMessageBox.showerror(message="Invalid authentication file")
        else:
            extract_text_in_image(encrypted_image, authentication)
