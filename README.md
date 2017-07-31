# hold-the-line

hold-the-line - Simple Python voicemail and SMS/MMS receiver for holding onto phone numbers in Twilio

Verifies Twilio security signatures at all times; this may make local testing difficult without additional changes.

Runs through AWS Lambda via [Zappa](https://github.com/Miserlou/Zappa), see past commits for gevent/systemd/init.d/etc. versions.

## Zappa usage

```console
$ ~/Library/Python/2.7/bin/virtualenv env
$ source env/bin/activate
(env) $ pip install 'twilio<6.0' zappa phonenumbers marrow.mailer flask
(env) $ zappa init
```

Then edit your `zappa_settings.json` to reflect your usage, e.g. if this is one of many hold-the-line instances, changing the name of the deployed project:

```json
{
    "dev": {
        "app_function": "holdtheline.app", 
        "aws_region": "us-east-2", 
        "profile_name": "zappa", 
        "s3_bucket": "zappa-██████████",
        "keep_warm": false,
        "project_name": "holdtheline-██████████"
    }
}
```

`keep_warm` is also set to `false` because Twilio will wait up to 15s for a response, and even on a cold start, Lambda will generally return in that time or less.

I deploy two different instances from the same source, so to deploy I then do:

```console
(env) $ cp holdtheline.██████████.cfg holdtheline.cfg
(env) $ zappa deploy dev -s zappa_settings.██████████.json 
```

## Public domain

Written in 2015 and 2016 and 2017 by Vitorio Miliano <http://vitor.io/>

To the extent possible under law, the author has dedicated all copyright and related and neighboring rights to this software to the public domain worldwide.  This software is distributed without any warranty.

You should have received a copy of the CC0 Public Domain Dedication along with this software.  If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.
