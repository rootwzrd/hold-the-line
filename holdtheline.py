## hold-the-line - Simple Python voicemail and SMS/MMS receiver for holding onto phone numbers in Twilio
## 
## Written in 2015 by Vitorio Miliano <http://vitor.io/>
## 
## To the extent possible under law, the author has dedicated all copyright and related and neighboring rights to this software to the public domain worldwide.  This software is distributed without any warranty.
## 
## You should have received a copy of the CC0 Public Domain Dedication along with this software.  If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from flask import Flask, request, redirect
import twilio.twiml
import twilio.rest
import ConfigParser
import mandrill

config = ConfigParser.ConfigParser()
config.readfp(open('holdtheline.cfg'))
twilio_outgoing_message = config.get('holdtheline', 'twilio_outgoing_message')
blocked_numbers = config.get('holdtheline', 'blocked_numbers').split(',')
line_email = config.get('holdtheline', 'line_email')
mandrill_api = config.get('holdtheline', 'mandrill_api')
mandrill_email = config.get('holdtheline', 'mandrill_email')
twilio_account_sid = config.get('holdtheline', 'twilio_account_sid')
twilio_auth_token = config.get('holdtheline', 'twilio_auth_token')

twilioclient = twilio.rest.TwilioRestClient(twilio_account_sid, twilio_auth_token)
mandrillclient = mandrill.Mandrill(mandrill_api)

app = Flask(__name__)

@app.route("/call", methods=['GET', 'POST'])
def handle_call():
    """When someone other than me dials in"""
    from_number = request.values.get('From', None)

    resp = twilio.twiml.Response()
    if from_number in blocked_numbers:
        resp.reject()
    else:
        resp.play(twilio_outgoing_message) # This audio file has a beep in it already
        resp.record(maxLength="300", playBeep=False, action="/voicemail", transcribe=True, transcribeCallback="/transcription")
        resp.say("Sorry, I couldn't hear your message.  Please try your call again later.")
        
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
        message = {'to': [{'email': line_email}],
                   'from_email': mandrill_email,
                   'subject': '[hold-the-line] {} has a text from {}'.format(to_number, from_number),
                   'text': mail_text}
        result = mandrillclient.messages.send(message=message)
    except mandrill.Error, e:
        print 'A mandrill error occurred: %s - %s' % (e.__class__, e)
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
        message = {'to': [{'email': line_email}],
                   'from_email': mandrill_email,
                   'subject': '[hold-the-line] {} has voicemail from {}'.format(to_number, from_number),
                   'text': mail_text}
        result = mandrillclient.messages.send(message=message)
    except mandrill.Error, e:
        print 'A mandrill error occurred: %s - %s' % (e.__class__, e)
        raise
    
    resp = twilio.twiml.Response()
    resp.hangup()
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=6600)
