# ESPHome_Logger
Write local logfiles from ESPHome log output

### Installation ###
1) Create/upload the three files (Dockerfile, run.py and config.yaml) to /addons/local_esphome_logger
2) Adapt the settings in run.py to you needs, currently there is a logrotion implemented, which rotate logs after either 2000 lines or a size of 500 KB. It will keep 5 logfiles. Those Settings can be adapted in lines 27 - 29.
3) Settings -> Apps -> Install App
4) Local Apps (Add-ons) -> install

### Configuration ###
1) Configure name, host (can be either IP, if static, or mDNS name) and encryption Key (which is the api key form your secrets.yaml)
2) Save
3) Restart the Add-On

### Usage ###
The Add-On writes all outout from the configured ESPHome devices in local logfiles under /share/esphome_logs. You can download those files via Samba or SCP, depending on what options you have to connect to your HA.
You could also symlink the folder to /homeassistant/esphome/logs and access it via the VSCode Add-On.

### Disclaimer ###
This Add-On has been created with the help of AI, but it does what it should.
