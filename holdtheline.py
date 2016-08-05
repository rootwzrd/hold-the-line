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
BLOCKED_NUMBERS = config.get('holdtheline', 'blocked_numbers').split(',')
CALL_REDIRECT = config.get('holdtheline', 'call_redirect')
BUTTON_SELECTION = config.get('holdtheline', 'button_selection')
BUTTON_REDIRECT = config.get('holdtheline', 'button_redirect')
BUTTONRETRY1_REDIRECT = config.get('holdtheline', 'buttonretry1_redirect')
BUTTONRETRY2_REDIRECT = config.get('holdtheline', 'buttonretry2_redirect')
BUTTONRETRY3_REDIRECT = config.get('holdtheline', 'buttonretry3_redirect')
TO_EMAIL = config.get('holdtheline', 'to_email')
FROM_EMAIL = config.get('holdtheline', 'from_email')
TEXT_SUBJECT = config.get('holdtheline', 'text_subject')
VOICEMAIL_SUBJECT = config.get('holdtheline', 'voicemail_subject')
TWILIO_ACCOUNT_SID = config.get('holdtheline', 'twilio_account_sid')
TWILIO_AUTH_TOKEN = config.get('holdtheline', 'twilio_auth_token')

twilioclient = twilio.rest.TwilioRestClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
mailer = marrow.mailer.Mailer(dict(transport = dict(config.items('marrow.mailer'))))

app = Flask(__name__)

def pass_number(number, addons):
    """Check number validity"""
    passnum = True
    
    try:
        marchex = json.load(addons)
        if marchex['results']['marchex_cleancall']['result']['result']['recommendation'] == 'BLOCK':
            passnum = False
    except:
        pass
                            
    try:
        gp = phonenumbers.parse(number)
    except:
        passnum = False
    else:
        if phonenumbers.is_possible_number(gp):
            if phonenumbers.is_valid_number(gp):
                if gp.country_code == 1:
                    gpi = int(str(gp.national_number)[phonenumbers.phonenumberutil.length_of_national_destination_code(gp):])
                    if gpi >= 5550100 and gpi <= 5550199:
                        passnum = False
            else:
                passnum = False
        else:
            passnum = False
            
    if number in BLOCKED_NUMBERS:
        passnum = False
        
    return passnum

@app.route("/call", methods=['GET', 'POST'])
def handle_call():
    """Check number validity and redirect or reject"""
    from_number = request.values.get('From', None)
    addons = request.values.get('AddOns', None)

    resp = twilio.twiml.Response()
    
    if pass_number(from_number, addons):
        resp.redirect(CALL_REDIRECT)
    else:
        resp.reject()
        
    return str(resp)

@app.route("/text", methods=['GET', 'POST'])
def handle_text():
    """Check number validity and reject or send email"""
    from_number = request.values.get('From', None)
    addons = request.values.get('AddOns', None)
        
    if pass_number(from_number, addons):
        to_number = request.values.get('To', None)
        sms_body = request.values.get('Body', None)
        mms = request.values.get('NumMedia', None)
        mail_text = '''{} has a new text from {}.

{}

'''.format(to_number, from_number, sms_body)

        if mms:
            mms = int(mms)
            if mms > 0:
                for m in range(0, mms):
                    mc = request.values.get('MediaUrl{}'.format(m), None)
                    mail_text = mail_text + '''Media content: {}
'''.format(mc)
        
        try:
            mailer.start()
            message = marrow.mailer.Message(author=FROM_EMAIL, to=TO_EMAIL)
            message.subject = TEXT_SUBJECT.format(from_num=from_number, to_num=to_number)
            message.plain = mail_text
            mailer.send(message)
            mailer.stop()
        except:
            e = sys.exc_info()
            print 'A mailer error occurred: %s - %s' % (e[0], e[1])
            raise

    resp = twilio.twiml.Response()
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
        message = marrow.mailer.Message(author=FROM_EMAIL, to=TO_EMAIL)
        message.subject = VOICEMAIL_SUBJECT.format(from_num=from_number, to_num=to_number)
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

@app.route('/button', methods=['GET', 'POST'])
def handle_button():
    """Route based on a single button selection"""
    digit_pressed = request.values.get('Digits', None)
    retry_time = request.values.get('Retry', None)
    
    resp = twilio.twiml.Response()
    
    if int(digit_pressed) == int(BUTTON_SELECTION):
        resp.redirect(BUTTON_REDIRECT)
    else:
        if int(retry_time) == 1:
            resp.redirect(BUTTONRETRY1_REDIRECT)
        elif int(retry_time) == 2:
            resp.redirect(BUTTONRETRY2_REDIRECT)
        else:
            resp.redirect(BUTTONRETRY3_REDIRECT)
    
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=6600)
