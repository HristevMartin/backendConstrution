import json
from datetime import datetime

from flask import request
from marshmallow import ValidationError
from mongoengine import NotUniqueError, DoesNotExist

from managers.user import User
from models.passenger import Passenger, PassengerType
from flask_restful import Resource
from mongoengine.queryset.visitor import Q

from models.user import Users


class PassengersByCartId(Resource):
    def get(self, cartId):
        try:
            passengers = Passenger.objects(cartId=cartId)
            data_to_return = [{
                'id': str(passenger.id),
                'title': passenger.title,
                'firstName': passenger.firstName,
                'lastName': passenger.lastName,
                'dateOfBirth': passenger.dateOfBirth.strftime('%Y-%m-%d') if passenger.dateOfBirth else None,
                'gender': passenger.gender,
                'nationality': passenger.nationality,
                'passportNumber': passenger.passportNumber,
                'email': passenger.email,
                'phoneNumber': passenger.phoneNumber,
                'address': passenger.address,
                'frequentFlyerNumber': passenger.frequentFlyerNumber
            } for passenger in passengers]
            return data_to_return, 200
        except Exception as e:
            return {'message': str(e)}, 500

class CreatePassenger(Resource):
    def post(self):
        data = request.get_json()

        if not data or 'firstName' not in data or 'lastName' not in data or 'cartId' not in data or 'passengerType' not in data:
            return {"message": "Missing required fields"}, 400

        try:
            passenger_type = PassengerType.objects.get(passenger_type=data['passengerType']['passengerType'])
            passenger_type_string = passenger_type.passenger_type
        except PassengerType.DoesNotExist:
            return {"message": "Invalid passengerTypeId"}, 400

        try:
            passenger = Passenger(
                title=data['title'],
                firstName=data['firstName'],
                lastName=data['lastName'],
                dateOfBirth=data['dateOfBirth'],
                gender=data['gender'],
                nationality=data['nationality'],
                passportNumber=data['passportNumber'],
                email=data['email'],
                phoneNumber=data['phoneNumber'],
                address=data['address'],
                emergencyContactName=data['emergencyContactName'],
                emergencyContactPhone=data['emergencyContactPhone'],
                bookingId=data.get('bookingID'),
                cartId=data['cartId'],
                passengerType=passenger_type_string,
                frequentFlyerNumber=data.get('frequentFlyerNumber')
            )
            passenger.save()
            data = passenger.to_mongo().to_dict()
            data['_id'] = str(data['_id'])
            return data['_id'], 201
        except ValidationError as e:
            return {"message": str(e)}, 400


class ListAllPassengers(Resource):
    def get(self):
        passengers = Users.objects.all()
        data_to_return = [json.loads(passenger.to_json()) for passenger in passengers]
        return data_to_return, 200


class PassengerDetail(Resource):
    def patch(self, id):
        data = request.get_json()
        if not data:
            return {"message": "Missing data payload"}, 400
        try:
            passenger = Passenger.objects.get(id=id)

            if 'name' in data:
                first_name, last_name = data['name'].split()
                data['firstName'] = first_name
                data['lastName'] = last_name
                data['dateOfBirth'] = data['dob']
                data.pop('dob')
                data.pop('name')

            for key, value in data.items():
                if hasattr(passenger, key):
                    setattr(passenger, key, value)

            passenger.save()
            return {"message": "Passenger updated successfully"}, 200

        except ValidationError as ve:
            return {"message": str(ve)}, 400
        except DoesNotExist:
            return {"message": "Passenger not found"}, 404
        except Exception as e:
            return {"message": str(e)}, 500

class SearchPassengers(Resource):
    def post(self):
        data = request.get_json()

        search_query = data.get('searchQuery')
        if not search_query:
            passengers = Passenger.objects.all()
            data_to_return = [json.loads(passenger.to_json()) for passenger in passengers]
            return data_to_return, 200

        try:
            dob = datetime.strptime(search_query, "%Y-%m-%d")
            query = Q(dateOfBirth=dob)
        except ValueError:
            query = Q(firstName__icontains=search_query) | Q(lastName__icontains=search_query)

        results = Passenger.objects(query)

        passengers = [{
            "id": str(passenger.id),
            "name": passenger.firstName + ' ' + passenger.lastName,
            "dob": passenger.dateOfBirth.strftime("%Y-%m-%d") if passenger.dateOfBirth else None,
            "email": passenger.email,
            "mobile": passenger.phoneNumber
        } for passenger in results]

        if not passengers:
            return {"passengers": [], "message": "No passengers found"}, 200

        return passengers, 200