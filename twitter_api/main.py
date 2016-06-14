import binascii
import sqlite3
import os

from flask import Flask
from flask import g
from flask_restful import Resource, Api, reqparse
from utils import *


app = Flask(__name__)
api = Api(app)

profile_properties = ['user_id', 'username', 'first_name', 'last_name', 'birth_date']
tweet_properties = ['id', 'text', 'date']

def connect_db(db_name):
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

def format_tweets(tweet):
    tweet_resource = dict(zip(tweet_properties, tweet))
    tweet_resource['uri'] = '/tweet/{}'.format(tweet['id'])
    return tweet_resource


# implement your views here
class Login(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('username', type = str, required = True, help = 'Username of profile.')
        self.reqparse.add_argument('password', type = str, required = True, help = 'Password for profile.')

    def post(self):
        login_req = self.reqparse.parse_args(strict = True)
        user_info = g.db.execute('select username, password, id from user where username = :user_req;', {'user_req': login_req['username']}).fetchone()

        if not user_info:
            return '', 404

        if not user_info[1] == md5(login_req['password'].encode('utf-8')).hexdigest():
            return '', 401

        new_token = binascii.hexlify(os.urandom(32))

        g.db.execute('insert into auth (user_id, access_token) values (:usr, :token);', {'usr': user_info[2], 'token': new_token})
        g.db.commit()
        import pdb; pdb.set_trace()
        return {'access_token': new_token}, 201

class Logout(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('access_token', type = str, help = 'Access token for API use.')

    def post(self):
        logout_req = self.reqparse.parse_args()

        if not logout_req['access_token']:
            return '', 401

        g.db.execute("delete from auth where access_token = :token;", {'token': logout_req['access_token']})
        g.db.commit()

        return '', 204

class Profile(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('first_name', type = str, help = 'First name for profile.', required = True)
        self.reqparse.add_argument('last_name', type = str, help = 'Last name for profile.', required = True)
        self.reqparse.add_argument('birth_date', type = str, help = 'Birthdate for profile.', required = True)
        self.reqparse.add_argument('access_token', type = str, help = 'Access token for session.')

    def get(self, username):
        g.db.row_factory = sqlite3.Row
        user_info = g.db.execute("select id, username, first_name, last_name, birth_date from user where username = :user;", {'user': username}).fetchone()

        if not user_info:
            return '', 404

        profile = dict(zip(profile_properties, user_info))

        tweets = g.db.execute("select id, content, created from tweet where user_id = :user;", {'user': profile['user_id']}).fetchall()

        profile['tweet'] = [format_tweets(tweet) for tweet in tweets]
        profile['tweet_count'] = len(tweets)

        return profile

    def post(self):
        profile_req = self.reqparse.parse_args(strict =  True)

        if not profile_req['access_token']:
            return '', 401

        user = g.db.execute("select user_id from auth where access_token = :token;", {'token': profile_req['access_token']}).fetchone()

        if not user:
            return '', 401

        g.db.execute('update user set first_name = :first, last_name = :last, birth_date = :birth where id = :usr', {'first': profile_req['first_name'], 'last': profile_req['last_name'], 'birth': profile_req['birth_date'], 'usr': user[0]})
        g.db.commit()

        return '', 201


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401

api.add_resource(Login, '/login')
api.add_resource(Logout, '/logout')
api.add_resource(Profile, '/profile/<string:username>', '/profile')
