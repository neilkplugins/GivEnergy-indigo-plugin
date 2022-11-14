#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2022 neilk
#
# Based on the sample dimmer plugin

################################################################################
# Imports
################################################################################
import indigo
import requests
import json
from datetime import datetime, timedelta, date


################################################################################
# Globals
################################################################################


################################################################################
class Plugin(indigo.PluginBase):
    ########################################
    # Class properties
    ########################################

    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.debug = pluginPrefs.get("showDebugInfo", False)
        self.deviceList = []

    ########################################
    def deviceStartComm(self, device):
        self.debugLog("Starting device: " + device.name)
        self.debugLog(str(device.id) + " " + device.name)
        # Update Device States after upgrade
        device.stateListOrDisplayStateIdChanged()
        if device.id not in self.deviceList:
            self.update(device)
            self.deviceList.append(device.id)

    ########################################
    def deviceStopComm(self, device):
        self.debugLog("Stopping device: " + device.name)
        if device.id in self.deviceList:
            self.deviceList.remove(device.id)

    ########################################
    def runConcurrentThread(self):
        self.debugLog("Starting concurrent thread")
        try:
            while True:
                try:
                    pollingFreq = int(self.pluginPrefs['polling_frequency'])
                except:
                    pollingFreq = 15
                # we sleep (by a user defined amount, default 60s) first because when the plugin starts, each device
                # is updated as they are started.
                self.sleep(1 * pollingFreq)
                # now we cycle through each WLED
                for deviceId in self.deviceList:
                    # call the update method with the device instance
                    self.update(indigo.devices[deviceId])
        except self.StopThread:
            pass

    ########################################
    def update(self, device):

        if device.deviceTypeId == "givenergy_inverter":
            self.debugLog("Updating Inverter device: " + device.name)
            requestsTimeOut = float(self.pluginPrefs.get('request_timeout'))
            url = "https://api.givenergy.cloud/v1/inverter/{serial_num}/system-data/latest".format(
                serial_num=device.pluginProps["inverter_serial"])
            self.debugLog("URL is: " + url)
            headers = {
                'Authorization': 'Bearer ' + device.pluginProps["api_key"] + '',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            self.debugLog("Headers are:")
            self.debugLog(headers)

            try:
                response = requests.request('GET', url, headers=headers, timeout=requestsTimeOut)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                self.errorLog(
                    "HTTP error getting %s %s data: %s" % (device.name, device.pluginProps["inverter_serial"], str(e)))
                device.setErrorStateOnServer('Not Responding')
                return
            except Exception as e:
                self.errorLog(
                    "Unknown error getting %s %s data: %s" % (device.name, device.pluginProps["inverter_serial"], str(e)))
                device.setErrorStateOnServer('Not Responding')
                return
            # Get the JSON from the API to update device states
            latest_json = json.loads(response.text)

            self.debugLog("API Response was:")
            self.debugLog(latest_json)
            # Now update states
            state_updates = []
            state_updates.append({'key': "data_timestamp", 'value': latest_json['data']['time']})
            state_updates.append({'key': "solar_power", 'value': latest_json['data']['solar']['power']})
            state_updates.append({'key': "array_1_voltage", 'value': latest_json['data']['solar']['arrays'][0]['voltage']})
            state_updates.append({'key': "array_1_current", 'value': latest_json['data']['solar']['arrays'][0]['current']})
            state_updates.append({'key': "array_1_power", 'value': latest_json['data']['solar']['arrays'][0]['power']})
            state_updates.append({'key': "array_2_voltage", 'value': latest_json['data']['solar']['arrays'][1]['voltage']})
            state_updates.append({'key': "array_2_current", 'value': latest_json['data']['solar']['arrays'][1]['current']})
            state_updates.append({'key': "array_2_power", 'value': latest_json['data']['solar']['arrays'][1]['power']})
            state_updates.append({'key': "grid_voltage", 'value': latest_json['data']['grid']['voltage']})
            state_updates.append({'key': "grid_current", 'value': latest_json['data']['grid']['current']})
            state_updates.append({'key': "grid_power", 'value': latest_json['data']['grid']['power']})
            state_updates.append({'key': "grid_frequency", 'value': latest_json['data']['grid']['frequency']})
            state_updates.append({'key': "battery_percentage", 'value': latest_json['data']['battery']['percent']})
            state_updates.append({'key': "battery_power", 'value': latest_json['data']['battery']['power']})
            state_updates.append({'key': "battery_temp", 'value': latest_json['data']['battery']['temperature']})
            state_updates.append({'key': "inverter_temp", 'value': latest_json['data']['inverter']['temperature']})
            state_updates.append({'key': "inverter_power", 'value': latest_json['data']['inverter']['power']})
            state_updates.append(
                {'key': "inverter_output_voltage", 'value': latest_json['data']['inverter']['output_voltage']})
            state_updates.append(
                {'key': "inverter_output_frequency", 'value': latest_json['data']['inverter']['output_frequency']})
            state_updates.append({'key': "inverter_eps_power", 'value': latest_json['data']['inverter']['eps_power']})
            state_updates.append(
                {'key': "inverter_output_voltage", 'value': latest_json['data']['inverter']['output_voltage']})
            state_updates.append({'key': "consumption", 'value': latest_json['data']['consumption']})
            # # Now update in one go
            device.updateStatesOnServer(state_updates)
            return

        if device.deviceTypeId == "givenergy_flow":
            self.debugLog("Updating Flow device: " + device.name+ " with aggregation "+ device.pluginProps['aggregation'])

            self.debugLog("Which is linked to Inverter  "+ device.pluginProps['inverterID'])
            inverter_device = indigo.devices[int(device.pluginProps['inverterID'])]
            self.debugLog(inverter_device.pluginProps["inverter_serial"])

            time_now = datetime.now()
            match device.pluginProps['aggregation']:
                case "0":
                    self.debugLog("Half Hourly Reporting")
                    start_time = date.today()
                    end_time = date.today()
                    #end_time = time_now + (time_now.min - time_now) % timedelta(minutes=30)
                    #start_time = time_now - (time_now - time_now.min) % timedelta(minutes=30)
                case "1":
                    self.debugLog("Daily Reporting")
                    start_time = date.today()
                    #end_time = time_now + (time_now.min - time_now) % timedelta(minutes=30)
                    end_time = date.today()
                case "2":
                    self.debugLog("Monthly Reporting")
                    start_time = datetime(time_now.year, time_now.month, 1).date()
                    #end_time = time_now + (time_now.min - time_now) % timedelta(minutes=30)
                    end_time = date.today()
                case "3":
                    self.debugLog("Yearly Reporting")
                    start_time = date(date.today().year, 1,1)
                    #end_time = time_now + (time_now.min - time_now) % timedelta(minutes=30)
                    end_time = date.today()

            self.debugLog ("Start Time is "+ str(start_time))
            self.debugLog("End Time is " + str(end_time))

            requestsTimeOut = float(self.pluginPrefs.get('request_timeout'))
            url = "https://api.givenergy.cloud/v1/inverter/{serial_num}/energy-flows".format(
                serial_num=inverter_device.pluginProps["inverter_serial"])
            self.debugLog("URL is: " + url)
            payload = json.dumps({
                "start_time": str(start_time),
                "end_time": str(end_time),
                "grouping": int(device.pluginProps['aggregation'])
            })

            self.debugLog("Payload is:")
            self.debugLog(payload)
            headers = {
                'Authorization': 'Bearer ' + inverter_device.pluginProps["api_key"] + '',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            self.debugLog("Headers are:")
            self.debugLog(headers)

            try:
                 response = requests.request('POST', url, headers=headers, json=payload, timeout=requestsTimeOut)
                 response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                 self.errorLog(
                     "HTTP error getting %s %s data: %s" % (device.name, inverter_device.pluginProps["inverter_serial"], str(e)))
                 device.setErrorStateOnServer('Not Responding')
                 return
            except Exception as e:
                 self.errorLog("Unknown error getting %s %s data: %s" % (device.name, inverter_device.pluginProps["inverter_serial"], str(e)))
                 device.setErrorStateOnServer('Not Responding')
                 return
            # Get the JSON from the API to update device states
            latest_json = json.loads(response.text)

            self.debugLog("API Response was:")


            self.debugLog("Flow API Response Starts")
            self.debugLog(latest_json)
            self.debugLog("Flow API Response Ends")



            # Now update states
            # state_updates = []
            # state_updates.append({'key': "start_time", 'value': latest_json['data']['start_time']})
            # state_updates.append({'key': "end_time", 'value': latest_json['data']['end_time']})
            #
            # # # Now update in one go
            # device.updateStatesOnServer(state_updates)
            return
        return

    ########################################
    # UI Validate, Plugin Preferences
    ########################################
    def validatePrefsConfigUi(self, valuesDict):
        self.debugLog(valuesDict)
        try:
            timeoutint = float(valuesDict['request_timeout'])
        except:
            self.errorLog("Invalid entry for GivEnergy Plugin Config API Timeout - must be a number")
            errorsDict = indigo.Dict()
            errorsDict['request_timeout'] = "Invalid entry for  GivEnergy Config API Timeout - must be a number"
            return (False, valuesDict, errorsDict)
        try:
            pollingfreq = int(valuesDict['polling_frequency'])
        except:
            self.errorLog(
                "Invalid entry for GivEnergy Plugin Config Polling Frequency - must be a whole number greater than 0")
            errorsDict = indigo.Dict()
            errorsDict[
                'polling_frequency'] = "Invalid entry for GivEnergy Plugin Config Polling Frequency - must be a whole number greater than 0"
            return (False, valuesDict, errorsDict)

        if int(valuesDict['polling_frequency']) == 0:
            self.errorLog("Invalid entry for GivEnergy Plugin Config Polling Frequency - must be greater than 0")
            errorsDict = indigo.Dict()
            errorsDict[
                'polling_frequency'] = "Invalid entry for GivEnergy Plugin Config Polling Frequency - must be a whole number greater than 0"
            return (False, valuesDict, errorsDict)
        if int(valuesDict['request_timeout']) == 0:
            self.errorLog("Invalid entry for GivEnergy Plugin Config Requests Timeout - must be greater than 0")
            errorsDict = indigo.Dict()
            errorsDict[
                'request_timeout'] = "Invalid entry for GivEnergy Plugin Config Requests Timeout - must be greater than 0"
            return (False, valuesDict, errorsDict)

        # Otherwise we are good
        return (True, valuesDict)

    ########################################
    # Menu Methods
    ########################################
    def toggleDebugging(self):
        if self.debug:
            indigo.server.log("Turning off debug logging")
            self.pluginPrefs["showDebugInfo"] = False
        else:
            indigo.server.log("Turning on debug logging")
            self.pluginPrefs["showDebugInfo"] = True
        self.debug = not self.debug

    def getInverterDevices(self, filter="", valuesDict=None, typeId="", targetId=0):

        retList = []
        devicePlugin = valuesDict.get("devicePlugin", None)
        for dev in indigo.devices.iter():
            if dev.protocol == indigo.kProtocol.Plugin and \
                    dev.pluginId == "com.barn.indigoplugin.GivEnergy":
                retList.append((dev.id, dev.name))

        retList.sort(key=lambda tup: tup[1])
        return retList
