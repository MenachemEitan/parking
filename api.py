from flask import Flask, request, render_template, session, redirect, url_for
from flask_cors import CORS, cross_origin
from services import user_service, parking_service
import sms_service
from validate_email import validate_email
from functools import wraps
import datetime

db = user_service.db
db2 = parking_service.db
app = Flask(__name__)
app.config["DEBUG"] = True
app.config['SECRET_KEY'] = 'super secret'
CORS(app)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('email'):
            return redirect(url_for('login'))
        return fn(*args, **kwargs)

    return wrapper


@app.route('/logout')
def logout():
    session.pop('email', None)
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def home():
    session.clear()
    return render_template("home.html")


@app.route('/login', methods=['GET', 'POST'])
@cross_origin()
def login():
    user_mail = request.form.get("user_mail")
    if user_mail is None:
        return render_template("home.html")
    if '@' not in user_mail:
        user_mail = user_mail + "@savion.huji.ac.il"
    password = request.form.get("password")
    msg = user_service.login(user_mail, password)
    if msg is None:
        session['email'] = user_mail
        if user_service.is_manager(user_mail):
            return render_template('manager.html', colours=get_parking_lot_list(),
                                   details_drivers=user_service.details_drivers()['lis'],
                                   drivers=user_service.details_drivers()['dic'],
                                   details_users=user_service.details_users()['lis'],
                                   users=user_service.details_users()['dic'],
                                   block_parking=get_block_parking_spots_lis(),
                                   all_parking_spots=get_all_parking_spots_lis()
                                   )
        return render_template("req.html", colours=get_parking_lot_list(), intervals=get_all_intervals(),
                               notification="",
                               warning="")
    return render_template("home.html", notification=msg,
                           warning="")


@app.route('/req', methods=['GET', 'POST'])
@cross_origin()
@login_required
def req():
    if "email" not in session:
        session.clear()
        return render_template("home.html")

    # parking_lot_name
    if request.form.get("parking_lot_name") is None:
        return render_template("req.html", colours=get_parking_lot_list(),
                               intervals=get_all_intervals(), notification=" ...בחר חניון",
                               warning="")

    # interval
    if request.form.get("interval") is None:
        return render_template("req.html", colours=get_parking_lot_list(),
                               intervals=get_all_intervals(), notification="...בחר אינטרוול",
                               warning="")
    if not check_valid_interval(request.form.get("parking_lot_name"), request.form.get("interval")):
        return render_template("req.html", colours=get_parking_lot_list(),
                               intervals=get_all_intervals(), notification="",
                               warning="האינטרוול הנבחר אינו מתאים לחניה")

    # date
    if request.form.get("date") is None:
        return render_template("req.html", colours=get_parking_lot_list(),
                               intervals=get_all_intervals(), notification=" ...בחר תאריך",
                               warning="")

    if request.form.get("date")[-1] != '0':
        return render_template("req.html", colours=get_parking_lot_list(),
                               intervals=get_all_intervals(), notification="",
                               warning="על הדקות להיות כפולות של 10")

    session["parking_lot_name"] = request.form.get("parking_lot_name")
    session["is_truck"] = request.form.get("isTrack") is not None
    session["date_req"] = set_date(request.form.get("date"), request.form.get("interval"))

    # שים לב,session["parking_spot_name"] זה שם של חניה! לא מילון שמייצג חניה כמו שהיה עד 10/1/21
    msg = parking_service.there_free_parking_spot(session["parking_lot_name"],
                                                  session["is_truck"],
                                                  session["date_req"])
    if msg is not None:
        session["parking_spot_name"] = msg
        return render_template("det_req.html", colours=get_parking_lot_list(), intervals=get_all_intervals())

    other_parking_lot = parking_service.is_there_a_vacancy(session["is_truck"], session["parking_lot_name"],
                                                           session["date_req"])

    if other_parking_lot is not None:
        return render_template("req.html", colours=get_parking_lot_list(),
                               intervals=get_all_intervals()) + " אתה מוזמן להזין שוב את הפרטים, ולהזמין בה. " + other_parking_lot + " אך יש חניה פנויה בחניון " + \
               session["parking_lot_name"] + " אין חניה פנויה בחניון "
    else:
        return render_template("home.html", notification=" אין חניות בזמן המבוקש - פנה למוקד הביטחון ",
                               warning="")


@app.route('/det_req', methods=['GET', 'POST'])
@cross_origin()
@login_required
def det_req():
    if "date_req" not in session:
        session.clear()
        return render_template("home.html")

    session["car_number"] = request.form.get("car_number")
    session["driver_name"] = request.form.get("driver_name")
    session["company_name"] = request.form.get("company_name")
    session["driver_phone"] = request.form.get("driver_phone")
    session["applicant_name"] = request.form.get("applicant_name")
    session["department"] = request.form.get("department")
    session["free_parking"] = request.form.get("free_parking") is not None

    msg = parking_service.det_req(session["email"], session["car_number"], session["company_name"],
                                  session["driver_phone"], session["driver_name"],
                                  session["applicant_name"], session["department"], session["date_req"],
                                  session["parking_lot_name"],
                                  session["parking_spot_name"],
                                  session["is_truck"], session["free_parking"])
    if type(msg) == list:
        return render_template("req.html", colours=get_parking_lot_list(),
                               intervals=get_all_intervals(),
                               notification=" אתה מוזמן להזין שוב את הפרטים, ולהזמין בה. " + msg[
                                   0] + " אך יש חניה פנויה בחניון " + session[
                                                "parking_lot_name"] + " אין חניה פנויה בחניון ",
                               warning="")
    session.clear()
    return render_template("home.html", notification=msg, warning="")


@app.route('/register', methods=['GET', 'POST'])
@cross_origin()
def register():
    user_mail = request.form.get("user_mail")

    if '@' not in user_mail:
        user_mail = user_mail + "@savion.huji.ac.il"
    if validate_email(user_mail):
        phone_number = request.form.get("phone_number")
        department = request.form.get("department")
        return render_template('home.html', notification=user_service.register(user_mail, phone_number, department),
                               warning="")

    session.clear()
    return render_template("home.html", notification="", warning=db.message["NOT_SUCCESS_SEND_MAIL"])


def get_parking_lot_list():
    return user_service.get_parking_lot_list()


def get_parking_spots_list(parking_lot_name):
    return user_service.get_parking_spots_list(parking_lot_name)


@app.route('/add_parking_lot', methods=['POST', 'GET'])
@cross_origin()
def add_parking_lot():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            intervals = []
            for interval in request.form.get("intervals").split(','):
                # check that the input is only like '10,20,40,60,70'
                if len(interval) != 2 or not interval.isdigit() or interval[-1] != '0':
                    return render_template('edit_parking.html',
                                           colours=get_parking_lot_list(),
                                           notification="",
                                           warning="input " + str(interval) + " as an interval is not valid.  set intervals only like that: 10,20,40,60,70")
                intervals.append(interval)

            msg = parking_service.add_parking_lot(request.form.get("parking_lot_name"), intervals)
            return render_template('edit_parking.html', colours=get_parking_lot_list(), notification=msg, warning="")
    session.clear()
    return render_template("home.html")


@app.route('/add_parking_spot', methods=['POST', 'GET'])
@cross_origin()
def add_parking_spot():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            if request.form.get("parking_lot_name") is None:
                return render_template('edit_parking.html', colours=get_parking_lot_list())
            msg = parking_service.add_parking_spot(request.form.get("parking_lot_name"),
                                                    request.form.get("parking_spot_name"),
                                                    len(request.form) == 3)
            return render_template('edit_parking.html', colours=get_parking_lot_list(), notification=msg, warning="")


    session.clear()
    return render_template("home.html")


@app.route('/show_parking_in_dates', methods=['POST', 'GET'])
@cross_origin()
def show_parking_in_dates():
    if "email" in session:
        if user_service.is_manager(session["email"]):

            parking_lot_name = request.form.get("parking_lot_name")
            date_req = request.form.get("dates")
            if date_req is None:
                date_req = request.form.get("date")

            if '-' not in date_req:
                date_req = date_req + ' - ' + date_req

            if parking_lot_name is None or date_req is None:
                return back_to_manager_screen()

            free_parking = request.form.get("free_parking") is not None
            reqs_dict = list_req_to_dict_lis(
                parking_service.show_parking_in_dates(parking_lot_name, date_req, free_parking))

            return render_template('show_parking_in_dates.html', reqs_dict=reqs_dict)

    session.clear()
    return render_template("home.html")


@app.route('/user_details', methods=['POST', 'GET'])
@cross_origin()
def user_details():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            user_mail = request.form.get("details_users")
            if user_mail is None:
                if "users_names" in request.form.to_dict():
                    user_mail = request.form.to_dict()["users_names"]
                else:
                    return back_to_manager_screen()
            user = db.get_entity_by_id("UserAccount", user_mail)
            return render_template('user_details.html', user=user)
    session.clear()
    return render_template("home.html")


@app.route('/add_offenses_to_user', methods=['POST', 'GET'])
@cross_origin()
def add_offenses_to_user():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            entity_id = request.form.get("user_mail")
            offense = request.form.get("offense")
            user = user_service.add_offenses("UserAccount", entity_id, offense)
            return "<h3>העבירה נוספה בהצלחה</h3>" + render_template('user_details.html', user=user)
    session.clear()
    return render_template("home.html")


@app.route('/user_details_helper', methods=['POST', 'GET'])
@cross_origin()
def user_details_helper():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            detail = request.form.to_dict()
            details = {key: detail[key] for key in detail if len(detail[key]) != 0 and key != "details_users"}
            users = {}
            users_help = {}

            len_details = len(details)
            for user in db.get_all_entities('UserAccount'):
                i = 0
                for key in details:
                    if details[key] != user[key]:
                        break
                    i += 1
                if i == len_details:
                    users[user["user_mail"]] = user

            lis = []

            for i in users:
                lis.append("user_mail: " + str(i) + ", phone_number: " + str(
                    users[i]["phone_number"]) + ", department: " + str(users[i]["department"]))
                users_help["user_mail: " + str(i) + ", phone_number: " + str(
                    users[i]["phone_number"]) + ", department: " + str(users[i]["department"])] = str(i)

            if len(lis) > 0:
                return render_template('user_details_helper.html'
                                       , users_names=user_service.get_all_element_names("UserAccount"),
                                       users=lis,
                                       users_help=users_help
                                       )
            return back_to_manager_screen()

    session.clear()
    return render_template("home.html")


@app.route('/edit_user', methods=['POST', 'GET'])
@cross_origin()
def edit_user():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            return render_template('edit_user.html', colours=get_parking_lot_list(),
                                   details_drivers=user_service.details_drivers()['lis'],
                                   drivers=user_service.details_drivers()['dic'],
                                   details_users=user_service.details_users()['lis'],
                                   users=user_service.details_users()['dic'],
                                   block_parking=get_block_parking_spots_lis()
                                   )
    session.clear()
    return render_template("home.html")


@app.route('/remove_parking_spot', methods=['POST', 'GET'])
@cross_origin()
def remove_parking_spot():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            if request.form.get("parking_lot_and_spot_name") is None:
                return render_template('edit_parking.html', colours=get_parking_lot_list())
            if len(request.form.get("parking_lot_and_spot_name").split(',')) == 2:
                parking_lot_name = request.form.get("parking_lot_and_spot_name").split(',')[0]
                parking_spot_name = request.form.get("parking_lot_and_spot_name").split(',')[1]
                msg = parking_service.remove_parking_spot(parking_lot_name, parking_spot_name)
                return msg + render_template(
                    'edit_parking_lot_helper.html',
                    get_parking_spots_list=get_parking_spots_list(parking_lot_name),
                    parking_lot_name=parking_lot_name
                )
    session.clear()
    return render_template("home.html")


@app.route('/driver_details', methods=['POST', 'GET'])
@cross_origin()
def driver_details():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            driver_phone = request.form.get("details_drivers")
            if driver_phone is None:
                if "drivers_names" in request.form.to_dict():
                    driver_phone = request.form.to_dict()["drivers_names"]
                else:
                    return back_to_manager_screen()
            driver = db.get_entity_by_id("Driver", driver_phone)
            return render_template('driver_details.html', driver=driver)
    session.clear()
    return render_template("home.html")


@app.route('/add_offenses_to_driver', methods=['POST', 'GET'])
@cross_origin()
def add_offenses_to_driver():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            entity_id = request.form.get("driver_phone")
            offense = request.form.get("offense")
            driver = user_service.add_offenses("Driver", entity_id, offense)
            return "<h3>העבירה נוספה בהצלחה</h3>" + render_template('driver_details.html', driver=driver)
    session.clear()
    return render_template("home.html")


@app.route('/driver_details_helper', methods=['POST', 'GET'])
@cross_origin()
def driver_details_helper():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            detail = request.form.to_dict()
            details = {key: detail[key] for key in detail if len(detail[key]) != 0 and key != "details_drivers"}
            drivers = {}
            drivers_help = {}
            len_details = len(details)
            for driver in db.get_all_entities('Driver'):
                i = 0
                for key in details:
                    if details[key] != driver[key]:
                        break
                    i += 1
                if i == len_details:
                    drivers[driver["driver_phone"]] = driver

            lis = []
            for i in drivers:
                lis.append("driver_phone: " + str(i) + ", driver_name: " + str(
                    drivers[i]["driver_name"]) + ", company_name: " + str(drivers[i]["company_name"]))
                drivers_help["driver_phone: " + str(i) + ", driver_name: " + str(
                    drivers[i]["driver_name"]) + ", company_name: " + str(drivers[i]["company_name"])] = str(i)

            if len(lis) > 0:
                return render_template('driver_details_helper.html',
                                       drivers_names=user_service.get_all_element_names("Driver"),
                                       drivers=lis,
                                       drivers_help=drivers_help
                                       )
            return back_to_manager_screen()
    session.clear()
    return render_template("home.html")


@app.route('/manager', methods=['POST', 'GET'])
@cross_origin()
def back_to_manager_screen():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            return render_template('manager.html', colours=get_parking_lot_list(),
                                   details_drivers=user_service.details_drivers()['lis'],
                                   drivers=user_service.details_drivers()['dic'],
                                   details_users=user_service.details_users()['lis'],
                                   users=user_service.details_users()['dic'],
                                   block_parking=get_block_parking_spots_lis(),
                                   all_parking_spots=get_all_parking_spots_lis()
                                   )
    session.clear()
    return render_template("home.html")


def list_req_to_dict_lis(lis):
    dic = {}
    for req in lis:
        parking_spot_name = req['parking_spot_name']
        if parking_spot_name not in dic:
            dic[parking_spot_name] = [req]
        else:
            dic[parking_spot_name].append(req)
    return dic


def list_req_to_dict(lis):
    dic = {}
    for req in lis:
        dic[req['parking_spot_name']] = req
    return dic


@app.route('/edit_parking', methods=['POST', 'GET'])
@cross_origin()
def edit_parking():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            return render_template('edit_parking.html', colours=get_parking_lot_list())
    session.clear()
    return render_template("home.html")


@app.route('/edit_parking_lot_helper', methods=['POST', 'GET'])
@cross_origin()
def edit_parking_lot_helper():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            parking_lot_name = request.form.get("parking_lot_name")
            if parking_lot_name is None:
                return render_template('edit_parking.html', colours=get_parking_lot_list())
            return render_template('edit_parking_lot_helper.html',
                                   get_parking_spots_list=get_parking_spots_list(parking_lot_name),
                                   parking_lot_name=parking_lot_name
                                   )

    session.clear()
    return render_template("home.html")


@app.route('/remove_parking_lot', methods=['POST', 'GET'])
@cross_origin()
def remove_parking_lot():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            msg = parking_service.remove_parking_lot(request.form.get("parking_lot_name"))
            return render_template('edit_parking.html', colours=get_parking_lot_list(),
                                         drivers_names=user_service.get_all_element_names("Driver")
                                         , users_names=user_service.get_all_element_names("UserAccount"),notification=msg,warning=""
                                         )
    session.clear()
    return render_template("home.html")


@app.route('/go_to_req', methods=['POST', 'GET'])
@cross_origin()
def go_to_req():
    if 'email' in session:
        if user_service.is_manager(session['email']):
            return render_template("req.html", colours=get_parking_lot_list(), intervals=get_all_intervals())

    session.clear()
    return render_template("home.html")


@app.route('/block_parking_manager', methods=['POST', 'GET'])
@cross_origin()
def block_parking_manager():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            parking_lot_name = request.form.get("parking_lot_name")
            parking_spot_details = request.form.get("parking_spot_details")
            date_req = request.form.get("dates")
            is_truck = request.form.get("is_truck") is not None
            applicant_name = request.form.get("applicant_name")
            reason_details = request.form.get("reason_details")
            parking_spot_name = None
            if parking_spot_details is not None:
                park_lot = parking_spot_details.split('*')[1]
                if parking_lot_name is not None:
                    if park_lot != parking_lot_name:
                        return back_to_manager_screen()
                parking_spot_name = parking_spot_details.split('*')[3]
                parking_lot_name = park_lot

            if (parking_spot_details is None and parking_lot_name is None) or date_req is None:
                return back_to_manager_screen()

            msg = parking_service.block_parking_manager(parking_lot_name, parking_spot_name, date_req, is_truck,
                                                        applicant_name,
                                                        reason_details)

            return render_template('manager.html', colours=get_parking_lot_list(),
                                   details_drivers=user_service.details_drivers()['lis'],
                                   drivers=user_service.details_drivers()['dic'],
                                   details_users=user_service.details_users()['lis'],
                                   users=user_service.details_users()['dic'],
                                   block_parking=get_block_parking_spots_lis(),
                                   all_parking_spots=get_all_parking_spots_lis(),
                                   notification=msg,
                                   warning=""
                                   )

    session.clear()
    return render_template("home.html")


@app.route('/release_block', methods=['POST', 'GET'])
@cross_origin()
def release_block():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            details = request.form.get("colours")
            if details is None:
                return back_to_manager_screen()
            # detail = '___ :זמן: *___* חניון: ___ חניה: ___ מבקש: ___ סיבה'
            # הזמן מופיע כמו בשורה הבאה:
            # 28/12/2020 00:00 - 28/12/2020 00:40 2021-01-05 13:28:38.705477
            msg = parking_service.release_block(str(details).split('*')[1])
            return msg + render_template('manager.html', colours=get_parking_lot_list(),
                                         details_drivers=user_service.details_drivers()['lis'],
                                         drivers=user_service.details_drivers()['dic'],
                                         details_users=user_service.details_users()['lis'],
                                         users=user_service.details_users()['dic'],
                                         block_parking=get_block_parking_spots_lis(),
                                         all_parking_spots=get_all_parking_spots_lis()
                                         )

    session.clear()
    return render_template("home.html")


def get_block_parking_spots_lis():
    return parking_service.get_block_parking_spots_lis()


@app.route('/add_manager', methods=['POST', 'GET'])
@cross_origin()
def add_manager():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            massage = str(user_service.get_all_managers()) + " ניסיון להכנסת מנהל נכשל. כרגע המנהלים הם "
            user = user_service.add_manager(request.form.get("user_mail"))
            if user is not None:
                massage = str(user_service.get_all_managers()) + " ניסיון להכנסת מנהל הצליח. כרגע המנהלים הם "

            return massage + render_template('user_details.html', user=user)
    session.clear()
    return render_template("home.html")


@app.route('/remove_manager', methods=['POST', 'GET'])
@cross_origin()
def remove_manager():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            massage = str(user_service.get_all_managers()) + " ניסיון להסרת מנהל נכשל. כרגע המנהלים הם "
            user = user_service.add_manager(request.form.get("user_mail"))
            if user is not None:
                massage = str(user_service.get_all_managers()) + " ניסיון להסרת מנהל הצליח. כרגע המנהלים הם "

            return massage + render_template('user_details.html', user=user)
    session.clear()
    return render_template("home.html")


@app.route('/remove_user', methods=['POST', 'GET'])
@cross_origin()
def remove_user():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            msg = "!!!לא ניתן להתאבד דרך תוכנה זו. אנא נסה זאת במקום אחר"
            if session["email"] != request.form.get("user_mail"):
                msg = user_service.remove_user(request.form.get("user_mail"))

            return msg + render_template('manager.html',
                                         colours=get_parking_lot_list(),
                                         details_drivers=
                                         user_service.details_drivers()[
                                             'lis'],
                                         drivers=
                                         user_service.details_drivers()[
                                             'dic'],
                                         details_users=
                                         user_service.details_users()[
                                             'lis'],
                                         users=
                                         user_service.details_users()[
                                             'dic'],
                                         block_parking=get_block_parking_spots_lis(),
                                         all_parking_spots=get_all_parking_spots_lis()
                                         )
    session.clear()
    return render_template("home.html")


@app.route('/remove_offense_from_user', methods=['POST', 'GET'])
@cross_origin()
def remove_offense_from_user():
    if "email" in session:
        if user_service.is_manager(session["email"]):
            if '*' not in request.form.get("offense"):
                user = user_service.get_user(request.form.get("offense"))
                if user != {}:
                    return render_template('user_details.html', user=user)

            offence = request.form.get("offense").split('*')[1]
            user_mail = request.form.get("offense").split('*')[0]
            user = user_service.remove_offense("UserAccount", user_mail, offence)
            if user is not None:
                return render_template('user_details.html', user=user)

    session.clear()
    return render_template("home.html")


def get_all_intervals():
    return parking_service.get_all_intervals()


def check_valid_interval(parking_lot_name, interval):
    return parking_service.check_valid_interval(parking_lot_name, interval)


def set_date(date, interval):
    """
    get date like 17/02/2021 18:40 and interval like 20, and return 17/02/2021 18:40 - 17/02/2021 19:00
    :param date: String like 17/02/2021 18:40
    :param interval: String like 20
    :return: String like 17/02/2021 18:40 - 17/02/2021 19:00
    """
    end = parking_service.date_to_datetime(date) + datetime.timedelta(minutes=int(interval))
    return date + " - " + end.strftime("%d/%m/%Y %H:%M")


def get_all_parking_spots_lis():
    return parking_service.get_all_parking_spots_lis()


###################

def send_sms(recipient, sms_content):
    return sms_service.send_sms(recipient, sms_content)


if __name__ == '__main__':
    # while True:
    print("START")
    try:
        # app.run(debug=True, host='0.0.0.0')
        app.run(debug=True)
        ################################
    except Exception as e:
        print(e)
        print("FAIL")
        send_sms("0523978957", str(e))
        send_sms("0544847550", str(e))
        user_service.send_mail("cheziraf@gmail.com", str(e))
        user_service.send_mail("menahemeitan@gmail.com", str(e))
