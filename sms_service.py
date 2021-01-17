from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import Element

import xml.etree.ElementTree as etree

from sms_config import (USERNAME, PASSWORD,
                        SENDER)
import requests
from urllib.parse import urlencode, quote_plus


def send_sms(recipient, sms_content):
    # print("===Sending sms==== to%s " % recipient)
    url = "https://uapi.inforu.co.il/SendMessageXml.ashx"
    root = Element("Inforu")
    tree = ElementTree(root)

    # User
    user = Element("User")
    root.append(user)

    username = etree.SubElement(user, "Username")
    username.text = USERNAME
    password = etree.SubElement(user, "Password")
    password.text = PASSWORD

    # Content
    content = Element("Content")
    content.set("Type", "sms")
    root.append(content)
    message = etree.SubElement(content, "Message")
    message.text = sms_content

    # Recipients
    recipients = Element("Recipients")
    root.append(recipients)
    phone_number = etree.SubElement(recipients, "PhoneNumber")
    phone_number.text = recipient

    # Settings
    settings = Element("Settings")
    root.append(settings)
    sender = etree.SubElement(settings, "Sender")
    sender.text = SENDER

    data = etree.tostring(root).decode()
    # print("=== XML data is==")
    # print(data)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = {"InforuXML": data}
    payload = urlencode(payload, quote_via=quote_plus)
    response = requests.request("POST", url,
                                headers=headers,
                                data=payload)
    # print(response.text.encode('utf8'))
    return response.text.encode('utf8')
