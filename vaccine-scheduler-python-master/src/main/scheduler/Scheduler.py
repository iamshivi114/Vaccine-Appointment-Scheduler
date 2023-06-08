from model.Vaccine import Vaccine
from model.Caregiver import Caregiver
from model.Patient import Patient
from util.Util import Util
from db.ConnectionManager import ConnectionManager
import pymssql
import datetime


'''
objects to keep track of the currently logged-in user
Note: it is always true that at most one of currentCaregiver and currentPatient is not null
        since only one user can be logged-in at a time
'''
current_patient = None

current_caregiver = None


def create_patient(tokens):
    if len(tokens) != 3:
        print("Failed to create user.")
        return

    username = tokens[1]
    password = tokens[2]

    if username_exists_patients(username):
        print("Username taken, try again!")
        return

    if not password_strong(password):
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    patient = Patient(username, salt=salt, hash=hash)

    try:
        patient.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)



def create_caregiver(tokens):
    # create_caregiver <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Failed to create user.")
        return

    username = tokens[1]
    password = tokens[2]
    # check 2: check if the username has been taken already
    if username_exists_caregiver(username):
        print("Username taken, try again!")
        return

    if not password_strong(password):
        return


    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the caregiver
    caregiver = Caregiver(username, salt=salt, hash=hash)

    # save to caregiver information to our database
    try:
        caregiver.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)


def username_exists_caregiver(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False

def username_exists_patients(username):
    cm = ConnectionManager()
    conn = cm.create_connection()
    select_username = "SELECT * FROM Patients WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def login_patient(tokens):
    global current_patient
    if current_caregiver is not None or current_patient is not None:
        print("User already logged in.")
        return
    if len(tokens) != 3:
        print("Login failed.")
        return

    username = tokens[1]
    password = tokens[2]

    patient = None
    try:
        patient = Patient(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    if patient is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_patient = patient



def login_caregiver(tokens):
    # login_caregiver <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_caregiver
    if current_caregiver is not None or current_patient is not None:
        print("User already logged in.")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Login failed.")
        return

    username = tokens[1]
    password = tokens[2]

    caregiver = None
    try:
        caregiver = Caregiver(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if caregiver is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_caregiver = caregiver


def search_caregiver_schedule(tokens):

    global current_caregiver
    global current_patient

    if current_caregiver == None and current_patient == None:
        print("Please login first!")
        return
    if (len(tokens) != 2):
        print("Please try again!")
        return

    date = tokens[1]
    date_list = date.split("-")
    month = int(date_list[0])
    day = int(date_list[1])
    year = int(date_list[2])
    d = datetime.datetime(year, month, day)
    get_availablities = "SELECT Time, Username FROM Availabilities WHERE Time = %s ORDER BY Username"
    get_doses = "SELECT * FROM Vaccines"

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)
    try:
        cursor.execute(get_availablities, d)
        schedule = cursor.fetchall()
        cursor.execute(get_doses)
        vaccines = cursor.fetchall()

        if len(schedule) <= 0:
            print("Sorry, no available appointments for the date", date)

        sep = "-" * (len(vaccines) * 20)
        header = ["Caregiver"] + [vaccine["Name"].rjust(10) for vaccine in vaccines]
        print("\t".join(header))
        print(sep)
        for row in schedule:
            doses = [str(vaccine["Doses"]).rjust(10) for vaccine in vaccines]
            print("\t".join([row['Username']] + doses))
    except pymssql.Error:
        print("Data retrieve failed! Please try again!")
        return
    except ValueError:
        print("Please enter a valid date. Try again!")
        return
    except Exception:
        print("Error occured. Try again!")
        return
    finally:
        cm.close_connection()


def reserve(tokens):
    global current_caregiver
    global current_patient

    if current_caregiver == None and current_patient == None:
        print("Please login first!")
        return
    if current_patient == None:
        print("You need to be logged in as a patient. Please login first!")
    if len(tokens) != 3:
        print("Please try again!")
        return

    date = extract_date(tokens[1])
    vaccine_name = tokens[2]

    available_caregiver = find_available_caregiver(date)
    if not available_caregiver:
        return

    doses = check_vaccine_availability(vaccine_name)
    if not doses:
        return

    appt_id = generate_appointment_id()
    print(f"Appointment ID: {appt_id}, Caregiver username: {available_caregiver}")

    if not register_appointment(appt_id, available_caregiver, current_patient, date, vaccine_name):
        return

    if not update_vaccine_stock(vaccine_name):
        return


def extract_date(date_token):
    date_tokens = date_token.split("-")
    return datetime.datetime(int(date_tokens[2]), int(date_tokens[0]), int(date_tokens[1]))


def find_available_caregiver(date):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()

    available_caregiver_query = "SELECT Username FROM Availabilities WHERE Time = (%s) ORDER BY Username"

    try:
        cursor.execute(available_caregiver_query, (date))
        caregiver_username = cursor.fetchone()
    finally:
        cm.close_connection()

    if caregiver_username is None:
        print("No Caregiver is available!")
        return None
    return caregiver_username[0]


def check_vaccine_availability(vaccine_name):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()

    get_vaccine_query = "SELECT Name, Doses FROM Vaccines WHERE Name = (%s)"

    try:
        cursor.execute(get_vaccine_query, vaccine_name)
        vaccine_doses = cursor.fetchone()
    finally:
        cm.close_connection()

    if vaccine_doses is None:
        print("We do not have this vaccine. Please try again!")
        return None
    elif vaccine_doses[1] == 0:
        print("Not enough available doses!")
        return None
    return vaccine_doses[1]


def generate_appointment_id():
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()

    get_last_appt_id_query = "SELECT MAX(AppID) FROM Appointments"
    try:
        cursor.execute(get_last_appt_id_query)
        last_appt_id = cursor.fetchone()[0]
    finally:
        cm.close_connection()


    if last_appt_id is None:
        return 1
    else:
        return last_appt_id + 1


def register_appointment(appt_id, caregiver, patient, date, vaccine_name):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()

    insert_appointment_query = "INSERT INTO Appointments VALUES (%s, %s, %s, %s, %s)"
    update_caregiver_availability_query = "DELETE FROM Availabilities WHERE Username = (%s) AND Time = (%s)"

    try:
        cursor.execute(insert_appointment_query, (appt_id, caregiver, patient.username, date, vaccine_name))
        cursor.execute(update_caregiver_availability_query, (caregiver, date))
        conn.commit()
    except pymssql.Error:
        print("Error occurred when making reservation")
        return False
    finally:
        cm.close_connection()
    return True


def update_vaccine_stock(vaccine_name):
    try:
        named_vaccine = Vaccine(vaccine_name, 0)
        named_vaccine.get()
        named_vaccine.decrease_available_doses(1)
        return True
    except pymssql.Error as e:
        print("Db-Error:", e)
        return False
    except Exception as e:
        print("Error occurred when decreasing doses")
        print("Error:", e)
        return False

def upload_availability(tokens):
    #  upload_availability <date>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        return

    date = tokens[1]
    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    try:
        d = datetime.datetime(year, month, day)
        current_caregiver.upload_availability(d)
    except pymssql.Error as e:
        print("Upload Availability Failed")
        print("Db-Error:", e)
        quit()
    except ValueError:
        print("Please enter a valid date!")
        return
    except Exception as e:
        print("Error occurred when uploading availability")
        print("Error:", e)
        return
    print("Availability uploaded!")


def cancel(tokens):
    global current_caregiver
    global current_patient

    if current_caregiver == None and current_patient == None:
        print("Please login first!")
        return
    if (len(tokens) != 2):
        print("Please try again!")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)
    cancel_id = tokens[1]

    try:
        appointment = "SELECT AppID, Name, p_username, c_username, Name, Time FROM Appointments WHERE AppID = %d"
        cursor.execute(appointment, cancel_id)
        get_appointment = cursor.fetchone()
        isValid = False
        if current_patient is not None and get_appointment['p_username'] == current_patient.username:
            isValid = True
        elif current_caregiver is not None and get_appointment['c_username'] == current_caregiver.username:
            isValid = True

        if isValid:
            delete_appointment = "DELETE FROM Appointments WHERE AppID = %d"
            vaccine = Vaccine(get_appointment["Name"], None).get()
            vaccine.increase_available_doses(1)
            cursor.execute(delete_appointment, cancel_id)
            conn.commit()
            print("Appointment cancelled succesfully!")
            if current_patient is not None:
                date = get_appointment['Time']
                caregiver = get_appointment['c_username']
                command = "INSERT INTO Availabilities VALUES (%d, %d)"
                parameters = (date, caregiver)
                with conn.cursor() as cursor:
                    cursor.execute(command, parameters)
                    conn.commit()
        else:
            print("Sorry, but couldn't find any appointment!")
    except pymssql.Error:
        print("Data retrieve failed! Please try again!")
        return
    except ValueError:
        print("Please enter a valid date. Try again!")
        return
    except Exception as e:
        print("Error occured. Try again!", e)
        return
    finally:
        cm.close_connection()



def add_doses(tokens):
    #  add_doses <vaccine> <number>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    #  check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    vaccine_name = tokens[1]
    doses = int(tokens[2])
    vaccine = None
    try:
        vaccine = Vaccine(vaccine_name, doses).get()
    except pymssql.Error as e:
        print("Error occurred when adding doses")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when adding doses")
        print("Error:", e)
        return

    # if the vaccine is not found in the database, add a new (vaccine, doses) entry.
    # else, update the existing entry by adding the new doses
    if vaccine is None:
        vaccine = Vaccine(vaccine_name, doses)
        try:
            vaccine.save_to_db()
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    else:
        # if the vaccine is not null, meaning that the vaccine already exists in our table
        try:
            vaccine.increase_available_doses(doses)
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    print("Doses updated!")


def show_appointments(tokens):
    global current_caregiver
    global current_patient

    if current_caregiver == None and current_patient == None:
        print("Please login first!")
        return
    if (len(tokens) != 1):
        print("Please try again!")
        return
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)
    try:
        queries = {
            "patient": {
                "username": current_patient.username if current_patient else None,
                "sql": "SELECT AppID, Name, Time, c_username FROM Appointments WHERE p_username = %s ORDER BY AppID",
                "role": "c_username"
            },
            "caregiver": {
                "username": current_caregiver.username if current_caregiver else None,
                "sql": "SELECT AppID, Name, Time, p_username FROM Appointments WHERE c_username = %s ORDER BY AppID",
                "role": "p_username"
            }
        }
        for role, query_info in queries.items():
            if query_info["username"] is not None:
                cursor.execute(query_info["sql"], query_info["username"])
                appointments = cursor.fetchall()

                if len(appointments) == 0:
                    print("There are no appointments scheduled")
                else:
                    print("{: >10}\t{: >10}\t{: >10}\t{: >10}\t".format("Appointment ID", "Vaccine", "Date", query_info["role"].split('_')[0].title()))

                    for appointment in appointments:
                        print("{: >10}\t{: >10}\t{: >10}\t{: >10}\t".format(appointment["AppID"], appointment["Name"], str(appointment["Time"]), appointment[query_info["role"]]))
    except pymssql.Error:
        print("Data retrieve failed! Please try again!")
        return
    except ValueError:
        print("Please enter a valid date. Try again!")
        return
    except Exception as e:
        print("Error occured. Try again!", e)
        return
    finally:
        cm.close_connection()


def logout(tokens):
    global current_caregiver
    global current_patient

    if current_caregiver == None and current_patient == None:
        print("Please login first!")
        return
    if (len(tokens) != 1):
        print("Please try again!")
        return
    else:
        current_caregiver = None
        current_patient = None
        print("Successfully logged out!")

def password_strong(password):
    if len(password) < 8:
        print("Password must be at least 8 characters")
        return False
    if not any(char.isupper() for char in password) or not any(char.islower() for char in password):
        print("Password must be a mixture of both uppercase and lowercase letters.")
        return False
    if not any(char.isdigit() for char in password):
        print("Password must be a mixture of letters and numbers.")
        return False
    if not any(char in '!@#?' for char in password):
        print("Password must contain at least one special character from !, @, #, ?.")
        return False
    return True



def start():
    stop = False
    print()
    print(" *** Please enter one of the following commands *** ")
    print("> create_patient <username> <password>")  # //TODO: implement create_patient (Part 1)
    print("> create_caregiver <username> <password>")
    print("> login_patient <username> <password>")  # // TODO: implement login_patient (Part 1)
    print("> login_caregiver <username> <password>")
    print("> search_caregiver_schedule <date>")  # // TODO: implement search_caregiver_schedule (Part 2)
    print("> reserve <date> <vaccine>")  # // TODO: implement reserve (Part 2)
    print("> upload_availability <date>")
    print("> cancel <appointment_id>")  # // TODO: implement cancel (extra credit)
    print("> add_doses <vaccine> <number>")
    print("> show_appointments")  # // TODO: implement show_appointments (Part 2)
    print("> logout")  # // TODO: implement logout (Part 2)
    print("> Quit")
    print()
    while not stop:
        response = ""
        print("> ", end='')

        try:
            response = str(input())
        except ValueError:
            print("Please try again!")
            break

        #response = response.lower()
        tokens = response.split(" ")
        if len(tokens) == 0:
            ValueError("Please try again!")
            continue
        operation = tokens[0]
        if operation == "create_patient":
            create_patient(tokens)
        elif operation == "create_caregiver":
            create_caregiver(tokens)
        elif operation == "login_patient":
            login_patient(tokens)
        elif operation == "login_caregiver":
            login_caregiver(tokens)
        elif operation == "search_caregiver_schedule":
            search_caregiver_schedule(tokens)
        elif operation == "reserve":
            reserve(tokens)
        elif operation == "upload_availability":
            upload_availability(tokens)
        elif operation == "cancel":
            cancel(tokens)
        elif operation == "add_doses":
            add_doses(tokens)
        elif operation == "show_appointments":
            show_appointments(tokens)
        elif operation == "logout":
            logout(tokens)
        elif operation == "quit":
            print("Bye!")
            stop = True
        else:
            print("Invalid operation name!")


if __name__ == "__main__":
    '''
    // pre-define the three types of authorized vaccines
    // note: it's a poor practice to hard-code these values, but we will do this ]
    // for the simplicity of this assignment
    // and then construct a map of vaccineName -> vaccineObject
    '''

    # start command line
    print()
    print("Welcome to the COVID-19 Vaccine Reservation Scheduling Application!")

    start()
