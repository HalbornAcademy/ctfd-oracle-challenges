#!/usr/bin/env python3
from flask import Flask, request, abort
from brownie import *
from dotenv import load_dotenv
import json
import os

import random

app = Flask(__name__)

load_dotenv()

challenges = {}


@app.route("/create", methods=["POST"])
def create():
    """
    Create challenge given a team_id. If force_new is true,
    a new instance must be created and the old instance may be deleted.

    Return a description containing any
    information needed to access the challenge

    > return challenge_details
    """
    data = request.form or request.get_json()
    team_id = str(data["team_id"])
    force_new = data["force_new"]

    def _new_challenge():
        return Challenge1.deploy({'from':a[0]})

    if force_new:
        challenges[team_id] = _new_challenge()

    try:
        challenges[team_id]
    except KeyError:
        challenges[team_id] = _new_challenge()

    return "Challenge deployed at: {}".format(challenges[team_id])

@app.route("/attempt", methods=["POST"])
def check_solve():
    """
    Check a solve, given a team_id

    Return with a 200 code on successful solve or abort on
    a failed solve attempt
    """
    data = request.form or request.get_json()

    team_id = str(data["team_id"])

    try:
        challenge = challenges[team_id]
    except KeyError:
        abort(401)

    if challenge.solved():
        return {'correct': True, 'message': 'Solved'}
    else:
        return {'correct': False, 'message': 'Not solved'}

@app.route("/fund", methods=["POST"])
def do_fund():
    """
    Check a solve, given a team_id

    Return with a 200 code on successful solve or abort on
    a failed solve attempt
    """
    data = request.form or request.get_json()

    wallet = str(data["wallet"])

    if wallet == '' or wallet is None:
        return "No wallet provided"

    try:
        accounts[0].transfer(wallet, web3.toWei(1, 'ether'))
        return "Send 1 ETHER"
    except Exception as e:
        return str(e)

def main():
    accounts.from_mnemonic(os.getenv('MNEMONIC'))
    app.run(debug=True, threaded=True, host="127.0.0.1", port=4001)