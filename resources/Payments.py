from flask_restful import Resource
from flask import request
import stripe, os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
print('show me the secret key', stripe.api_key)

class   PayWithStripe(Resource):
    def post(self):
        try:
            data = request.get_json(force=True) 
            job_id = data.get("jobId")
            trader_id = data.get("traderId")

            amount = 500 

            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency="gbp",
                 payment_method_types=["card", "revolut_pay"],
                metadata={
                    "jobId": job_id,
                    "traderId": trader_id,
                    "type": "pay_to_apply",
                },
            )

            return {"clientSecret": intent.client_secret}, 200

        except stripe.error.StripeError as e:
            return {"error": getattr(e, "user_message", str(e))}, 400
        except Exception as e:
            return {"error": str(e)}, 400
