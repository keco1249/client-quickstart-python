import os, re;
from flask import Flask, jsonify, request, Response
from faker import Factory
from twilio.util import TwilioCapability
import twilio.twiml

app = Flask(__name__)
fake = Factory.create()
alphanumeric_only = re.compile('[\W_]+')
phone_pattern = re.compile(r"^[\d\+\-\(\) ]+$")

# Account Sid and Auth Token can be found in your account dashboard
ACCOUNT_SID = 'ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
AUTH_TOKEN = 'YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY'

# TwiML app outgoing connections will use
APP_SID = 'APZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ'

CALLER_ID = '+12345678901'
CLIENT = 'jenny'

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/token', methods=['GET'])
def token():
    # get credentials for environment variables
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    application_sid = os.environ['TWILIO_TWIML_APP_SID']
    
    # Generate a random user name
    identity = alphanumeric_only.sub('', fake.user_name())

    # Create a Capability Token
    capability = TwilioCapability(account_sid, auth_token)
    capability.allow_client_outgoing(application_sid)
    capability.allow_client_incoming(identity)
    token = capability.generate()

    # Return token info as JSON
    return jsonify(identity=identity, token=token)

@app.route('/app_token')
def apptoken():
    account_sid = os.environ.get("ACCOUNT_SID", ACCOUNT_SID)
    auth_token = os.environ.get("AUTH_TOKEN", AUTH_TOKEN)
    app_sid = os.environ.get("APP_SID", APP_SID)

    capability = TwilioCapability(account_sid, auth_token)

    # This allows outgoing connections to TwiML application
    if request.values.get('allowOutgoing') != 'false':
        capability.allow_client_outgoing(app_sid)

    # This allows incoming connections to client (if specified)
    client = request.values.get('client')
    if client != None:
        capability.allow_client_incoming(client)

    # This returns a token to use with Twilio based on the account and capabilities defined above
    return capability.generate()

@app.route('/call', methods=['GET', 'POST'])
def call():
  """ This method routes calls from/to client                  """
  """ Rules: 1. From can be either client:name or PSTN number  """
  """        2. To value specifies target. When call is coming """
  """           from PSTN, To value is ignored and call is     """
  """           routed to client named CLIENT                  """
  resp = twilio.twiml.Response()
  from_value = request.values.get('From')
  to = request.values.get('To')
  if not (from_value and to):
    resp.say("Invalid request")
    return str(resp)
  from_client = from_value.startswith('client')
  caller_id = os.environ.get("CALLER_ID", CALLER_ID)
  if not from_client:
    # PSTN -> client
    resp.dial(callerId=from_value).client(CLIENT)
  elif to.startswith("client:"):
    # client -> client
    resp.dial(callerId=from_value).client(to[7:])
  else:
    # client -> PSTN
    resp.dial(to, callerId=caller_id)
  return str(resp)

    
@app.route("/voice", methods=['POST'])
def voice():
    resp = twilio.twiml.Response()
    if "To" in request.form and request.form["To"] != '':
        dial = resp.dial(callerId=os.environ['TWILIO_CALLER_ID'])
        # wrap the phone number or client name in the appropriate TwiML verb
        # by checking if the number given has only digits and format symbols
        if phone_pattern.match(request.form["To"]):
            dial.number(request.form["To"])
        else:
            dial.client(request.form["To"])
    else:
        resp.say("Thanks for calling!")

    return Response(str(resp), mimetype='text/xml')


if __name__ == '__main__':
    app.run(debug=True)