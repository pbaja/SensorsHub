![SensorsHub](http://i.imgur.com/tBlr8TD.png)  
# SensorsHub  
**Current version: ALPHA**  
  
## Features  
 - Light/Dark theme  
 - Averaging data from database in charts for better readability  
 - Multiple sensors can send multiple fields (temperature, humidity, battery, etc.)  
 - Displaying data from exact date and time
 - Each field is fully configurable, including icon, color, unit, display name
 - Irregular data is correctly displayed on charts
 - Very simple API, super user and developer friendly
  
## Installation  
 - Install dependencies: `sudo apt-get install python3 pip3 git-core`
 - Install requirements: `sudo pip3 install cherrypy passlib`
 - Download code: `git clone https://github.com/SkewPL/SensorsHub.git`
 - Add executable flag `cd SensorsHub && chmod +x run.py`
 - Run using `./run.py` or `python3 run.py`
 - Go to the `http://yourip` and configure everything.  
  
## Documentation  
Documentation including setting up sensors is available at [Wiki page](https://github.com/SkewPL/SensorsHub/wiki)
  
## Screenshots  
#### Home page  
![Home page](http://i.imgur.com/gNqCmVM.png)  
#### Single sensor view  
![Single sensor](http://i.imgur.com/UQIUI1u.png)  
#### Settings home page  
![Settings page](http://i.imgur.com/sahXFFh.png)  
#### Sensors list  
![Sensors list](http://i.imgur.com/4HsapW4.png)
  
## TODO  
 - [ ] Multiple languages support
 - [ ] Update home page field values with javascript  
 - [x] Make pairing with sensors more easly
 - [ ] Allow guests to change theme to dark/light  
 - [x] Better Sensors page, more readable  
 - [x] Create Log page, well, implement logging first.  
 - [ ] Create About page  
 - [ ] Multiple accounts with permissions  
 - [x] Allow sensors to send Field descriptions and display names when creating them  
 - [ ] Sending data TO sensors (a.k.a. switches)  
 - [ ] Multiple field types: bool, int, float, percent  
 - [ ] Comparing data for multiple periods from multiple fields  
 - [ ] More API functions for developers (Getting data from database, modifying)  
 - [ ] Auto update
