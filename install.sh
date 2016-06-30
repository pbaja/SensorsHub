#!/bin/bash

# Some variables
SERVICE_NAME="sensorshub"
DESCRIPTION="Web interface for gathering data from many sensors"
WORKING_DIR=$(cd $(dirname $0) && pwd)/

# Override name if argument is supplied
if [ $# -ne 0 ]; then
    echo "-> Using '"$1"' as service name"
    SERVICE_NAME=$1
fi

# Check if system is using systemd as init
if [[ ! $(file /sbin/init) == *"systemd"* ]]
then
    echo "-> Install script currently works only with systemd. Sorry."
    exit 1
fi

# Check if script is running with root
if [[ $EUID -ne 0 ]]; then
   echo "-> Root access is needed for installation process. Aborting."
   exit 1
fi

# Check if service is not installed
if [ -f "/etc/systemd/system/"$SERVICE_NAME".service" ]; then
    echo "-> Service is already installed. Stopping/removing old service."
    systemctl stop $SERVICE_NAME".service"
    rm "/etc/systemd/system/"$SERVICE_NAME".service"
fi

# Install dependencies
echo "-> Installing dependencies"

apt-get install python3 python3-pip > /dev/null
if [ $? -ne 0 ]; then
    echo "-> There was a problem with installing dependencies. apt-get command failed. Aborting."
    exit 1
fi

pip3 install cherrypy passlib markdown2 > /dev/null
if [ $? -ne 0 ]; then
    echo "-> There was a problem with installing dependencies: pip3 command failed. Aborting."
    exit 1
fi

# Configure permissions
echo "-> Configuring permissions"
chmod +x run.py

# Create service file
echo "-> Creating service"

if [ -f $SERVICE_NAME".service" ] ; then
    rm $SERVICE_NAME".service"
fi

echo "[Unit]" >> ${SERVICE_NAME}".service"
echo "Description="$DESCRIPTION >> $SERVICE_NAME".service"
echo "After=syslog.target" >> $SERVICE_NAME".service"
echo "" >> $SERVICE_NAME".service"
echo "[Service]" >> $SERVICE_NAME".service"
echo "Type=simple" >> $SERVICE_NAME".service"
echo "ExecStart="$WORKING_DIR"run.py" >> $SERVICE_NAME".service"
echo "PIDFile="$WORKING_DIR"sensorshub.pid" >> $SERVICE_NAME".service"
echo "WorkingDirectory="$WORKING_DIR >> $SERVICE_NAME".service"
echo "RestartSec=2" >> $SERVICE_NAME".service"
echo "Restart=on-abnormal" >> $SERVICE_NAME".service"

cp $SERVICE_NAME".service" "/etc/systemd/system/"$SERVICE_NAME".service"
if [ $? -ne 0 ]; then
    echo "Cannot copy service file. Aborting."
    rm $SERVICE_NAME".service"
    exit 1
fi

# Install service
echo "-> Installing and starting service"
systemctl daemon-reload
systemctl start $SERVICE_NAME".service"

# Cleanup unwanted files
echo "-> Cleaning up"
rm $SERVICE_NAME".service" 2> /dev/null
rm "LICENCE.md" 2> /dev/null
rm "README.md" 2> /dev/null
rm "CHANGELOG.md" 2> /dev/null
rm "version.json" 2> /dev/null

# Just for statistics, generate unique machine id and send it to server
# There is no sensitive data at all :)
PROCESSOR_ID=$(dmidecode -t 4 | grep ID | sed 's/.*ID://;s/ //g')
NETWORK_MAC=$(ifconfig | grep eth0 | awk '{print $NF}' | sed 's/://g')
MACHINEID=$(echo $PROCESSOR_ID$NETWORK_MAC | sha256sum | awk '{print $1}')

echo "$MACHINEID" > "machineid.txt"
wget "http://skew.tk/sensorshub?machineid="$MACHINEID"&status=0" -O /dev/null &>/dev/null

# Done!
echo "-> Installed successfully. SensorsHub will automatically start at system boot, and restart when crashed. Neat!"