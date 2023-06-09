<img width="509" alt="image" src="https://user-images.githubusercontent.com/121883945/230636687-20e27227-23be-4a5e-9905-2122f49d1dd7.png">

**Stegcore** is a steganography software that uses Ascon128 and the 3-lsb to hide
text data behind images.

## ReadMe Details
1. What is Stegcore?
2. What's the difference?
3. How to use
4. Other tools

## What is Stegcore?
Stegcore is a crypto-stego application that carries out steganography using text
cryptography and the least significant bit method to secure text data such as IP
addresses, source codes and other critical information.

## What's the difference?
In contrast to conventional steganography software, Stegcore uses the the Ascon
lightweight cryptography algorithm and LSB technique to hide data. The image
below explains the process.

![Proposed Model](https://user-images.githubusercontent.com/121883945/230630515-d4cab07b-2983-4418-a7d0-2ac5b00b19e4.png)

Supported image formats are (*.png) and (*.jpg).

## How to use:
Download all files in the 'Stegcore scripts' directory and run the main.py file.

## How to use
There are
1. Embed: To hide the text data in the image
2. Extract: To extract the text data from the image

## Other tools
In the 'Image tests' folder, there is a script that can be used to check the
SSIM, PSNR and payload capacity of images.

SSIM - Structure Similarity Index measure
The SSIM index compares the structural information of an original image and a
modified image, such as an image with steganographic content. It measures the 
similarity between the two images based on three factors: luminance, contrast,
and structure. Best range: 0.95 - 1.00

PSNR - Peak-to-Signal Ratio
PSNR (Peak Signal-to-Noise Ratio) is a widely used metric for measuring the
quality of a signal, particularly in image and video compression applications.
It measures the ratio of the maximum power of a signal to the power of its 
associated noise. A higher PSNR value indicates a better-quality signal.
Best range: ≥35

Payload Capacity
Payload capacity refers to the amount of data that can be hidden or embedded
within a cover object, such as an image, audio file, or video, without 
significantly altering its original appearance or functionality. It represents
the maximum size of the secret message or information that can be concealed 
within a carrier object.
