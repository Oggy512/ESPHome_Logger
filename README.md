# ESPHome_Logger
Write local logfiles from ESPHome log output

### Installation ###
1) Create/upload the three files (Dockerfile, run.py and config.yaml) to /addons/local_esphome_logger (You need the option to connect to your HA via SSH)
2) Adapt the settings in run.py to your needs, currently there is a logrotion implemented, which rotate logs after either 2000 lines or a size of 500 KB. It will keep 5 logfiles. Those Settings can be adapted in lines 27 - 29.
3) In HA: Settings -> Apps -> Install App
4) Local Apps (Add-ons) -> ESPHome Logger -> install

### Configuration ###
1) Configure name, host (can be either IP, if static, or mDNS name) and encryption Key (which is the api key form your secrets.yaml)
2) Save
3) Restart the Add-On

### Usage ###
The Add-On writes all output from the configured ESPHome devices in local logfiles under /share/esphome_logs. It also removes the ANSI colorcodes for better reading. You can download the logfiles via Samba or SCP, depending on what options you have to connect to your HA.
You could also symlink the folder to /homeassistant/esphome/logs and access it via the VSCode Add-On.

### Disclaimer ###
This Add-On has been created not only, but with the help of AI. So far I couldn't find any issues, but let me know, if you do.
