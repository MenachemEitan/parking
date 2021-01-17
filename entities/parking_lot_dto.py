from datetime import datetime
import json


class ParkingReq(object):
    """
    this class represents a parking request
    """

    def __init__(self, user_mail, car_number, company_name, driver_phone,
                 applicant_name, department, date_req, parking_lot_name, parking_spot_name, is_truck=False,
                 free_parking=False,
                 is_spacial_req=False):
        """
        initial parking request
        :param applicant_name: should not be the same person of "User_account.user_name"
        :param department: always be the department of "User_account.department"
        :param free_parking: Should be exempt from payment?
        """
        self.user_mail = user_mail
        self.car_number = car_number
        self.company_name = company_name
        self.driver_phone = driver_phone
        self.applicant_name = applicant_name
        self.department = department
        self.date_req = date_req
        self.parking_lot_name = parking_lot_name
        self.parking_spot_name = parking_spot_name
        self.free_parking = free_parking
        self.is_truck = is_truck
        self.time_ask_req = str(datetime.now())
        self.is_spacial_req = is_spacial_req  # manager task. ghost parking

    def toJson(self):
        return json.dumps(self.__dict__)


############            ParkingSpot            ########################

class ParkingSpot:
    """
    this class represent specific parking in a specific parking lot
    """

    def __init__(self, place_number, is_truck=False):
        """
        initial the Parking_spot
        :param place_number:
        :param is_truck:
        """
        self.place_number = place_number
        self.is_truck = is_truck
        self.parking_reqs_dict = {}  # dict{key = date, value = Parking_req}

    def toJson(self):
        return json.dumps(self.__dict__)


############            ParkingLot            ##########################

class ParkingLot:
    """this class represent a parking lot"""

    def __init__(self, parking_lot_name, interval_time):
        self.parking_lot_name = parking_lot_name
        self.parking_spots = {}  # dict{ key = parking_spot_num, val = parking_spot}
        self.interval_time = interval_time  # list of intervals[20, 40,...]

    def toJson(self):
        return json.dumps(self.__dict__)
