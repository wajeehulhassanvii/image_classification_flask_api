from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import requests
import bcrypt
import subprocess
import json

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.ImageRecognition
users = db['Users']


# handler functions
def user_exists(username):
    """return if user exists or not"""
    if users.find({"Username": username}).count() == 0:
        return False
    else:
        return True


def generateReturnDictionary(status, msg):
    retJson = {
        "status": status,
        "msg": msg
    }
    return retJson


# rest APIs
class Register(Resource):
    def post(self):
        """Post method for user login"""
        posted_data = request.get_json()

        username = posted_data['username']
        password = posted_data['password']

        if user_exists(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username"
            }
            return jsonify(retJson)

        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Tokens": 6
        })

        retJson = {
            "status": 200,
            "msg": "You have successfully signed up to  the image Rec API"
        }
        return jsonify(retJson)


def verify_pw(username, password):
    if not user_exists(username):
        return False
    hashed_pw = users.find({
        "Username": username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw)==hashed_pw:
        return True
    else:
        return False


def verify_credentials(username, password):
    if not user_exists(username):
        return jsonify({
            "status": 302,
            "msg": "Invalid username"
        })
    correct_pw = verify_pw(username, password)
    if not correct_pw:
        return jsonify({
            "status": 302,
            "msg": "Invalid Password"
        })
    return None, False


class Classify(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        url = postedData["url"]

        retJson, error = verify_credentials(username, password)
        if error:
            return jsonify(retJson)

        tokens = users.find({
            "Username":username
        })[0]["Tokens"]

        if tokens<=0:
            return jsonify(generateReturnDictionary(303, "Not Enough Tokens"))

        r = requests.get(url)
        retJson = {}
        with open('temp.jpg', 'wb') as f:
            f.write(r.content)
            proc = subprocess.Popen('python classify_image.py --model_dir=. --image_file=./temp.jpg', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            ret = proc.communicate()[0]
            proc.wait()
            with open("text.txt") as f:
                retJson = json.load(f)


        users.update({
            "Username": username
        },{
            "$set":{
                "Tokens": tokens-1
            }
        })

        return retJson



class Refill(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["admin_pw"]
        amount = posted_data["amount"]

        if not user_exists(username):
            return jsonify({
                "status": 301,
                "msg": "Invalid Username"
            })
        correct_pw = "abc123"

        if not password == correct_pw:
            return jsonify({
                "status": 304,
                "msg": "Invalid Administrator Pasword"
            })

        users.update({
            "Username": username
        },{
            "$set":{
                "Tokens": amount
            }
        })

        return jsonify({
            "status": 200,
            "msg": "Refilled successfully"
        })


api.add_resource(Register, '/register')
api.add_resource(Classify, '/classify')
api.add_resource(Refill, '/refill')

if __name__=="__main__":
    app.run(host="0.0.0.0", port="5000")