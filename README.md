# SimpliSafe Plugin for IndigoDomo
This plugin **requires** that you have paid for the SimpliSafe "Interactive Alarm Monitoring" because it relies on the API that comes along with that.

**NOTE:** SimpliSafe does not provide any event based notification of when the Alarm state changes.  This plugin will update the state of the alarm when initiated by Indigo, but it will currently NOT reflect changes when they are initiated from other locations (like the keypad or mobile app)

## Device
There will be one device (alarm system) available with this plugin.  You are required to enter your SimpliSafe login information into the settings.

## Actions
There are three different SimpliSafe actions available to you:
* Arm SimpliSafe - Home
* Arm SimpliSafe - Away
* Disarm SimpliSafe

This plugin is still considered to be in a BETA stage.  Please feel free to provide comments.

## Triggers
Alarm state changes will generate Indigo triggers for 'Device State Changed':
* Alarm Status Changed
* Alarm Status is Armed - Home
* Alarm Status is Armed - Away
* Alarm is Disarmed - off
* Alarm Status is Unknown

**PLEASE Remember** that alarm state changes are not always captured if they are not initiated from Indigo

## Poor mans event handling (aka Polling)
In an effort to capture the current alarm state, there is a Device Action:
* Get SimpliSafe Alarm State

This will check (poll) to get the current alarm state and then update the device status.  You can create a schedule in Indigo to run this action as often as you like.  **Please Understand** that this is using your login information and account for every call and should limit the polling interval as much as possible.
