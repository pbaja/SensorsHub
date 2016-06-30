from passlib.hash import pbkdf2_sha256
import cherrypy, random, string, time, sqlite3, logging, libs.statistics

class Account():
    """Class containing one account"""

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
        """Hash password using pbkdf2_sha256"""
        return pbkdf2_sha256.encrypt(password)

class Accounts(object):
    """Class containing functions for all acounts"""

    def __init__(self, core):
        """Initialize variables and create default admin account if it does not exist"""
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

    def create_user(self, user, password, email=""):
        """Creates new user based on supplied username, password, and/or email"""
        with sqlite3.connect("db.sqlite") as conn:
            # Hash password
            hashed_pass = pbkdf2_sha256.encrypt(password)

            result = conn.execute("INSERT INTO accounts (user, password, email) VALUES (?,?,?);",
                                  [user, hashed_pass, email])
            account = Account(result.lastrowid, user, hashed_pass, email)
            self.accounts.append(account)
            logging.info("Created user {}".format(user))
            return account
        return None

    def current_user(self):
        """Return Account for logged in user based on cookie, also verify session"""
        user = cherrypy.request.cookie.get("user")
        session = cherrypy.request.cookie.get("session")

        # Check if cookies exist
        if user is None or session is None: return None

        # Check if user exists
        user = self.get_user(user=user.value)
        if user is None:
            logging.warning("Cookie with user {} ({}) exists, but user is not in database".format(user.user,self.core.get_client_ip()))
            return None

        # Check if user session is valid
        if user.session != session.value:
            logging.warning("Cookie with user {} ({}) exists, but session cookie is invalid".format(user.user, self.core.get_client_ip()))
            return None

        # Everything ok, return user
        return user

    def protect(self, bypass_in_demo_mode=False):
        """Returns user if he's logged in, otherwise redirects to login page"""

        # Check current logged in user
        user = self.current_user()

        # If allowed, return None when demo mode
        if user is not None or (bypass_in_demo_mode and self.core.config.get("demo_mode")):
            return user

        if user is None:
            raise cherrypy.HTTPRedirect("/settings/login")

    def get_user(self, user=None, uid=None, in_list=True, in_database=True):
        """Returns Account from loaded accounts, based on username or uid"""

        # If user is in account list, get him from there
        if in_list:
            for account in self.accounts:
                if account.user == user or account.uid == uid: return account

        # Otherwise download him from database
        if in_database:
            with sqlite3.connect("db.sqlite") as conn:
                result = None
                if user is not None:
                    result = conn.execute("SELECT uid, password, email FROM accounts WHERE user=?;", [user]).fetchone()
                elif uid is not None:
                    result = conn.execute("SELECT uid, password, email FROM accounts WHERE user=?;", [user]).fetchone()
                if result is not None:
                    account = Account(result[0], user, result[1])
                    account.email = result[2]
                    self.accounts.append(account)
                    return account

        # Return None if not found
        return None

    def login_user(self, user, password):
        """Tries to login user using username and password, returns Account object when succeed, otherwise None"""
        # Get user
        user = self.get_user(user=user)

        # Check if user exists
        if user is None:
            logging.info("Someone tried to log in with username {}, but cannot find that user in database".format(user.user))
            return None

        # Check user password
        if not pbkdf2_sha256.verify(password, user.password):
            logging.warning("User {} supplied wrong password".format(user.user))
            return None

        # Everything ok
        # Update session key and lastlogin value in database
        user.session = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
        user.lastlogin = int(time.time())
        user.commit()

        # Create cookies
        cherrypy.response.cookie["user"] = user.user
        cherrypy.response.cookie["user"]["path"] = "/"
        cherrypy.response.cookie["user"]["max-age"] = 3600 * 6
        cherrypy.response.cookie["session"] = user.session
        cherrypy.response.cookie["session"]["path"] = "/"
        cherrypy.response.cookie["session"]["max-age"] = 3600 * 6
        logging.info("User {} ({}) logged in".format(user.user, self.core.get_client_ip()))

        # Return user account
        libs.statistics.Statistics.snooper(2)
        return user

    def logout_user(self):
        """Logs out user, including destroying cookies and removing user from loaded accounts"""
        user = self.current_user()

        # Check if we need logouting
        if user is None: return False

        # Reset cookies
        cherrypy.response.cookie["user"] = ""
        cherrypy.response.cookie["user"]["path"] = "/"
        cherrypy.response.cookie["user"]["max-age"] = 0
        cherrypy.response.cookie["session"] = ""
        cherrypy.response.cookie["session"]["path"] = "/"
        cherrypy.response.cookie["session"]["max-age"] = 0

        # Reset session key in database and remove from list
        user.session = ""
        user.commit()
        self.accounts.remove(user)

        # Logouted
        logging.info("User {} ({}) logged out".format(user.user, self.core.get_client_ip()))
        return True
        # Reset session key