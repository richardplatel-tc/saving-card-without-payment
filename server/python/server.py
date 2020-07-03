#! /usr/bin/env python3.6

"""
server.py
SSVC-Payments setupintent demo
Python 3.6 or newer required.
"""

import requests
import json
import os

from flask import Flask, render_template, jsonify, request, send_from_directory
from dotenv import load_dotenv, find_dotenv

from uuid import uuid4 as uuid
from traceback import format_exc
from time import time

load_dotenv(find_dotenv())

static_dir = str(os.path.abspath(os.path.join(
    __file__, "..", os.getenv("STATIC_DIR"))))
ssvc_url = os.getenv("SSVC_PAYMENTS_URL")
ssvc_auth = os.getenv("SSVC_AUTH_KEY")

app = Flask(__name__, static_folder=static_dir,
            static_url_path="", template_folder=static_dir)

def ssvc_get(url, *args, **kwargs):
    headers = kwargs.pop('headers', {})
    headers.setdefault("x-srs-auth-api-key", ssvc_auth)
    u = '{}{}'.format(ssvc_url, url)
    return requests.get(
        u,
        *args,
        headers=headers,
        **kwargs)

def ssvc_post(url, *args, **kwargs):
    headers = kwargs.pop('headers', {})
    headers.setdefault("x-srs-auth-api-key", ssvc_auth)
    headers.setdefault("Content-Type", "application/json")
    u = '{}{}'.format(ssvc_url, url)
    return requests.post(
        u,
        *args,
        headers=headers,
        **kwargs)


_datastore='vault.json'
def read_store():
    with open(_datastore, 'r') as ds:
        return json.load(ds)

def write_store(s):
    with open(_datastore, 'w') as ds:
        json.dump(s, ds, indent=2)

def save_customer(cust):
    s = read_store()
    if "_id" not in cust:
        cust['_id'] = str(uuid())
    s[cust['_id']] = cust
    write_store(s)

def get_customer(cid):
    s = read_store()
    return s[cid]

def fetch_customer_details(cid, vault_id):
    # Note these are old API methods that work with vault ids, nothing 
    # new for setupintents.
    r = ssvc_get('vault/items/{}'.format(vault_id))

    # ignore 404s, these are setupintents that were never confirmed, see note
    # in create_setup_intent()
    if r.ok:
        cc = r.json()['object_data']['credit_card']
        return {
            'name' : cc['contact']['billing']['first_name'] + cc['contact']['billing']['last_name'],
            'email' : cc['contact']['billing']['email'],
            'address' : cc['contact']['billing']['address'],
            'type' : cc['type'],
            'number' : cc['number'],
            'exp' : '{}/{}'.format(cc['month'], cc['year']),
            }
    else:
        return None

@app.route('/customers')
def list_customers():
    ret = dict()
    for c,v in read_store().items():
        d = fetch_customer_details(c, v['vault_item_id'])
        if d: ret[c] = d
    return jsonify(ret)

@app.route('/customers/<cid>/charge', methods=['POST'])
def charge_customer(cid):
    c = get_customer(cid)
    vid = c['vault_item_id']
    req_cust = {
        "id": "12354", 
        "ip_address": "44.22.14.65"
    }
    req_tx = {
        "type" : "CHARGE",
        "order_id" : str(int(time())),
        "currency": "USD",
        "descriptor" : "ABC 123",
        "amount" : 2323,
    }
    req_vi = {
        "id" : vid,
        "contact" : {
            "shipping" : {}
        }
    }
        

    r = ssvc_post('payments',
        data = json.dumps({
            "vault_item" : req_vi,
            "transaction" : req_tx,
            "customer" : req_cust,
        }),
    )

    return jsonify(r.json())
        

@app.route('/', methods=['GET'])
def get_setup_intent_page():
    return render_template('index.html')


@app.route('/create-setup-intent', methods=['POST'])
def create_setup_intent():

    r = ssvc_post(
        "setup",
        data = json.dumps({}),
    )
    setup_intent = r.json()['object_data']['processor_fields']
    # for demo save every vault_id we get, in reality it only makes sense
    # to save the vault id if/when the end-user-device confirms a payment method
    save_customer({
        'vault_item_id' : r.json()['object_data']['vault_item_id']
    })
    return jsonify(setup_intent)

if __name__ == '__main__':
    app.run(host="localhost", port=4242, debug=True)
