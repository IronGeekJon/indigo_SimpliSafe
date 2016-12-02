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
        self.session_id = None
        self.debug = True
        self.state = 'unknown'
        self.uid = None
        self.location = None

        self.startSession()

    def __del__(self):
        self.logout()
        indigo.PluginBase.__del__(self)

    def deviceStartComm(self, dev):
        if self.ensureLogin(dev):
            self.getLocation()
            if isinstance(dev, indigo.Device):
                indigo.server.log("Updating device state")
                self.updateDeviceState(dev)
        else:
            self.abort("Unable to start device")

    def deviceStopComm(self, dev):
        self.logout()

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

    def getAlarmState(self, action):
        #PluginAction class
        deviceId = action.deviceId
        device = indigo.devices[deviceId]
        self.updateDeviceState(device)

    def setAlarm(self, state, dev):
        if self.ensureLogin(dev):
            self.getLocation()
            self.setState(state, dev)
            # self.get_dashboard()
        else:
            indigo.server.log("Error logging in.", isError=True)

    def abort(self, msg):
        indigo.server.log("Error: %s" % msg, isError=True)

    def setState(self, state, device):

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
        self.state = result_codes[str(result_code)].lower()

        self.updateDeviceState(device)

        indigo.server.log("Alarm State: %s" % self.state)
        return self.state

    def updateDeviceState(self, dev):
        if not self.ensureLogin(dev):
            self.abort("Not logged in - unable to update alarm state")
            return

        #get the current state from the server
        self.getLocation()

        indigo.server.log("Current State: " + self.state)

        stateToDisplay = 'Unknown'
        imageToDisplay = indigo.kStateImageSel.SensorOff
        if self.state == 'off':
            stateToDisplay = 'Disarmed'
            imageToDisplay = indigo.kStateImageSel.SensorTripped
        elif self.state == 'pending off':
            self.state = 'off' # reset 'pending off' to 'off'
            stateToDisplay = 'Disarmed'
            imageToDisplay = indigo.kStateImageSel.SensorTripped
        elif self.state == 'home':
            stateToDisplay = 'Armed - Home'
            imageToDisplay = indigo.kStateImageSel.SensorOn
        elif self.state == 'away':
            stateToDisplay = 'Armed - Away'
            imageToDisplay = indigo.kStateImageSel.SensorOn
        else:
            self.state = 'unknown'

        indigo.server.log("State NOW: " + self.state)

        dev.updateStateOnServer('alarmState', value=self.state, uiValue=stateToDisplay, clearErrorState=True)
        dev.updateStateImageOnServer(imageToDisplay)
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

    def getLocation(self):

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
        self.state = response_object['locations'][self.location]['system_state'].lower()

    def ensureLogin(self, dev):

        username = dev.pluginProps["username"]
        password = dev.pluginProps["password"]
        hasUsername = username is not None and username != u""
        hasPassword = password is not None and password != u""

        if not username or not password:
            self.abort("You must provide a username and password.")
            return false

        if self.isLoggedIn():
            indigo.server.log("Existing Session found.  Not logging in again.")
            return True

        self.startSession()

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

        self.username = response_object['username']
        self.session_id = response_object['session']
        self.uid = response_object['uid']

        return self.isLoggedIn()

    def logout(self):

        if isLoggedIn():
            logout_data = {
                'no_persist': '0',
                'XDEBUG_SESSION_START': 'session_name',
            }

            response = self.session.post(LOGOUT_URL)
            response_object = json.loads(response.text)

        self.session = None
        self.session_id = None
        self.uid = None

    def isLoggedIn(self):
        hasSession = self.session != None and self.session != ""
        hasSessionId = self.session_id != None and self.session_id != ""
        hasUid = self.uid != None and self.uid != ""

        return hasSession and hasUid and hasSessionId

    def startSession(self):
        # Create a requests session to persist the cookies
        self.session = requests.session()
