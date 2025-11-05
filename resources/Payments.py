from flask_restful import Resource
from flask import request
import stripe, os
import json
from models.application import Application
from datetime import datetime

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

APPLICATION_FEE_PENCE = 199
APPLICATION_CURRENCY = "gbp"

class PayWithStripe(Resource):
    def post(self):
        try:
            data = request.get_json(force=True) or {}

            job_id = data.get("job_id")
            user_id = data.get("user_id")            
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


class CreateFreeApplication(Resource):
    """
    Create an application without Stripe payment.
    Used when payment functionality is disabled.
    Creates application with status 'paid' so it works with existing checks.
    """
    def post(self):
        try:
            data = request.get_json(force=True) or {}
            
            job_id = data.get("job_id")
            user_id = data.get("user_id")
            application_text = data.get("application_text", "")
            
            if not job_id:
                return {"error": "job_id is required"}, 400
            if not user_id:
                return {"error": "user_id is required"}, 400
            
            print('='*80)
            print('🆓 CREATE FREE APPLICATION REQUEST')
            print('='*80)
            print(f'📋 job_id: {job_id}')
            print(f'👤 trader_id (user_id): {user_id}')
            print(f'💬 application_text: {application_text[:100] if application_text else "None"}...')
            
            # Check if application already exists (paid or initiated)
            existing_app = Application.objects(
                job_id=job_id,
                trader_id=user_id
            ).first()
            
            if existing_app:
                if existing_app.status == "paid":
                    print(f'✅ Application already exists and is paid: {existing_app.application_id}')
                    return {
                        "success": True,
                        "message": "Application already exists",
                        "applicationId": str(existing_app.application_id),
                        "status": existing_app.status
                    }, 200
                else:
                    # Update existing application to paid status
                    print(f'📝 Updating existing application ({existing_app.status}) to paid')
                    existing_app.status = "paid"
                    existing_app.application_message = application_text
                    existing_app.stripe_pi_id = "free_application_no_payment"
                    existing_app.amount = 0
                    existing_app.currency = "gbp"
                    existing_app.save()
                    print(f'✅ Updated application to paid: {existing_app.application_id}')
                    
                    return {
                        "success": True,
                        "message": "Application updated to paid",
                        "applicationId": str(existing_app.application_id),
                        "status": existing_app.status
                    }, 200
            
            # Create new free application
            print(f'🆕 Creating new free application...')
            app = Application(
                job_id=job_id,
                trader_id=user_id,
                stripe_pi_id="free_application_no_payment",  # Placeholder for required field
                amount=0,  # Free application
                currency="gbp",
                status="paid",  # Set as paid so it works with existing checks
                application_message=application_text
            )
            app.save()
            
            print(f'✅ Created free application: {app.application_id}')
            print('='*80)
            
            return {
                "success": True,
                "message": "Free application created successfully",
                "applicationId": str(app.application_id),
                "status": app.status
            }, 201
            
        except Exception as e:
            print('='*80)
            print(f'❌ ERROR creating free application: {str(e)}')
            print('='*80)
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to create free application: {str(e)}"}, 500


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



class StripeWebhookTest(Resource):
    """
    Simple test endpoint to see what Stripe sends
    """
    
    def post(self):
        print('inside endpoint')
        payload = request.data

        print('show me the payload', payload)
        
        headers = dict(request.headers)
        
        try:
            data = json.loads(payload)
        except:
            data = {"error": "Could not parse JSON"}
        
        print("\n" + "="*80)
        print(f"🔔 WEBHOOK RECEIVED at {datetime.now()}")
        print("="*80)
        
        print("\n📋 HEADERS:")
        print("-"*80)
        for key, value in headers.items():
            print(f"  {key}: {value}")
        
        print("\n📦 PAYLOAD:")
        print("-"*80)
        print(json.dumps(data, indent=2))
        
        print("\n🎯 KEY INFORMATION:")
        print("-"*80)
        
        # Extract useful info if available
        if isinstance(data, dict):
            event_type = data.get('type', 'Unknown')
            print(f"  Event Type: {event_type}")
            
            if 'data' in data and 'object' in data['data']:
                obj = data['data']['object']
                
                print(f"  Payment Intent ID: {obj.get('id', 'N/A')}")
                print(f"  Amount: {obj.get('amount', 'N/A')} {obj.get('currency', '').upper()}")
                print(f"  Status: {obj.get('status', 'N/A')}")
                
                # Check for metadata
                if 'metadata' in obj:
                    print(f"\n  📝 Metadata:")
                    for key, value in obj['metadata'].items():
                        print(f"    {key}: {value}")
        
        print("\n" + "="*80 + "\n")
        
        try:
            with open('webhook_logs.txt', 'a') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Webhook received at {datetime.now()}\n")
                f.write(f"{'='*80}\n")
                f.write(f"Headers:\n{json.dumps(headers, indent=2)}\n")
                f.write(f"Payload:\n{json.dumps(data, indent=2)}\n")
                f.write(f"{'='*80}\n\n")
        except:
            pass
        
        # Always return success so Stripe knows we received it
        return {
            "status": "received",
            "message": "Webhook logged successfully",
            "event_type": data.get('type', 'unknown') if isinstance(data, dict) else 'unknown'
        }, 200