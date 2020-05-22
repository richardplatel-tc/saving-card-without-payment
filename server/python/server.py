#! /usr/bin/env python3.6

"""
server.py
Stripe Recipe.
Python 3.6 or newer required.
"""

import stripe
import json
import os

from flask import Flask, render_template, jsonify, request, send_from_directory
from dotenv import load_dotenv, find_dotenv

from uuid import uuid4 as uuid
from traceback import format_exc

# Setup Stripe python client library
load_dotenv(find_dotenv())
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
stripe.api_version = os.getenv('STRIPE_API_VERSION')

static_dir = str(os.path.abspath(os.path.join(
    __file__, "..", os.getenv("STATIC_DIR"))))
app = Flask(__name__, static_folder=static_dir,
            static_url_path="", template_folder=static_dir)

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

@app.route('/customers')
def list_customers():
    return jsonify({c : 'payment_method' in v for c,v in read_store().items()})

@app.route('/customers/<cid>/charge', methods=['POST'])
def charge_customer(cid):
    class NoError(Exception): #woof!
        pass
    ret = dict()
    ret['status'] = []
    try:
        c = get_customer(cid)
        ret['status'].append(f'Found customer {cid}')
        if 'payment_method' not in c:
            ret['status'].append(f'No PaymentMethod stored locally, querying Stripe')
            pms = stripe.PaymentMethod.list(
                customer=c['stripe_customer'],
                type="card",
            )
            if pms and 'data' in pms and len(pms['data']):
                c['payment_method'] = pms['data'][0]['id']
                save_customer(c)
                ret['status'].append(f'Found PaymentMethod {c["payment_method"]} in Stripe, saved locally')
            else:
                ret['status'].append(f'No PaymentMethods for customer')
                raise NoError()
        else:
            ret['status'].append('Client has a PaymentMethod stored locally')

        # Charge that cust!
        pm = c['payment_method']
        ret['status'].append(f'Creating PaymentIntent with method {pm}')
        pm = stripe.PaymentIntent.create(
            amount=1099,
            currency='usd',
            customer=c['stripe_customer'],
            payment_method=pm,
            off_session=True,
            confirm=True,
        )
        ret['status'].append(f'Created PaymentIntent {pm["id"]} status {pm["status"]}')

    except Exception as e:
        if  type(e) is not NoError: 
            ret['exception'] = format_exc() 
    finally:
        return jsonify(ret)
        

@app.route('/', methods=['GET'])
def get_setup_intent_page():
    return render_template('index.html')


@app.route('/public-key', methods=['GET'])
def get_publishable_key():
    return jsonify(publicKey=os.getenv('STRIPE_PUBLISHABLE_KEY'))


@app.route('/create-setup-intent', methods=['POST'])
def create_setup_intent():
    # Create or use an existing Customer to associate with the SetupIntent.
    # The PaymentMethod will be stored to this Customer for later use.
    customer = stripe.Customer.create()

    setup_intent = stripe.SetupIntent.create(
        customer=customer['id']
    )
    save_customer({
        'stripe_customer' : customer['id'],
        'stripe_setup_intent' : setup_intent['id'],
    })
    
    return jsonify(setup_intent)


@app.route('/webhook', methods=['POST'])
def webhook_received():
    # You can use webhooks to receive information about asynchronous payment events.
    # For more about our webhook events check out https://stripe.com/docs/webhooks.
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    request_data = json.loads(request.data)

    if webhook_secret:
        # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
        signature = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                payload=request.data, sig_header=signature, secret=webhook_secret)
            data = event['data']
        except Exception as e:
            return e
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event['type']
    else:
        data = request_data['data']
        event_type = request_data['type']
    data_object = data['object']

    if event_type == 'setup_intent.created':
        print('🔔 A new SetupIntent was created.')

    if event_type == 'setup_intent.succeeded':
        print(
            '🔔 A SetupIntent has successfully set up a PaymentMethod for future use.')
    
    if event_type == 'payment_method.attached':
        print('🔔 A PaymentMethod has successfully been saved to a Customer.')

        # At this point, associate the ID of the Customer object with your
        # own internal representation of a customer, if you have one.

        # Optional: update the Customer billing information with billing details from the PaymentMethod
        stripe.Customer.modify(
            data_object['customer'],
            email=data_object['billing_details']['email']
        )
        print('🔔 Customer successfully updated.')

    if event_type == 'setup_intent.setup_failed':
        print(
            '🔔 A SetupIntent has failed the attempt to set up a PaymentMethod.')

    return jsonify({'status': 'success'})


if __name__ == '__main__':
    app.run(host="localhost", port=4242, debug=True)
