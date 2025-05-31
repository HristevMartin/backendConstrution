import urllib.parse
from datetime import datetime

import pandas as pd
import requests
from flask import jsonify
from flask import request
from flask_restful import Resource
from mongoengine import ValidationError

from managers.auth import verify_token
from models.cart import Order, ItemDetails, TravelDetails
from models.makeswift_user import ProductDetails, CustomField
from util.heper_func import call_external_api, parse_file


class OrderView(Resource):
    def get(self):
        orders = Order.objects().all()
        data = [self.serialize_order(order) for order in orders]
        return data, 200

    def serialize_order(self, order):
        return {
            "cartId": order.cartId,
            "isTaxIncluded": order.isTaxIncluded,
            "currencyCode": order.currencyCode,
            "lineItems": [self.serialize_line_item(item) for item in order.lineItems],
            "travelDetails": [self.serialize_travel_detail(detail) for detail in order.travelDetails],
            "status": order.status,
            "createdDate": order.createdDate.isoformat() if order.createdDate else None,
            "createdBy": str(order.createdBy.id) if order.createdBy else None
        }

    def serialize_line_item(self, item):
        return {
            "name": item.name,
            "imageUrl": item.imageUrl,
            "entityId": item.entityId,
            "productEntityId": item.productEntityId,
            "variantEntityId": item.variantEntityId,
            "quantity": item.quantity,
            "extendedListPrice": item.extendedListPrice,
            "extendedSalePrice": item.extendedSalePrice,
            "discountedAmount": item.discountedAmount,
            "selectedOptions": item.selectedOptions
        }

    def serialize_travel_detail(self, detail):
        return {
            "departureDate": detail.departureDate.isoformat() if detail.departureDate else None,
            "fromAirport": detail.fromAirport,
            "toAirport": detail.toAirport,
            "time": detail.time,
            "flightNumber": detail.flightNumber,
            "selectedOptions": detail.selectedOptions
        }

    def post(self):
        api_token = "o8j8uy9xn9xho70slsurdhuazabetdx"
        data = request.get_json()

        if data is None:
            return 'No data provided!', 400

        token = request.headers.get('Authorization')
        user = None

        if token and token.split()[-1] != 'undefined':
            user = verify_token(token.split()[-1])
            if not user:
                return jsonify({'message': 'Invalid or expired token!'}), 401

        existing_order = Order.objects(cartId=data['entityId']).first()

        if existing_order:
            if user and not existing_order.createdBy:
                existing_order.createdBy = user.id
        else:
            existing_order = Order(
                cartId=data['entityId'],
                isTaxIncluded=data['isTaxIncluded'],
                currencyCode=data['currencyCode'],
                lineItems=[],
                travelDetails=[],
                status='Pending',
                createdDate=datetime.now(),
                createdBy=user.id if user else None
            )

        headers = {
            "X-Auth-Token": api_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        for item in data['lineItems']['physicalItems']:
            product_id = item['productEntityId']
            selected_option = next((opt['value'] for opt in item['selectedOptions'] if opt['name'] == 'Class'), None)

            api_url = f"https://api.bigcommerce.com/stores/9toeoafwnx/v3/catalog/products/{product_id}/custom-fields"

            try:
                response = requests.get(api_url, headers=headers)
                response.raise_for_status()
                custom_fields_data = response.json()['data']
                custom_fields = {field['name']: field['value'] for field in custom_fields_data}

                if not any(td.flightNumber == str(item['productEntityId']) and \
                           td.selectedOptions[0] == selected_option for td in existing_order.travelDetails):
                    date, time = custom_fields.get('Departure Date').split('T')
                    travel_details = TravelDetails(
                        departureDate=date,
                        fromAirport=custom_fields.get('From'),
                        returnDate=custom_fields.get('Return Date', None),
                        toAirport=custom_fields.get('To'),
                        time=time,
                        # arrivalDate=custom_fields.get('Arrival Date', None),
                        flightNumber=str(item['productEntityId']),
                        # flightNumber=custom_fields.get('Flight Number'),
                        selectedOptions=[selected_option]
                    )
                    existing_order.travelDetails.append(travel_details)

                # Adding new line items based on selectedOptions
                if not any(li.productEntityId == item['productEntityId'] and \
                           li.selectedOptions[0] == selected_option for li in existing_order.lineItems):
                    line_item = ItemDetails(
                        name=item['name'],
                        imageUrl=item['imageUrl'],
                        entityId=item['entityId'],
                        productEntityId=item['productEntityId'],
                        variantEntityId=item['variantEntityId'],
                        quantity=item['quantity'],
                        extendedListPrice=item['extendedListPrice']['value'],
                        extendedSalePrice=item['extendedSalePrice']['value'],
                        discountedAmount=item['discountedAmount']['value'],
                        selectedOptions=[selected_option]
                    )
                    existing_order.lineItems.append(line_item)

            except requests.RequestException as e:
                return jsonify({"error": str(e)}), 500

        try:
            existing_order.save()
            return {'message': 'Order processed successfully!'}, 201
        except Exception as e:
            return {'error': str(e)}, 500


class MockUpProductCategory(Resource):
    def get(self):
        product_details_list = ProductDetails.objects.all()
        data = []

        for product_details in product_details_list:
            product_dict = {
                "entityName": product_details.entityName,
                f"customFields_{product_details.entityName[0]}": [{
                    "key": field.key,
                    "label": field.label,
                    "type": field.type,
                    "required": field.required,
                    "placeholder": field.placeholder,
                    "options": field.options
                } for field in product_details.customFields]
            }
            data.append(product_dict)

        print('data is', data)

        return data, 200

    def post(self):
        data = request.get_json()

        try:
            product_details = ProductDetails(
                entityName=data['entityName'],
                customFields=[{
                    'key': field['key'],
                    'type': field['type'],
                    'label': field.get('label', ''),
                    'required': field.get('required', False),
                    'placeholder': field.get('placeholder', ''),
                    'options': field.get('options', [])
                } for field in data['customFields']]
            )
            # Save the document to the database
            product_details.save()

            return {"message": "Data is saved successfully"}, 201
        except Exception as e:
            print(f"Error saving data: {e}")
            return {'error': str(e)}, 500


class UpdateProductCategory(Resource):
    def patch(self, entity_name):
        data = request.get_json()
        print('Received update:', data)

        try:
            entity_name = urllib.parse.unquote_plus(entity_name)

            product_details = ProductDetails.objects.get(entityName=entity_name)

            if 'entityName' in data:
                product_details.entityName = data['entityName']

            # Handle updates in customFields if provided
            if 'customFields' in data:
                updated_fields = data['customFields']
                for field in updated_fields:
                    existing_field = next((f for f in product_details.customFields if f.key == field['key']), None)
                    if existing_field:
                        existing_field.label = field.get('label', existing_field.label)
                        existing_field.type = field.get('type', existing_field.type)
                        existing_field.required = field.get('required', existing_field.required)
                        existing_field.placeholder = field.get('placeholder', existing_field.placeholder)
                        existing_field.options = field.get('options', existing_field.options)

            # Save the changes to the database
            product_details.save()
            return {"message": "Product details updated successfully"}, 200

        except Exception as e:
            print(f"Error updating product details: {e}")
            return {"error": str(e)}, 500

    def post(self, entity_name):
        data = request.get_json()

        try:
            product_details = ProductDetails.objects.get(entityName=entity_name)
            new_field = {
                'key': data['key'],
                'type': data['type'],
                'label': data.get('label', ''),
                'required': data.get('required', False),
                'placeholder': data.get('placeholder', ''),
                'options': data.get('options', [])
            }
            product_details.update(push__customFields=new_field)
            product_details.reload()
            return {"message": "Custom field added successfully"}, 201

        except Exception as e:
            return {"error": str(e)}, 500


class DeleteCustomField(Resource):
    def delete(self, entity_name, field_key):
        try:
            entity_name = urllib.parse.unquote_plus(entity_name)

            product_details = ProductDetails.objects.get(entityName=entity_name)

            product_details.customFields = [field for field in product_details.customFields if field.key != field_key]

            product_details.save()

            return {"message": f"Custom field '{field_key}' deleted successfully"}, 200
        except Exception as e:
            print(f"Error deleting custom field: {e}")
            return {"error": str(e)}, 500


class AddCustomField(Resource):
    def post(self, entity_name):
        new_field_data = request.get_json()
        try:
            entity_name = urllib.parse.unquote_plus(entity_name)
            product_details = ProductDetails.objects.get(entityName=entity_name)

            new_custom_field = CustomField(
                key=new_field_data['key'],
                type=new_field_data['type'],
                label=new_field_data.get('label', ''),
                required=new_field_data.get('required', False),
                placeholder=new_field_data.get('placeholder', ''),
                options=new_field_data.get('options', [])
            )

            product_details.customFields.append(new_custom_field)

            product_details.save()

            return {"message": "New custom field added successfully"}, 201
        except ValidationError as e:
            # Print and return the validation error details
            print(f"Validation Error: {e}")
            return {"error": str(e)}, 400
        except Exception as e:
            print(f"Error adding new custom field: {e}")
            return {"error": str(e)}, 500


data2 = []


class AddInitialProductType(Resource):
    def get(self):
        print('data2 is', data2)
        return data2

    def post(self):
        global data2
        data = request.get_json()
        data2.append(data)
        return data, 201


class FileUploadResource(Resource):
    def post(self):
        uploaded_file = request.files.get('file')

        if not uploaded_file:
            return {"message": "No file was uploaded."}, 400

        try:
            df = pd.read_excel(uploaded_file)
            all_entities = []

            for index, row in df.iterrows():
                entity_name = [row['Entity_Name']]  # Ensuring entity_name is a list
                product_details = ProductDetails.objects(entityName=entity_name).first()

                if not product_details:
                    product_details = ProductDetails(entityName=entity_name, customFields=[])

                entity_payload = {'entityName': entity_name, 'customFields': []}

                for col in [col for col in df.columns if 'Key' in col]:
                    key_idx = col.replace('Key', '')
                    key = row[f'Key{key_idx}']
                    type = row.get(f'Type{key_idx}', '').lower()
                    label = row.get(f'Label{key_idx}', '')
                    required = row.get(f'Required{key_idx}', False)
                    placeholder = row.get(f'Placeholder{key_idx}', '')

                    options_raw = str(row.get(f'Options{key_idx}', ''))
                    options = [{'value': opt.strip(), 'label': opt.strip()} for opt in
                               options_raw.split(",")] if options_raw else []

                    existing_field = next(
                        (cf for cf in product_details.customFields if cf.key == key and cf.type == type), None)

                    if existing_field:
                        # Update only if there are changes
                        if (existing_field.label != label or existing_field.required != required or
                                existing_field.placeholder != placeholder or existing_field.options != options):
                            existing_field.label = label
                            existing_field.required = required
                            existing_field.placeholder = placeholder
                            existing_field.options = options
                    else:
                        new_field = CustomField(key=key, type=type, label=label, required=required,
                                                placeholder=placeholder, options=options)
                        product_details.customFields.append(new_field)

                    entity_payload['customFields'].append({
                        'key': key,
                        'type': type,
                        'label': label,
                        'required': required,
                        'placeholder': placeholder,
                        'options': options
                    })

                product_details.save()
                all_entities.append(entity_payload)

            # response = requests.post('http://springapi.example.com/api/target', json={'entities': all_entities})
            # if response.status_code == 200:
            #     return {"message": "File processed successfully and data sent to Spring API"}, 200
            # else:
            #     return {"message": "Failed to send data to Spring API", "details": response.text}, 500

        except Exception as e:
            return {"message": str(e)}, 500


class DeleteEntityName(Resource):
    def delete(self):
        try:
            data = request.get_json()
            for entity_name in data['categories']:
                entity_name = urllib.parse.unquote_plus(entity_name[0])
                product_details = ProductDetails.objects.get(entityName=entity_name)
                product_details.delete()
            return {"message": "Product details deleted successfully"}, 200
        except Exception as e:
            return {"error": str(e)}, 500


class SampleEndpoint(Resource):
    def get(self):
        return {"message": "This is a sample endpoint"}, 200

    def post(self):
        data = [
            {
                "id": "1",
                "payload": {
                    "name": "Hotel Sunset Views",
                    "description": "A luxurious hotel with views of the sunset across the coast.",
                    "price": "150",
                    "url": "https://example.com/images/hotel1.jpg"
                }
            },
            {
                "id": "2",
                "payload": {
                    "name": "Mountain Escape Resort",
                    "description": "Escape into the mountains at this beautiful resort offering scenic hikes and relaxing spas.",
                    "price": "200",
                    "url": "https://example.com/images/hotel2.jpg"
                }
            },
            {
                "id": "3",
                "payload": {
                    "name": "Urban Downtown Hotel",
                    "description": "Located in the heart of the city, this hotel puts you in the middle of the action.",
                    "price": "99",
                    "url": "https://example.com/images/hotel3.jpg"
                }
            }
        ]

        return data, 201


class ProductBulkUpload(Resource):
    def post(self):
        file = request.files.get('file')
        category_id = request.form.get('categoryId')

        if not file:
            return {"error": "No file part"}, 400
        if file.filename == '':
            return {"error": "No selected file"}, 400

        try:
            data = parse_file(file, file.content_type)
            if category_id:
                category_id_list = [int(category_id)]
                for product in data:
                    product['categoryId'] = category_id_list
            response = call_external_api(data)
            if response:
                return {"message": "File processed successfully"}, 201
            else:
                return {"message": "Failed to process the file"}, 500
        except Exception as e:
            return {"error": str(e)}, 500


class ProductDetailWithImage(Resource):
    def get(self, product_id):
        headers = {
            'X-Auth-Token': '1vslmigkd47u8ljjqyqfvf1hry200r5',
            'Content-Type': 'application/json',
        }

        try:
            product_detail = f'https://api.bigcommerce.com/stores/9toeoafwnx/v3/catalog/products/{product_id}'
            response = requests.get(product_detail, headers=headers)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to fetch product details'}), response.status_code
            product_id = response.json()['data']['id']


            product_url = f'https://api.bigcommerce.com/stores/9toeoafwnx/v3/catalog/products/{product_id}/custom-fields'
            product_response = requests.get(product_url, headers=headers)
            if product_response.status_code != 200:
                return jsonify({'error': 'Failed to fetch product details'}), product_response.status_code

            product_data = product_response.json()
            if 'data' not in product_data:
                return jsonify({'error': 'Product not found'}), 404

            images_url = f'https://api.bigcommerce.com/stores/9toeoafwnx/v3/catalog/products/{product_id}/images'
            images_response = requests.get(images_url, headers=headers)
            if images_response.status_code != 200:
                return jsonify({'error': 'Failed to fetch product images'}), images_response.status_code

            images_data = images_response.json()

            product_with_images = {
                "product_id": product_id,
                **product_data,
                'images': images_data.get('data', [])
            }

            return jsonify(product_with_images)

        except Exception as e:
            return jsonify({'error': str(e)}), 500


