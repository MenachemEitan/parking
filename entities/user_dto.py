import json


############            UserAccount            ########################

class UserAccount:
    """מחלקת חשבונות משתמשים - מייל, עבירות קודמות, תאריך בקשה אחרונה"""
    """this class represent user account - include all his details"""

    def __init__(self, user_mail, phone_number, department, password, num_try_identify=0, is_manager=False):
        self.user_mail = user_mail  # string prefix user mail
        self.phone_number = phone_number
        self.department = department  # string
        self.last_request = {}
        self.previous_offenses = []
        self.password = password
        self.num_try_identify = num_try_identify
        self.is_manager = is_manager

    def toJson(self):
        return json.dumps(self.__dict__)


############            RegularDriver            #######################

class Driver:
    """this class represent driver that come usually - include all his details"""

    def __init__(self, driver_name, driver_phone, car_number, company_name):
        """
        :param driver_name: string
        :param driver_phone: string?
        :param car_number: list of (strings or ints?)
        :param company_name: string
        """
        self.driver_name = driver_name
        self.driver_phone = driver_phone
        self.car_number = car_number
        self.company_name = company_name

        self.last_request = {}
        self.previous_offenses = []

    def toJson(self):
        return json.dumps(self.__dict__)
