import smtplib
import database
from database import persistence_db
import entities
import random


def login(usermail, password):
    if usermail in database.persistence_db.data["UserAccount"]:
        return int(password) == int(database.persistence_db.data["UserAccount"][usermail].password)
    return False


def register(user_mail, phone_number, department):
    password = random.randint(1000, 9999)
    user = entities.user_dto.UserAccount(user_mail, phone_number, department, password)
    if send_mail(user_mail, password):
        database.persistence_db.db.add_entity('UserAccount',user,user_mail)
        # database.persistence_db.data['UserAccount'][user_mail] = \
        #     entities.user_dto.UserAccount(user_mail, phone_number, department, password)

        return True
    else:
        return False


def is_manager(usermail):
    return usermail in database.persistence_db.data["managers"]


def add_manager(user_mail):
    if user_mail not in database.persistence_db.data["managers"]:
        database.persistence_db.data["managers"].add(user_mail)
        return True
    return False


def get_all_managers():
    return database.persistence_db.data["managers"]


def get_parking_lot_list():
    return [parking_lot for parking_lot in database.persistence_db.data["ParkingLot"]]


##################################################################
#                      שולח מייל
def send_mail(mail_to, message, titel=""):
    try:
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        server.login(persistence_db.mail_from, persistence_db.password_mail)
        server.sendmail(persistence_db.mail_from, mail_to, str(message))
        server.quit()

        return True
    except:
        return False


def send_whatssap():
    pass

#####################################
#######################################


def getAllUsers():
    usersAsJsons = []
    usersAsJsons = database.persistence_db.get_all_entities('user')
    return usersAsJsons

def getUserById(user_email):
    user = database.persistence_db.get_entity_by_id('user', user_email)
    return user

def get_element(element_name, id):
    return database.persistence_db.get_entity_by_id(element_name, id)


# def login(user_mail, password):
#     loginSuccessFuly = False
#     for user in database.persistence_db.get_all_entities('user'):
#         if user['user_mail'] == user_mail:
#             if user['password'] == password:
#                 loginSuccessFuly = True
#                 break
#
#     return loginSuccessFuly


def chek_previous_offenses(user_mail):
    user = getUserById()
    if user.previous_offenses >= 3:
        return False
    else:
        return True
