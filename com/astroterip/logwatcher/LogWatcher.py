#
#  Name: LogWatcher
#  Version: 1.0
#  Author: Nicholas Jones
#  com.astroterip.logging.LogWatcher
#  Description: Monitor log files in a particular file system folder for any new occurrences of a piece of text.
#               When a match if found, a user specified batch file is executed.
#               The application is strictly readonly.

import argparse
import configparser
import os
import subprocess
import time
import threading
from subprocess import Popen

class LogWatcherConfig:
    def __init__(self, name, logFolder, logFileExtension, searchText, executionFile, eventName, inactivityMonitor, inactivitySeconds):
        self.name = name
        self.logFolder = logFolder
        self.logFileExtension = logFileExtension
        self.logSeachText = searchText
        self.executionFile = executionFile
        self.eventName = eventName
        self.inactivityMonitor = inactivityMonitor
        self.inactivitySeconds = inactivitySeconds
    # end def

    def getName(self):
        return self.name

# end class


class LogFile:
    def __init__(self, config, filename):
        self.config = config
        self.filename = filename
        self.logPosition = 0
        self.changed = False
        self.lastModified = ""
        self.size = -1
        self.timeLastMod = 0

    def updateFromOs(self):
        filePath = os.path.join(self.config.logFolder, self.filename)
        size = os.path.getsize(filePath)
        if (size != self.size):
            self.changed = True
        # end if
        self.size = os.path.getsize(filePath)
        self.lastModified = time.strftime('%Y%m%d%H%M%S', time.gmtime(os.path.getmtime(filePath)))
        self.timeLastMod = os.path.getmtime(filePath)

    # end def

    def printToStdio(self, text):
        datetimeStamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(datetimeStamp + " " + self.config.getName() + ": " + text)

    def getLastLineMatchingText(self, text, intialLoading):
        filePath = os.path.join(self.config.logFolder, self.filename)
        position = 0
        matchedLogText = ""


        with open(filePath, 'r') as f:
            for line in f:
                position = position + 1
                if position > self.logPosition or self.logPosition == 0:
                    if text in line:
                        if not intialLoading:
                            self.printToStdio("found matching text in log " + self.filename + " at position " + str(position))
                        # end if
                        matchedLogText = line
                    # end if
                # end if

            # end for loop

            self.logPosition = position

        # end with open file scope
        return matchedLogText
    # end def
# end class LogFile



class LogMatch:
    def __init__(self, dateTime: str, eventName: str, logText: str, logFileName: str):
        self.dateTime = dateTime
        self.logText = logText
        self.eventName = eventName
        self.logFileName = logFileName
    # end def
# end def

# class to list the log files that are present in the log folder.
class LogWatcher:
    def __init__(self, config: LogWatcherConfig):
        self.config = config
        self.logFileList = []

    def getExecutionFile(self):
        return self.config.executionFile
    # end def

    # this just cleans the in-memory references to log files
    # remove bookmarks of files that have been removed from the logging folder
    def cleanLogList(self):
        for logFile in self.logFileList:
            filePath = os.path.join(self.config.logFolder, logFile.filename)
            if not os.path.exists(filePath):
                self.printToStdio("log " + logFile.filename + " no longer exists, remove from the logWatch")
                self.logFileList.remove(logFile)
            # end if
        # end for
    # end def

    def printToStdio(self, text):
        datetimeStamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(datetimeStamp + " " + self.config.getName() + ": " + text)

    # scanLogs - check if there's any new text matches
    def scanLogsForMatch(self, initialLoad):
        self.cleanLogList()

        for filename in os.listdir(self.config.logFolder):
            filePath = os.path.join(self.config.logFolder, filename)


            if not os.path.isdir(filePath):
                if filePath.endswith(self.config.logFileExtension):
                    logFile = self.getFileInList(filename)



                    if not self.getFileInList(filename):
                        logFile = LogFile(self.config, filename)
                        self.logFileList.append(logFile)
                        self.printToStdio("add log file to scanning: " + filePath)
                    # end if not in list
                # end if
            # end if
        # end for loop

        minFileAge = 9999999

        for logFile in self.logFileList:
            currentFilePath = os.path.join(self.config.logFolder, logFile.filename)
            dateTimeStamp = time.strftime('%Y%m%d%H%M%S', time.gmtime(os.path.getmtime(currentFilePath)))


            # only bother scanning the file if it has been updated
            if (dateTimeStamp > logFile.lastModified):
                self.printToStdio("scan " + logFile.filename)
                matchedLogText = logFile.getLastLineMatchingText(self.config.logSeachText, initialLoad)
                if not initialLoad and len(matchedLogText) > 0:
                    logMatch = LogMatch(dateTimeStamp, self.config.eventName, matchedLogText, logFile.filename)
                    return logMatch
                # end if
            # end if
            logFile.updateFromOs()
            if self.config.inactivityMonitor:
                print("last modified " + str(logFile.timeLastMod) + " age in sec: " + str(time.time() - logFile.timeLastMod))
                if minFileAge > (time.time() - logFile.timeLastMod):
                    minFileAge = (time.time() - logFile.timeLastMod)
                # end if

            # end if
        # end if

        if self.config.inactivityMonitor:
            if minFileAge > self.config.inactivitySeconds:
                print("no change in folder " + self.config.logFolder + " for " + str(minFileAge) + " seconds")
            # end if
        # end if

        return None
    # end def

    # retrieve the logFile object from the logFileList
    def getFileInList(self, filename):
        for logFile in self.logFileList:
           if logFile.filename == filename:
               return logFile
           # end if
        # end for
        return None
    # end def
# end class



class LogWatcherConfigMgr:
    def __init__(self, configPath):
        self.configPath = configPath
        self.config = configparser.ConfigParser()
        self.config.read(self.configPath)
        self.logWatchLocations = []
        self.scanInterval = self.config["general"]["scanInterval"]

        try:
            for sectionNumber in range(1, 100):
                sectionName = "logwatch_" + str(sectionNumber)
                name = self.config[sectionName]['name']
                print("loading " + name)
                logFolder = self.config[sectionName]['folder']
                logFileExtension = self.config[sectionName]['fileExtension']
                logSearchText = self.config[sectionName]['searchText']
                executionFile = self.config[sectionName]['executionFile']
                eventName = self.config[sectionName]['eventName']
                inactivityMonitor = self.config[sectionName]['inactivityMonitor']
                inactivitySeconds = int(self.config[sectionName]['inactivitySeconds'])


                logWatcherConfig = LogWatcherConfig(name, logFolder, logFileExtension, logSearchText, executionFile, eventName, inactivityMonitor, inactivitySeconds)
                self.logWatchLocations.append(logWatcherConfig)
            # end for
        except (KeyError):
            print("no more config")

    # end def

    def getConfig(self):
        return self.logWatchLocations;
    # end def

    def getScanInterval(self) -> int:
        return self.scanInterval
    # end if

# end class


def eggTimer():
    global eggsAreReady
    eggsAreReady = True
# end def


def main(args):
    configMgr = LogWatcherConfigMgr("logWatcher.ini")

    configArray = configMgr.getConfig();
    logWatcherArray = []

    # Iterate through the config to create the log watchers
    for config in configArray:
        logWatcher = LogWatcher(config)
        # initial load to by-pass any existing matches
        logWatcher.scanLogsForMatch(True)
        logWatcherArray.append(logWatcher)
    # end for

    global eggsAreReady
    eggsAreReady = False
    t = threading.Timer(int(configMgr.scanInterval), eggTimer)
    t.start()

    while True:
        if eggsAreReady:
            for logWatcher in logWatcherArray:
                logMatch = logWatcher.scanLogsForMatch(False)
                if logMatch is not None:
                    subprocess.call([logWatcher.getExecutionFile(), logMatch.logText])
                # end if



            # end if

            t.cancel()
            eggsAreReady = False

            # restart
            t = threading.Timer(int(configMgr.scanInterval), eggTimer)
            t.start()
        # end if

        time.sleep(2)
    # end while
# end def main


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Log watch-dog to lookout for text and call a .bat file if it appears')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0')

    args = parser.parse_args()

    main(args)
# end if
