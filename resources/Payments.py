from flask_restful import Resource
from flask import request
import stripe, os
from models.application import Application

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
print('show me the secret key', stripe.api_key)

APPLICATION_FEE_PENCE = 500
APPLICATION_CURRENCY = "gbp"

class PayWithStripe(Resource):
    def post(self):
        try:
            data = request.get_json(force=True) or {}

            job_id = data.get("job_id")
            user_id = data.get("user_id")            # trader_id in model
            application_text = data.get("application_text")

            if not job_id:
                return {"error": "job_id is required"}, 400
            if not user_id:
                return {"error": "user_id is required"}, 400

            # Block duplicate paid apps
            existing_paid = Application.objects(
                job_id=job_id, trader_id=user_id, status="paid"
            ).first()
            if existing_paid:
                return {"error": "You have already applied to this job."}, 409

            # Idempotency for retry safety
            idem_key = f"apply:{job_id}:{user_id}:{APPLICATION_FEE_PENCE}:{APPLICATION_CURRENCY}"

            # Create PI
            intent = stripe.PaymentIntent.create(
                amount=APPLICATION_FEE_PENCE,
                currency=APPLICATION_CURRENCY,
                payment_method_types=["card"],
                metadata={
                    "job_id": job_id,
                    "user_id": user_id,
                    "application_text": (application_text or "")[:500],
                    "type": "pay_to_apply",
                }
                # idempotency_key=idem_key,
            )

            # Find existing draft app
            app = Application.objects(
                job_id=job_id,
                trader_id=user_id,
                status__in=["initiated", "failed", "cancelled", "refunded"],
            ).first()

            print('show me the app', app)

            if app:
                app.stripe_pi_id = intent.id
                app.amount = APPLICATION_FEE_PENCE
                app.currency = APPLICATION_CURRENCY
                app.application_message = application_text
                app.status = "initiated"
                app.save()
            else:
                app = Application(
                    job_id=job_id,
                    trader_id=user_id,
                    stripe_pi_id=intent.id,
                    amount=APPLICATION_FEE_PENCE,
                    currency=APPLICATION_CURRENCY,
                    status="initiated",
                    application_message=application_text,
                ).save()

            return {
                "clientSecret": intent.client_secret,
                "applicationId": str(app.application_id),
            }, 200

        except stripe.error.StripeError as e:
            return {"error": getattr(e, "user_message", str(e))}, 400
        except Exception as e:
            return {"error": str(e)}, 400

    def put(self):
        try:
            data = request.get_json(force=True) or {}
            user_id = data.get("user_id")
            job_id = data.get("job_id")
            print('show me the user id', user_id)
            application = Application.objects(trader_id=user_id, job_id=job_id).first()
            print('show me the application', application)
            print('show me the job id', job_id)
            print('it is marked as paid')
            application.status = "paid"
            application.save()
            return {"message": "Application marked as paid"}, 200
        except Exception as e:
            print('show me the error', e)
            return {"error": str(e)}, 400


class CheckPaymentStatus(Resource):
    def get(self, user_id, job_id):
        try:
            print('show me the user id', user_id)
            if not user_id:
                return {"error": "user_id is required"}, 400
            
            
            application = Application.objects(job_id=job_id,trader_id=user_id).first()
            if application:
                return {"status": application.status}, 200
            else:
                return {"status": "not found"}, 404

        except Exception as e:
            return {"error": str(e)}, 400