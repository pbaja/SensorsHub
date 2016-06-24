from passlib.hash import pbkdf2_sha256
from cherrypy._cpcompat import base64_decode
import cherrypy, random, string, time, sqlite3, logging

class Account():

    def __init__(self, uid, user="", hashed_password="", email=""):
        self.uid = uid
        self.user = user
        self.password = hashed_password
        self.lastlogin = int(time.time())
        self.session = ""
        self.email = email

    def load(self):
        """Load user information from database"""
        with sqlite3.connect("db.sqlite") as conn:
            result = conn.execute("SELECT user, password, lastlogin, email FROM accounts WHERE uid=?;",[self.uid]).fetchall()
            result = result[0]
            self.user = result[0]
            self.password = result[1]
            self.lastlogin = result[2]
            self.email = result[3]
            return True
        return False

    def commit(self):
        """Send user information to database"""
        with sqlite3.connect("db.sqlite") as conn:
            values = [self.password,self.lastlogin,self.session,self.email, self.uid]
            conn.execute("UPDATE accounts SET password=?, lastlogin=?, session=?, email=? WHERE uid=?",values)
            return True
        return False

    @staticmethod
    def hash_password(password):
        return pbkdf2_sha256.encrypt(password)

class Accounts(object):

    def __init__(self, core):
        self.core = core
        self.accounts = []

        # Create default admin account if it does not exist
        with sqlite3.connect("db.sqlite") as conn:
            if len(conn.execute("SELECT user FROM accounts WHERE user='admin';").fetchall()) == 0:
                logging.warning("Default admin account does not exist. Creating one for you.")
                if self.create_user("admin", "admin"):
                    logging.info("Account created. Default user: admin, password: admin. Change them immidiately!")
                else:
                    logging.error("Failed to create admin account!")

    def get_user(self, user=None, uid=None):
        for account in self.accounts:
            if account.user == user or account.uid == uid:
                return account
        return None

    def login_user(self, user, password):
        # Check if user exist
        with sqlite3.connect("db.sqlite") as conn:
            result = conn.execute("SELECT uid, password, email FROM accounts WHERE user=?;", [user]).fetchall()
            if len(result) > 0:
                result = result[0]
                # Verify password
                if pbkdf2_sha256.verify(password, result[1]):
                    # Password okay, login
                    account = Account(result[0],user, result[1])
                    account.session = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
                    account.lastlogin = int(time.time())
                    account.email = result[2]
                    account.commit()
                    self.accounts.append(account)
                    # Create cookies
                    cherrypy.response.cookie["user"] = account.user
                    cherrypy.response.cookie["user"]["path"] = "/"
                    cherrypy.response.cookie["user"]["max-age"] = 3600 * 6
                    cherrypy.response.cookie["session"] = account.session
                    cherrypy.response.cookie["session"]["path"] = "/"
                    cherrypy.response.cookie["session"]["max-age"] = 3600 * 6
                    logging.info("User {} ({}) logged in".format(user, self.core.get_client_ip()))
                    return account
                else:
                    logging.warning("User {} supplied wrong password".format(user))
            else:
                logging.info("Someone tried to log in with username {}, but cannot find that user in database".format(user))
        return None

    def create_user(self, user, password, email=""):
        with sqlite3.connect("db.sqlite") as conn:
            hashed_pass = pbkdf2_sha256.encrypt(password)
            cur = conn.cursor()
            cur.execute("INSERT INTO accounts (user, password, email) VALUES (?,?,?);", [user, hashed_pass, email])
            account = Account(cur.lastrowid,user,hashed_pass, email)
            self.accounts.append(account)
            return account
        return None

    def logout_user(self, account=None):
        if account is None:
            account = self.verify_user()
        if account:
            # Remove user sesion key
            account.session = ""
            account.commit()
            # Remove user from list
            self.accounts.remove(account)
            # Reset session key
            cherrypy.response.cookie["session"] = ""
            cherrypy.response.cookie["session"]["path"] = "/"
            cherrypy.response.cookie["session"]["max-age"] = 3600 * 6
            logging.info("User {} ({}) logged out".format(account.user, self.core.get_client_ip()))
            return True
        return False

    def protect(self):
        """Use this function, when you want users to log in before accessing page"""
        account = self.verify_user()
        if not account:
            raise cherrypy.HTTPRedirect("/settings/login")
        return account

    def verify_user(self):
        user = cherrypy.request.cookie.get("user")
        session = cherrypy.request.cookie.get("session")
        # Check if cookies exist
        if user and session:
            # Check if user exist and his session
            account = self.get_user(user=user.value)
            if account:
                if account.session == session.value:
                    # Everything ok, return
                    return account
                else:
                    # Session key is not correct, logout
                    account.session = ""
                    account.update()
                    self.accounts.remove(account)
                    logging.warning("User {} ({}) is logged in, but cookie contains wrong token".format(account.user, self.core.get_client_ip()))
                    return None
        return None