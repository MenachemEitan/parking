import smtplib
from database import persistence_db
import entities
import random
import threading

db = persistence_db.db


def login(user_mail, password):
    """
    return user_mail exist and user_mail[password] == password
    :param user_mail: String
    :param password: String
    :return: boolean
    """
    persistence_db.load_all_to_data()
    user = persistence_db.db.get_entity_by_id('UserAccount', user_mail)
    if user == {}:
        user = persistence_db.db.get_entity_by_id('REGISTER', user_mail)
        if user == {}:
            return persistence_db.message["MAIL_NOT_EXIST"]
        if str(password) == str(user["password"]):
            persistence_db.db.add_entity('UserAccount', user, user_mail)
            persistence_db.db.remove_entity('REGISTER', user_mail)
            return None
        return persistence_db.message["WRONG_PASS"]
    if str(password) == str(user["password"]):
        return None
    return persistence_db.message["WRONG_PASS"]


def register(user_mail, phone_number, department):
    """
    if the mail is valid, create user by the details and call ro db.add_entity
    :param user_mail: String @savion...
    :param phone_number: String
    :param department: String
    :return: boolean is success?
    """
    user = db.get_entity_by_id('UserAccount', user_mail)
    if user != {}:
        password = str(random.randint(1000, 9999))
        if send_mail(user_mail, password):
            user['password'] = password
            persistence_db.db.add_entity('UserAccount', user, user_mail)
            return persistence_db.message["SUCCESS_REGISTER_FORGET_PASS"]
        return persistence_db.message["NOT_SUCCESS_SEND_MAIL"]

    elif db.POSTFIX_MAIL in user_mail:
        password = str(random.randint(1000, 9999))
        if send_mail(user_mail, password):
            user = db.get_entity_by_id('REGISTER', user_mail)
            if user == {}:
                user = entities.user_dto.UserAccount(user_mail, phone_number, department, password)
                threading.Timer(15 * 60, db.remove_entity, args=["REGISTER", user_mail]).start()
            persistence_db.db.add_entity('REGISTER', user, user_mail)
            return persistence_db.message["SUCCESS_REGISTER"]
        return persistence_db.message["NOT_SUCCESS_SEND_MAIL"]
    return persistence_db.message["NOT_SUCCESS_REGISTER_POSTFIX_MAIL"]


def is_manager(user_mail):
    """
    return is user "user_mail" is manager?
    :param user_mail: String
    :return: boolean user_mail[is_manager]
    """
    return persistence_db.db.get_entity_by_id("UserAccount", user_mail)['is_manager']


def add_manager(user_mail):
    """
    make user_mail to be a manager
    :return: boolean is success
    """
    user = persistence_db.db.get_entity_by_id('UserAccount', user_mail)
    if user == {}:
        return None
    user['is_manager'] = True
    persistence_db.db.add_entity('UserAccount', user, user_mail)
    return user


def remove_manager(user_mail):
    """
    make user_mail to be a manager
    :return: boolean is success
    """
    user = persistence_db.db.get_entity_by_id('UserAccount', user_mail)
    if user == {}:
        return None
    user['is_manager'] = False
    persistence_db.db.add_entity('UserAccount', user, user_mail)
    return user


def remove_user(user_mail):
    user = persistence_db.db.get_entity_by_id("UserAccount", user_mail)
    if user != {}:
        for req in user['last_request']:
            parking_lot = persistence_db.db.get_entity_by_id("ParkingLot",
                                                             user['last_request'][req]['parking_lot_name'])
            if user['last_request'][req]['parking_spot_name'] in parking_lot['parking_spots']:
                if user['last_request'][req]['date_req'] in \
                        parking_lot['parking_spots'][user['last_request'][req]['parking_spot_name']][
                            'parking_reqs_dict']:
                    del \
                        parking_lot['parking_spots'][user['last_request'][req]['parking_spot_name']][
                            'parking_reqs_dict'][
                            user['last_request'][req]['date_req']]

                    persistence_db.db.add_entity("ParkingLot", parking_lot, parking_lot['parking_lot_name'])

    return persistence_db.message["SUCCESS_REMOVE_USER"] if persistence_db.db.remove_entity('UserAccount', user_mail) \
        else persistence_db.message["NOT_SUCCESS_REMOVE_USER"]


def get_parking_lot_list():
    """
    :return: list of all parking lots dicts
    """
    return [parking_lot['parking_lot_name'] for parking_lot in persistence_db.db.get_all_entities("ParkingLot")]


def get_parking_spots_list(parking_lot_name):
    """
    :return: list of all parking lots dicts
    """
    parking_lot = persistence_db.db.get_entity_by_id("ParkingLot", parking_lot_name)
    if parking_lot != {}:
        return [parking_spot_name for parking_spot_name in parking_lot['parking_spots']]
    return []


def send_mail(mail_to, message, titel=""):
    """
    send mail message, titel to mail_to
    :param mail_to: String
    :param message: String
    :param titel: String
    :return: boolean is success?
    """
    try:
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        server.login(persistence_db.db.mail_from, persistence_db.db.password_mail)
        server.sendmail(persistence_db.db.mail_from, mail_to, str(message).encode('ascii', 'ignore').decode('ascii'))
        server.quit()
        return True

    except:
        return False


def get_all_element_names(entity_name):
    """
    return all the keys in entity_name dict (like all the users name)
    :param entity_name: String
    :return: list ["name", "name",...]
    """
    return [entity["value_id"] for entity in persistence_db.db.get_all_entities(entity_name)]


def add_offenses(entity_name, entity_id, offense):
    """
    add offenses to the entity_id list
    :param entity_name: String
    :param entity_id: String
    :param offense: String
    :return: offenses list
    """
    my_criminal_lover_CHANI = persistence_db.db.get_entity_by_id(entity_name, entity_id)
    my_criminal_lover_CHANI["previous_offenses"].append(offense)
    persistence_db.db.add_entity(entity_name, my_criminal_lover_CHANI, entity_id)

    return persistence_db.db.get_entity_by_id(entity_name, entity_id)


def remove_offense(entity_name, user_mail, offense):
    user = persistence_db.db.get_entity_by_id(entity_name, user_mail)
    if user != {}:
        if offense in user['previous_offenses']:
            user['previous_offenses'].remove(offense)
            persistence_db.db.add_entity(entity_name, user, user_mail)
        return user


def details_drivers():
    """
    list of few drivers details
    :return: list
    """
    lis = []
    dic = {}
    for i in persistence_db.db.get_all_entities("Driver"):
        lis.append("driver_phone: " + str(i["driver_phone"]) + ", driver_name: " + str(
            i["driver_name"]) + ", company_name: " + str(i["company_name"]))
        dic["driver_phone: " + str(i["driver_phone"]) + ", driver_name: " + str(
            i["driver_name"]) + ", company_name: " + str(i["company_name"])] = str(i["driver_phone"])
    return {'lis': lis, 'dic': dic}


def details_users():
    lis = []
    dic = {}
    for i in persistence_db.db.get_all_entities("UserAccount"):
        lis.append(
            "user_mail: " + str(i["user_mail"]) + ", phone_number: " + str(i["phone_number"]) + ", department: " + str(
                i["department"]))
        dic["user_mail: " + str(i["user_mail"]) + ", phone_number: " + str(i["phone_number"]) + ", department: " + str(
            i["department"])] = str(i["user_mail"])

    return {'lis': lis, 'dic': dic}


def get_all_managers():
    return [user["user_mail"] for user in persistence_db.db.get_all_entities("UserAccount") if user["is_manager"]]


def get_user(user_mail):
    return db.get_entity_by_id('UserAccount', user_mail)
