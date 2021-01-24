import database
from database import persistence_db
from entities import parking_lot_dto, user_dto
from services import user_service
from datetime import datetime
import threading
import calendar
import sms_service

db = database.persistence_db.db
lock = threading.Lock()


def det_req(user_mail, car_number, company_name, driver_phone, driver_name,
            applicant_name, department, date_req, parking_lot_name, parking_spot_name, is_truck, free_parking):
    """
    get req detail and if possible, create it, save it on parking_lot["parking_spots"][parking_spot]["parking_reqs_dict"]
    :param user_mail: String
    :param car_number: String
    :param company_name: String
    :param driver_phone: String
    :param driver_name: String
    :param applicant_name: String
    :param department: String
    :param date_req: String by format "17/02/2021 18:40 - 17/02/2021 19:00" (start - end)
    :param parking_lot_name: String
    :param parking_spot_name: String
    :param is_truck: boolean
    :param free_parking: boolean
    :return: String (details)
    """

    driver = db.get_entity_by_id('Driver', driver_phone)
    if driver == {}:
        driver = vars(user_dto.Driver(driver_name, driver_phone, car_number, company_name))

        db.add_entity('Driver', driver, driver_phone)

    elif len(driver['previous_offenses']) >= 3:
        return "הנהג אינו מורשה להחנות"

    parking_lot = db.get_entity_by_id("ParkingLot", parking_lot_name)
    parking_spot = parking_lot['parking_spots'][parking_spot_name]

    if is_match(parking_spot, date_req):
        req = parking_lot_dto.ParkingReq(user_mail, car_number, company_name, driver_phone,
                                         applicant_name, department, date_req, parking_lot_name,
                                         parking_spot_name,
                                         is_truck, free_parking,
                                         user_service.is_manager(user_mail))
    else:
        parking_spot_name = there_free_parking_spot(parking_lot_name, is_truck, date_req)
        if parking_spot_name is not None:
            req = parking_lot_dto.ParkingReq(user_mail, car_number, company_name, driver_phone,
                                             applicant_name, department, date_req, parking_lot_name,
                                             parking_spot_name, is_truck, free_parking,
                                             user_service.is_manager(user_mail))
        else:
            another_parking_lot_name = is_there_a_vacancy(is_truck, parking_lot_name, date_req)
            if another_parking_lot_name is not None:
                return [another_parking_lot_name]
            return "לא נשארו מקומות חניה בזמן המבוקש, נסה זמן אחר או פנה למוקד הביטחון"

    parking_spot = parking_lot['parking_spots'][parking_spot_name]
    parking_spot['parking_reqs_dict'][date_req] = vars(req)
    driver['last_request'][date_req] = vars(req)
    user = db.get_entity_by_id('UserAccount', user_mail)
    user['last_request'][date_req] = vars(req)
    db.add_entity('UserAccount', user, user_mail)
    parking_lot["parking_spots"][parking_spot_name] = parking_spot

    # timer for send message to leave
    lock.acquire()
    db.add_entity("ParkingLot", parking_lot, parking_lot_name)
    db.add_entity("Driver", driver, driver_phone)

    if len(requests_by_parking_lot_and_date(parking_lot_name, date_req)) == 1:
        send_date = 60 * days_between(date_req[19:], 5)
        threading.Timer(send_date, send_sms_for_all_relevant_drivers,
                        args=[parking_lot_name, date_req]).start()
    lock.release()

    # send order details to user (mail) and driver (SMS)
    if not req.is_spacial_req:
        msg_driver = "  הוזמנה עבורך חניה\nלחניון {}\nלחניה {}\nבפקולטה לרפואה בעין כרם\nלתאריך\n{}".format(
            req.parking_lot_name, req.parking_spot_name, req.date_req)

        msg_user = "  הוזמנה עבורך חניה\nלחניון {}\nלחניה {}\nבפקולטה לרפואה בעין כרם\nלתאריך\n{}".format(
            req.parking_lot_name, req.parking_spot_name, req.date_req)
        sms_service.send_sms(req.driver_phone, msg_driver)
        user_service.send_mail(user['user_mail'], msg_user, "title")
    return "בקשת חניה אושרה"


def is_best_match(parking_spot, date_req):
    """
    check if we choose this parking_spot, it will not create space that smaller then
    maximum interval of this parking_lot (avoid creating holes)
    :param parking_spot: dict
    :param date_req: String by format "17/02/2021 18:40 - 17/02/2021 19:00"
    :return: True/ False
    """
    for req in parking_spot["parking_reqs_dict"]:
        if not is_collision(date_req, req):
            return False

    for req in parking_spot["parking_reqs_dict"]:
        if req[:16] == date_req[19:] or req[19:] == date_req[:16]:
            return True
    return False


def is_there_a_vacancy(is_truck, parking_lot_name, date_req):
    """
    return name of parking_lot that has free and match parking spot at date_req, and the parking lot != parking_lot_name
    :param is_truck: boolean
    :param parking_lot_name:  string
    :param date_req: String by format "17/02/2021 18:40 - 17/02/2021 19:00" (start - end)
    :return: String | boolean
    """
    for parking_lot in db.get_all_entities('ParkingLot'):
        if parking_lot['parking_lot_name'] != parking_lot_name:
            if there_free_parking_spot(parking_lot['parking_lot_name'], is_truck, date_req) is not None:
                return parking_lot['parking_lot_name']


def add_parking_lot(parking_lot_name, interval_time):
    """
    create(if not exist) parking lot with given details and send him to 'db.add_entity' function
    :param parking_lot_name: String
    :param interval_time: list[20, 40, ...]
    :return: details String
    """
    if db.get_entity_by_id("ParkingLot", parking_lot_name) == {}:
        parking_lot = parking_lot_dto.ParkingLot(parking_lot_name, interval_time)
        db.add_entity("ParkingLot", parking_lot, parking_lot_name)
        return "the parking lot name " + parking_lot_name + " was successfully added"
    return "the parking lot name " + parking_lot_name + " already exit"


def add_parking_spot(parking_lot_name, parking_spot_name, is_truck):
    """
    add parking spot with given details
    :param parking_lot_name: String
    :param parking_spot_name: String
    :param is_truck: boolean
    :return: details String
    """
    parking_lot = db.get_entity_by_id('ParkingLot', parking_lot_name)
    if parking_spot_name in parking_lot['parking_spots']:
        return "the parking spot " + parking_spot_name + " is already exist in parking lot " + parking_lot_name
    parking_spot = vars(parking_lot_dto.ParkingSpot(parking_spot_name, is_truck))
    parking_lot['parking_spots'][parking_spot_name] = parking_spot
    db.add_entity("ParkingLot", parking_lot, parking_lot_name)
    return "the parking spot name " + parking_spot_name + " was successfully added to parking lot " + parking_lot_name


def requests_by_parking_lot_and_date(parking_lot_name, date_req):
    """
    return list of all ParkingReq (represented by dict) that exist at end of date_req time in parking_lot_name
    :param parking_lot_name: string. name of Parking_lot
    :param date_req: String by format "17/02/2021 18:40 - 17/02/2021 19:00"
    :return: list of Parking_req that exist at date_req time
    """
    req_lis = []
    parking_lot = db.get_entity_by_id("ParkingLot", parking_lot_name)
    for parking_spot_name in parking_lot["parking_spots"]:
        for req in parking_lot['parking_spots'][parking_spot_name]['parking_reqs_dict']:
            # if end time of req == end time of date_req
            if req[19:] == date_req[19:]:
                req_lis.append(parking_lot['parking_spots'][parking_spot_name]['parking_reqs_dict'][req])
    return req_lis


def send_sms_for_all_relevant_drivers(parking_lot_name, date_req):
    """
    send message like "You must leave the parking lot in five minutes" to mail for users, and whatsapp for drivers -
     that have req in date_req interval.
    :param parking_lot_name: string of the name of the Parking_lot object required for treatment
    :param date_req: String by format "17/02/2021 18:40 - 17/02/2021 19:00"
    :return: None
    """
    for reg in requests_by_parking_lot_and_date(parking_lot_name, date_req):
        # if it's not manager task ("ghost parking")
        if (not reg['is_spacial_req']) and reg['driver_phone'] is not None:
            sms_service.send_sms(reg['driver_phone'], persistence_db.message["LIVE_IN_FIVE_MINUTE"])


def days_between(date, exit_time):
    """
    return how many minutes exist between date and now - exit_time
    :param date: String by format "24/12/2020 08:20"
    :param exit_time: int
    :return: int
    """
    time = str(datetime.now().year) + '-' + str(datetime.now().month) + '-' + str(datetime.now().day)
    time_2 = date[6:10] + '/' + date[3:5] + "/" + date[0:2]
    return (days_between_helper(time_2, time) * 24 * 60) + hours_between(date, exit_time)


def days_between_helper(d1, d2):
    return abs((datetime.strptime(d2, "%Y-%m-%d") - datetime.strptime(d1, "%Y/%m/%d")).days)


def hours_between(date, exit_time):
    hour = str(datetime.now().hour)
    if len(hour) == 1:
        hour = '0' + hour
    if len(hour) == 0:
        hour = '00'

    minute = str(datetime.now().minute)
    if len(hour) == 1:
        minute = '0' + minute
    if len(minute) == 0:
        minute = '00'

    time = hour + '-' + minute
    time_2 = date[11:13] + '-' + date[14:16]
    return ((int(time_2[0:2]) - int(time[0:2])) * 60) + (int(time_2[3:5]) - int(time[3:5])) - exit_time


def is_time_between(start, end, time):
    """
    return start <= time <= end
    :param start: String by format "24/12/2020 08:20"
    :param end: String by format "24/12/2020 08:20"
    :param time: String by format "24/12/2020 08:20"
    :return: boolean
    """
    return date_to_datetime(start) <= date_to_datetime(time) <= date_to_datetime(end)


def show_parking_in_dates(parking_lot_name, date_req, free_parking=False):
    """
    return list of reqs (dicts) that exist in parking_lot_name between [start, end] time, and free_parking (filter)
    :param parking_lot_name: String
    :param date_req: String by format "17/02/2021 18:40 - 17/02/2021 19:00" (start - end)
    :param free_parking: boolean: to filter?
    :return: list [{req}, {req},...]
    """
    req_lis = []
    parking_lot = db.get_entity_by_id("ParkingLot", parking_lot_name)

    for parking_spot_name in parking_lot["parking_spots"]:
        for req in parking_lot["parking_spots"][parking_spot_name]["parking_reqs_dict"]:

            if is_collision(date_req, req):
                req = parking_lot["parking_spots"][parking_spot_name]["parking_reqs_dict"][req]
                if free_parking:
                    if req["free_parking"]:
                        req_lis.append(req)
                else:
                    req_lis.append(req)
    return req_lis


def remove_parking_lot(parking_lot_name):
    parking_lot = db.get_entity_by_id("ParkingLot", parking_lot_name)
    if parking_lot != {}:
        for parking_spot_name in parking_lot['parking_spots'].copy():
            remove_parking_spot(parking_lot_name, parking_spot_name)
        db.remove_entity("ParkingLot", parking_lot_name)
        return "החניון {} הושמד בהצלחה".format(parking_lot_name)
    return "החניון {} לא היה קיים, ולכן הושמד באופן ריק... בדיחות עולב של שנה א'".format(parking_lot_name)


def remove_parking_spot(parking_lot_name, parking_spot_name):
    parking_lot = db.get_entity_by_id("ParkingLot", parking_lot_name)
    if parking_lot != {}:
        if parking_spot_name in parking_lot["parking_spots"]:
            clear_parking_spot(parking_lot_name, parking_spot_name)
            # if parking_spot_name in parking_lot["parking_spots"]:
            del parking_lot["parking_spots"][parking_spot_name]
            db.add_entity("ParkingLot", parking_lot, parking_lot_name)
            return "חניה {} הוסרה בהצלחה מחניון {}".format(parking_spot_name, parking_lot_name)
        return "לא קיימת חניה בשם {} בחניון {}".format(parking_spot_name, parking_lot_name)
    return "לא קיים חניון בשם {}".format(parking_lot_name)


def clear_parking_spot(parking_lot_name, parking_spot_name):
    """
    clear all the reqs in parking spot (אם מוחקים - אז מוחקים גם מנהג, משתמש)
    "clear him" mean to try to move him to other parking spot. anyway remove him from current parking spot.
    :param parking_lot_name:
    :param parking_spot_name:
    """

    parking_spot = db.get_entity_by_id("ParkingLot", parking_lot_name)['parking_spots'][parking_spot_name]

    date_reqs_for_remove = [date_req for date_req in parking_spot["parking_reqs_dict"] if
                            not try_to_move_to_other_parking_spot(parking_spot["parking_reqs_dict"][date_req])]

    parking_lot = db.get_entity_by_id("ParkingLot", parking_lot_name)

    for date_req in date_reqs_for_remove:
        del parking_lot['parking_spots'][parking_spot_name]["parking_reqs_dict"][date_req]

    db.add_entity('ParkingLot', parking_lot, parking_lot_name)

    for date_req in [req['value_id'] for req in db.get_all_entities('MANAGER_TASK') if
                     req['parking_spot_name'] == parking_spot_name and req['parking_lot_name'] == parking_lot_name]:
        db.remove_entity('MANAGER_TASK', date_req)


def date_to_datetime(date):
    """
    covert String like "24/12/2020 08:20" to datetime object
    :param date: String "24/12/2020 08:20"
    :return: datetime object
    """
    return datetime(day=int(date[0:2]), month=int(date[3:5]), year=int(date[6:10]), hour=int(date[11:13]),
                    minute=int(date[14:16]))


def get_all_intervals():
    intervals = set()
    parking_lots = db.get_all_entities('ParkingLot')
    for parking_lot in parking_lots:

        for interval in parking_lot['interval_time']:
            intervals.add(interval)

    return list(intervals)


def check_valid_interval(parking_lot_name, interval):
    return interval in db.get_entity_by_id('ParkingLot', parking_lot_name)['interval_time']


#             ############ for block parking spot - manager task ############              #

# use
def block_parking_manager(parking_lot_name, parking_spot_name, date_req, is_truck, applicant_name, reason_details):
    """
    block parking_spot_name (for manager)
    :param parking_lot_name: String
    :param parking_spot_name: String | None
    :param date_req: String by format "17/02/2021 18:40 - 17/02/2021 19:00" (start - end)
    :param is_truck: boolean
    :param applicant_name: String
    :param reason_details: String
    :return: String of message like "the process is success"
    """
    # parking_spot_name is None, try to find an empty parking spot
    if parking_spot_name is None:
        parking_spot_name = there_free_parking_spot(parking_lot_name, is_truck, date_req)

        # if an empty parking spot not exist, try to find any parking spot that its not block by manager
        if parking_spot_name is None:
            parking_spot_name = there_parking_spot_that_not_block(is_truck, parking_lot_name, date_req)
            if parking_spot_name is None:
                return "!charli d'amelio is my bestie אח יקר, כל החניות תפוסות על ידי מנהלים... מתההה.. "

    # check that the parking spot that the manager want to block - it not already block (in part or in all date_req)
    else:
        parking_spot = db.get_entity_by_id("ParkingLot", parking_lot_name)['parking_spots'][parking_spot_name]
        if parking_spot['is_truck'] != is_truck:
            if is_truck:
                return "ברצונך לחסום חניית משאית אך חניה {} אינה למשאית".format(parking_spot_name)
            return "ברצונך לחסום חנייה רגילה אך חניה {} מיועדת למשאית".format(parking_spot_name)

        for req in parking_spot["parking_reqs_dict"]:
            # if date_req, req['date_req'] are collision and req['is_spacial_req'] == True
            if parking_spot["parking_reqs_dict"][req]['is_spacial_req'] and is_collision(date_req, parking_spot[
                "parking_reqs_dict"][req]['date_req']):
                return "החניה המבוקשת כבר תפוסה על ידי מנהל בשעה המבוקשת"

    # clear the parking_spot_name
    clear_the_spot_if_not_manager_task(parking_lot_name, parking_spot_name, date_req)

    # set the manager_task on parking_spot_name

    # we save the reason_details on req in car_number filed !!!
    req = vars(parking_lot_dto.ParkingReq("parkingservisek@gmail.com", reason_details, "MANAGER_TASK", None,
                                          applicant_name, "MANAGER_TASK", date_req, parking_lot_name,
                                          parking_spot_name, is_truck,
                                          False,
                                          True))

    parking_lot = db.get_entity_by_id("ParkingLot", parking_lot_name)
    parking_lot['parking_spots'][parking_spot_name]['parking_reqs_dict'][date_req] = req

    lock.acquire()
    # TODO maybe add another details
    db.add_entity("MANAGER_TASK", req, date_req + " " + str(datetime.now()))
    db.add_entity('ParkingLot', parking_lot, parking_lot_name)

    # timer for send message to leave
    if len(requests_by_parking_lot_and_date(parking_lot_name, date_req)) == 1:
        send_date = 60 * days_between(date_req[19:], 5)
        threading.Timer(send_date, send_sms_for_all_relevant_drivers,
                        args=[parking_lot_name, date_req]).start()
    lock.release()

    return "בקשת חניה לטווח המבוקש אושרה"


# use check
def there_free_parking_spot(parking_lot_name, is_truck, date_req, parking_spot_name_not_choose=None):
    """
    return name free parking spot - if there is a match. None if not
    :param is_truck: boolean
    :param parking_lot_name: string
    :param date_req: String by format "17/02/2021 18:40 - 17/02/2021 19:00"
    :return: String parking_spot_name | None
    """
    parking_spots = db.get_entity_by_id("ParkingLot", parking_lot_name)['parking_spots']

    # try to set the car in parking_spot. choose only parking_spot that this parking will not create space that small
    # from the maximum interval of this parking_lot (avoid creating holes)
    for parking_spot_name in parking_spots:
        if parking_spot_name_not_choose is not None:
            if parking_spot_name_not_choose == parking_spot_name:
                continue
        parking_spot = parking_spots[parking_spot_name]
        if parking_spot['is_truck'] == is_truck:
            if is_best_match(parking_spot, date_req):
                return parking_spot_name
            # if date_req not in parking_spot["parking_reqs_dict"]:
            # return parking_spot

    for parking_spot_name in parking_spots:
        if parking_spot_name_not_choose is not None:
            if parking_spot_name_not_choose == parking_spot_name:
                continue
        parking_spot = parking_spots[parking_spot_name]
        if parking_spot['is_truck'] == is_truck:
            if is_match(parking_spot, date_req):
                return parking_spot_name


# use
def is_match(parking_spot, date_req):
    """
    check if this date_req can be set in parking_spot (if it not cause collision)
    :param parking_spot: dict
    :param date_req: 17/02/2021 18:40 - 17/02/2021 19:00 (start - end)
    :return: True/ False
    """
    for req in parking_spot["parking_reqs_dict"]:
        if is_collision(date_req, req):
            return False
    return True


# use
def is_collision(date_1, date_2):
    """

    :param date_1: "17/02/2021 18:40 - 17/02/2021 19:00 (start - end)"
    :param date_2: "17/02/2021 18:40 - 17/02/2021 19:00 (start - end)"
    :return:
    """
    start_date_1 = date_to_datetime(date_1[:16])
    end_date_1 = date_to_datetime(date_1[19:])
    start_date_2 = date_to_datetime(date_2[:16])
    end_date_2 = date_to_datetime(date_2[19:])

    return start_date_1 <= start_date_2 < end_date_1 or \
           start_date_1 < end_date_2 <= end_date_1 or \
           start_date_2 <= start_date_1 < end_date_2 or \
           start_date_2 < end_date_1 <= end_date_2


# use
def there_parking_spot_that_not_block(is_truck, parking_lot_name, date_req):
    """
    try to find any parking spot that it's not block by manager
    :param is_truck: boolean
    :param parking_lot_name: String
    :param date_req: string like "31/12/2020 00:00 - 01/01/2021 00:00"
    :return:
    """
    parking_spots = db.get_entity_by_id("ParkingLot", parking_lot_name)['parking_spots']

    for parking_spot_name in parking_spots:
        if parking_spots[parking_spot_name]['is_truck'] == is_truck:
            i = len(parking_spots[parking_spot_name]["parking_reqs_dict"])
            for req in parking_spots[parking_spot_name]["parking_reqs_dict"]:
                if req['is_spacial_req'] and is_collision(date_req, req['date_req']):
                    break
                i -= 1
                if i == 0:
                    return parking_spot_name


# use
def clear_the_spot_if_not_manager_task(parking_lot_name, parking_spot_name, date_req):
    """
    clear all the reqs in parking spot that there date have a collision with date_req
    "clear him" mean to try to move him to other parking spot. anyway remove him from current parking spot.
    :param parking_lot_name:
    :param parking_spot_name:
    :param date_req:
    """
    parking_spot = db.get_entity_by_id("ParkingLot", parking_lot_name)['parking_spots'][parking_spot_name]

    date_reqs_for_remove = []
    for date in parking_spot["parking_reqs_dict"]:
        # if date_req, req['date_req'] are collision
        if is_collision(date_req, date):
            if not try_to_move_to_other_parking_spot(parking_spot["parking_reqs_dict"][date]):
                date_reqs_for_remove.append(date)

    parking_lot = db.get_entity_by_id("ParkingLot", parking_lot_name)

    for date in date_reqs_for_remove:
        del parking_lot['parking_spots'][parking_spot_name]["parking_reqs_dict"][date]

    db.add_entity('ParkingLot', parking_lot, parking_lot_name)


# use
def try_to_move_to_other_parking_spot(req):
    """
    move the req to other spot if possible. if not - remove the req from user, driver (need to remove it from
    parking_spot outside of this function הסיבה שלא מוחקים פה את הבקשה מתוך החניה היא שזה יוצר בעייה כי בלולאה
    חיצונית רצים על הבקשות וקוראים לפונקציה הזו. לכן זה נעשה בשני שלבים. . send mail/ SMS where need :param req:
    ParkingReq object :return: is success? True/ False
    """
    parking_lot = db.get_entity_by_id("ParkingLot", req['parking_lot_name'])
    user = db.get_entity_by_id('UserAccount', req['user_mail'])
    driver = db.get_entity_by_id('Driver', req['driver_phone'])

    # try to find another parking_spot
    parking_spot_name = there_free_parking_spot(req['parking_lot_name'], req['is_truck'], req['date_req'],
                                                req['parking_spot_name'])

    # if we find free parking_spot so replace the req to it
    if parking_spot_name is not None:
        # update the parking_spot_name in req
        req['parking_spot_name'] = parking_spot_name
        # update user
        if user != {}:
            if req['date_req'] in user['last_request']:
                user['last_request'][req['date_req']] = req
                msg_user = "שונתה החניה עבורך. פרטי החניה החדשים: חניון {}, חניה: {} בפקולטה לרפואה בעין כרם לתאריך {}". \
                    format(req['parking_lot_name'], req['parking_spot_name'], req['date_req'])
                user_service.send_mail(user['user_mail'], msg_user, "title")
                db.add_entity('UserAccount', user, user['user_mail'])

        # update driver
        if driver != {}:
            if req['date_req'] in driver['last_request']:
                driver['last_request'][req['date_req']] = req
                msg_driver = "הזמנת חניה עבורך שונתה. פרטי חניה חדשים: חניון {}, חניה: {} בפקולטה לרפואה בעין כרם, " \
                             "תאריך {}".format(req['parking_lot_name'], req['parking_spot_name'], req['date_req'])
                sms_service.send_sms(req['driver_phone'], msg_driver)
                db.add_entity("Driver", driver, driver['driver_phone'])

        # update parking_lot
        parking_lot['parking_spots'][parking_spot_name]['parking_reqs_dict'][req['date_req']] = req
        db.add_entity("ParkingLot", parking_lot, parking_lot['parking_lot_name'])
        return True

    else:
        if user != {}:
            if req['date_req'] in user['last_request']:
                msg_user = "הזמנת החניה לחניון {}, חניה: {} בפקולטה לרפואה בעין כרם,\nתאריך  {}, בוטלה עקב אילוצי " \
                           "מערכת.".format(req['parking_lot_name'], req['parking_spot_name'], req['date_req'])
                user_service.send_mail(user['user_mail'], msg_user, "title")
                del user['last_request'][req['date_req']]
                db.add_entity('UserAccount', user, user['user_mail'])

        if driver != {}:
            if req['date_req'] in driver['last_request']:
                msg_driver = "הזמנת החניה לחניון {}, חניה: {} בפקולטה לרפואה בעין כרם,\nתאריך {}, בוטלה עקב אילוצי " \
                             "מערכת.".format(req['parking_lot_name'], req['parking_spot_name'], req['date_req'])
                sms_service.send_sms(req['driver_phone'], msg_driver)
                del driver['last_request'][req['date_req']]
                db.add_entity("Driver", driver, driver['driver_phone'])

        return False


def get_all_parking_spots_lis():
    """
    return list of strings with this format: list[___ :זמן: ___ חניון: *___* חניה *___* מבקש: ___ סיבה,...]
    :return: list
    """
    return ['חניון: *{}* חניה: *{}*'.format(parking_lot['parking_lot_name'], parking_spot_name)
            for parking_lot in db.get_all_entities('ParkingLot')
            for parking_spot_name in parking_lot['parking_spots']]


# use
def get_block_parking_spots_lis():
    """
    return list of strings with this format: list[___ :זמן: ___ חניון: *___* חניה *___* מבקש: ___ סיבה,...]
    :return: list
    """
    all_block = db.get_all_entities('MANAGER_TASK')
    return ['זמן: *{}* חניון: *{}* חניה: {} מבקש: {} סיבה: {}'.format(
        req['value_id'],
        req['parking_lot_name'],
        req['parking_spot_name'],
        req['applicant_name'],
        req['car_number'])
        for req in all_block]


# use
def release_block(date):
    """
    remove request in "date" that is "MANAGER_TASK"
    :param date: string like "28/12/2020 00:00 - 28/12/2020 00:40 2021-01-05 13:28:38.705477"
    :return: String -  details msg
    """

    req = db.get_entity_by_id("MANAGER_TASK", date)
    if req == {}:
        return "לא קיימת חניה חסומה בטווח המבוקש"

    parking_lot = db.get_entity_by_id("ParkingLot", req['parking_lot_name'])

    del parking_lot['parking_spots'][req['parking_spot_name']]['parking_reqs_dict'][date[:35]]

    db.remove_entity("MANAGER_TASK", date)
    db.add_entity("ParkingLot", parking_lot, parking_lot['parking_lot_name'])
    return "החסימה הוסרה בהצלחה"
