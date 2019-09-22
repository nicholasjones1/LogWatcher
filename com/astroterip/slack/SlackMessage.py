# send a message to a Slack web hooks app
import argparse
import configparser

import requests


class Slack:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)
        self.security_token = self.config["slack"]["security_token"]
        self.slack_url = self.config["slack"]["slack_url"]
        self.content_type = self.config["slack"]["content_type"]
    # end def

    def send_message(self, message):
        data = "{\"text\":" + "\"" + message + "\"}"
        headers = {'content-type': 'application/json'}
        r = requests.post(self.slack_url+self.security_token, headers=headers, data=data)
        print(r.text)
    # end def
# end class

def main(args):
    slack = Slack("slack.ini")

    slack.send_message(args.msg)
# end if


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Send a message to Slack')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('-m', '--message', action='store', dest='msg')

    args = parser.parse_args()

    main(args)
# end if


