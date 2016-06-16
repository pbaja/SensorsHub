#!/bin/sh

# This script will keep your executable running in background forever
#
# Just configure in below and run me with "start" parameter. Whoila! Your executable is running in background.
# If you want to stop it, just run me with "stop" parameter.
# If you want to check status, run with "status" parameter.
# If you want to restart your executable (in the hard way) run me with "kill" parameter.


#Name of pid file that will be created, must be unique
name="sensorshub"
#Working directory (Needs / at the end)
directory="$(cd $(dirname $0) && pwd)/"
#Command to execute (it will be reexecuted when crashed/exited)
executable="python3 run.py"

#Checking if watchdog is already running
if [ -e "$name.pid" ]; then
	pid=$(cat "$name.pid")
	if ! (ps -p $(cat "$name.pid") > /dev/null)
	then
		unset pid
		rm "$name.pid"
	fi
fi

#Checking if executable is already working
if [ -e "e$name.pid" ]; then
	epid=$(cat "e$name.pid")
	if ! (ps -p $(cat "e$name.pid") > /dev/null)
	then
		unset epid
		rm "e$name.pid"
	fi
fi

case "$1" in
	start)
		if [ $pid ]; then
			echo "Watchdog already running"
		else
			echo "Starting watchdog in background"
			cd $directory
			$directory$(basename "$0") run &
			echo $! > "$name.pid"
		fi
		;;
	status)
		if [ $pid ]; then
			echo "Watchdog running"
		else
			echo "Watchdog not running"
		fi

		if [ $epid ]; then
			echo "Executable running"
		else
			echo "Executable not running"
		fi
		;;
	stop)
		if [ $pid ]; then
			kill $pid
			rm "$name.pid"
			echo "Killed watchdog"
		else
			echo "Watchdog not running"
		fi

		if [ $epid ]; then
			kill $(cat "e$name.pid")
			rm "e$name.pid"
			echo "Killed executable"
		else
			echo "Executable not running"
		fi
		;;
	kill)
		if [ $epid ]; then
			kill $(cat "e$name.pid")
			rm "e$name.pid"
			echo "Killed executable, it should be restarted by watchdog"
		else
			echo "Executable not running"
		fi
		;;
	run)
		cd $directory
		while true
		do
			if ! [ -e "e$name.pid" ] || ! (ps -p $(cat "e$name.pid") > /dev/null)
			then
				echo "Spawning $name"
				$executable >> "$name.log" 2>&1 &
				echo $! > "e$name.pid"
			fi
			sleep 1
		done
		;;
	*)
		echo ""
		echo "Avaliable arguments:"
		echo ""
		echo "start - Start process in background"
		echo "stop - Kill process in background and watchdog"
		echo "status - Check if watchdog and process are running"
		echo "kill - Kill only process in background, watchdog should restart it shortly"
		echo ""
		;;
esac
exit 0