#!/usr/bin/python3.4
import os, libs.core

# Save current pid to file
with open("sensorshub.pid","w") as pidfile:
    pidfile.write(str(os.getpid()))

# Begin starting up
libs.core.Core()