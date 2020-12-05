import database
from database import persistence_db
import entities
from entities import parking_lot_dto, user_dto
from services import user_service
from datetime import datetime
import threading

lock = threading.Lock()


def det_req(user_mail, car_number, company_name, driver_phone, driver_name,
            applicant_name, department, date_req, parking_lot, is_truck, free_parking=False):
    if driver_phone not in database.persistence_db.data['Driver']:
        database.persistence_db.data['Driver'][driver_phone] = \
            entities.user_dto.Driver(driver_name, driver_phone, car_number, company_name)
    if len(database.persistence_db.data['Driver'][driver_phone].previous_offenses) >= 3:
        return "הנהג אינו מורשה להחנות"

    req = entities.parking_lot_dto.ParkingReq(user_mail, car_number, company_name, driver_phone,
                                              applicant_name, department, date_req, parking_lot)

    for parking_spot in database.persistence_db.data['ParkingLot'][parking_lot].parking_spots:
        if database.persistence_db.data['ParkingLot'][parking_lot].parking_spots[parking_spot].is_truck == is_truck:
            if date_req not in database.persistence_db.data['ParkingLot'][parking_lot].parking_spots[
                parking_spot].parking_reqs_dict:
                lock.acquire()
                database.persistence_db.data['ParkingLot'][parking_lot].parking_spots[parking_spot].parking_reqs_dict[
                    date_req]= req
                database.persistence_db.data['Driver'][driver_phone].last_request.append(req)
                user_service.send_mail(user_mail, " נקלטה ואושרה" + date_req + "בקשתך לחניה לתאריך ")

                if len(requests_by_parking_lot_and_date(parking_lot, date_req)) == 1:
                    send_data = days_between(date_req, database.persistence_db.data['ParkingLot'][parking_lot].interval_time - 5)
                    threading.Timer(send_data, send_mail_and_whatsapp_for_all_relevant,
                                    args=[parking_lot, date_req]).start()

                lock.release()
                return "בקשת חניה אושרה"

    return "הרשמתך לא נקלטה. אנא נסה שוב"


def there_free_parking_spot(is_truck, parking_lot_name, date_req):
    for parking_spot in database.persistence_db.data['ParkingLot'][parking_lot_name].parking_spots:
        if database.persistence_db.data['ParkingLot'][parking_lot_name].parking_spots[parking_spot].is_truck == is_truck:
            if date_req not in database.persistence_db.data['ParkingLot'][parking_lot_name].parking_spots[parking_spot].parking_reqs_dict:
                return parking_spot
    return None


def is_there_a_vacancy(is_truck, parking_lot_name, date_req):
    for parking_lot in database.persistence_db.data['ParkingLot']:
        if parking_lot != parking_lot_name:
            if there_free_parking_spot(is_truck, parking_lot, date_req):
                return parking_lot
    return None


def show_parking_lot(parking_lot, date):
    spots = []
    if parking_lot in database.persistence_db.data["ParkingLot"]:
        for spot in database.persistence_db.data["ParkingLot"][parking_lot].parking_spots:
            if date in database.persistence_db.data["ParkingLot"][parking_lot][spot].parking_reqs_dict:
                spots.append(
                    (spot, database.persistence_db.data["ParkingLot"][parking_lot][spot].parking_reqs_dict[date]))
    return spots


def add_parking_lot(parking_lot_name, interval_time=20):
    if parking_lot_name not in database.persistence_db.data["ParkingLot"]:
        database.persistence_db.data["ParkingLot"][parking_lot_name] = entities.parking_lot_dto.ParkingLot(
            parking_lot_name, interval_time)
        return " נוסף בהצלחה " + parking_lot_name + " החניון "
    return " כבר קיים במערכת, ולכן לא נוסף מחדש " + parking_lot_name + " החניון "


def remove_parking_lot(parking_lot_name):
    if parking_lot_name in database.persistence_db.data["ParkingLot"]:
        del database.persistence_db.data["ParkingLot"][parking_lot_name]
        return " הושמד בהצלחה " + parking_lot_name + " החניון "
    return " לא היה קיים במערכת, ולכן הושמד באופן ריק" + parking_lot_name + " החניון "


def add_parking_spot(parking_lot_name, parking_spot_name, is_truck):
    if parking_spot_name not in database.persistence_db.data["ParkingLot"][parking_lot_name].parking_spots:
        database.persistence_db.data["ParkingLot"][parking_lot_name].parking_spots[
            parking_spot_name] = entities.parking_lot_dto.ParkingSpot(parking_spot_name, is_truck)
        return " נוספה בהצלחה " + parking_lot_name + " חניה מספר "
    return " כבר קיימת במערכת, ולכן לא נוספה מחדש " + parking_lot_name + " החניה "


def remove_parking_spot(parking_lot_name, parking_spot_name):
    if parking_lot_name in database.persistence_db.data["ParkingLot"]:
        if parking_spot_name in database.persistence_db.data["ParkingLot"][parking_lot_name].parking_spots:
            del database.persistence_db.data["ParkingLot"][parking_lot_name].parking_spots[parking_spot_name]
            return "החניה הוסרה בהצלחה"
        return "לא קיימת כזו חניה"
    return "לא קיים כזה חניון"


def requests_by_parking_lot_and_date(parking_lot, date_req=datetime.now()):
    """
    return list of all Parking_req that exist at date_req time in parking_lot_name
    :param parking_lot:  string. name of Parking_lot
    :param date_req: string with this format: 2020-11-19 11:00 + 00:00 / 00:20 / 00:40
    :return: list of Parking_req that exist at date_req time
    """

    return [
        database.persistence_db.data["ParkingLot"][parking_lot].parking_spots[parking_spot].parking_reqs_dict[date_req]
        for parking_spot in database.persistence_db.data["ParkingLot"][parking_lot].parking_spots if
        date_req in database.persistence_db.data["ParkingLot"][parking_lot].parking_spots[
            parking_spot].parking_reqs_dict]


def send_mail_and_whatsapp_for_all_relevant(parking_lot_name, date_req):
    # TODO We really need to send a date_req? maybe just send for req that have the current interavl
    """
    send message like "You must leave the parking lot in five minutes" to mail for users, and whatsapp for drivers -
     that have req in date_req interval.
    :param parking_lot_name: string of the name of the Parking_lot object required for treatment
    :param date_req: string with this format: 2020-11-19 11:00 + 00:00 / 00:20 / 00:40 that we need to send
    :return:
    """
    for reg in requests_by_parking_lot_and_date(parking_lot_name, date_req):
        # if it's not manager task ("ghost parking")
        if not reg.is_spacial_req:
            user_service.send_mail(reg.user.user_mail, "Hello dear\nYou must leave the parking lot in five minutes")
            # user_service.send_whatsapp(reg.drivers_phone, "You must leave the parking lot in five minutes")


###########################################################
#                 "מחשב הפרש זמנים "
###########################################################
def days_between(date, exit_time):
    time = str(datetime.now().year) + '-' + str(datetime.now().month) + '-' + str(datetime.now().day)
    time_2 = date[6:10] + '/' + date[3:5] + "/" + date[0:2]
    return (days_between_helper(time_2, time) * 24 * 60) + hours_batween(date, exit_time)


def days_between_helper(d1, d2):
    d1 = datetime.strptime(d1, "%Y/%m/%d")
    d2 = datetime.strptime(d2, "%Y-%m-%d")
    return abs((d2 - d1).days)


def hours_batween(date, exit_time):
    time = str(datetime.now().hour) + '-' + str(datetime.now().minute)
    time_2 = date[11:13] + '-' + date[14:16]
    return (int(time_2[0:2]) - int(time[0:2])) * 60 + (int(time[3:5]) - int(time_2[3:5]) + exit_time)
