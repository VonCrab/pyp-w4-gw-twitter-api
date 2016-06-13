# -*- coding: utf-8 -*-

import binascii
import sqlite3
import os

from flask import Flask
from flask import g
from flask_restful import Resource, Api, reqparse
from utils import *


app = Flask(__name__)
api = Api(app)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


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

        return {'access_token': new_token}, 201

class Logout(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('access_token', type = str, help = 'Access token for API use.')

    def post(self):
        logout_req = self.reqparse.parse_args()

        if not logout_req['access_token']:
            return '', 401

        # remove from the auth table
        g.db.execute("delete from auth where access_token = :token;", {'token': logout_req['access_token']})
        g.db.commit()

        return '', 204


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401

api.add_resource(Login, '/login')
api.add_resource(Logout, '/logout')
