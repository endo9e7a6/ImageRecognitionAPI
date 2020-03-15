from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import requests
import subprocess
from classify_image import classify


app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.usersDatabase
users_col = db["users"]
users_col.drop()






def check_credentials_format(posted_data):
    if "username" not in posted_data or "password" not in posted_data:
        return 301
    if type(posted_data["username"]) not in [str] or type(posted_data["password"]) not in [str]:
        return 302
    return 200


def check_password(posted_data):
    username = posted_data["username"]
    if username not in users_col.distinct("username"):
        return 310
    encoded_password = users_col.find({"username": username})[0]["password"]
    if not bcrypt.checkpw(posted_data["password"].encode('utf8'), encoded_password):
        return 311
    return 200


def check_image_format(posted_data):
    if "image_url" not in posted_data:
        return 301
    if type(posted_data["image_url"]) not in [str]:
        return 302
    return 200


class Register(Resource):
    def post(self):
        posted_data = request.get_json()
        status_code = check_credentials_format(posted_data)
        if status_code != 200:
            return jsonify({
                "Message": "Problem with credentials format",
                "Status Code": status_code
            })

        username = posted_data['username']
        password = posted_data['password']
        l_users = users_col.distinct("username")
        if username in l_users:
            return jsonify({
                "Message": "User already exists",
                "Status Code": 303
            })

        salt = bcrypt.gensalt(10)
        hashed = bcrypt.hashpw(password.encode('utf8'), salt)

        users_col.insert({"username": username, "password": hashed, "tokens": 10})

        return jsonify({
            "Status Code": 200,
            "Message": "User registerd succesfully"
        })


class ClassifyImage(Resource):
    def post(self):
        posted_data = request.get_json()
        status_code = check_credentials_format(posted_data)
        if status_code != 200:
            return jsonify({
                "Message": "Problem with credentials format",
                "Status Code": status_code
            })
        status_code = check_password(posted_data)
        if status_code != 200:
            return jsonify({
                "Message": "Incorrect credentials",
                "Status Code": status_code
            })
        status_code = check_image_format(posted_data)
        if status_code != 200:
            return jsonify({
                "Message": "Problem with documents format",
                "Status Code": status_code
            })

        username = posted_data["username"]
        tokens = users_col.find({"username": username})[0]["tokens"]
        if tokens <= 0:
            return jsonify({
                "Message": "Not enough tokens",
                "Status Code": 330
            })

        tokens -= 1
        users_col.update({"username": username}, {"$set": {"tokens": tokens}})




        # ur = 'https://images.unsplash.com/photo-1526319238109-524eecb9b913?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&w=1000&q=80'
        ur = posted_data["image_url"]
        r = requests.get(ur)
        with open("temp.jpg", "wb") as f:
            f.write(r.content)
            f.close()

        d_results = classify(model_dir='./', image_file='./temp.jpg', num_top_predictions=5)


        return jsonify({
            "Message": "[{}] Classification: {}".format(tokens, str(d_results)),
            "Status Code": 200
        })


api.add_resource(Register, '/register')
api.add_resource(ClassifyImage, '/classify')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port="5000", debug=True)


