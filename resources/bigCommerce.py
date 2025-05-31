import requests
from flask_restful import Resource
from flask import request


# class GetAddOnProducts(Resource):
#     def post(self):
#         print('destination')
#         destination = request.get_json()
#
#         headers = {
#             'X-Auth-Token': '1vslmigkd47u8ljjqyqfvf1hry200r5',
#             'Content-Type': 'application/json',
#         }
#         response = requests.get('https://api.bigcommerce.com/stores/9toeoafwnx/v3/catalog/categories', headers=headers)
#         if response.status_code != 200:
#             return {'error': 'Failed to fetch product details'}, response.status_code
#
#         data = response.json()['data']
#         category_names = [[x['name'], x['id']] for x in data]
#
#         category_names_res = []
#         for key in category_names:
#             if key[0] == 'AddOn':
#                 category_names_res.append(key)
#
#         data = category_names_res[0][1]
#         a = 6
#         #Get the products under the category
#         response_products = requests.get(f'https://api.bigcommerce.com/stores/9toeoafwnx/v3/catalog/products?categories:in={data}&include=custom_fields', headers=headers)
#         if response_products.status_code != 200:
#             return {'error': 'Failed to fetch product details'}, response.status_code
#         data_products = response_products.json()['data']
#
#         result_payload = []
#
#         for product in data_products:
#             payload = {}
#             payload['productId'] = product['id']
#             payload['productName'] = product['name']
#             payload['description'] = product['description']
#             payload['price'] = product['price']
#             result_payload.append(payload)
#
#         print('result_payload', result_payload)
#         return result_payload, 200



class GetAddOnProducts(Resource):
    def post(self):
        print('destination')
        destination = request.get_json()

        headers = {
            'X-Auth-Token': '1vslmigkd47u8ljjqyqfvf1hry200r5',
            'Content-Type': 'application/json',
        }
        response = requests.get('https://api.bigcommerce.com/stores/9toeoafwnx/v3/catalog/categories', headers=headers)
        if response.status_code != 200:
            return {'error': 'Failed to fetch product details'}, response.status_code

        data = response.json()['data']
        category_names = [[x['name'], x['id']] for x in data]

        category_names_res = []
        for key in category_names:
            if key[0] == 'AddOn':
                category_names_res.append(key)

        data = category_names_res[0][1]
        a = 6
        #Get the products under the category
        response_products = requests.get(f'https://api.bigcommerce.com/stores/9toeoafwnx/v3/catalog/products?categories:in={data}&include=custom_fields', headers=headers)
        if response_products.status_code != 200:
            return {'error': 'Failed to fetch product details'}, response.status_code
        data_products = response_products.json()['data']

        result = []
        for product in data_products:
            product_id = product.get('id')
            custom_fields = product.get('custom_fields', [])
            custom_fields.append({'name': 'description', 'value': product.get('description')})
            result.append({
                'product_id': product_id,
                'custom_fields': {field['name']: field['value'] for field in custom_fields}
            })

        # filtered_products = [product for product in result if product['custom_fields']['destination'] == destination['destination']]
        target_destination = destination['destination']


        filtered_products = [
            product for product in result
            if
            ('destination' not in product['custom_fields'] or product['custom_fields'][
                'destination'] == target_destination)
        ]
        print('filtered_products', filtered_products)
        return filtered_products, 200
