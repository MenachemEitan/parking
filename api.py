from flask import Flask, request, jsonify, url_for, render_template, render_template_string
from flask_cors import CORS, cross_origin
from flask_login import LoginManager
from services import user_service, parking_service
from datetime import datetime
import database.persistence_db

# login_manager = LoginManager()

app = Flask(__name__)
app.config["DEBUG"] = True
# login_manager.init_app(app)
CORS(app)


@app.route('/')
@cross_origin()
def home():
    return render_template("home.html", colours=get_parking_lot_list())


@app.route('/login', methods=['GET', 'POST'])
@cross_origin()
def login():
    usermail = request.args.get("usermail")
    password = request.args.get("password")
    if user_service.login(usermail, password):
        if user_service.is_manager(usermail):
            return render_template('manager.html', colours=get_parking_lot_list())
        return render_template("req.html", colours=get_parking_lot_list())
    return " הסיסמה שגויה או המייל לא קיים " + render_template("home.html", colours=get_parking_lot_list())


@app.route('/req', methods=['GET', 'POST'])
@cross_origin()
def req():
    is_truck = request.args.get("isTrack") is not None
    parking_lot_name = request.args.get("colours")
    date_req = request.args.get("date")

    if date_req[14:] not in ['00', '20', '40']:
        return "נא להזין דקות 00 או 20 או 40. למשל 04:20" + render_template("req.html", colours=get_parking_lot_list())

    if parking_service.there_free_parking_spot(is_truck, parking_lot_name, date_req) is not None:
        return render_template("det_req.html", colours=get_parking_lot_list())
    other_parking_lot = parking_service.is_there_a_vacancy(is_truck, parking_lot_name, date_req)
    if other_parking_lot is not None:
        return render_template(
            "req.html",
            colours=get_parking_lot_list()) + " אתה מוזמן להזין שוב את הפרטים, ולהזמין בה. " + other_parking_lot + " אך יש חניה פנויה בחניון " + parking_lot_name + "אין חניה פנויה בחניון"
    else:
        return " הודעה - אין חניות בזמן המבוקש - פנה למוקד הביטחון "


@app.route('/det_req', methods=['GET'])
@cross_origin()
def det_req():
    user_mail = request.args.get("user_mail")
    car_number = request.args.get("car_number")
    company_name = request.args.get("company_name")
    driver_phone = request.args.get("driver_phone")
    applicant_name = request.args.get("applicant_name")
    department = request.args.get("department")
    parking_lot_name = request.args.get("parking_lot_name")

    # TODO token...
    is_truck = False
    date_req = "date_req"
    driver_name = "driver_name"

    return parking_service.det_req(user_mail, car_number, company_name, driver_phone, driver_name,
                                   applicant_name, date_req, department, parking_lot_name, is_truck)


@app.route('/register', methods=['GET'])
@cross_origin()
def register():
    usermail = request.args.get("usermail")
    phone_number = request.args.get("phone_number")
    department = request.args.get("department")
    if user_service.register(usermail, phone_number, department):
        return "נשלחה לך סיסמה במייל" + render_template('home.html', colours=get_parking_lot_list())
    return "המערכת לא הצליחה לשלוח מייל עם סיסמה. נא וודא שהמייל תקין, ונסה שנית"


@app.route('/show_parking_lot', methods=['GET'])
@cross_origin()
def show_parking_lot():
    if request.args.get("colours") is not None:
        return str(
            parking_service.show_parking_lot(request.args.get("colours"), request.args.get("date"))) + render_template(
            'manager.html', colours=get_parking_lot_list())
    return " אין חניונים במערכת " + render_template('manager.html', colours=get_parking_lot_list())


@app.route('/parking_lots', methods=['GET'])
@cross_origin()
def parking_lots():
    return str(user_service.get_parking_lot_list()) + render_template('manager.html', colours=get_parking_lot_list())


def get_parking_lot_list():
    return user_service.get_parking_lot_list()


@app.route('/add_manager', methods=['POST', 'GET'])
@cross_origin()
def add_manager():
    massage = str(user_service.get_all_managers()) + " ניסיון להכנסת מנהל נכשל. כרגע המנהלים הם "
    if user_service.add_manager(request.args.get("usermail")):
        massage = str(user_service.get_all_managers()) + " ניסיון להכנסת מנהל הצליח. כרגע המנהלים הם "

    return massage + render_template('manager.html', colours=get_parking_lot_list())


@app.route('/add_parking_lot', methods=['POST', 'GET'])
@cross_origin()
def add_parking_lot():
    return parking_service.add_parking_lot(request.args.get("usermail")) + render_template('manager.html',
                                                                                           colours=get_parking_lot_list())


@app.route('/remove_parking_lot', methods=['POST', 'GET'])
@cross_origin()
def remove_parking_lot():
    msg = parking_service.remove_parking_lot(request.args.get("colours"))
    return msg + render_template('manager.html', colours=get_parking_lot_list())


@app.route('/add_parking_spot', methods=['POST', 'GET'])
@cross_origin()
def add_parking_spot():
    return parking_service.add_parking_spot(request.args.get("colours"), request.args.get("parking_spot_name"),
                                            len(request.args) == 3) + render_template('home.html',
                                                                                      colours=get_parking_lot_list())


@app.route('/remove_parking_spot', methods=['POST', 'GET'])
@cross_origin()
def remove_parking_spot():
    return parking_service.remove_parking_spot(request.args.get("colours"),
                                               request.args.get("parking_spot_name")) + render_template('manager.html',
                                                                                                        colours=get_parking_lot_list())


if __name__ == '__main__':
    app.run()


#############לא בשימוש.......########
@app.route('/manager', methods=['GET'])
@cross_origin()
def manager(usermail, password):
    pass

###########
# @app.route('/api/register_user', methods=['POST'])
# @cross_origin()
# def register_user():
#     print('yipi yaty')
#     r_u_o = request.get_json(force=True)
#     print(r_u_o)
#     services.user_service.register_user(r_u_o["user_mail"],
#                                         r_u_o["phone_number"],
#                                         r_u_o["department"],
#                                         r_u_o["password"], 0)
#     return jsonify(r_u_o)
#
# @app.route('/api/get_all_users', methods=['GET'])
# @cross_origin()
# def get_all_users():
#     print('yipiyay getting all users')
#     return jsonify(services.user_service.getAllUsers())
#
# @app.route('/api/login', methods=['POST'])
# @cross_origin()
# def login():
#     print('yipi yaty')
#     loginObj = request.get_json(force=True)
#     if services.user_service.login(loginObj['user_email'], loginObj['password']):
#         return jsonify(200)
#     else:
#         return jsonify(404)
#
# @app.route('/api/user_by_id', methods=['GET'])
# @cross_origin()
# def user_by_id():
#     user_email = request.args.get('user_email')
#     user = services.user_service.getUserById(user_email)
#     return jsonify(user)

######################################################################
