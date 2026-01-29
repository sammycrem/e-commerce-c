import logging
import string
import random
from flask_mail import Mail, Message
import smtplib, ssl
from email.mime.text import MIMEText

import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, render_template , render_template_string
import re
import json
import html
import requests
import re
import urllib.parse
from urllib.parse import urlparse, parse_qs
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PIL import Image



logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('util.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def str_to_bool(string):
  """Converts a string to a boolean value.

  Args:
    string: The string to convert.

  Returns:
    True if the string is "True" or "1", False if the string is "False" or "0",
    None otherwise.
  """

  if string.lower() == "true":
    return True
  elif string.lower() == "false":
    return False
  elif string == "1":
    return True
  elif string == "0":
    return False
  else:
    return None
# ---------end 
def generate_id(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return str(result_str)
# ---------end------------
def send_email(sender_email,smtp_password, smtp_server, smtp_port, recipient_email, subject, body):
    """Sends an email using STARTTLS."""
    message_text="send correctly to: " + recipient_email
    try:
      # Connect to the SMTP server using STARTTLS
      server = smtplib.SMTP(smtp_server, smtp_port)  # Replace with your SMTP server and port
      server.ehlo()
      server.starttls()
      server.login(sender_email, smtp_password)  # Replace with your email password

      # Create the email message
      message = MIMEText(body, _subtype='html')
      message['From'] = sender_email
      message['To'] = recipient_email
      message['Subject'] = subject

      #logger.info('Sendmail' + str(server.))

      # Send the email
      server.sendmail(sender_email, recipient_email, message.as_string())
      
    except Exception as e:
       logger.info('Sendmail' + str(e))
       message_text=e
    finally:
        server.quit()
        return message_text
# ---------end------------

def send_emailTls2(sender_email,smtp_password, smtp_server, smtp_port, recipient_email, subject, body):
    """Sends an email using STARTTLS."""
    message_text="send correctly to: " + recipient_email
    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email

    # Attach HTML content
    html_part = MIMEText(body, "html")
    msg.attach(html_part)

    try:
      server = smtplib.SMTP(smtp_server, smtp_port)
      server.starttls()
      server.login(sender_email, smtp_password)
      server.sendmail(sender_email, recipient_email, msg.as_string())
      
      logger.info("Email sent successfully! to " + recipient_email)
    except Exception as e:
        logger.info(f"Failed to send email: {str(e)}" + " to: " + recipient_email)
        message_text=e

    finally:
        server.quit()
        return message_text

# ---------end------------

def check_file_exists(filename):
  """Checks if a file exists.

  Args:
    filename: The name of the file to check.

  Returns:
    True if the file exists, False otherwise.
  """

  return os.path.isfile(filename)
# ---------end------------

def load_config_from_text_file(filename):
  """
  Loads configuration values from a text file into a dictionary.

  Args:
    filename: The name of the text file containing the configuration.

  Returns:
    A dictionary containing the loaded configuration values.
  """

  config_dict = {}
  with open(filename) as f:
    for line in f:
      line = line.strip()  # Remove leading/trailing whitespace
      if line and not line.startswith('#'):  # Skip comments
        k, v = line.split('=', 1)
        config_dict[k] = v
    # try:
    #     os.remove(filename)
        
    # except FileNotFoundError:
    #     print(f"File {filename} not found.")
    
  return config_dict
# ---------end------------
def encrypt_config_values(config_dict, encrypt_config_file):
  """
  Encrypts the values in a configuration dictionary.

  Args:
    config_dict: The dictionary containing the configuration values.

  Returns:
    A new dictionary with encrypted values.
  """
    # Load the encryption key from an environment variable
  encryption_key = os.environ.get('ENCRYPTION_KEY')
  if not encryption_key:
    raise ValueError("Encryption key is not set.")

  cipher = Fernet(encryption_key.encode())
  encrypted_config = {}
  for key, value in config_dict.items():
    encrypted_value = cipher.encrypt(value.encode())
    encrypted_config[key] = encrypted_value.decode()
  with open(encrypt_config_file, 'w') as f:
    for key, value in encrypted_config.items():
      
      f.write(f"{key}¢{value}\n")
      os.environ[key] = value
  return encrypted_config
# ---------end------------
def load_encrypted_config_from_env():
  """
  Loads encrypted configuration values from environment variables and decrypts them.

  Returns:
    A dictionary containing the decrypted configuration values.
  """
  encryption_key = os.environ.get('ENCRYPTION_KEY')
  if not encryption_key:
    raise ValueError("Encryption key is not set.")

  cipher = Fernet(encryption_key.encode())
  decrypted_config = {}
  for key, value in os.environ.items():
    if key.startswith('APP_'):
      try:
        decrypted_value = cipher.decrypt(value.encode()).decode()
        decrypted_config[key] = decrypted_value
      except Exception:
        pass  # Ignore non-encrypted values
  return decrypted_config
# ---------end------------
def load_encrypted_config_from_encreption_file():
  """
  Loads encrypted configuration values from environment variables and decrypts them.

  Returns:
    A dictionary containing the decrypted configuration values.
  """

  filename="./encrypt_config_file.txt"
  encryption_key = os.environ.get('ENCRYPTION_KEY')
  if not encryption_key:
    raise ValueError("Encryption key is not set.")

  cipher = Fernet(encryption_key.encode())
  decrypted_config = {}

  with open(filename) as f:
    for line in f:
      line = line.strip()  # Remove leading/trailing whitespace
      if line and not line.startswith('#'):  # Skip comments
        k, v = line.split('¢')
        try:
            decrypted_value = cipher.decrypt(v.encode()).decode()
            decrypted_config[k] = decrypted_value
        except Exception:
            pass  # Ignore non-encrypted values
  return decrypted_config
# ---------end------------
def init_config(config_file, encrypt_config_file):
    # Load configuration from the text file
    if check_file_exists(config_file):
        config_dict = load_config_from_text_file(config_file)

        # Encrypt the configuration values and store them as environment variables
        encrypted_config = encrypt_config_values(config_dict,encrypt_config_file)
        for key, value in encrypted_config.items():
            os.environ[key] = value

        # Load the decrypted configuration from environment variables
        decrypted_config = load_encrypted_config_from_env()
    else:
       decrypted_config = load_encrypted_config_from_encreption_file() #load_encrypted_config_from_env()
    return decrypted_config
# ---------end------------


def encrypt_password(password, encryption_key):
    """Encrypts a password using Fernet encryption."""
    if not encryption_key:
        raise ValueError("Encryption key is not set.")

    try:
        cipher = Fernet(encryption_key.encode())
        encrypted_value = cipher.encrypt(password.encode())
        return encrypted_value.decode()  # Decode to string for storage
    except Exception as e:
        raise ValueError(f"Encryption failed: {e}")
# ---------end------------

def decrypt_password(encrypted_password, encryption_key):
    """Decrypts an encrypted password using Fernet decryption."""
    if not encryption_key:
        raise ValueError("Encryption key is not set.")
    try:
        cipher = Fernet(encryption_key.encode())
        decrypted_value = cipher.decrypt(encrypted_password.encode())
        return decrypted_value.decode()
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")
# ---------end------------

def generate_key():
    """Generates a Fernet key. Never store keys in code for production!"""
    return Fernet.generate_key().decode()
# ---------end------------

def create_directory(path):
    """
    Create a directory if it doesn't exist.

    Parameters:
    path (str): The path of the directory to create.
    """
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Directory '{path}' created successfully!")
    else:
        print(f"Directory '{path}' already exists.")
# ---------end------------

def replace_string(input_file, output_file, old_string, new_string):
    with open(input_file, 'r') as file:
        file_data = file.read()

    # Replace the target string
    file_data = file_data.replace(old_string, new_string)

    # Write the file out again
    with open(output_file, 'w') as file:
        file.write(file_data)
    return file_data
# ---------end------------


def download_file(url, filename):
  """Downloads a file from a URL and saves it to the specified filename.

  Args:
    url: The URL of the file to download.
    filename: The name of the file to save locally.
  """

  try:
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Raise an exception for failed downloads

    with open(filename + ".jpg", 'wb') as f:
      for chunk in response.iter_content(1024):
        f.write(chunk)

    return "Done"

  except requests.exceptions.RequestException as e:
    print(f"Error downloading file: {e}")
    return  str(e)


def download_image(url, save_as):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
      url  = replace_width_and_height(url, 2, 2)
      response = requests.get(url, headers=headers)
      if response.status_code == 200:
          with open(save_as, 'wb') as file:
              file.write(response.content)
          resize_image(save_as, save_as, max_size_mb=2)
          print(f"Image successfully downloaded and saved as {save_as}")
          return "Done"
      else:
          print(f"Failed to download image. Status code: {response.status_code}")
          return response.status_code
    except requests.exceptions.RequestException as e:
      print(f"Error downloading file: {e}")
      return  str(e)
  
def extract_width_and_height(url):
  """Extracts the width and height from a URL containing query parameters.

  Args:
    url: The URL to parse.

  Returns:
    A tuple containing the extracted width and height, or None if they are not found.
  """

  # Try regular expression matching first
  match = re.search(r"&w=(\d+)&h=(\d+)", url)
  if match:
    return int(match.group(1)), int(match.group(2))

  # If regular expression fails, try URL parsing
  parsed_url = urllib.parse.urlparse(url)
  query_params = dict(parsed_url.query.split("&"))
  w = int(query_params.get("w", None))
  h = int(query_params.get("h", None))

  if w and h:
    return w, h

  return None

def replace_width_and_height(url, new_width, new_height):
  """Replaces the width and height values in a URL with new values.

  Args:
    url: The URL to modify.
    new_width: The new width value.
    new_height: The new height value.

  Returns:
    The modified URL.
  """
  if not "w=" in url :
     return url
  
  # Extract the original width and height
  # Parse the URL and extract the query parameters
  parsed_url = urlparse(url)
  query_params = parse_qs(parsed_url.query)

  # Extract the values of 'w' and 'h'
  old_width = query_params.get('w', [None])[0]
  old_height = query_params.get('h', [None])[0]
  if old_width:
    new_width = int(old_width) // 1
  if old_height:
    new_height = int(old_height) // 1

  if old_width is not None :
    # Replace the width and height values in the URL
    url = url.replace(f"&w={old_width}", f"&w={new_width}")
  if  old_height is not None:
    # Replace the width and height values in the URL
    url = url.replace(f"&h={old_height}", f"&h={new_height}")
  #else:
    # Add the width and height values to the URL if they don't exist
  #  url += f"&w={new_width}&h={new_height}"

  return url


#.....end-----------------


def process_image_data(session_id, client_id, file_name, img_name, img_alt, img_title):
  """
  Processes image data and updates/creates the client_id.json file.

  Args:
    client_id: The ID of the client.
    file_name: The name of the image file.
    img_name: The name of the image.
    img_alt: The alt text for the image.
    img_title: The title of the image.
  """
  file_path = f"./export/{session_id}/{client_id}/images/images.json"
  img_id= str(generate_id(5))
  image_data = {
      "img_name": img_name,
      "img_alt": img_alt,
      "img_title": img_title,
      "file_name": file_name,
      "img_id" :  img_id
  }

  if os.path.exists(file_path):
    with open(file_path, 'r') as f:
      try:
        data = json.load(f)
      except json.JSONDecodeError:
        data = []  # Handle empty or invalid JSON

    # Check if an image with the same file_name already exists
    for i, item in enumerate(data):
      if item["file_name"] == file_name: #or item["img_name"] == file_name:
        if item["img_name"] != img_name: # delete old file if the image name is changed and the upload filename is the same
          os.system("rm " + f'./export/{session_id}/{client_id}/images/{item["img_name"]}')
         
        
        data[i] = image_data  # Update existing entry
        break
    else:
      data.append(image_data)  # Append new entry

  else:
    data = [image_data]  # Create new list with the initial entry

  with open(file_path, 'w') as f:
    json.dump(data, f, indent=2)
  return str(img_id)
# ---------end------------

def resize_image(input_path, output_path, max_size_mb=2):
    """
    Resizes an image while maintaining aspect ratio if its size exceeds the specified maximum size in MB.

    Args:
        input_path: Path to the input image file.
        output_path: Path to save the resized image file.
        max_size_mb: Maximum allowed size of the image in MB.

    Returns:
        True if the image was resized, False otherwise.
    """

    try:
        # Open the image
        img = Image.open(input_path)

        # Get image size in bytes
        img_size_bytes = os.path.getsize(input_path)
        img_size_mb = img_size_bytes / (1024 * 1024)

        if img_size_mb <= max_size_mb:
            # Image size is already within the limit
            return False

        # Calculate the scaling factor to achieve the desired size
        scale = (max_size_mb * 1024 * 1024) / img_size_bytes
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)

        # Resize the image while maintaining aspect ratio
        img = img.resize((new_width, new_height), Image.LANCZOS)

        # Save the resized image
        img.save(output_path, optimize=True, quality=60)  # Adjust quality as needed

        return True

    except Exception as e:
        print(f"Error resizing image: {e}")
        return False
# ---------end------------

def rename_image(old_name, new_name, upload_folder):
    """Renames an image file in the given directory.

    Args:
      old_name: The original name of the image file.
      new_name: The new name for the image file.
      upload_folder: The directory where the image file is located.

    Returns:
      True if the file was renamed successfully, False otherwise.
    """
    try:
        old_path = os.path.join(upload_folder, old_name)
        new_path = os.path.join(upload_folder, new_name)
        os.rename(old_path, new_path)
        return True
    except Exception as e:
        print(f"Error renaming image: {e}")
        return False
# ---------end------------
def get_json_image(img_name, json_path):
  """
  Reads the JSON file and returns the object with the matching img_name.

  Args:
    img_name: The name of the image to find.
    json_path: The path to the JSON file.

  Returns:
    The JSON object with the matching img_name, or None if not found.
  """
  try:
    with open(json_path, 'r') as f:
      data = json.load(f)

    for item in data:
      if item['img_name'] == img_name:
        return item

    return None  # Image not found

  except FileNotFoundError:
    print(f"Error: File '{json_path}' not found.")
    return None
  except json.JSONDecodeError:
    print(f"Error: Invalid JSON data in '{json_path}'.")
    return None
  except Exception as e:
    print(f"An unexpected error occurred: {e}")
    return None
# ---------end------------


def get_json_image_id(img_id, json_path):
  """
  Reads the JSON file and returns the object with the matching img_name.

  Args:
    img_name: The name of the image to find.
    json_path: The path to the JSON file.

  Returns:
    The JSON object with the matching img_name, or None if not found.
  """
  try:
    with open(json_path, 'r') as f:
      data = json.load(f)

    for item in data:
      if item['img_id'] == img_id:
        return item

    return None  # Image not found

  except FileNotFoundError:
    print(f"Error: File '{json_path}' not found.")
    return None
  except json.JSONDecodeError:
    print(f"Error: Invalid JSON data in '{json_path}'.")
    return None
  except Exception as e:
    print(f"An unexpected error occurred: {e}")
    return None
# ---------end------------



def is_valid_image(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify()  # Check if it's a valid image
        return True
    except (IOError, SyntaxError):
        return False
# ---------end------------    

def translate(word, language, name):
   return 'Welcome to ' + name
# ---------end------------

def get_folders_in_directory(directory_path):
    """
    Creates a list of all folders (directories) directly under the given directory.

    Args:
        directory_path: The path to the directory to search.

    Returns:
        A list of folder names, or an empty list if the directory doesn't exist or is empty.
    """

    folder_list = []
    try:
        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            items = os.listdir(directory_path)
            for item in items:
                item_path = os.path.join(directory_path, item)
                if os.path.isdir(item_path):
                    folder_list.append(item)
        else:
            print(f"Directory '{directory_path}' does not exist or is not a directory.")

    except OSError as e:
        print(f"Error accessing directory '{directory_path}': {e}")

    return folder_list
# ---------end------------

def check_string_number_inclusion(number_str, second_string):
    """
    Checks if the number at the end of the first string is present in the second string.

    Args:
        first_string: A string ending with a number, e.g., "Law Firms and Attorneys -14".
        second_string: A string containing numbers separated by underscores, e.g., "10_14_15" or "10_14".

    Returns:
        True if the number from the first string is found in the second string, False otherwise.
    """

    try:
        # Extract the number from the first string
        
        number = int(number_str)

        # Split the second string into individual numbers
        second_numbers_str = second_string.split("_")
        second_numbers = [int(num) for num in second_numbers_str]

        # Check if the number is in the second list of numbers
        return number in second_numbers

    except (ValueError, IndexError):
        # Handle cases where the strings are not in the expected format
        return False
# ---------end------------    

def concatenate_text_files(first_file_path, second_file_path, output_file_path):
    """
    Concatenates the content of the first text file to the end of the second text file,
    and writes the combined content to a new output file.

    Args:
        first_file_path: The path to the first text file.
        second_file_path: The path to the second text file.
        output_file_path: The path to the new output text file.

    Returns:
        True if the concatenation was successful, False otherwise.
    """

    try:
        if not os.path.exists(first_file_path) or not os.path.isfile(first_file_path):
            print(f"Error: First file '{first_file_path}' does not exist or is not a file.")
            return False

        if not os.path.exists(second_file_path) or not os.path.isfile(second_file_path):
            print(f"Error: Second file '{second_file_path}' does not exist or is not a file.")
            return False

        with open(first_file_path, 'r') as first_file, open(second_file_path, 'r') as second_file, open(output_file_path, 'w') as output_file:
            # Copy content of the second file first
            output_file.write(second_file.read())
            # Copy content of the first file after the second file
            output_file.write(first_file.read())

        return True

    except OSError as e:
        print(f"Error: An error occurred during file processing: {e}")
        return False
# ---------end------------

def get_random_element_from_json(json_string):
    """
    Reads a one-dimensional JSON array from a string and returns a random element.

    Args:
        json_string: A string containing a JSON array, e.g., '["apple", "banana", "cherry"]'.

    Returns:
        A random element from the JSON array, or None if the JSON is invalid or empty.
    """

    try:
        data = json.loads(json_string)
        if isinstance(data, list) and data:  # Check if it's a non-empty list
            return random.choice(data)
        else:
            print("Error: JSON string does not contain a valid, non-empty array.")
            return None
    except json.JSONDecodeError:
        print("Error: Invalid JSON string.")
        return None
    except IndexError: # catches empty list edge case.
        print("Error: json input is an empty list")
        return None
# ---------end------------

def calculate_totals_internal(items, shipping_country_iso=None, promo_code=None, shipping_method='standard', user_id=None):
    """
    items: list of {sku: ..., quantity: N}
    shipping_country_iso: str like 'DE' or 'US'
    promo_code: optional promo code string
    shipping_method: 'standard', 'express', or 'economic'
    user_id: optional user ID for user-specific promo codes

    Returns a dict:
    {
      subtotal_cents: int,
      discount_cents: int,
      subtotal_after_discount_cents: int,
      vat_cents: int,
      shipping_cost_cents: int,
      total_cents: int,
      shipping_zone: zone.name or None
    }
    """
    # Resolve variants
    skus = [it.get('sku') for it in items if it.get('sku')]
    from .models import Variant, Promotion
    from sqlalchemy.orm import joinedload
    variants = Variant.query.options(joinedload(Variant.product)).filter(Variant.sku.in_(skus)).all()
    variant_map = {v.sku: v for v in variants}

    cart_items = []
    subtotal = 0

    for it in items:
        sku = it.get('sku')
        qty = int(it.get('quantity') or 0)
        if qty <= 0:
            continue
        v = variant_map.get(sku)
        if not v:
            # skip unknown SKUs (caller may want to validate earlier)
            continue

        unit_price = int((v.product.base_price_cents or 0) + (v.price_modifier_cents or 0))
        subtotal += unit_price * qty

        product_snapshot = {
            "name": v.product.name,
            "product_sku": v.product.product_sku,
            "variant_sku": v.sku,
            "category": v.product.category,
            "weight_grams": v.product.weight_grams,
            "dimensions_json": v.product.dimensions_json
        }

        cart_items.append({
            "sku": sku,
            "quantity": qty,
            "unit_price_cents": unit_price,
            "product_snapshot": product_snapshot
        })

    # Promotion/discount
    discount_cents = 0
    promo = None
    if promo_code:
        promo = Promotion.query.filter_by(code=promo_code, is_active=True).first()
        from datetime import datetime, timezone
        if promo:
            promo_valid_to = promo.valid_to
            if promo_valid_to and promo_valid_to.tzinfo is None:
                promo_valid_to = promo_valid_to.replace(tzinfo=timezone.utc)

            if promo_valid_to and promo_valid_to < datetime.now(timezone.utc):
                promo = None  # expired
            elif promo.user_id is not None and promo.user_id != user_id:
                promo = None  # not valid for this user

    if promo:
        if promo.discount_type == 'PERCENT':
            # promo.discount_value expected as percentage (e.g., 20 for 20)
            try:
                from math import ceil
                pct = float(promo.discount_value)
                discount_cents = int(ceil(subtotal * (pct / 100.0)))
            except Exception:
                discount_cents = 0
        elif promo.discount_type == 'FIXED':
            # assume discount_value stored as cents for 'FIXED' (compat with your earlier code)
            try:
                discount_cents = int(promo.discount_value)
            except Exception:
                discount_cents = 0
        # ensure discount not greater than subtotal
        if discount_cents > subtotal:
            discount_cents = subtotal

    subtotal_after_discount = max(0, subtotal - discount_cents)

    # VAT calculation on discounted prices
    # Create a copy of cart_items to adjust prices for VAT calc without affecting other logic
    vat_calc_items = [item.copy() for item in cart_items]
    if promo and discount_cents > 0:
        if promo.discount_type == 'PERCENT':
            pct_off = Decimal(promo.discount_value) / Decimal(100)
            for item in vat_calc_items:
                original_price = cents_to_decimal(item['unit_price_cents'])
                discounted_price = original_price * (Decimal(1) - pct_off)
                item['unit_price_cents'] = decimal_to_cents(discounted_price)
        elif promo.discount_type == 'FIXED':
            if subtotal > 0:
                # Distribute fixed discount proportionally
                for item in vat_calc_items:
                    line_total = cents_to_decimal(item['unit_price_cents']) * item['quantity']
                    proportion = line_total / cents_to_decimal(subtotal)
                    line_discount = cents_to_decimal(discount_cents) * proportion
                    # Discount per unit
                    if item['quantity'] > 0:
                        unit_discount = line_discount / item['quantity']
                        new_unit_price = cents_to_decimal(item['unit_price_cents']) - unit_discount
                        item['unit_price_cents'] = decimal_to_cents(new_unit_price)

    _, item_vat_total_cents = compute_vat_for_cart(vat_calc_items, shipping_country_iso)
    vat_total = item_vat_total_cents


    # Shipping calculation
    zone = find_shipping_zone_for_country(shipping_country_iso)
    shipping_cost_cents = 0
    base_shipping_cost_cents = 0
    if zone:
        base_shipping_cost_cents = compute_shipping_cost_for_cart(cart_items, zone)
        shipping_cost_cents = base_shipping_cost_cents

        # Apply shipping method modifiers
        if shipping_method == 'express':
            shipping_cost_cents = int(shipping_cost_cents * 1.25)
        elif shipping_method == 'economic':
            shipping_cost_cents = int(shipping_cost_cents * 0.9)

        # apply free shipping threshold if configured (after modifiers? Usually standard shipping is free, express might not be)
        try:
            if zone.free_shipping_threshold_cents is not None and isinstance(zone.free_shipping_threshold_cents, int):
                if subtotal_after_discount >= int(zone.free_shipping_threshold_cents):
                    shipping_cost_cents = 0
        except Exception:
            pass

    # Add VAT on shipping
    shipping_vat_rate = get_vat_rate_for_product(shipping_country_iso, None)
    shipping_vat_cents = decimal_to_cents(cents_to_decimal(shipping_cost_cents) * shipping_vat_rate)
    vat_total += shipping_vat_cents

    total = subtotal_after_discount + vat_total + shipping_cost_cents

    return {
        "subtotal_cents": int(subtotal),
        "discount_cents": int(discount_cents),
        "subtotal_after_discount_cents": int(subtotal_after_discount),
        "vat_cents": int(vat_total),
        "item_vat_cents": int(item_vat_total_cents),
        "shipping_cost_cents": int(shipping_cost_cents),
        "base_shipping_cost_cents": int(base_shipping_cost_cents),
        "total_cents": int(total),
        "shipping_zone": (zone.name if zone else None),
        "vat_rate": float(shipping_vat_rate)
    }



def compute_vat_for_cart(cart_items: list, country_iso: str):
    """
    Assumes prices are EX-VAT (stored in unit_price_cents). Returns vat per item and total vat.
    Returns: (list_of_item_vat_cents, total_vat_cents)
    """
    total_vat = 0
    item_vats = []
    for it in cart_items:
        qty = int(it.get('quantity', 0))
        unit_cents = int(it.get('unit_price_cents', 0))
        category = it.get('product_snapshot', {}).get('category') if it.get('product_snapshot') else None
        vat_rate = get_vat_rate_for_product(country_iso, category)

        # Correct VAT calculation: Convert cent values to decimal Euros before applying ratios
        unit_price_decimal = cents_to_decimal(unit_cents)
        vat_per_unit_decimal = unit_price_decimal * Decimal(vat_rate)
        # Then convert back to cents using decimal_to_cents
        vat_per_unit_cents = decimal_to_cents(vat_per_unit_decimal)

        line_vat = vat_per_unit_cents * qty
        item_vats.append({'sku': it.get('sku') or it.get('variant_sku'), 'unit_vat_cents': vat_per_unit_cents, 'line_vat_cents': line_vat})
        total_vat += line_vat
    return item_vats, total_vat

def find_shipping_zone_for_country(country_iso: str):
    from .models import ShippingZone
    import json
    zones = ShippingZone.query.all()
    for z in zones:
        try:
            if country_iso and country_iso.upper() in [c.upper() for c in (z.countries_json or [])]:
                return z
        except Exception:
            # countries_json may be stored as string; try to parse
            try:
                arr = json.loads(z.countries_json) if isinstance(z.countries_json, str) else z.countries_json
                if country_iso and country_iso.upper() in [c.upper() for c in (arr or [])]:
                    return z
            except Exception:
                continue
    return None

def compute_shipping_cost_for_cart(cart_items: list, shipping_zone):
    """cart_items are like [{'quantity':..., 'product_snapshot':{'weight_grams':..., 'dimensions_json': {...}} , 'unit_price_cents':...}, ...]"""
    if not shipping_zone:
        return 0
    # compute total effective weight in kg accounting volumetric weight per item
    total_kg = Decimal('0')
    for it in cart_items:
        qty = int(it.get('quantity', 0))
        ps = it.get('product_snapshot', {}) or {}
        weight_g = int(ps.get('weight_grams') or 0)
        dims = ps.get('dimensions_json') or {}
        actual_kg = Decimal(weight_g) / Decimal(1000)
        volumetric_kg = Decimal('0')
        try:
            l = Decimal(dims.get('length') or 0)
            w = Decimal(dims.get('width') or 0)
            h = Decimal(dims.get('height') or 0)
            if l and w and h:
                volumetric_kg = (l * w * h) / Decimal(shipping_zone.volumetric_divisor or 5000)
        except Exception:
            volumetric_kg = Decimal('0')
        effective_kg = max(actual_kg, volumetric_kg)
        total_kg += effective_kg * qty

    base_cost = cents_to_decimal(int(shipping_zone.base_cost_cents or 0))
    cost_per_kg = cents_to_decimal(int(shipping_zone.cost_per_kg_cents or 0))
    total_cost = base_cost + (total_kg * cost_per_kg)

    # free shipping threshold
    if shipping_zone.free_shipping_threshold_cents and isinstance(shipping_zone.free_shipping_threshold_cents, int):
        # caller should pass subtotal to compare — we will not handle that here; caller may override by checking threshold.
        pass

    return decimal_to_cents(total_cost)



from decimal import Decimal, ROUND_HALF_UP
from .extensions import db

def decimal_to_cents(d: Decimal) -> int:
    return int((d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) * 100).to_integral_value())

def cents_to_decimal(cents: int) -> Decimal:
    return Decimal(cents) / Decimal(100)

def get_country_by_iso(iso_code: str):
    from .models import Country
    if not iso_code: return None
    return Country.query.filter(db.func.upper(Country.iso_code) == iso_code.upper()).first()

def get_vat_rate_for_product(country_iso: str, product_category: str):
    """Return Decimal VAT rate like Decimal('0.2000')"""
    from .models import VatRate
    country = get_country_by_iso(country_iso)
    if not country:
        return Decimal('0.0')
    # try category-specific
    vr = VatRate.query.filter_by(country_id=country.id, category=product_category).first()
    if vr:
        return Decimal(vr.vat_rate)
    # fallback
    return Decimal(country.default_vat_rate or 0)


