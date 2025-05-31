from flask_restful import Resource
import requests

class Categories(Resource):
    def get(self):
        api_url = "https://api.bigcommerce.com/stores/9toeoafwnx/v3/catalog/categories"
        api_token = "o8j8uy9xn9xho70slsurdhuazabetdx"

        headers = {
            "X-Auth-Token": api_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()['data']
            return data, 200
        except requests.RequestException as e:
            return {"error": str(e)}, 500