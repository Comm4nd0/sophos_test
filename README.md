## Sophos Test

### Setup

Edit setting.cfg, specifically 'monitor_dir' and 'output_dir' to real directories you want to monitor.

pip install -r requirements

### run

python3.8 monitor.py

python3.8 decode.py


#### Additions
* Threading the file handler
* Combine FileMonitor and Decode
* Add disallowed mime types
* More error handling
* PII method as its own class
* look for other data serialisation types e.g. yaml, xml
* look for other keys which might hold PII
