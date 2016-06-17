# SensorsHub
**Work in progress! Current version is super alpha, many features needs to be added, but, basic functionality already works like a charm :)**  
  
![Dark theme](http://i.imgur.com/13W70j7.png)  
![Light theme](http://i.imgur.com/2Po0MSb.png)  

## Features  
 - Light/Dark theme  
 - Averaging data in charts for better readability  
 - Multiple sensors can send multiple fields  
 - Each field is fully configurable, including icon, color, unit, display name.
 - Irregular data is correctly displayed on charts

## Installation  
 - Install dependencies: `sudo apt-get install python3 pip3 git-core`
 - Install requirements: `sudo pip3 install cherrypy passlib`
 - Download code: `git clone https://github.com/SkewPL/SensorsHub.git`
 - Add executable flag `cd SensorsHub && chmod +x run.py`
 - Run using `./run.py`
 - Go to the `http://yourip:5000` website and configure everything.  
  
## TODO  
 - Update home page field values with javascript  
 - Make pairing with sensors more easly
 - Allow guests to change theme to dark/light  
 - Better Sensros page, more readable  
 - Create Log page, well, implement logging first.  
 - Create About page  
 - Multiple accounts with permissions  
 - Allow sensors to send Field descriptions and display names when creating them  
 - Sending data TO sensors  
 - Multiple field types: bool, int, float, percent  
 - Comparing data for multiple periods from multiple fields
