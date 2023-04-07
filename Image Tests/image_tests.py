#File: image_tests.py
#Author: Mercury
#Description: A script to check the SSIM, PSNR and payload capacity of images

'''
SSIM - Structure Similarity Index measure - Best range: 0.95 - 1.00
PSNR - Peak-to-Signal Ratio - Best range: ≥35
Payload Capacity - Best range: Determined by number of bits chosen
'''

#Importing the necessary libraries
from SSIM_PIL import compare_ssim
from PIL import Image
import math
import cv2
from stego_lsb import LSBSteg
from customtkinter import filedialog

#For SSIM
def ssim(original_image, new_image):
    #Prepping the images (Insert the image paths)
    first_image = Image.open(original_image)
    second_image = Image.open(new_image)
    #The engines
    ssim = compare_ssim(first_image, second_image)
    #Mission accomplished
    print(f"The SSIM of the two given images is {ssim}\n")

#For psnr
def psnr(original_image, new_image):
    original = cv2.imread(original_image)
    generated = cv2.imread(new_image)
    #Converting the images to RGBA
    original_image_rgba = cv2.cvtColor(original, cv2.COLOR_BGR2RGBA)
    generated_image_rgba = cv2.cvtColor(generated, cv2.COLOR_BGR2RGBA)
    # Calculating the mean squared error (MSE)
    mse = ((original_image_rgba - generated_image_rgba)**2).mean()
    #Calculating the maximum pixel value
    max_pixel_value = 255.0
    #Calculating the PSNR
    if mse == 0:
        psnr = float('inf')
    else:
        psnr = 20 * math.log10(max_pixel_value / math.sqrt(mse))
    #Mission accomplished
    print(f"PSNR: {psnr}\n")

#For payload checking
def payload_check(original_image, text_file_path, lsb):
    #The engine
    payload_capacity = LSBSteg.analysis(original_image, text_file_path, lsb)
    #Mission acoomplished
    print(f"payload_capacity\n")

#To select an option
def option_selection():
    print('''Select a number or use 'exit' to quit:
    1. SSIM
    2. PSNR
    3. Payload Check
    ''')

#Hitting the ignition
def main():
    print("Image tests tool")
    while True:
        option_selection()
        option = eval(input('Selection (1, 2 or 3): '))
        if option == 1:
            original_image = filedialog.askopenfilename(
                title='Select the original image',
                filetypes=[("Image files", ["*.png", "*.jpg"])])
            new_image = filedialog.askopenfilename(
                title='Select the modified image',
                filetypes=[("Image files", ["*.png", "*.jpg"])])
            ssim(original_image, new_image)
        elif option == 2:
            original_image = filedialog.askopenfilename(
                title='Select the original image',
                filetypes=[("Image files", ["*.png", "*.jpg"])])
            new_image = filedialog.askopenfilename(
                title='Select the modified image',
                filetypes=[("Image files", ["*.png", "*.jpg"])])
            psnr(original_image, new_image)
        elif option == 3:
            image = filedialog.askopenfilename(
                title='Select the Carrier Image',
                filetypes=[("Image files", ["*.png", "*.jpg"])])
            text_file = filedialog.askopenfilename(
                title='Select the Payload',
                filetypes=[("Text files", "*.txt")])
            lsb = eval(input("Choose how many bits (1-8): "))
            if lsb not in range(1, 9):
                print("Choose a number from 1 to 8")
                break
            payload_check(image, text_file, lsb)
        elif option in ['exit', 'break', 'quit']:
            exit()
        else:
            print("Give a valid input")

#In Jacob Zuma's voice: 'In the benninging'
if __name__ == "__main__":
    main()