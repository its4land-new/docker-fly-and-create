import os
import sys

from publishandshare.toolwrapper.wrapper.configuration import Configuration
from publishandshare.toolwrapper.wrapper.basicprocessing import BasicProcessing

sys.path.append(os.path.split(__file__)[0])

def printInfo (process, parameters):
    print("Project: {0}".format(process.projectName()))
    print("Tool: {0}".format(process.toolName()))
    print("Tool Version: {0}".format(process.toolVersion()))
    print("Entry Point: {0}".format(process.entryPointName()))
    print("Parameters: {0}".format(str(parameters)))

