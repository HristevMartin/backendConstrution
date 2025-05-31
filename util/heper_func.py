# import pandas as pd
# import requests
#
# def parse_file(file_stream, file_type):
#     """Parse the file based on its MIME type (CSV or Excel)."""
#     try:
#         if 'csv' in file_type:
#             df = pd.read_csv(file_stream)
#         elif 'excel' in file_type or 'spreadsheetml' in file_type:
#             df = pd.read_excel(file_stream)
#         else:
#             raise ValueError("Unsupported file format")
#     except Exception as e:
#         raise ValueError(f"Error reading the file: {e}")
#
#     field_mappings = {
#         "productName": "productName",
#         "productType": "productType",
#         "price": "price",
#         "imageUrl": "imageUrl",
#         "customFields": {
#             "name": "name",
#             "price": "price",
#             "city": "city",
#             "date": "date"
#         }
#     }
#
#     data = {}
#     for key, value in field_mappings.items():
#         if isinstance(value, dict):
#             data[key] = {nested_key: df.get(column_name).iloc[0] if column_name in df.columns else None
#                          for nested_key, column_name in value.items()}
#         else:
#             data[key] = df.get(value).iloc[0] if value in df.columns else None
#
#     return data


# import pandas as pd
# import json
#
# def parse_file(file_stream, file_type):
#     """Parse the file based on its MIME type (CSV, Excel, or JSON)."""
#     try:
#         if 'csv' in file_type:
#             df = pd.read_csv(file_stream)
#         elif 'excel' in file_type or 'spreadsheetml' in file_type:
#             df = pd.read_excel(file_stream)
#         elif 'json' in file_type:
#             file_content = file_stream.read()
#             if isinstance(file_content, bytes):
#                 file_content = file_content.decode('utf-8')
#             json_data = json.loads(file_content)
#             return parse_json_file(json_data)
#         else:
#             raise ValueError("Unsupported file format")
#
#     except Exception as e:
#         raise ValueError(f"Error reading the file: {e}")
#
#     return transform_df_to_data(df)
#
# import json
#
# def parse_json_file(file_stream):
#     """Parse a JSON file containing multiple products and extract custom fields."""
#     try:
#         # Assuming file_stream is already a readable file-like object
#         json_data = json.load(file_stream)
#     except Exception as e:
#         raise ValueError(f"Error reading the JSON file: {e}")
#
#     products = json_data.get('products', [])
#     parsed_products = []
#
#     # Define the field mappings including nested custom fields
#     field_mappings = {
#         "productName": "productName",
#         "productType": "productType",
#         "price": "price",
#         "imageUrl": "imageUrl",
#         "customFields": {
#             "name": "name",
#             "price": "price",  # This assumes the price is also part of custom fields, adjust as necessary
#             "city": "city",
#             "date": "date"
#         }
#     }
#
#     for product in products:
#         parsed_product = extract_data_based_on_mapping(product, field_mappings)
#         parsed_products.append(parsed_product)
#
#     return parsed_products
#
# def extract_data_based_on_mapping(data, field_mappings):
#     result = {}
#     for key, value in field_mappings.items():
#         if isinstance(value, dict):  # Handle nested structures for customFields
#             result[key] = {}
#             for nested_key, field_name in value.items():
#                 result[key][nested_key] = data.get(field_name)
#         else:
#             result[key] = data.get(value)
#     return result
#
# def transform_df_to_data(df):
#     field_mappings = {
#         "productName": "productName",
#         "productType": "productType",
#         "price": "price",
#         "imageUrl": "imageUrl",
#         "customFields": {
#             "name": "name",
#             "price": "price",
#             "city": "city",
#             "date": "date"
#         }
#     }
#
#     return extract_data_based_on_mapping(df.to_dict('records')[0], field_mappings)

import json
import pandas as pd
import requests


def parse_file(file_stream, file_type):
    """Parse the file based on its MIME type (CSV, Excel, or JSON)."""
    try:
        if 'csv' in file_type:
            df = pd.read_csv(file_stream)
            return transform_df_to_data(df)
        elif 'excel' in file_type or 'spreadsheetml' in file_type:
            df = pd.read_excel(file_stream)
            return transform_df_to_data(df)
        elif 'json' in file_type:
            file_content = file_stream.read()
            file_content = file_content.decode('utf-8') if isinstance(file_content, bytes) else file_content
            json_data = json.loads(file_content)
            return parse_json_data(json_data)
        else:
            raise ValueError("Unsupported file format")
    except Exception as e:
        raise ValueError(f"Error reading the file: {str(e)}")

def parse_json_data(json_data):
    """Parse already loaded JSON data containing multiple products."""
    products = [extract_data(product) for product in json_data]
    return products

def extract_data(product):
    """Extracts data dynamically, including all custom fields present."""
    fixed_fields = {
        "productName": product.get("productName"),
        "productType": product.get("productType"),
        "price": product.get("price"),
        "images": product.get("imageUrls"),
        "categoryId": product.get("categoryId", [])
    }

    custom_fields = product.get("customFields", {})
    fixed_fields["customFields"] = custom_fields

    return fixed_fields

def transform_df_to_data(df):
    """Transforms data from a DataFrame based on column names directly."""
    return df.to_dict('records')


def call_external_api(payload):
    auth_url = 'http://localhost:8080/api/authenticate'

    credentials = {
        'username': 'admin',
        'password': 'admin'
    }

    headers = {'Content-Type': 'application/json'}

    auth_response = requests.post(auth_url, json=credentials, headers=headers)

    if auth_response.status_code == 200:
        token = auth_response.json().get('id_token')

        next_url = 'http://localhost:8080/api/jdl/create-product'

        auth_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        response = requests.post(next_url, json=payload, headers=auth_headers)

        if response.status_code == 200:
            return True
        else:
            return response.status_code
    else:
        return auth_response.status_code

