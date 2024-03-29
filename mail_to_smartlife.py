import imaplib
import requests
from email.header import decode_header
import webbrowser
import os
from imap_tools import MailBox,A
import re
from tuyapy import TuyaApi
import time
import schedule
import cronitor

list_devices = []
# account credentials

cronitor.api_key = os.environ['CRONITOR']
my_email = os.environ['MAIL']
my_pass = os.environ['PASS']
DEBUG = os.environ['DEBUG']
genie_key = os.environ['OPSGENIE']
monitor = cronitor.Monitor('D9XpQJ')


class switch:
    def __init__(self, id, nombre, obj):
        self.id = id
        self.nombre = nombre
        self.obj = obj

def opsgenie(message):
    headers_opsgenie = {'Authorization': genie_key,'Content-Type': 'application/json'}
    endpoint_opsgenie = "https://api.opsgenie.com/v2/alerts"
    payload="{\n    \"message\": \""+message+"\"\n}"
    response = requests.post(endpoint_opsgenie, headers=headers_opsgenie, data=payload)
    return response


def rebootByName(list_devices,name):
        try:
            list_devices[name].turn_off()
            time.sleep(10)
            list_devices[name].turn_on()
            time.sleep(240)
            return True
        except Exception as e:
            print("Excepcion en Reboot: ")
            print(e)
            return False


def list_SmartLifeObjs():
    list_devices = False
    while list_devices == False:
        try:
            api = TuyaApi()
            username,password,country_code,application = "guido@pilarmining.co","Creative31.","44","smart_life"
            api.init(username,password,country_code,application)
            devices = api.get_all_devices()
            list_devices = dict(sorted(dict((i.name(),i) for i in devices if i.obj_type == 'switch').items()))
        except Exception as e:
            print("Error Obteniendo datos de SmartLife")
            print(e)
            list_devices = False
            time.sleep(10)
    return list_devices


def checkEmail(my_email,my_pass):
    try:
        list_mails=[]
        monitor.ping(state='run')
        mailbox =  MailBox('imap.gmail.com').login(my_email, my_pass )
        for msg in mailbox.fetch(A(seen=False)):
            print("NEW MAIL")
            list_mails.append(msg.text)
        monitor.ping(state='complete')
        mailbox.logout()
    except Exception as e:
        monitor.ping(state='fail')
    return list_mails


def getRigsFromMail(list_mails):
    list_rigs=[]
    for body in list_mails:
        body = body.replace("*","")
        tuple = ("p","a","b","c","d")
        for letter in tuple:
            for m in re.finditer(f"\.{letter}", body):
                index = m.start()
                string = body[index+1]+body[index+2]+body[index+3]+body[index+4]+body[index+5]
                list_rigs.append(string.upper())
                print('RIG CON ERROR: ',string.upper())
    return list_rigs

def update_list_smartlife():
    print("ACTUALIZANDO DATA DE SMARTLIFE")
    global list_devices
    list_devices=list_SmartLifeObjs()
    print("lista devices----")
    print(list_devices.keys())


update_list_smartlife()
schedule.every().day.at("00:00").do(update_list_smartlife)

while True:
    try:
        schedule.run_pending()
        if (DEBUG=="YES"):
            if(list_devices.keys()!=[]):
                print("lista devices----")
                print(list_devices.keys())

        list_mails = checkEmail(my_email,my_pass)
        if (DEBUG=="YES"):
            if(list_mails!=[]):
                print("lista mails --------")
                print(list_mails)

        error_rigs_list = getRigsFromMail(list_mails)
        if (DEBUG=="YES"):
            if(error_rigs_list!=[]):
                print("lista rigs --------")
                print(error_rigs_list)

        for name in error_rigs_list:
            if rebootByName(list_devices,name):
                print("Rig Rebooteado Correctamente: ")
                print(name)
                opsgenie("Rebootiado RIG: "+str(name)+", por favor revisar. Automatismo PMC")
            else:
                print("Error Rebooteando RIG:")
                print(name)
                opsgenie("Error rebooteando RIG: "+str(name))
        time.sleep(10)
    except Exception as e:
        monitor.ping(state='fail')
