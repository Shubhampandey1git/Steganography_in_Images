# Steganography_in_Images

from PIL import Image
from flask import Flask, request, send_file, render_template
import os
from io import BytesIO

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['STORAGE_FOLDER'] = 'storage/'

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STORAGE_FOLDER'], exist_ok=True)

# Redering index.html
@app.route('/')
def index():
    return render_template('index.html')

def to_binary(data):
    # Convert data to binary format.
    return ''.join(format(ord(char), '08b') for char in data)

def is_change_too_much(original_pixel, new_pixel, threshold=10):
    # Check if the change between original and new pixel is too much.
    return any(abs(original_pixel[i] - new_pixel[i]) > threshold for i in range(3))

def embed_message(image, message):
    # Embed a secret message into an image using LSB steganography.
    binary_message = to_binary(message) + '1111111111111110'  # End of message delimiter(secret can not be this)
    data_index = 0

    # Create a new image object
    pixels = list(image.getdata())
    original_pixels = pixels.copy()  # Keep the original pixel data for comparison

    def backtrack(index):
        nonlocal data_index
        if data_index >= len(binary_message):
            return True  # Successfully embedded the entire message
        
        if index >= len(pixels):
            return False  # Out of pixels to use
        
        pixel = list(pixels[index])
        # Try to embed the message bit by bit
        for j in range(3):  # RGB
            if data_index < len(binary_message):
                new_pixel_value = (pixel[j] & ~1) | int(binary_message[data_index])
                if is_change_too_much(original_pixels[index], (new_pixel_value, pixel[1], pixel[2])):
                    # If change is too much, skip this bit
                    continue
                pixel[j] = new_pixel_value
                data_index += 1

        # Update the pixel only if we succeeded
        pixels[index] = tuple(pixel)

        # Recursively attempt to embed the rest of the message
        if backtrack(index + 1):
            return True
        
        # If failed, backtrack by resetting data_index
        for j in range(3):
            if data_index > 0:
                data_index -= 1
                pixel[j] = original_pixels[index][j]  # Restore original pixel value
        
        return backtrack(index)  # Try next pixel

    backtrack(0)  # Start embedding from the first pixel

    # Save the modified image
    stego_image = Image.new(image.mode, image.size)
    stego_image.putdata(pixels)
    return stego_image


def extract_message(original_image, stego_image):
    # Extract a hidden message from an image using the original image as reference.
    binary_message = ''
    original_pixels = list(original_image.getdata())
    stego_pixels = list(stego_image.getdata())

    for original_pixel, stego_pixel in zip(original_pixels, stego_pixels):
        # Extract the least significant bit from each channel
        binary_message += ''.join(str(stego_channel & 1) for stego_channel in stego_pixel[:3])

    # Split by the delimiter and convert to string
    message = ''
    for i in range(0, len(binary_message), 8):
        byte = binary_message[i:i + 8]
        if byte == '11111111':
            break
        message += chr(int(byte, 2))

    return message

# Main
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return 'No file part', 400

    file = request.files['image']
    message = request.form['message']

    if file.filename == '':
        return 'No selected file', 400

    if file:
        image = Image.open(file.stream)
        stego_image = embed_message(image, message)

        # Save the stego image to a BytesIO object
        byte_io = BytesIO()
        stego_image.save(byte_io, 'PNG')
        byte_io.seek(0)

        return send_file(byte_io, mimetype='image/png', as_attachment=True, download_name='stego_image.png')


@app.route('/extract', methods=['POST'])
def extract_file():
    if 'original_image' not in request.files or 'stego_image' not in request.files:
        return 'No file part', 400

    original_file = request.files['original_image']
    stego_file = request.files['stego_image']

    if original_file.filename == '' or stego_file.filename == '':
        return 'No selected file', 400

    if original_file and stego_file:
        original_image = Image.open(original_file.stream)
        stego_image = Image.open(stego_file.stream)

        message = extract_message(original_image, stego_image)
        return render_template('extract.html', message=message)

@app.route('/extract_form')
def extract_form():
    return render_template('extract.html')

if __name__ == '__main__':
    app.run(debug=True)