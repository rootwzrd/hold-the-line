## hold-the-line - Simple Python voicemail and SMS/MMS receiver
##                 for holding onto phone numbers in Twilio
## 
## Written in 2015 and 2016 by Vitorio Miliano <http://vitor.io/>
## 
## To the extent possible under law, the author has dedicated all
## copyright and related and neighboring rights to this software
## to the public domain worldwide.  This software is distributed
## without any warranty.
## 
## You should have received a copy of the CC0 Public Domain
## Dedication along with this software.  If not, see
## <http://creativecommons.org/publicdomain/zero/1.0/>.

from flask import Flask, request, redirect
import twilio.twiml
import twilio.rest
import ConfigParser
import marrow.mailer
import sys
import json
import phonenumbers

config = ConfigParser.ConfigParser()
config.readfp(open('holdtheline.cfg'))
twilio_outgoing_message = config.get('holdtheline', 'twilio_outgoing_message')
blocked_numbers = config.get('holdtheline', 'blocked_numbers').split(',')
to_email = config.get('holdtheline', 'to_email')
from_email = config.get('holdtheline', 'from_email')
twilio_account_sid = config.get('holdtheline', 'twilio_account_sid')
twilio_auth_token = config.get('holdtheline', 'twilio_auth_token')

twilioclient = twilio.rest.TwilioRestClient(twilio_account_sid, twilio_auth_token)
mailer = marrow.mailer.Mailer(dict(transport = dict(config.items('marrow.mailer'))))

app = Flask(__name__)

@app.route("/call", methods=['GET', 'POST'])
def handle_call():
    """When someone other than me dials in"""
    from_number = request.values.get('From', None)
    addons = request.values.get('AddOns', None)

    reject = False

    marchex = json.load(addons)
    if 'code' in marchex:
        if marchex['code'] == None:
            if 'marchex_cleancall' in marchex['results']:
                if 'status' in marchex['results']['marchex_cleancall']:
                    if marchex['results']['marchex_cleancall']['status'] == 'successful':
                        if marchex['results']['marchex_cleancall']['result']['result']['recommendation'] == 'BLOCK':
                            reject = True
                            
    try:
        gp = phonenumbers.parse(from_number)
    except:
        reject = True
    else:
        if phonenumbers.is_possible_number(gp):
            if phonenumbers.is_valid_number(gp):
                if gp.country_code == 1:
                    gpi = int(str(gp.national_number)[phonenumbers.phonenumberutil.length_of_national_destination_code(gp):])
                    if gpi >= 5550100 or gpi <= 5550199:
                        reject = True
            else:
                reject = True
        else:
            reject = True
            
    if from_number in blocked_numbers:
        reject = True
        
    resp = twilio.twiml.Response()
    if reject:
        resp.reject()
    else:
        resp.redirect(call_redirect)
        
    return str(resp)

@app.route("/text", methods=['GET', 'POST'])
def handle_text():
    """When someone other than me dials in"""
    from_number = request.values.get('From', None)

    resp = twilio.twiml.Response()
    if from_number in blocked_numbers:
        pass
    else:
        to_number = request.values.get('To', None)
        sms_body = request.values.get('Body', None)
        mail_text = '''{} has a new text from {}.

{}

'''.format(to_number, from_number, sms_body)
    
    try:
        mailer.start()
        message = marrow.mailer.Message(author=from_email, to=to_email)
        message.subject = '[hold-the-line] {} has a text from {}'.format(to_number, from_number)
        message.plain = mail_text
        mailer.send(message)
        mailer.stop()
    except:
        e = sys.exc_info()
        print 'A mailer error occurred: %s - %s' % (e[0], e[1])
        raise

    resp = twilio.twiml.Response()
    return str(resp)

@app.route("/voicemail", methods=['GET', 'POST'])
def handle_voicemail():
    """Goodbye caller"""

    resp = twilio.twiml.Response()
    resp.hangup()
    return str(resp)

@app.route("/transcription", methods=['GET', 'POST'])
def handle_transcription():
    """Notify via email"""
    from_number = request.values.get('From', None)
    to_number = request.values.get('To', None)
    voicemail = request.values.get('RecordingUrl', None)
    transcript_status = request.values.get('TranscriptionStatus', None)
    
    mail_text = '''{} has a new voicemail from {}.

Recording: {}

'''.format(to_number, from_number, voicemail)
    if (transcript_status == "completed"):
        mail_text = mail_text + """Transcription:

{}
""".format(request.values.get('TranscriptionText', None))
    
    try:
        mailer.start()
        message = marrow.mailer.Message(author=from_email, to=to_email)
        message.subject = '[hold-the-line] {} has voicemail from {}'.format(to_number, from_number)
        message.plain = mail_text
        mailer.send(message)
        mailer.stop()
    except:
        e = sys.exc_info()
        print 'A mailer error occurred: %s - %s' % (e[0], e[1])
        raise
    
    resp = twilio.twiml.Response()
    resp.hangup()
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=6600)
