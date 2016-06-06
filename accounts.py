from passlib.hash import pbkdf2_sha256
from cherrypy._cpcompat import base64_decode
import cherrypy, random, string, time

class Accounts(object):

    def __init__(self):
        self.user = "admin"
        self.password = "admin"
        self.session = ""
        self.lastip = ""
        self.lastlogin = 0

    def login_user(self, user, password):
        # Check if user exist
        if self.user == user and self.password == password:
            # Create session
            self.session = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
            self.lastip = cherrypy.request.headers['Remote-Addr']
            self.lastlogin = int(time.time())
            # Create cookies
            cherrypy.response.cookie["user"] = user
            cherrypy.response.cookie["user"]["path"] = "/"
            cherrypy.response.cookie["user"]["max-age"] = 3600 * 6
            cherrypy.response.cookie["session"] = self.session
            cherrypy.response.cookie["session"]["path"] = "/"
            cherrypy.response.cookie["session"]["max-age"] = 3600 * 6
            return True
        return False

    def protect(self):
        """Use this function, when you want users to log in before accessing page"""
        if not self.verify_user():
            cherrypy.serving.response.headers['www-authenticate'] = 'Basic realm="Please login"'
            raise cherrypy.HTTPError(401, "You are not authorized to access that resource")

    def verify_user(self):
        user = cherrypy.request.cookie.get("user")
        session = cherrypy.request.cookie.get("session")
        # Check if cookies exist
        if user and session:
            # Check if user exist and his session
            if user == self.user and session == self.session:
                return True

        # If cookies does not exist, check for authorization header
        auth = cherrypy.request.headers.get('Authorization')
        if auth:
            scheme, params = auth.split(" ", 1)
            if scheme.lower() == "basic":
                username, password = base64_decode(params).split(":", 1)
                if self.login_user(username, password):
                    return True

        return False