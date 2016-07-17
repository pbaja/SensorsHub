![SensorsHub](http://i.imgur.com/tBlr8TD.png)  
# SensorsHub  
**Documentation: [Wiki page](https://github.com/SkewPL/SensorsHub/wiki)**  
**Changelog: [Here](https://github.com/SkewPL/SensorsHub/blob/master/changelog.md)**  
**Live demo: [Here](http://akwaria.ml)** (Polish language)
  
## Features  
 - Light/Dark theme  
 - Averaging data from database in charts for better readability  
 - Multiple sensors can send multiple fields (temperature, humidity, battery, etc.)  
 - Displaying data from exact date and time
 - Each field is fully configurable, including icon, color, unit, display name
 - Irregular data is correctly displayed on charts
 - Very simple API, super user and developer friendly
  
## Installation  
 - Download code: `wget https://github.com/SkewPL/SensorsHub/archive/master.zip`
 - Unzip and cd: `unzip master.zip && cd SensorsHub-master`
 - Run installer: `chmod +x install.sh && sudo ./install.sh`

If you want to change default server port from 80 to anything else, edit `config.json` and restart service using:  
`sudo systemctl restart sensorshub.service`
  
If you want to change directory/rename it after installation, just rerun install.sh to update service.  
  
## Screenshots  
#### Home page  
![Home page](http://i.imgur.com/gNqCmVM.png)  
#### Single sensor view  
![Single sensor](http://i.imgur.com/UQIUI1u.png)  
#### Settings home page  
![Settings page](http://i.imgur.com/sahXFFh.png)  ``
#### Sensors list  
![Sensors list](http://i.imgur.com/4HsapW4.png)
  
## TODO  
H - High priority, currently working on that  
M - Medium priority  
L - Low priority  
F - Future function, we need to implement some others first  
  
 - [ ] **H** Multiple field types: bool, int, float, percent  
 - [ ] **H** Better auto update function from website
 - [ ] **M** Basic triggers (for e.g. Send email when temperature is greater than x)
 - [ ] **M** Sending data to sensors (via sockets or ajax)  
 - [ ] **M** Multiple accounts with permissions  
 - [ ] **M** Language selection for guests
 - [ ] **L** More options for home charts
 - [ ] **L** Better and more documentation
 - [ ] **L** Allow guests to change theme to dark/light  
 - [ ] **L** PIN protected home page  
 - [ ] **L** Comparing data for multiple periods from multiple fields  
 - [ ] **L** More API functions for developers (Getting data from database, modifying)  
 - [ ] **F** Advanced Triggers (for e.g. close window, when temperature inside is lower than outside)
 - [ ] **F** Plugins system
 - [x] Multiple languages support
 - [x] Update home page field values with javascript  
 - [x] Make pairing with sensors more easly
 - [x] Better Sensors page, more readable  
 - [x] Create Log page, well, implement logging first.  
 - [x] Create About page  
 - [x] Allow sensors to send Field descriptions and display names when creating them  
 - [x] Auto update
