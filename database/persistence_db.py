import json
import os
import os.path
from os import path
from os.path import dirname, join
import threading

project_root = dirname(dirname(__file__))
files_path = join(project_root, 'files')
message = {
    "SUCCESS_REGISTER_FORGET_PASS": "נשלחה לך סיסמה למייל.",
    "SUCCESS_REGISTER": "נשלחה לך סיסמה למייל. יש להיכנס עם הסיסמה תוך 15 דקות",
    "NOT_SUCCESS_SEND_MAIL": "המערכת לא הצליחה לשלוח סיסמה למייל. נא וודא שהמייל תקין, ונסה שנית",
    "NOT_SUCCESS_REGISTER_POSTFIX_MAIL": "ניתן להתחבר רק למיילים בעלי סיומת @savion.huji.ac.il",
    "LIVE_IN_FIVE_MINUTE": "Hello dear\nYou must leave the parking lot in five minutes",
    "WRONG_PASS": "הוזנה סיסמה שגויה",
    "MAIL_NOT_EXIST": "המייל לא קיים במערכת. אנא בצע רישום מחדש",
    "SUCCESS_REMOVE_USER": "ניסיון להסרת משתמש הצליח\n",
    "NOT_SUCCESS_REMOVE_USER": "ניסיון להסרת משתמש נכשל\n",
    "SUCCESS_REMOVE_OFFENCE": "ניסיון להסרת עבירה הצליח",
    "NOT_SUCCESS_REMOVE_OFFENCE": "ניסיון להסרת עבירה כשל"
}


class DB():
    data = {"MANAGER_TASK": {}, "REGISTER": {}}
    num = 0
    # mail_from = "menahem.eitan@mail.huji.ac.il"
    # password_mail = "Studi5860193"

    mail_from = "parkingservisek@gmail.com"
    # mail_from = "bitahonek@gmail.com"
    password_mail = "M026758060"
    POSTFIX_MAIL = "@savion.huji.ac.il"

    def __init__(self):
        # create data = {"UserAccount":{}, "Driver:{},...  } from file that
        # exist in "files" directory
        for file_path in os.listdir(files_path):
            self.load_file_to_data(file_path)

    def load_file_to_data(self, file_path):
        full_filename = "%s/%s" % (files_path, file_path)
        if ".json" in full_filename:
            with open(full_filename) as fi:
                file_name = full_filename.split('/')[len(full_filename.split('/')) - 1]
                DB.data[file_name.split('.')[0]] = json.load(fi)

    def write_to_file(self, entity_name, collection):
        """
        write the collection to enitity_name.json file
        :param entity_name: string
        :param collection: dict
        :return: None
        """
        with open(files_path + entity_name + '.json', 'w') as outfile:
            json.dump(collection, outfile)

    def add_entity(self, entity_name, value, value_id):
        """
        add the dict value with the name value_id to data dict and to the json file
        :param entity_name: String
        :param value: dict
        :param value_id: String
        :return: None
        """
        if entity_name not in DB.data:
            DB.data[entity_name] = {}
        if type(value) != dict:
            value = vars(value)
        value['value_id'] = value_id
        DB.data[entity_name][value_id] = value
        self.write_to_file(entity_name, DB.data[entity_name])
        self.load_file_to_data(entity_name + '.json')

    def get_all_entities(self, entity_name):
        """
        get entity_name (can be only "Driver", "UserAccount", "ParkingLot")
        and return dict like {"driver_name": {"driver_name":...,...:...}, ...} (json format)
        :param entity_name: String
        :return: dict
        """
        # if path.exists(entity_name + '.json'):
        #     self.load_file_to_data(entity_name + '.json')

        if entity_name not in DB.data:
            DB.data[entity_name] = {}
        all_dicts = []

        for x in DB.data[entity_name]:
            x_as_dict = DB.data[entity_name][x]
            all_dicts.append(x_as_dict)
        return all_dicts

    def get_entity_by_id(self, entity_name, entity_id, login=False):
        """
        get data[entity_name][entity_id] (represent "Driver" or "UserAccount" or "ParkingLot")
        :param entity_name: String
        :param entity_id: String
        :return: dict
        """
        if login:
            if path.exists(entity_name + '.json'):
                self.load_file_to_data(entity_name + '.json')

        if entity_name not in DB.data:
            DB.data[entity_name] = {}

        if entity_id in DB.data[entity_name]:
            return DB.data[entity_name][entity_id]
        return {}

    def remove_entity(self, entity_name, value_id):
        if entity_name in DB.data:
            if value_id in DB.data[entity_name]:
                del DB.data[entity_name][value_id]

                with open(files_path + entity_name + '.json', 'w') as outfile:
                    json.dump(DB.data[entity_name], outfile)

                return True
        return False


db = DB()


def load_all_to_data():
    for file_path in os.listdir(files_path):
        db.load_file_to_data(file_path)
