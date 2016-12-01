import indigo
import requests
import json
import sys
import uuid

LOGIN_URL = 'https://simplisafe.com/mobile/login/'
LOGOUT_URL = 'https://simplisafe.com/mobile/logout'
LOCATIONS_URL = 'https://simplisafe.com/mobile/$UID$/locations'
DASHBOARD_URL = 'https://simplisafe.com/mobile/$UID$/sid/$LID$/dashboard'
EVENTS_URL = 'https://simplisafe.com/mobile/$UID$/sid/$LID$/events'
STATE_URL = 'https://simplisafe.com/mobile/$UID$/sid/$LID$/set-state'

class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        # Initialize variables
        self.session = None
        self.debug = True
        self.state = None
        self.uid = None
        self.location = None

        # Create a requests session to persist the cookies
        self.session = requests.session()

    def __del__(self):
        indigo.PluginBase.__del__(self)

    # def startup(self):
    #     indigo.server.log(u"SS - STARTUP")

    def armAlarmHome(self, action):
        #PluginAction class
        deviceId = action.deviceId
        device = indigo.devices[deviceId]
        self.setAlarm(u"home", device)

    def armAlarmAway(self, action):
        #PluginAction class
        deviceId = action.deviceId
        device = indigo.devices[deviceId]
        self.setAlarm(u"away", device)

    def disarmAlarm(self, action):
        #PluginAction class
        deviceId = action.deviceId
        device = indigo.devices[deviceId]
        self.setAlarm(u"off", device)

    def setAlarm(self, state, device):
        username = device.pluginProps["username"]
        password = device.pluginProps["password"]
        hasUsername = username is not None and username != u""
        hasPassword = password is not None and password != u""
        if hasUsername and hasPassword:
            self.login(username, password)
            self.get_location()
            self.set_state(state, device)
            # self.get_dashboard()
            self.logout()
        else:
            indigo.server.log("Username or password not set", isError=True)

    def abort(self, msg):
        indigo.server.log("Aborting and Logging Out. %s" % msg, isError=True)
        self.logout()

    def set_state(self, state, device):

        if state not in ('home', 'away', 'off'):
            self.abort("State must be 'home', 'away', or 'off'. You tried '%s'." % state)
            return

        state_data = {
            'state': state,
            'mobile': '1',
            'no_persist': '1',
            'XDEBUG_SESSION_START': 'session_name',
        }

        indigo.server.log("Setting alarm state to %s" % state)

        URL = STATE_URL.replace('$UID$', self.uid).replace('$LID$', self.location)
        response = self.session.post(URL, data=state_data)
        response_object = json.loads(response.text)

        result_codes = {
            '2': 'off',
            '4': 'home',
            '5': 'away',
        }
        result_code = response_object['result']
        self.state = result_codes[str(result_code)]

        self.updateDeviceState(device)

        indigo.server.log("Alarm State: %s" % self.state)
        return result_codes[str(result_code)]

    def updateDeviceState(self, device):
        stateToDisplay = 'unknown'
        if self.state == 'off':
            stateToDisplay = 'Disarmed'
        elif self.state == 'home':
            stateToDisplay = 'Armed - Home'
        elif self.state == 'away':
            stateToDisplay = 'Armed - Away'

        device.updateStateOnServer('alarmState', value=u'off', uiValue=stateToDisplay, clearErrorState=True)
    #
    # def get_state(self):
    #     return self.state
    #
    # def get_temperature(self):
    #     return self.temperature
    #
    def get_dashboard(self):

        if not self.uid:
            self.abort("You tried to get dashboard without first having a User ID set.")
            return

        if not self.location:
            self.abort("You tried to get dashboard without first having a location set.")
            return

        dashboard_data = {
            'no_persist': '0',
            'XDEBUG_SESSION_START': 'session_name',
        }

        URL = DASHBOARD_URL.replace('$UID$', self.uid).replace('$LID$', self.location)
        response = self.session.post(URL, data=dashboard_data)
        response_object = json.loads(response.text)

        if self.debug:
            indigo.server.log("Dashboard Response: %s" % response.text)

        response_object = json.loads(response.text)

        self.temperature = response_object['location']['monitoring']['freeze']['temp']

        if self.debug:
            indigo.server.log("Current Temperature: %s" % self.temperature)

    def get_location(self):

        if not self.uid:
            self.abort("You tried to get location without first having a User ID set.")
            return

        location_data = {
            'no_persist': '0',
            'XDEBUG_SESSION_START': 'session_name',
        }

        URL = LOCATIONS_URL.replace('$UID$', self.uid)
        response = self.session.post(URL, data=location_data)
        response_object = json.loads(response.text)

        # if self.debug:
        #     print "Location Response: %s" % response.text

        self.location = response_object['locations'].keys()[0]
        self.state = response_object['locations'][self.location]['system_state']

    def login(self, username, password):

        if not username or not password:
            self.abort("You must provide a username and password.")
            return

        login_data = {
            'name': username,
            'pass': password,
            'device_name': 'My iPhone',
            'device_uuid': str(uuid.uuid1()),
            'version': '1100',
            'no_persist': '1',
            'XDEBUG_SESSION_START': 'session_name',
        }

        response = self.session.post(LOGIN_URL, data=login_data)
        response_object = json.loads(response.text)

        # if self.debug:
        #     print "Login Response: %s" % response.text

        self.username = response_object['username']
        self.session_id = response_object['session']
        self.uid = response_object['uid']

    def logout(self):

        logout_data = {
            'no_persist': '0',
            'XDEBUG_SESSION_START': 'session_name',
        }

        response = self.session.post(LOGOUT_URL)
        response_object = json.loads(response.text)
