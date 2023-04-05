#File: ssim_psnr_payloadcheck.py
#Author: Mercury
#Description: A script to check the SSIM, PSNR and payload capacity of images

'''
Terms
SSIM - Structure Similarity Index measure
#######

PSNR - Peak-to-Signal...
########
Payload Capacity
#########
'''

#Importing the necessary libraries
from SSIM_PIL import compare_ssim
from PIL import Image
import math
import cv2
from stego_lsb import LSBSteg

def main():
    #What to edit
    original_image = "./Test files/test_image_4.jpg"
    new_image = "./Test files/output_4.png"
    text_file_path = "./Test files/Large_text.txt"
    lsb = 3

    #For SSIM
    #Prepping the images (Insert the image paths)
    first_image = Image.open(original_image)
    second_image = Image.open(new_image)
    #The engines
    ssim = compare_ssim(first_image, second_image)
    #Mission accomplished
    print(f"The SSIM of the two given images is {ssim}")

    #For psnr
    original = cv2.imread(original_image)
    generated = cv2.imread(new_image)
    # convert the images to RGBA
    original_image_rgba = cv2.cvtColor(original, cv2.COLOR_BGR2RGBA)
    generated_image_rgba = cv2.cvtColor(generated, cv2.COLOR_BGR2RGBA)
    # calculate the mean squared error (MSE)
    mse = ((original_image_rgba - generated_image_rgba)**2).mean()
    # calculate the maximum pixel value
    max_pixel_value = 255.0
    # calculate the PSNR
    if mse == 0:
        psnr = float('inf')
    else:
        psnr = 20 * math.log10(max_pixel_value / math.sqrt(mse))
    #Mission accomplished
    print(f"PSNR: {psnr}")

    #For payload checking
    #The engine
    payload_capacity = LSBSteg.analysis(original_image, text_file_path, lsb)
    #Mission acoomplished
    print(payload_capacity)

#Let's begin
main()